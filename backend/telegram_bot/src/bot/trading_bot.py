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
        self.scheduler_service = None
        self.user_states = {}
        
    def setup_bot(self):
        """Initialize bot and dispatcher"""
        try:
            # Create updater and dispatcher
            self.updater = Updater(token=self.token, use_context=True)
            self.dispatcher = self.updater.dispatcher
            logger.info("Bot and dispatcher initialized successfully")
            
            # Setup handlers
            self.setup_handlers()
            logger.info("Handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up bot: {e}")
            raise
        
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
        logger.info("Scheduler initialized (service will be added after bot starts)")
        
    def add_scheduler_jobs(self):
        """Add scheduler jobs after scheduler_service is created"""
        if not self.scheduler_service:
            logger.error("Cannot add scheduler jobs - scheduler_service not created")
            return
            
        # Schedule updates every 1 hour
        self.scheduler.add_job(
            self.scheduler_service.update_all_watchlists,
            'interval',
            minutes=1,
            id='watchlist_updates',
            max_instances=1
        )
        
        # FOR TESTING: Also add a 2-minute job to test immediately
        self.scheduler.add_job(
            self.debug_watchlist_state,
            'interval',
            minutes=1,
            id='debug_watchlist',
            max_instances=1
        )

        logger.info("Scheduler jobs added: Watchlist updates every 1 HOUR + debug every 1 minute")
        
    def debug_watchlist_state(self):
        """Debug function to check watchlist state"""
        logger.info("=== WATCHLIST DEBUG ===")
        
        # Get the SAME instance from bot_data
        if hasattr(self, 'updater') and self.updater:
            shared_service = self.updater.dispatcher.bot_data.get('scheduler_service')
            if shared_service:
                logger.info(f"Shared scheduler service watchlists: {list(shared_service.user_watchlists.keys())}")
                
                for user_id, data in shared_service.user_watchlists.items():
                    tokens = data.get('tokens', [])
                    logger.info(f"User {user_id}: {len(tokens)} tokens")
                    for token in tokens:
                        logger.info(f"  - {token['symbol']} ({token['timeframe']})")
                
                # Force update for testing using SHARED service
                if shared_service.user_watchlists:
                    logger.info("Forcing watchlist update for testing...")
                    shared_service.update_all_watchlists()
                else:
                    logger.info("No watchlists in shared service")
            else:
                logger.error("Shared scheduler service not found in bot_data")
                logger.info(f"Available bot_data keys: {list(self.updater.dispatcher.bot_data.keys())}")
        else:
            logger.error("Updater not available for debug")
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Trading Bot...")
        
        try:
            # Initialize bot FIRST
            self.setup_bot()
            
            # Start scheduler (without jobs)
            self.setup_scheduler()
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Start bot polling
            self.updater.start_polling()
            logger.info("Bot started successfully")
            
            # NOW create scheduler_service and store in bot_data
            try:
                # Add services path for import
                services_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services')
                if services_path not in sys.path:
                    sys.path.insert(0, services_path)
                    
                from scheduler_service import SchedulerService
                self.scheduler_service = SchedulerService(self)
                self.updater.dispatcher.bot_data['scheduler_service'] = self.scheduler_service
                logger.info("Scheduler service created and stored in dispatcher.bot_data")
                
                # Add scheduler jobs AFTER service is created
                self.add_scheduler_jobs()
                
            except Exception as e:
                logger.error(f"Error setting up scheduler service: {e}")
                import traceback
                traceback.print_exc()
            
            # Keep bot running
            logger.info("Bot is running. Press Ctrl+C to stop.")
            self.updater.idle()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.scheduler:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")