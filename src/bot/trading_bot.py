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
    
    all_watchlists = scheduler_service.get_all_watchlists()
    logger.info(f"Running notification job for {len(all_watchlists)} users.")
    
    for user_id, watchlist in all_watchlists.items():
        for item in watchlist:
            symbol = item['symbol']
            timeframe = item['timeframe']
            
            logger.info(f"Analyzing {symbol} ({timeframe}) for user {user_id}")
            result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
            
            if not result.get('error'):
                suggestion = result.get('analysis', {}).get('suggestion', '')
                # Only send notification if there's a clear BUY or SELL signal in the suggestion
                # if "BUY signal detected" in suggestion or "SELL signal detected" in suggestion:
                message_text = "🔔 **Watchlist Alert** 🔔\n\n" + format_analysis_result(result)
                try:
                    bot.send_message(chat_id=user_id, text=message_text, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error sending notification to user {user_id}: {e}")

def market_scanner_job(context: CallbackContext):
    """
    Market scanner job that finds reversal signals and sends them to subscribers.
    """
    bot = context.bot
    scanner_service: MarketScannerService = context.bot_data['scanner_service']
    scheduler_service: SchedulerService = context.bot_data['scheduler_service']
    previous_states = context.bot_data.get('scanner_states', {})
    
    logger.info("--- STARTING MARKET SCAN (4H) ---")
    flipped_tokens, new_states = scanner_service.run_scan(previous_states, timeframe='1d')
    context.bot_data['scanner_states'] = new_states
    logger.info(f"--- SCAN COMPLETE, FOUND {len(flipped_tokens)} REVERSAL SIGNALS ---")

    # If there are signals, send notifications to all subscribed users
    if flipped_tokens:
        subscribers = scheduler_service.get_scanner_subscribers()
        if subscribers:
            message = format_scanner_notification(flipped_tokens, '4h')
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
        job_queue.run_repeating(notification_job, interval=300, first=10)
        # job_queue.run_repeating(market_scanner_job, interval=14400, first=20)

    def run(self):
        """Start running the bot."""
        self.updater.start_polling()
        logger.info("Bot has started and is running...")
        self.updater.idle()