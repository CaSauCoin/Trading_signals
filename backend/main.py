import logging
import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv() 

# Import từ source code của bạn một cách tự nhiên
from src.bot.trading_bot import TradingBot

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Hàm chính để khởi chạy bot."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN không được tìm thấy trong biến môi trường! Vui lòng tạo file .env.")
        return

    try:
        logger.info("Khởi tạo bot...")
        bot = TradingBot(bot_token)
        
        logger.info("🤖 Bot đang bắt đầu...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng khi chạy bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()
