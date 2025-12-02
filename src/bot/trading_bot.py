import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from .services.analysis_service import BotAnalysisService
from .services.scheduler_service import SchedulerService
from .services.scanner_service import MarketScannerService
from .handlers import command_handlers, callback_handlers, message_handlers, error_handlers
from .formatters import format_analysis_result, format_scanner_notification
from src.bot import keyboards

logger = logging.getLogger(__name__)

# --- JOB FUNCTIONS ---
def notification_job(context: CallbackContext):
    """Scheduled job that runs periodically to check and send notifications."""
    bot = context.bot
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']
    analysis_service: BotAnalysisService = context.bot_data['analysis_service']

    interval_context = context.job.context
    if not interval_context:
        logger.error("Notification job run without interval context!")
        return

    all_watchlists = scheduler_service.get_all_watchlists()
    all_subscriptions = scheduler_service.get_watchlist_subscribers()

    users_to_check = [
        user_id for user_id, interval in all_subscriptions.items()
        if interval == interval_context
    ]

    logger.info(f"Running notification job ({interval_context}) for {len(users_to_check)} users.")

    for user_id in users_to_check:
        if user_id not in all_watchlists:
            continue

        watchlist = all_watchlists[user_id]

        for item in watchlist:
            symbol = item['symbol']
            timeframe = item['timeframe']

            logger.info(f"Analyzing {symbol} ({timeframe}) for user {user_id} (Job: {interval_context})")
            result = analysis_service.get_analysis_for_symbol(symbol, timeframe)

            if result.get('error'):
                continue


            new_suggestion = result.get('analysis', {}).get('suggestion', '')

            last_suggestion = scheduler_service.get_notification_state(user_id, symbol, timeframe)

            is_new_signal_actionable = "BUY" in new_suggestion or "SELL" in new_suggestion

            should_send = True

            if should_send:
                logger.info(f"NEW SIGNAL for user {user_id} on {symbol} {timeframe}. Sending notification.")
                message_text = "🔔 **Watchlist Alert** 🔔\n\n" + format_analysis_result(result)
                s_symbol = symbol.replace(' ', '')
                callback_data_sig = f"sig_{s_symbol}_{timeframe}"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚡ Copy Signal (TP/SL)", callback_data=callback_data_sig)],
                    [InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_main_menu")]
                ])
                try:
                    bot.send_message(chat_id=user_id, text=message_text, parse_mode='Markdown', reply_markup=keyboard)
                    # Cập nhật trạng thái *chỉ sau khi* gửi thành công
                    scheduler_service.update_notification_state(user_id, symbol, timeframe, new_suggestion)
                except Exception as e:
                    logger.error(f"Error sending notification to user {user_id}: {e}")
            else:
                is_last_signal_actionable = last_suggestion and ("BUY" in last_suggestion or "SELL" in last_suggestion)

                if not is_new_signal_actionable and is_last_signal_actionable:
                    logger.info(f"Signal for {symbol} {timeframe} for user {user_id} has disappeared. Resetting state.")
                    scheduler_service.update_notification_state(user_id, symbol, timeframe, new_suggestion)


def market_scanner_job(context: CallbackContext):
    """
    Market scanner job that finds reversal signals and sends them to subscribers.
    This job is parameterized by the timeframe.
    """
    bot = context.bot
    scanner_service: MarketScannerService = context.bot_data['scanner_service']
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']

    # 1. Lấy timeframe từ job context
    timeframe = context.job.context
    if not timeframe:
        logger.error("Market scanner job_run without timeframe context!")
        return

    all_subscribers_dict = scheduler_service.get_scanner_subscribers()
    subscribers_for_this_tf = [
        user_id for user_id, tf in all_subscribers_dict.items() if tf == timeframe
    ]

    logger.info(f"--- STARTING MARKET SCAN ({timeframe}) cho {len(subscribers_for_this_tf)} user(s) ---")

    if not subscribers_for_this_tf:
        logger.info(f"--- SCAN COMPLETE ({timeframe}), không có ai đăng ký. ---")
        return

    all_scanner_states = context.bot_data['scanner_states']
    previous_states_for_this_tf = all_scanner_states.get(timeframe, {})

    flipped_tokens, new_states = scanner_service.run_scan(previous_states_for_this_tf, timeframe=timeframe)

    all_scanner_states[timeframe] = new_states

    logger.info(f"--- SCAN COMPLETE ({timeframe}), FOUND {len(flipped_tokens)} REVERSAL SIGNALS ---")

    # 5. Gửi thông báo nếu có tín hiệu
    if flipped_tokens:
        message = format_scanner_notification(flipped_tokens, timeframe)
        logger.info(f"Sending market scan notifications ({timeframe}) to {len(subscribers_for_this_tf)} users...")
        for user_id in subscribers_for_this_tf:
            try:
                bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error sending market scan notification to user {user_id}: {e}")
    else:
        logger.info(f"Không có tín hiệu {timeframe} mới để gửi.")


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
        job_queue.run_repeating(notification_job, interval=300, first=10, context="5m")
        job_queue.run_repeating(notification_job, interval=900, first=15, context="15m")
        job_queue.run_repeating(notification_job, interval=1800, first=20, context="30m")
        job_queue.run_repeating(notification_job, interval=3600, first=25, context="1h")
        # job_queue.run_repeating(market_scanner_job, interval=14400, first=20)

    def run(self):
        """Start running the bot."""
        self.updater.start_polling()
        logger.info("Bot has started and is running...")
        self.updater.idle()