import sys
import os

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Test imports
try:
    sys.path.insert(0, 'backend/telegram_bot/src')
    from config.settings import BOT_TOKEN
    print("✅ Settings import successful")
    print(f"BOT_TOKEN exists: {'Yes' if BOT_TOKEN else 'No'}")
except Exception as e:
    print(f"❌ Settings import failed: {e}")

try:
    from bot.trading_bot import TradingBot
    print("✅ TradingBot import successful")
except Exception as e:
    print(f"❌ TradingBot import failed: {e}")