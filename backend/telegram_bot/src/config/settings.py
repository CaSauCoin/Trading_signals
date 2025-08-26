from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Analysis Configuration
WATCHLIST_LIMIT = int(os.getenv('WATCHLIST_LIMIT', 5))
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', 1))  # hours

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# File Storage Configuration
DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
WATCHLIST_FILE = DATA_DIR / 'watchlists.json'
USER_STATE_FILE = DATA_DIR / 'user_states.json'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Scheduler Configuration
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", 3600))  # 1 hour in seconds

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
    WATCHLIST_FILE = Path("user_watchlists.json")
    LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
    SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", 3600))  # Default to 1 hour
    MAX_WATCHLIST_ITEMS = int(os.getenv("MAX_WATCHLIST_ITEMS", 5))  # Default to 5 items per user

    @staticmethod
    def init_app(app):
        pass  # Additional app initialization can be done here if needed

# Other settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'