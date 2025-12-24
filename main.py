#!/usr/bin/env python3
"""
InterviewAlarm - Telegram Bot for monitoring interview scheduling pages

This bot monitors needle.co.il interview scheduling pages and notifies users
when new time slots become available.
"""

import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import Config
from database.db import Database
from monitor.scheduler import MonitorScheduler
from bot.handlers import (
    start_command,
    add_command,
    list_command,
    remove_command,
    help_command,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """
    Post-initialization callback
    Called after the bot is set up but before it starts
    """
    # Initialize database
    db = Database(Config.DATABASE_PATH)
    application.bot_data['db'] = db

    # Initialize and start monitoring scheduler
    scheduler = MonitorScheduler(
        bot=application.bot,
        db=db,
        check_interval_minutes=Config.CHECK_INTERVAL_MINUTES
    )
    scheduler.start()
    application.bot_data['scheduler'] = scheduler

    logger.info("Bot initialized successfully")


async def post_shutdown(application: Application):
    """
    Post-shutdown callback
    Called when the bot is shutting down
    """
    # Stop the scheduler
    if 'scheduler' in application.bot_data:
        scheduler = application.bot_data['scheduler']
        scheduler.stop()

    logger.info("Bot shutdown complete")


def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create the Application
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("remove", remove_command))

    logger.info("Command handlers registered")

    # Start the bot
    logger.info("Starting InterviewAlarm bot...")
    logger.info(f"Monitoring interval: {Config.CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"Database: {Config.DATABASE_PATH}")

    # Run the bot until Ctrl+C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
