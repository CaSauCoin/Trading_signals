import sys
import os
import logging

# Configure logging first
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add the telegram_bot/src directory to Python path
telegram_src_path = os.path.join(os.path.dirname(__file__), 'telegram_bot', 'src')
sys.path.insert(0, telegram_src_path)

# Also add the bot directory specifically
bot_path = os.path.join(telegram_src_path, 'bot')
sys.path.insert(0, bot_path)

try:
    from config.settings import BOT_TOKEN
    from bot.trading_bot import TradingBot
except ImportError as e:
    logger.error(f"Import error: {e}")
    print(f"Available paths: {sys.path[:5]}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Files in current dir: {os.listdir('.')}")
    sys.exit(1)

def main():
    try:
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python path: {sys.path[:3]}")
        
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found in environment variables")
            sys.exit(1)
            
        logger.info("Initializing bot...")
        bot = TradingBot(BOT_TOKEN)
        
        logger.info("🤖 Bot is starting...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()