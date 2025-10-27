import logging
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from .services.analysis_service import BotAnalysisService
from .services.scheduler_service import SchedulerService
from .services.scanner_service import MarketScannerService
from .handlers import command_handlers, callback_handlers, message_handlers, error_handlers
from .formatters import format_analysis_result, format_scanner_notification

logger = logging.getLogger(__name__)

# --- JOB FUNCTIONS ---
def notification_job(context: CallbackContext):
    """Scheduled job that runs periodically to check and send notifications."""
    bot = context.bot
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']
    analysis_service: BotAnalysisService = context.bot_data['analysis_service']
    
    watchlist_states: dict = context.bot_data.get['watchlists_state']


    all_watchlists = scheduler_service.get_all_watchlists()
    logger.info(f"Running notification job for {len(all_watchlists)} users.")
    
    for user_id, watchlist in all_watchlists.items():
            # Khởi tạo state cho user nếu chưa có
            if user_id not in watchlist_states:
                watchlist_states[user_id] = {}

            for item in watchlist:
                symbol = item['symbol']
                timeframe = item['timeframe']
                # Tạo một key định danh duy nhất cho cặp coin/timeframe
                item_key = f"{symbol}_{timeframe}"
                
                logger.debug(f"Analyzing {item_key} for user {user_id}")
                # analysis_service trả về toàn bộ dữ liệu từ AdvancedSMC
                result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
                
                if result.get('error'):
                    logger.warning(f"Error analyzing {item_key} for {user_id}: {result.get('error')}")
                    continue

                # --- LOGIC PHÁT HIỆN THAY ĐỔI TÍN HIỆU (ĐÃ CẬP NHẬT) ---
                
                # 1. Lấy tín hiệu mới (từ 'trading_signals' thay vì 'analysis')
                trading_signals = result.get('trading_signals', {})
                new_signal = "NEUTRAL"
                if trading_signals.get('entry_long'):
                    new_signal = "BUY"
                elif trading_signals.get('entry_short'):
                    new_signal = "SELL"

                # 2. Lấy tín hiệu cũ đã lưu
                previous_signal = watchlist_states[user_id].get(item_key, 'NEUTRAL')

                # 3. So sánh: Chỉ gửi thông báo nếu tín hiệu thay đổi và là MUA/BÁN
                if new_signal != previous_signal and new_signal in ('BUY', 'SELL'):
                    logger.info(f"SIGNAL CHANGE DETECTED for user {user_id} on {item_key}: {previous_signal} -> {new_signal}")

                    # 4. Lấy suggestion (đây là chuỗi text từ analysis_service)
                    suggestion = result.get('analysis', {}).get('suggestion', 'Không có chi tiết.')

                    # 5. Format thông báo mới (ĐÃ XÓA TP/SL/ENTRY VÌ KHÔNG CÓ DỮ LIỆU)
                    signal_emoji = "📈" if new_signal == 'BUY' else "📉"
                    message_text = (
                        f"🔔 **Cảnh Báo Tín Hiệu Watchlist** {signal_emoji}\n\n"
                        f"▫️ Cặp: **{symbol}**\n"
                        f"▫️ Khung: **{timeframe}**\n"
                        f"▫️ Tín hiệu: **{new_signal}**\n\n"
                        f"Chi tiết:\n{suggestion}"
                    )
                    
                    # 6. Gửi thông báo
                    try:
                        bot.send_message(chat_id=user_id, text=message_text, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Error sending signal change notification to user {user_id}: {e}")
                
                # 7. Cập nhật trạng thái mới (cho dù có gửi thông báo hay không)
                watchlist_states[user_id][item_key] = new_signal


def market_scanner_job(context: CallbackContext):
    """
    Market scanner job that finds reversal signals and sends them to subscribers.
    (Giữ nguyên logic của job này)
    """
    bot = context.bot
    scanner_service: MarketScannerService = context.bot_data['scanner_service']
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']
    previous_states = context.bot_data.get('scanner_states', {})
    
    logger.info("--- STARTING MARKET SCAN (1D) ---")
    flipped_tokens, new_states = scanner_service.run_scan(previous_states, timeframe='1d')
    context.bot_data['scanner_states'] = new_states
    logger.info(f"--- SCAN COMPLETE, FOUND {len(flipped_tokens)} REVERSAL SIGNALS ---")

    if flipped_tokens:
        subscribers = scheduler_service.get_scanner_subscribers()
        if subscribers:
            message = format_scanner_notification(flipped_tokens, '1d')
            logger.info(f"Sending market scan notifications to {len(subscribers)} users...")
            for user_id in subscribers:
                try:
                    bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error sending market scan notification to user {user_id}: {e}")
        else:
            logger.info("No users subscribed to market scan notifications.")

class TradingBot:
    def __init__(self, token: str):
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self._setup_bot_data()
        self._setup_handlers()
        self._setup_jobs()

    def _setup_bot_data(self):
        """Initialize and inject services into bot context."""
        self.dispatcher.bot_data['analysis_service'] = BotAnalysisService()
        self.dispatcher.bot_data['scheduler_service'] = SchedulerService()
        self.dispatcher.bot_data['scanner_service'] = MarketScannerService()
        self.dispatcher.bot_data['user_states'] = {}
        self.dispatcher.bot_data['scanner_states'] = {}
        
        # THÊM MỚI: Khởi tạo state cho watchlist
        self.dispatcher.bot_data['watchlist_states'] = {}
        
    def _setup_handlers(self):
        """Register all handlers for the bot."""
        self.dispatcher.add_handler(CommandHandler('start', command_handlers.start_command))
        self.dispatcher.add_handler(CommandHandler('watchlist', command_handlers.watchlist_command))
        self.dispatcher.add_handler(CommandHandler('analysis', command_handlers.analysis_command))
        
        self.dispatcher.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handlers.handle_message))
        self.dispatcher.add_error_handler(error_handlers.error_handler)

    def _setup_jobs(self):
        """Schedule background jobs."""
        job_queue = self.updater.job_queue
        
        # THAY ĐỔI: Chạy `notification_job` thường xuyên (ví dụ: mỗi 10 giây)
        # Bạn có thể tăng/giảm `interval` tùy vào hiệu năng server và
        # giới hạn rate limit của API mà bạn gọi trong AdvancedSMC
        job_queue.run_repeating(notification_job, interval=10, first=5)
        
        # Giữ nguyên job scan thị trường
        job_queue.run_repeating(market_scanner_job, interval=14400, first=20) # 14400s = 4 giờ

    def run(self):
        """Start running the bot."""
        self.updater.start_polling()
        logger.info("Bot has started and is running...")
        self.updater.idle()