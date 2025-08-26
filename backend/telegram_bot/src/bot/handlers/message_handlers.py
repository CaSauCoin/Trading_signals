import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def handle_message(update: Update, context: CallbackContext):
    """Handle text messages from users"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Initialize user states if not exists
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    # Check if user is in a waiting state
    user_state = context.bot_data['user_states'].get(user_id)
    
    if user_state and user_state.get('waiting_for') == 'custom_token':
        handle_custom_token_input(update, context, message_text)
        # Clear the waiting state
        del context.bot_data['user_states'][user_id]
    else:
        # Default response for unexpected messages
        update.message.reply_text(
            "🤖 **Use the menu buttons below or send /start to begin.**\n\n"
            "Available commands:\n"
            "• /start - Main menu\n"
            "• /analysis [SYMBOL] [TIMEFRAME] - Quick analysis\n\n"
            "Example: `/analysis BTC/USDT 4h`",
            parse_mode='Markdown'
        )

def handle_custom_token_input(update: Update, context: CallbackContext, token_input: str):
    """Process custom token input from user"""
    logger.info(f"Processing custom token input: {token_input}")
    
    try:
        # Parse and validate token input
        symbol, timeframe = parse_token_input(token_input)
        
        if not symbol:
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
        
        # Import analysis function from callback_handlers
        from handlers.callback_handlers import analyze_with_smc, format_analysis_result
        
        # Perform analysis
        result = analyze_with_smc(symbol, timeframe)
        
        if result.get('error'):
            processing_msg.edit_text(
                f"❌ **Analysis failed for {symbol}:**\n"
                f"{result.get('message', 'Unknown error')}\n\n"
                "Please check the token symbol and try again.\n"
                "Use /start to return to menu.",
                parse_mode='Markdown'
            )
            return
        
        # Format and send results
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
            processing_msg.edit_text(
                formatted_result, 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Markdown error: {e}")
            # Fallback without markdown
            plain_message = formatted_result.replace('*', '').replace('_', '')
            processing_msg.edit_text(plain_message, reply_markup=reply_markup)
        
        logger.info(f"Successfully analyzed custom token: {symbol}")
        
    except Exception as e:
        logger.error(f"Error processing custom token: {e}")
        update.message.reply_text(
            f"❌ **Error processing your request:**\n"
            f"{str(e)[:100]}...\n\n"
            "Please try again or use /start to return to menu.",
            parse_mode='Markdown'
        )

def parse_token_input(token_input: str):
    """Parse token input and return (symbol, timeframe)"""
    token_input = token_input.upper().strip()
    
    # Common timeframe patterns
    timeframe_pattern = r'\b(1M|3M|5M|15M|30M|1H|2H|4H|6H|8H|12H|1D|3D|1W|1M)\b'
    
    # Extract timeframe if present
    timeframe_match = re.search(timeframe_pattern, token_input)
    timeframe = timeframe_match.group(1).lower() if timeframe_match else '4h'
    
    # Remove timeframe from input to get clean symbol
    symbol_part = re.sub(timeframe_pattern, '', token_input).strip()
    
    # Normalize symbol formats
    symbol = normalize_symbol(symbol_part)
    
    return symbol, timeframe

def normalize_symbol(symbol_input: str):
    """Normalize symbol to standard format"""
    if not symbol_input:
        return None
    
    symbol_input = symbol_input.upper().replace(' ', '')
    
    # If already in SYMBOL/USDT format
    if '/' in symbol_input:
        parts = symbol_input.split('/')
        if len(parts) == 2:
            base, quote = parts
            # Validate base symbol (3-10 characters, alphanumeric)
            if re.match(r'^[A-Z0-9]{1,10}$', base) and quote in ['USDT', 'BTC', 'ETH', 'BNB']:
                return f"{base}/{quote}"
    
    # If in SYMBOLUSDT format
    if symbol_input.endswith('USDT') and len(symbol_input) > 4:
        base = symbol_input[:-4]
        if re.match(r'^[A-Z0-9]{1,10}$', base):
            return f"{base}/USDT"
    
    # If just symbol (assume USDT pair)
    if re.match(r'^[A-Z0-9]{1,10}$', symbol_input):
        return f"{symbol_input}/USDT"
    
    # Invalid format
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