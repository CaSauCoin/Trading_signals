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

# --- CÁC HÀM JOB ---
def notification_job(context: CallbackContext):
    # ... (Giữ nguyên job cho watchlist)
    pass # Giữ nguyên logic cũ

def market_scanner_job(context: CallbackContext):
    """
    Job quét thị trường, tìm tín hiệu đảo chiều và gửi cho subscribers.
    """
    bot = context.bot
    scanner_service: MarketScannerService = context.bot_data['scanner_service']
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']
    previous_states = context.bot_data.get('scanner_states', {})
    
    logger.info("--- BẮT ĐẦU QUÉT THỊ TRƯỜNG (4H) ---")
    flipped_tokens, new_states = scanner_service.run_scan(previous_states, timeframe='4h')
    context.bot_data['scanner_states'] = new_states
    logger.info(f"--- KẾT THÚC QUÉT, TÌM THẤY {len(flipped_tokens)} TÍN HIỆU ĐẢO CHIỀU ---")

    # Nếu có tín hiệu, gửi thông báo đến tất cả người dùng đã đăng ký
    if flipped_tokens:
        subscribers = scheduler_service.get_scanner_subscribers()
        if subscribers:
            message = format_scanner_notification(flipped_tokens, '4h')
            logger.info(f"Đang gửi thông báo quét thị trường đến {len(subscribers)} người dùng...")
            for user_id in subscribers:
                try:
                    bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Lỗi khi gửi thông báo quét thị trường đến user {user_id}: {e}")
        else:
            logger.info("Không có người dùng nào đăng ký nhận tin quét thị trường.")

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
        self.dispatcher.bot_data['user_states'] = {}
        self.dispatcher.bot_data['scanner_states'] = {}
        
    def _setup_handlers(self):
        """Đăng ký tất cả các handlers cho bot."""
        self.dispatcher.add_handler(CommandHandler('start', command_handlers.start_command))
        self.dispatcher.add_handler(CommandHandler('watchlist', command_handlers.watchlist_command))
        self.dispatcher.add_handler(CommandHandler('analysis', command_handlers.analysis_command))
        
        # Thêm handler cho lệnh đăng ký và hủy đăng ký
        self.dispatcher.add_handler(CommandHandler('subscribescanner', command_handlers.subscribe_scanner_command))
        self.dispatcher.add_handler(CommandHandler('unsubscribescanner', command_handlers.unsubscribe_scanner_command))
        
        self.dispatcher.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handlers.handle_message))
        self.dispatcher.add_error_handler(error_handlers.error_handler)

    def _setup_jobs(self):
        """Lập lịch cho các công việc chạy nền."""
        job_queue = self.updater.job_queue
        job_queue.run_repeating(notification_job, interval=3600, first=10)
        job_queue.run_repeating(market_scanner_job, interval=14400, first=20)

    def run(self):
        """Bắt đầu chạy bot."""
        self.updater.start_polling()
        logger.info("Bot đã khởi động và đang chạy...")
        self.updater.idle()