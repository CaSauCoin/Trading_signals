import logging
import sys
import os

logger = logging.getLogger(__name__)

# Global variables to store imported functions
analysis_service = None
analyze_with_smc = None
format_price = None

def import_analysis_functions():
    """Import analysis functions with proper error handling"""
    global analysis_service, analyze_with_smc, format_price
    
    if analysis_service is not None:
        return True  # Already imported
    
    try:
        # Method 1: Add handlers to sys.path
        current_dir = os.path.dirname(__file__)  # services directory
        src_dir = os.path.dirname(current_dir)  # src directory  
        bot_dir = os.path.join(src_dir, 'bot')  # bot directory
        handlers_dir = os.path.join(bot_dir, 'handlers')  # handlers directory
        
        if handlers_dir not in sys.path:
            sys.path.insert(0, handlers_dir)
            logger.info(f"Added handlers path: {handlers_dir}")
        
        import callback_handlers
        analysis_service = callback_handlers.analysis_service
        analyze_with_smc = callback_handlers.analyze_with_smc
        format_price = callback_handlers.format_price
        logger.info("Successfully imported analysis functions")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import analysis functions: {e}")
        try:
            # Method 2: Try alternative path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            handlers_path = os.path.join(base_dir, 'bot', 'handlers')
            
            if handlers_path not in sys.path:
                sys.path.insert(0, handlers_path)
            
            import callback_handlers
            analysis_service = callback_handlers.analysis_service
            analyze_with_smc = callback_handlers.analyze_with_smc
            format_price = callback_handlers.format_price
            logger.info("Successfully imported using alternative path")
            return True
            
        except ImportError as e2:
            logger.error(f"All import methods failed: {e2}")
            return False

def get_analysis_functions():
    """Get analysis functions, importing if necessary"""
    if import_analysis_functions():
        return analysis_service, analyze_with_smc, format_price
    return None, None, None