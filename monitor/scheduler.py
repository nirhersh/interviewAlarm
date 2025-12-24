import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot
from telegram.error import TelegramError
from database.db import Database
from scraper.needle_scraper import scrape_needle_page, NeedleScraperError
from bot import messages

logger = logging.getLogger(__name__)


class MonitorScheduler:
    def __init__(self, bot: Bot, db: Database, check_interval_minutes: int = 5):
        """
        Initialize the monitoring scheduler

        Args:
            bot: Telegram Bot instance
            db: Database instance
            check_interval_minutes: How often to check for new slots (default 5 minutes)
        """
        self.bot = bot
        self.db = db
        self.check_interval_minutes = check_interval_minutes
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the monitoring scheduler"""
        # Add job to check URLs
        self.scheduler.add_job(
            self.check_all_urls,
            trigger=IntervalTrigger(minutes=self.check_interval_minutes),
            id='check_urls',
            name='Check all tracked URLs for new slots',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"Monitoring scheduler started (checking every {self.check_interval_minutes} minutes)")

    def stop(self):
        """Stop the monitoring scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Monitoring scheduler stopped")

    async def check_all_urls(self):
        """Check all tracked URLs for new time slots"""
        try:
            # Get all tracked URLs
            tracked_urls = self.db.get_all_tracked_urls()

            if not tracked_urls:
                logger.debug("No URLs to monitor")
                return

            logger.info(f"Checking {len(tracked_urls)} tracked URLs for new slots...")

            # Check each URL
            for tracked_url in tracked_urls:
                try:
                    await self.check_url(tracked_url)
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(
                        f"Error checking URL {tracked_url['url']}: {e}",
                        exc_info=True
                    )
                    continue

            logger.info("Finished checking all URLs")

        except Exception as e:
            logger.error(f"Error in check_all_urls: {e}", exc_info=True)

    async def check_url(self, tracked_url: dict):
        """
        Check a single URL for new time slots

        Args:
            tracked_url: Dictionary with id, user_id, url, company_name
        """
        url = tracked_url['url']
        tracked_url_id = tracked_url['id']
        user_id = tracked_url['user_id']
        company_name = tracked_url['company_name']

        try:
            # Scrape current slots
            result = scrape_needle_page(url)
            current_slots = result['slots']

            # Get new slots by comparing with DB
            new_slots = self.db.get_new_slots(tracked_url_id, current_slots)

            if new_slots:
                logger.info(
                    f"Found {len(new_slots)} new slot(s) for {company_name} (user {user_id})"
                )

                # Save new slots to DB
                self.db.save_time_slots(tracked_url_id, new_slots, is_notified=False)

                # Send notification to user
                await self.send_new_slot_notification(
                    user_id,
                    company_name,
                    url,
                    new_slots
                )

                # Mark slots as notified
                start_times = [slot['start_time'] for slot in new_slots]
                self.db.mark_slots_notified(tracked_url_id, start_times)

            else:
                logger.debug(f"No new slots for {company_name} (user {user_id})")

        except NeedleScraperError as e:
            logger.warning(f"Scraping error for {url}: {e}")
            # Don't notify user for scraping errors during monitoring
            # They already know the URL is tracked

        except Exception as e:
            logger.error(f"Unexpected error checking {url}: {e}", exc_info=True)

    async def send_new_slot_notification(
        self,
        user_id: int,
        company_name: str,
        url: str,
        new_slots: list
    ):
        """
        Send notification to user about new slots

        Args:
            user_id: Telegram user ID
            company_name: Name of the company
            url: Interview scheduling URL
            new_slots: List of new time slots
        """
        try:
            message = messages.format_new_slot_notification(
                company_name,
                url,
                new_slots
            )

            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

            logger.info(f"Sent notification to user {user_id} about {len(new_slots)} new slot(s)")

        except TelegramError as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}", exc_info=True)
