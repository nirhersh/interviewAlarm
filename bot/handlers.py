from telegram import Update
from telegram.ext import ContextTypes
from database.db import Database
from scraper.needle_scraper import scrape_needle_page, NeedleScraperError
from bot import messages
import logging

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        messages.format_welcome_message(),
        parse_mode='Markdown'
    )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /add <url> command
    Scrapes the URL, saves to DB with initial slots
    """
    user_id = update.effective_user.id

    # Check if URL was provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            messages.format_error_message(
                "Please provide a URL.\n\nUsage: /add <url>\n\n"
                "Example:\n/add https://needle.co.il/candidate-slots/1d22a516-a3a5-4f9a-a2c2-896eddea945e"
            )
        )
        return

    url = context.args[0]

    # Send "processing" message
    processing_msg = await update.message.reply_text("Fetching interview page...")

    try:
        # Scrape the page
        result = scrape_needle_page(url)
        company_name = result['company_name']
        slots = result['slots']

        # Get database instance from context
        db: Database = context.bot_data['db']

        # Add URL to database
        tracked_url_id = db.add_tracked_url(user_id, url, company_name)

        if tracked_url_id is None:
            # URL already tracked
            await processing_msg.edit_text(
                messages.format_error_message("You're already tracking this URL!")
            )
            return

        # Save initial slots (marked as already notified)
        if slots:
            db.save_time_slots(tracked_url_id, slots, is_notified=True)

        # Send summary
        summary = messages.format_slot_summary(company_name, url, slots)
        await processing_msg.edit_text(summary, parse_mode='Markdown')

        logger.info(f"User {user_id} added URL: {url} ({company_name})")

    except NeedleScraperError as e:
        await processing_msg.edit_text(
            messages.format_error_message(str(e))
        )
        logger.error(f"Scraping error for {url}: {e}")

    except Exception as e:
        await processing_msg.edit_text(
            messages.format_error_message(f"An unexpected error occurred: {str(e)}")
        )
        logger.error(f"Unexpected error in add_command: {e}", exc_info=True)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command - show all tracked URLs"""
    user_id = update.effective_user.id

    try:
        # Get database instance
        db: Database = context.bot_data['db']

        # Get user's tracked URLs
        tracked_urls = db.get_user_tracked_urls(user_id)

        # Format and send
        message = messages.format_tracked_urls_list(tracked_urls)
        await update.message.reply_text(message, parse_mode='Markdown')

        logger.info(f"User {user_id} listed {len(tracked_urls)} tracked URLs")

    except Exception as e:
        await update.message.reply_text(
            messages.format_error_message(f"Failed to retrieve tracked URLs: {str(e)}")
        )
        logger.error(f"Error in list_command: {e}", exc_info=True)


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove <url> command"""
    user_id = update.effective_user.id

    # Check if URL was provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            messages.format_error_message(
                "Please provide a URL to remove.\n\nUsage: /remove <url>"
            )
        )
        return

    url = context.args[0]

    try:
        # Get database instance
        db: Database = context.bot_data['db']

        # Remove the URL
        removed = db.remove_tracked_url(user_id, url)

        if removed:
            await update.message.reply_text(
                messages.format_success_message(
                    f"Successfully stopped tracking the URL.\n\n{url}"
                )
            )
            logger.info(f"User {user_id} removed URL: {url}")
        else:
            await update.message.reply_text(
                messages.format_error_message("URL not found in your tracked list.")
            )

    except Exception as e:
        await update.message.reply_text(
            messages.format_error_message(f"Failed to remove URL: {str(e)}")
        )
        logger.error(f"Error in remove_command: {e}", exc_info=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await start_command(update, context)
