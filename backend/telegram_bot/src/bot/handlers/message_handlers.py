from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import sys
import os

# Add the correct path to AdvancedSMC
current_dir = os.path.dirname(__file__)  # handlers directory
src_dir = os.path.dirname(os.path.dirname(current_dir))  # src directory
telegram_bot_dir = os.path.dirname(src_dir)  # telegram_bot directory
backend_dir = os.path.dirname(telegram_bot_dir)  # backend directory
advancedSMC_path = os.path.join(backend_dir, 'AdvancedSMC')
sys.path.insert(0, advancedSMC_path)

try:
    from AdvancedSMC import AdvancedSMC
    SMC_AVAILABLE = True
    analysis_service = AdvancedSMC()
except ImportError as e:
    print(f"Warning: Could not import AdvancedSMC: {e}")
    SMC_AVAILABLE = False
    analysis_service = None

def handle_message(update: Update, context: CallbackContext):
    """Handle text messages from users"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Get user state from bot_data
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    user_state = context.bot_data['user_states'].get(user_id, {})
    
    if user_state.get("waiting_for") == "custom_token":
        process_custom_token(update, context, text)
    elif user_state.get("waiting_for") == "watchlist_add":
        process_watchlist_add(update, context, text)
    else:
        # Check if it looks like a token
        if validate_token_format(text):
            analyze_token_direct(update, context, text)
        else:
            update.message.reply_text(
                "❓ Tôi không hiểu lệnh này.\n"
                "Gửi /start để xem menu hoặc gửi tên token (VD: BTC hoặc BTC/USDT)"
            )

def process_custom_token(update: Update, context: CallbackContext, token_input: str):
    """Process custom token input"""
    user_id = update.effective_user.id
    token_input = token_input.upper().strip()
    
    # Reset user state
    reset_user_state(user_id, context)

    if validate_token_format(token_input):
        show_timeframe_selection(update, context, token_input)
    else:
        update.message.reply_text(
            "❌ **Format token không hợp lệ!**\n\n"
            "✅ **Ví dụ hợp lệ:** BTC, BTC/USDT, PEPE\n\n"
            "Vui lòng thử lại hoặc /start để quay về menu.",
            parse_mode='Markdown'
        )

def process_watchlist_add(update: Update, context: CallbackContext, token_input: str):
    """Process watchlist add token input"""
    user_id = update.effective_user.id
    token_input = token_input.upper().strip()
    
    # Reset user state
    reset_user_state(user_id, context)
    
    if validate_token_format(token_input):
        # Add to watchlist with default timeframe
        add_to_watchlist(update, context, token_input, '4h')
    else:
        update.message.reply_text(
            "❌ **Format token không hợp lệ!**\n\n"
            "✅ **Ví dụ hợp lệ:** BTC, BTC/USDT, PEPE\n\n"
            "Vui lòng thử lại.",
            parse_mode='Markdown'
        )

def analyze_token_direct(update: Update, context: CallbackContext, symbol: str):
    """Analyze token directly with default timeframe"""
    analyze_token(update, context, symbol, '4h')

def analyze_token(update: Update, context: CallbackContext, symbol: str, timeframe: str):
    """Analyze token using AdvancedSMC"""
    # Show loading message
    loading_msg = update.message.reply_text(f"🔄 **Đang phân tích {symbol} {timeframe}...**", parse_mode='Markdown')
    
    try:
        # Check if analysis service is available
        if not analysis_service:
            loading_msg.edit_text(
                f"❌ **Lỗi hệ thống**\n\n"
                f"AdvancedSMC service không khả dụng.",
                parse_mode='Markdown'
            )
            return
        
        # Perform analysis
        result = analyze_with_smc(symbol, timeframe)
        
        if result.get('error'):
            loading_msg.edit_text(
                f"❌ **Lỗi phân tích {symbol}**\n\n"
                f"Chi tiết: {result.get('message', 'Unknown error')}",
                parse_mode='Markdown'
            )
            return
        
        # Format and send results
        formatted_result = format_analysis_result(result)
        
        # Create action buttons
        keyboard = [
            [InlineKeyboardButton("➕ Thêm vào Watchlist", callback_data=f'watchlist_add_{symbol}_{timeframe}')],
            [InlineKeyboardButton("🔄 Làm mới", callback_data=f'refresh_{symbol}_{timeframe}')],
            [InlineKeyboardButton("⏱️ Đổi timeframe", callback_data=f'timeframe_{symbol}')],
            [InlineKeyboardButton("🔙 Menu chính", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        loading_msg.edit_text(formatted_result, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        loading_msg.edit_text(
            f"❌ **Lỗi phân tích {symbol}**\n\n"
            f"Chi tiết: {str(e)}",
            parse_mode='Markdown'
        )

def analyze_with_smc(symbol: str, timeframe: str):
    """Analyze symbol using AdvancedSMC"""
    try:
        if not analysis_service:
            return {
                'error': True,
                'message': 'AdvancedSMC service not available'
            }
        
        # Normalize symbol format
        if '/' not in symbol and not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"
        elif '/' in symbol:
            symbol = symbol.replace('/', '')
        
        # Mock analysis result - replace with actual AdvancedSMC calls
        result = {
            'error': False,
            'symbol': symbol,
            'timeframe': timeframe,
            'analysis': {
                'signal': {'signal': 'BUY', 'confidence': 75},
                'order_blocks': {'status': 'Bullish OB found'},
                'fair_value_gaps': {'status': 'FVG detected'},
                'break_of_structure': {'status': 'BOS confirmed'},
                'liquidity_zones': {'status': 'Liquidity swept'},
                'timestamp': '2025-08-26T15:30:00'
            }
        }
        
        return result
        
    except Exception as e:
        return {
            'error': True,
            'message': f'Analysis failed: {str(e)}'
        }

def show_timeframe_selection(update: Update, context: CallbackContext, symbol: str):
    """Show timeframe selection for analysis"""
    keyboard = [
        [InlineKeyboardButton("15m", callback_data=f'analyze_{symbol}_15m'),
         InlineKeyboardButton("1h", callback_data=f'analyze_{symbol}_1h')],
        [InlineKeyboardButton("4h", callback_data=f'analyze_{symbol}_4h'),
         InlineKeyboardButton("1d", callback_data=f'analyze_{symbol}_1d')],
        [InlineKeyboardButton("3d", callback_data=f'analyze_{symbol}_3d'),
         InlineKeyboardButton("1w", callback_data=f'analyze_{symbol}_1w')],
        [InlineKeyboardButton("🔙 Quay lại", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"⏱️ **Chọn timeframe cho {symbol}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def add_to_watchlist(update: Update, context: CallbackContext, symbol: str, timeframe: str):
    """Add token to user watchlist"""
    update.message.reply_text(
        f"✅ **Đã thêm {symbol} ({timeframe}) vào watchlist!**\n\n"
        "📋 Sử dụng /start → Watchlist để quản lý danh sách theo dõi.",
        parse_mode='Markdown'
    )

def format_analysis_result(result: dict) -> str:
    """Format analysis results for display"""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"
    
    symbol = result.get('symbol', 'Unknown')
    timeframe = result.get('timeframe', '4h')
    analysis = result.get('analysis', {})
    
    # Extract analysis data
    signal = analysis.get('signal', {})
    order_blocks = analysis.get('order_blocks', {})
    fvg = analysis.get('fair_value_gaps', {})
    bos = analysis.get('break_of_structure', {})
    liquidity = analysis.get('liquidity_zones', {})
    
    # Format signal emoji
    signal_emoji = "🟢" if signal.get('signal') == 'BUY' else "🔴" if signal.get('signal') == 'SELL' else "🟡"
    
    # Format the message
    formatted_msg = f"""
📊 **Phân tích SMC: {symbol} ({timeframe})**

{signal_emoji} **Tín hiệu:** {signal.get('signal', 'NEUTRAL')}
📈 **Độ tin cậy:** {signal.get('confidence', 0)}%

🔲 **Order Blocks:** {order_blocks.get('status', 'N/A')}
⚡ **Fair Value Gaps:** {fvg.get('status', 'N/A')}
📊 **Break of Structure:** {bos.get('status', 'N/A')}
💧 **Liquidity Zones:** {liquidity.get('status', 'N/A')}

⏰ **Cập nhật:** {analysis.get('timestamp', 'N/A')}

⚠️ *Chỉ mang tính chất tham khảo, không phải lời khuyên đầu tư.*
    """
    
    return formatted_msg.strip()

def reset_user_state(user_id: int, context):
    """Reset user state"""
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    context.bot_data['user_states'][user_id] = {"waiting_for": None}

def validate_token_format(token: str) -> bool:
    """Validate token format"""
    if not token:
        return False
    
    token = token.upper().strip()
    
    # Check for pair format (e.g., BTC/USDT)
    if '/' in token:
        parts = token.split('/')
        if len(parts) == 2 and all(part.isalpha() and len(part) >= 2 for part in parts):
            return True
    
    # Check for single token format (e.g., BTC)
    if token.isalpha() and 2 <= len(token) <= 10:
        return True
    
    return False