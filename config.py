import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""

    # Telegram Bot Token (required)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Database path (optional, defaults to interview_alarm.db in current directory)
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'interview_alarm.db')

    # Check interval in minutes (optional, defaults to 5)
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '5'))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is not set. "
                "Please set it in .env file or environment variables.\n"
                "Get your token from @BotFather on Telegram."
            )

        if cls.CHECK_INTERVAL_MINUTES < 1:
            raise ValueError("CHECK_INTERVAL_MINUTES must be at least 1")

        return True
