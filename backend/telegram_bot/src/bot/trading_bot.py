import logging
import sys
import os
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# Add utils to Python path
utils_path = os.path.join(os.path.dirname(__file__), 'utils')
sys.path.append(utils_path)

# Import handlers using absolute imports
from handlers.command_handlers import start_command, analysis_command
from handlers.callback_handlers import handle_callback
from handlers.message_handlers import handle_message
from handlers.error_handlers import error_handler

# Import services using absolute imports
from services.scheduler_service import SchedulerService

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, token):
        self.token = token
        self.updater = None
        self.dispatcher = None
        self.scheduler = None
        self.user_states = {}
        
    def setup_handlers(self):
        """Register all handlers"""
        # Command handlers
        self.dispatcher.add_handler(CommandHandler("start", start_command))
        self.dispatcher.add_handler(CommandHandler("analysis", analysis_command))
        
        # Callback handlers
        self.dispatcher.add_handler(CallbackQueryHandler(handle_callback))
        
        # Message handlers - THIS IS IMPORTANT!
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        
        # Error handler
        self.dispatcher.add_error_handler(error_handler)
        
    def setup_scheduler(self):
        """Setup background scheduler"""
        self.scheduler = BackgroundScheduler()
        scheduler_service = SchedulerService(self)
        
        # Add hourly watchlist update job
        self.scheduler.add_job(
            scheduler_service.update_all_watchlists,
            'interval',
            hours=1,
            id='watchlist_updates'
        )
        
    def run(self):
        """Run the bot"""
        try:
            # Create updater and dispatcher
            self.updater = Updater(token=self.token, use_context=True)
            self.dispatcher = self.updater.dispatcher
            
            # Setup handlers
            self.setup_handlers()
            
            # Setup scheduler
            self.setup_scheduler()
            
            # Start scheduler
            self.scheduler.start()
            
            # Start bot
            self.updater.start_polling()
            
            logger.info("Bot started successfully!")
            
            # Keep running
            self.updater.idle()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            try:
                if self.scheduler and self.scheduler.running:
                    self.scheduler.shutdown()
                if self.updater:
                    self.updater.stop()
            except:
                pass