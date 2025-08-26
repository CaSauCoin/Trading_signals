import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def handle_message(update: Update, context: CallbackContext):
    """Handle text messages from users"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    logger.info(f"User {user_id} sent message: {message_text}")
    
    # Initialize user states if not exists
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
        logger.info("Initialized user_states in bot_data")
    
    # Check if user is in a waiting state
    user_state = context.bot_data['user_states'].get(user_id)
    logger.info(f"User {user_id} state: {user_state}")
    
    if user_state and user_state.get('waiting_for') == 'custom_token':
        logger.info(f"Processing custom token for user {user_id}: {message_text}")
        handle_custom_token_input(update, context, message_text)
        # Clear the waiting state
        if user_id in context.bot_data['user_states']:
            del context.bot_data['user_states'][user_id]
            logger.info(f"Cleared custom_token state for user {user_id}")
    elif user_state and user_state.get('waiting_for') == 'watchlist_token':
        logger.info(f"Processing watchlist token for user {user_id}: {message_text}")
        handle_watchlist_token_input(update, context, message_text)
        # Clear the waiting state
        if user_id in context.bot_data['user_states']:
            del context.bot_data['user_states'][user_id]
            logger.info(f"Cleared watchlist_token state for user {user_id}")
    else:
        logger.info(f"No matching state for user {user_id}, showing default response")
        # Default response for unexpected messages
        update.message.reply_text(
            "🤖 **Use the menu buttons below or send /start to begin.**\n\n"
            "Available commands:\n"
            "• /start - Main menu\n"
            "• /analysis [SYMBOL] [TIMEFRAME] - Quick analysis\n\n"
            "Example: `/analysis BTC 4h`",
            parse_mode='Markdown'
        )

def handle_watchlist_token_input(update: Update, context: CallbackContext, token_input: str):
    """Process watchlist token input from user"""
    user_id = update.effective_user.id
    logger.info(f"Processing watchlist token input: '{token_input}' for user {user_id}")
    
    try:
        # Parse token input
        symbol, timeframe = parse_token_input(token_input)
        logger.info(f"Parsed - Symbol: {symbol}, Timeframe: {timeframe}")
        
        if not symbol:
            logger.warning(f"Invalid symbol format for input: {token_input}")
            update.message.reply_text(
                "❌ **Invalid token format!**\n\n"
                "Please use: `BTC`, `BTC 1h`, or `BTC/USDT`\n"
                "Use /start to return to menu.",
                parse_mode='Markdown'
            )
            return
        
        # Get or create scheduler service - FIX IMPORT PATH
        if 'scheduler_service' not in context.bot_data:
            logger.info("Creating new scheduler service instance")
            try:
                # Import from services directory
                import sys
                import os
                
                # Add services directory to Python path
                services_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'services')
                if services_path not in sys.path:
                    sys.path.insert(0, services_path)
                    logger.info(f"Added services path: {services_path}")
                
                from scheduler_service import SchedulerService
                context.bot_data['scheduler_service'] = SchedulerService(None)
                logger.info("Successfully created scheduler service")
            except ImportError as e:
                logger.error(f"Failed to import SchedulerService: {e}")
                # Try alternative import
                try:
                    from services.scheduler_service import SchedulerService
                    context.bot_data['scheduler_service'] = SchedulerService(None)
                    logger.info("Successfully imported using services.scheduler_service")
                except ImportError as e2:
                    logger.error(f"Alternative import also failed: {e2}")
                    update.message.reply_text(
                        "❌ **System error: Watchlist service unavailable**\n\n"
                        "Please try again later or use /start to return to menu.",
                        parse_mode='Markdown'
                    )
                    return
        
        scheduler_service = context.bot_data['scheduler_service']
        logger.info(f"Got scheduler service: {type(scheduler_service)}")
        
        # Add to watchlist
        logger.info(f"Attempting to add {symbol} {timeframe} to watchlist for user {user_id}")
        success = scheduler_service.add_to_watchlist(user_id, symbol, timeframe)
        logger.info(f"Add to watchlist result: {success}")
        
        if success:
            watchlist_data = scheduler_service.get_user_watchlist(user_id)
            total_tokens = len(watchlist_data.get('tokens', []))
            
            logger.info(f"Successfully added {symbol} to watchlist. Total tokens: {total_tokens}")
            update.message.reply_text(
                f"✅ **Added {symbol} ({timeframe}) to watchlist!**\n\n"
                f"📊 Total tokens: {total_tokens}/10\n"
                f"🔔 You'll receive notifications every 10 minutes\n\n"
                "Use /start to manage your watchlist.",
                parse_mode='Markdown'
            )
        else:
            # Check if limit exceeded or already exists
            watchlist_data = scheduler_service.get_user_watchlist(user_id)
            tokens = watchlist_data.get('tokens', [])
            
            # Check if already exists
            exists = any(t['symbol'] == symbol and t['timeframe'] == timeframe for t in tokens)
            
            if exists:
                logger.info(f"{symbol} {timeframe} already exists in watchlist")
                update.message.reply_text(
                    f"⚠️ **{symbol} ({timeframe}) is already in your watchlist!**\n\n"
                    "Use /start to view your watchlist.",
                    parse_mode='Markdown'
                )
            elif len(tokens) >= 10:
                logger.info(f"Watchlist full for user {user_id}: {len(tokens)}/10")
                update.message.reply_text(
                    f"❌ **Watchlist is full! (10/10)**\n\n"
                    "Remove some tokens before adding new ones.\n"
                    "Use /start to manage your watchlist.",
                    parse_mode='Markdown'
                )
            else:
                logger.error(f"Unknown error adding {symbol} to watchlist")
                update.message.reply_text(
                    f"❌ **Failed to add {symbol} to watchlist.**\n\n"
                    "Please try again or use /start to return to menu.",
                    parse_mode='Markdown'
                )
        
    except Exception as e:
        logger.error(f"Error processing watchlist token: {e}", exc_info=True)
        update.message.reply_text(
            f"❌ **Error processing token:**\n"
            f"{str(e)[:100]}...\n\n"
            "Please try again or use /start to return to menu.",
            parse_mode='Markdown'
        )

def handle_custom_token_input(update: Update, context: CallbackContext, token_input: str):
    """Process custom token input from user"""
    logger.info(f"Processing custom token input: {token_input}")
    
    try:
        # Parse and validate token input
        symbol, timeframe = parse_token_input(token_input)
        logger.info(f"Parsed symbol: {symbol}, timeframe: {timeframe}")
        
        if not symbol:
            logger.warning(f"Invalid symbol format: {token_input}")
            update.message.reply_text(
                "❌ **Invalid token format!**\n\n"
                "Please use one of these formats:\n"
                "• `BTC` (will use BTC/USDT)\n"
                "• `BTC/USDT`\n"
                "• `BTCUSDT`\n"
                "• `BTC 1h` (with timeframe)\n"
                "• `BTC/USDT 4h`\n\n"
                "Try again or use /start to return to menu.",
                parse_mode='Markdown'
            )
            return
        
        # Show processing message
        processing_msg = update.message.reply_text(
            f"🔄 **Analyzing {symbol} {timeframe}...**\n"
            "Please wait while I fetch the data...",
            parse_mode='Markdown'
        )
        
        # Check if analysis service is available first
        logger.info("Checking analysis service availability...")
        try:
            from handlers.callback_handlers import analysis_service
            if not analysis_service:
                logger.error("Analysis service not available")
                processing_msg.edit_text(
                    "❌ **Analysis service not available**\n\n"
                    "Please try again later or contact support.\n"
                    "Use /start to return to menu.",
                    parse_mode='Markdown'
                )
                return
            
            logger.info(f"Analysis service available: {type(analysis_service)}")
        except ImportError as e:
            logger.error(f"Import error: {e}")
            processing_msg.edit_text(
                "❌ **System error: Cannot import analysis service**\n\n"
                "Please try again later.\n"
                "Use /start to return to menu.",
                parse_mode='Markdown'
            )
            return
        
        # Import analysis functions
        logger.info("Importing analysis functions...")
        from handlers.callback_handlers import analyze_with_smc, format_analysis_result
        
        # Perform analysis with timeout protection
        logger.info(f"Starting analysis for {symbol} {timeframe}")
        result = analyze_with_smc(symbol, timeframe)
        logger.info(f"Analysis completed. Error: {result.get('error', False)}")
        
        if result.get('error'):
            error_msg = result.get('message', 'Unknown error')
            logger.error(f"Analysis failed: {error_msg}")
            processing_msg.edit_text(
                f"❌ **Analysis failed for {symbol}:**\n"
                f"{error_msg}\n\n"
                "Please check the token symbol and try again.\n"
                "Use /start to return to menu.",
                parse_mode='Markdown'
            )
            return
        
        # Format and send results
        logger.info("Formatting analysis results...")
        formatted_result = format_analysis_result(result)
        
        # Create timeframe buttons for further analysis
        symbol_encoded = symbol.replace('/', '_')
        keyboard = [
            [InlineKeyboardButton("📊 15m", callback_data=f'tf_{symbol_encoded}_15m'),
             InlineKeyboardButton("📊 1h", callback_data=f'tf_{symbol_encoded}_1h'),
             InlineKeyboardButton("📊 4h", callback_data=f'tf_{symbol_encoded}_4h')],
            [InlineKeyboardButton("📊 1d", callback_data=f'tf_{symbol_encoded}_1d'),
             InlineKeyboardButton("📊 3d", callback_data=f'tf_{symbol_encoded}_3d'),
             InlineKeyboardButton("📊 1w", callback_data=f'tf_{symbol_encoded}_1w')],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f'tf_{symbol_encoded}_{timeframe}'),
             InlineKeyboardButton("🏠 Menu", callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send results
        try:
            logger.info("Sending formatted results...")
            processing_msg.edit_text(
                formatted_result, 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
            logger.info("Results sent successfully")
        except Exception as e:
            logger.error(f"Markdown error: {e}")
            # Fallback without markdown
            plain_message = formatted_result.replace('*', '').replace('_', '')
            processing_msg.edit_text(plain_message, reply_markup=reply_markup)
        
        logger.info(f"Successfully analyzed custom token: {symbol}")
        
    except Exception as e:
        logger.error(f"Error processing custom token: {e}", exc_info=True)
        try:
            update.message.reply_text(
                f"❌ **Error processing your request:**\n"
                f"{str(e)[:100]}...\n\n"
                "Please try again or use /start to return to menu.",
                parse_mode='Markdown'
            )
        except:
            # If even the error message fails
            update.message.reply_text(
                "❌ Critical error occurred. Please use /start to return to menu."
            )

def parse_token_input(token_input: str):
    """Parse token input and return (symbol, timeframe)"""
    token_input = token_input.upper().strip()
    logger.info(f"Parsing token input: '{token_input}'")
    
    # Common timeframe patterns (fixed regex)
    timeframe_pattern = r'\b(15M|30M|1H|2H|4H|6H|8H|12H|1D|3D|1W)\b'
    
    # Extract timeframe if present
    timeframe_match = re.search(timeframe_pattern, token_input)
    timeframe = timeframe_match.group(1).lower() if timeframe_match else '4h'
    logger.info(f"Extracted timeframe: {timeframe}")
    
    # Remove timeframe from input to get clean symbol
    symbol_part = re.sub(timeframe_pattern, '', token_input).strip()
    logger.info(f"Symbol part after timeframe removal: '{symbol_part}'")
    
    # Normalize symbol formats
    symbol = normalize_symbol(symbol_part)
    logger.info(f"Normalized symbol: {symbol}")
    
    return symbol, timeframe

def normalize_symbol(symbol_input: str):
    """Normalize symbol to standard format"""
    if not symbol_input:
        logger.warning("Empty symbol input")
        return None
    
    symbol_input = symbol_input.upper().replace(' ', '')
    logger.info(f"Normalizing symbol: '{symbol_input}'")
    
    # If already in SYMBOL/USDT format
    if '/' in symbol_input:
        parts = symbol_input.split('/')
        if len(parts) == 2:
            base, quote = parts
            # Validate base symbol (1-10 characters, alphanumeric)
            if re.match(r'^[A-Z0-9]{1,10}$', base) and quote in ['USDT', 'BTC', 'ETH', 'BNB']:
                result = f"{base}/{quote}"
                logger.info(f"Symbol format valid: {result}")
                return result
    
    # If in SYMBOLUSDT format
    if symbol_input.endswith('USDT') and len(symbol_input) > 4:
        base = symbol_input[:-4]
        if re.match(r'^[A-Z0-9]{1,10}$', base):
            result = f"{base}/USDT"
            logger.info(f"Converted SYMBOLUSDT to {result}")
            return result
    
    # If just symbol (assume USDT pair)
    if re.match(r'^[A-Z0-9]{1,10}$', symbol_input):
        result = f"{symbol_input}/USDT"
        logger.info(f"Added /USDT to symbol: {result}")
        return result
    
    # Invalid format
    logger.warning(f"Invalid symbol format: '{symbol_input}'")
    return None

def validate_token_symbol(symbol: str):
    """Validate if token symbol is potentially valid"""
    if not symbol:
        return False
    
    # Remove / and check if base symbol is reasonable
    base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
    
    # Should be 1-10 characters, alphanumeric
    if not re.match(r'^[A-Z0-9]{1,10}$', base_symbol):
        return False
    
    # Common invalid patterns
    invalid_patterns = ['TEST', 'FAKE', 'SCAM']
    if base_symbol in invalid_patterns:
        return False
    
    return True