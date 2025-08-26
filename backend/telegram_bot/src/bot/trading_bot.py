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
        self.scheduler_service = SchedulerService(self)
        
        # Wrapper function để run async trong sync context
        def run_watchlist_update():
            """Sync wrapper for async watchlist update"""
            try:
                # Create new event loop for this thread
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async function
                loop.run_until_complete(self.scheduler_service.update_all_watchlists())
                
            except Exception as e:
                logger.error(f"Error in scheduled watchlist update: {e}")
        
        # Add job với sync wrapper
        self.scheduler.add_job(
            run_watchlist_update,  # Use sync wrapper instead
            'interval',
            hours=1,  # Every 1 hour
            id='watchlist_updates',
            max_instances=1
        )
        
        logger.info("Scheduler configured: Watchlist updates every 1 HOUR")
        
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