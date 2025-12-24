# InterviewAlarm Bot

A Telegram bot that monitors needle.co.il interview scheduling pages and notifies you when new time slots become available.

## Features

- Track multiple interview scheduling URLs
- Automatic monitoring every 5 minutes
- Instant Telegram notifications when new slots appear
- Simple command interface
- Persistent storage with SQLite

## Prerequisites

- Python 3.8 or higher
- Conda environment (myenv)
- Telegram account
- Google Chrome or Chromium browser (for web scraping)

### Installing Chrome/Chromium

**On Ubuntu/Debian/WSL:**
```bash
sudo apt-get update
sudo apt-get install -y chromium-browser
```

**Or install Google Chrome:**
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb
```

## Installation

### 1. Set up Conda Environment

```bash
conda activate myenv
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` to create a new bot
3. Follow the prompts to set a name and username for your bot
4. Copy the bot token you receive

### 4. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your bot token:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Usage

### Starting the Bot

```bash
python main.py
```

The bot will start and begin monitoring tracked URLs every 5 minutes.

### Telegram Commands

Open your bot on Telegram and use these commands:

- `/start` - Show welcome message and help
- `/add <url>` - Start tracking a needle.co.il interview page
- `/list` - Show all your tracked URLs
- `/remove <url>` - Stop tracking a URL
- `/help` - Show help message

### Example Workflow

1. **Start the bot:**
   ```
   /start
   ```

2. **Add a URL to track:**
   ```
   /add https://needle.co.il/candidate-slots/1d22a516-a3a5-4f9a-a2c2-896eddea945e
   ```

   The bot will:
   - Scrape the page
   - Show you current available slots
   - Start monitoring for new slots

3. **View your tracked URLs:**
   ```
   /list
   ```

4. **Get notifications:**
   - The bot checks every 5 minutes
   - When new slots appear, you'll receive an instant notification
   - The notification includes company name, new slots, and the link

5. **Remove a URL:**
   ```
   /remove https://needle.co.il/candidate-slots/1d22a516-a3a5-4f9a-a2c2-896eddea945e
   ```

## Project Structure

```
interviewAlarm/
├── bot/
│   ├── handlers.py          # Command handlers
│   └── messages.py          # Message formatting
├── scraper/
│   └── needle_scraper.py    # Web scraping logic
├── database/
│   └── db.py                # Database operations
├── monitor/
│   └── scheduler.py         # Background monitoring
├── main.py                  # Application entry point
├── config.py                # Configuration
├── requirements.txt         # Dependencies
└── .env                     # Environment variables
```

## Configuration

You can customize the bot behavior in `.env`:

```bash
# Required: Your Telegram bot token
TELEGRAM_BOT_TOKEN=your_token_here

# Optional: Database file path (default: interview_alarm.db)
DATABASE_PATH=interview_alarm.db

# Optional: Check interval in minutes (default: 5)
CHECK_INTERVAL_MINUTES=5
```

## How It Works

1. **User adds URL:** Bot scrapes the page and saves current slots to database
2. **Background monitoring:** Every 5 minutes, bot checks all tracked URLs
3. **Comparison:** Compares current slots with database slots
4. **Notification:** If new slots found, sends Telegram notification
5. **Update database:** Saves new slots to prevent duplicate notifications

## Troubleshooting

### Bot doesn't respond
- Make sure the bot is running (`python main.py`)
- Check that your bot token is correct in `.env`
- Verify you started a conversation with the bot on Telegram

### Scraping errors
- Ensure the URL is a valid needle.co.il candidate-slots URL
- Check your internet connection
- The page structure may have changed - contact maintainer

### Database errors
- Check file permissions for `interview_alarm.db`
- Make sure the database isn't locked by another process

## Stopping the Bot

Press `Ctrl+C` in the terminal where the bot is running.

## Logs

The bot logs important events to console. Logging includes:
- Bot startup and shutdown
- URLs added/removed
- New slots detected
- Errors and warnings

## Support

For issues or questions, open an issue on the GitHub repository.

## License

This project is provided as-is for personal use.
