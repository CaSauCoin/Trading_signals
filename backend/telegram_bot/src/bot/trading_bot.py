import logging
import sys
import os
import asyncio
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# Add utils to Python path
utils_path = os.path.join(os.path.dirname(__file__), 'utils')
sys.path.append(utils_path)

# Import handlers using absolute imports
from handlers.command_handlers import start_command, analysis_command, delete_my_data_command
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
        # Store scheduler service in bot_data for handlers to access
        if not hasattr(self.dispatcher, 'bot_data'):
            self.dispatcher.bot_data = {}
        
        if hasattr(self, 'scheduler_service') and self.scheduler_service:
            self.dispatcher.bot_data['scheduler_service'] = self.scheduler_service
        
        # Command handlers
        self.dispatcher.add_handler(CommandHandler("start", start_command))
        self.dispatcher.add_handler(CommandHandler("analysis", analysis_command))
        self.dispatcher.add_handler(CommandHandler("deletemydata", delete_my_data_command))
        
        # Callback handlers
        self.dispatcher.add_handler(CallbackQueryHandler(handle_callback))
        
        # Message handlers
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        
        # Error handler
        self.dispatcher.add_error_handler(error_handler)
        
    def setup_scheduler(self):
        """Setup background scheduler"""
        # Initialize scheduler service FIRST
        self.scheduler_service = SchedulerService(self)
        
        # Then create scheduler
        self.scheduler = BackgroundScheduler()
        
        # Simple sync function - no async needed
        def run_watchlist_update():
            """Sync function for watchlist update"""
            try:
                logger.info("🚀 Starting scheduled watchlist analysis...")
                # Call the sync function directly
                self.scheduler_service.update_all_watchlists()  # No await
                logger.info("✅ Scheduled watchlist analysis completed successfully")
            except Exception as e:
                logger.error(f"❌ Error in scheduled watchlist analysis: {e}")
    
        # Add job with sync function
        self.scheduler.add_job(
            run_watchlist_update,
            'interval',
            hours=1,  # Every 1 hour for production
            id='watchlist_updates',
            max_instances=1
        )

        logger.info("⏰ Scheduler configured: Watchlist analysis every 1 HOUR")
        
    def run(self):
        """Run the bot"""
        try:
            # Create updater and dispatcher
            self.updater = Updater(token=self.token, use_context=True)
            self.dispatcher = self.updater.dispatcher
            
            # Setup scheduler FIRST (this creates scheduler_service)
            self.setup_scheduler()
            
            # Setup handlers AFTER scheduler (so scheduler_service exists)
            self.setup_handlers()
            
            # Start scheduler
            self.scheduler.start()
            
            # Start bot
            self.updater.start_polling()
            
            logger.info("🤖 Trading Bot started successfully!")
            logger.info(f"📊 Scheduler service initialized: {hasattr(self, 'scheduler_service')}")
            
            # Keep running
            self.updater.idle()
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"💥 Fatal error in bot startup: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            try:
                if hasattr(self, 'scheduler') and self.scheduler and self.scheduler.running:
                    self.scheduler.shutdown()
                    logger.info("⏰ Scheduler shutdown completed")
                if self.updater:
                    self.updater.stop()
                    logger.info("🤖 Bot updater stopped")
            except Exception as cleanup_error:
                logger.error(f"🧹 Error during cleanup: {cleanup_error}")