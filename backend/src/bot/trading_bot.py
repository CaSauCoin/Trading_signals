# src/bot/trading_bot.py
import logging
import os
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from telegram import Update
from .services.analysis_service import BotAnalysisService
from .services.scheduler_service import SchedulerService
from .services.scanner_service import MarketScannerService 
from .handlers import command_handlers, callback_handlers, message_handlers, error_handlers
from .formatters import format_analysis_result, format_scanner_notification 

logger = logging.getLogger(__name__)


def notification_job(context: CallbackContext):
    """Công việc được lập lịch, chạy mỗi phút để kiểm tra và gửi thông báo."""
    bot = context.bot
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']
    analysis_service: BotAnalysisService = context.bot_data['analysis_service']
    
    all_watchlists = scheduler_service.get_all_watchlists()
    logger.info(f"Chạy job thông báo cho {len(all_watchlists)} người dùng.")
    
    for user_id, watchlist in all_watchlists.items():
        for item in watchlist:
            symbol = item['symbol']
            timeframe = item['timeframe']
            
            logger.info(f"Phân tích {symbol} ({timeframe}) cho user {user_id}")
            result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
            
            if not result.get('error'):
                signal = result.get('analysis', {}).get('signal')
                # Chỉ gửi thông báo nếu có tín hiệu MUA hoặc BÁN
                if signal in ["MUA", "BÁN"]:
                    message_text = "🔔 **Cảnh báo Watchlist** 🔔\n\n" + format_analysis_result(result)
                    try:
                        bot.send_message(chat_id=user_id, text=message_text, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Lỗi khi gửi thông báo tới user {user_id}: {e}")

def market_scanner_job(context: CallbackContext):
    """
    Job quét thị trường mỗi 4 giờ, tìm các tín hiệu đảo chiều.
    """
    bot = context.bot
    scanner_service: MarketScannerService = context.bot_data['scanner_service']
    previous_states = context.bot_data.get('scanner_states', {})
    
    logger.info("--- BẮT ĐẦU QUÉT THỊ TRƯỜNG (4H) ---")
    
    flipped_tokens, new_states = scanner_service.run_scan(previous_states, timeframe='4h')
    
    # Cập nhật lại state cho lần chạy tiếp theo
    context.bot_data['scanner_states'] = new_states
    
    logger.info(f"--- KẾT THÚC QUÉT, TÌM THẤY {len(flipped_tokens)} TÍN HIỆU ĐẢO CHIỀU ---")

    # Nếu có tín hiệu đảo chiều, gửi thông báo đến admin
    if flipped_tokens:
        admin_id = os.getenv("ADMIN_CHAT_ID")
        if admin_id:
            message = format_scanner_notification(flipped_tokens, '4h')
            try:
                bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo quét thị trường: {e}")
        else:
            logger.warning("ADMIN_CHAT_ID chưa được cài đặt, không thể gửi thông báo quét.")


class TradingBot:
    def __init__(self, token: str):
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self._setup_bot_data()
        self._setup_handlers()
        self._setup_jobs() 

    def _setup_bot_data(self):
        """Khởi tạo và đưa các services vào context của bot."""
        self.dispatcher.bot_data['analysis_service'] = BotAnalysisService()
        self.dispatcher.bot_data['scheduler_service'] = SchedulerService()
        self.dispatcher.bot_data['scanner_service'] = MarketScannerService()
        # Khởi tạo user_states
        self.dispatcher.bot_data['user_states'] = {}
        self.dispatcher.bot_data['scanner_states'] = {} 
        
    def _setup_handlers(self):
        """Đăng ký tất cả các handlers cho bot."""
        # Command Handlers
        self.dispatcher.add_handler(CommandHandler('start', command_handlers.start_command))
        self.dispatcher.add_handler(CommandHandler('analysis', command_handlers.analysis_command))
        self.dispatcher.add_handler(CommandHandler('watchlist', command_handlers.watchlist_command))
        # Callback Query Handler
        self.dispatcher.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))
        
        # Message Handler
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handlers.handle_message))
        
        # Error Handler
        self.dispatcher.add_error_handler(error_handlers.error_handler)

    def _setup_jobs(self):
        """Lập lịch cho các công việc chạy nền."""
        job_queue = self.updater.job_queue
        # Chạy job mỗi 60 giây
        job_queue.run_repeating(notification_job, interval=4800, first=10)
        job_queue.run_repeating(market_scanner_job, interval=12600, first=20)

    def run(self):
        """Bắt đầu chạy bot."""
        self.updater.start_polling()
        self.updater.idle()
