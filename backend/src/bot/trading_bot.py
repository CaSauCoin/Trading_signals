# src/bot/trading_bot.py
import logging
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from telegram import Update
from .services.analysis_service import BotAnalysisService
from .services.scheduler_service import SchedulerService
from .handlers import command_handlers, callback_handlers, message_handlers, error_handlers
from .formatters import format_analysis_result

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
        # Khởi tạo user_states
        self.dispatcher.bot_data['user_states'] = {}
        
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
        job_queue.run_repeating(notification_job, interval=60, first=10)

    def run(self):
        """Bắt đầu chạy bot."""
        self.updater.start_polling()
        self.updater.idle()