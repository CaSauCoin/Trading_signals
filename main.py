import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv() 

# Import from your source code naturally
from src.bot.trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main function to start the bot."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables! Please create .env file.")
        return

    try:
        logger.info("Initializing bot...")
        bot = TradingBot(bot_token)
        
        logger.info("🤖 Bot is starting...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Critical error running bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()