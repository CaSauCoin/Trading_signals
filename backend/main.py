import sys
import os

# Add the telegram_bot/src directory to Python path
telegram_src_path = os.path.join(os.path.dirname(__file__), 'telegram_bot', 'src')
sys.path.insert(0, telegram_src_path)

# Also add the bot directory specifically
bot_path = os.path.join(telegram_src_path, 'bot')
sys.path.insert(0, bot_path)

from config.settings import BOT_TOKEN
from bot.trading_bot import TradingBot

def main():
    print(f"Python path: {sys.path[:3]}")  # Debug line
    bot = TradingBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()