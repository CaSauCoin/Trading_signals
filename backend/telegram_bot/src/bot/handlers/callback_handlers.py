from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import sys
import os
import logging

logger = logging.getLogger(__name__)

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
    logger.warning(f"⚠️ Could not import AdvancedSMC: {e}")
    SMC_AVAILABLE = False
    analysis_service = None

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Initialize user states if not exists
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    # Get scheduler service from bot_data if available
    scheduler_service = context.bot_data.get('scheduler_service')
    
    # Route callbacks
    if data == 'custom_token':
        handle_custom_token_callback(query, context, user_id)
    elif data.startswith('analyze_'):
        handle_analyze_callback(query, context, data)
    elif data == 'select_pair':
        handle_select_pair_callback(query, context)
    elif data == 'watchlist_menu':
        show_watchlist_menu(query, context)
    elif data.startswith('watchlist_'):
        handle_watchlist_callback(query, context, data, scheduler_service)
    elif data.startswith('timeframe_'):
        handle_timeframe_callback(query, context, data)
    elif data.startswith('refresh_'):
        handle_refresh_callback(query, context, data)
    elif data == 'back_to_main':
        handle_back_to_main(query, context)
    elif data == 'help':
        show_help(query)
    else:
        query.edit_message_text("⚠️ Feature under development...")

def handle_custom_token_callback(query, context, user_id):
    """Handle custom token input callback"""
    context.bot_data['user_states'][user_id] = {"waiting_for": "custom_token"}
    query.edit_message_text(
        "✏️ **Enter Custom Token**\n\n"
        "Send the token name you want to analyze:\n"
        "• Example: BTC, ETH, PEPE\n"
        "• Or pairs: BTC/USDT, ETH/USDT\n\n"
        "💡 Supports all Binance tokens!",
        parse_mode='Markdown'
    )

def handle_analyze_callback(query, context, data):
    """Handle analysis callback"""
    parts = data.split('_')
    if len(parts) >= 3:
        symbol = '_'.join(parts[1:-1])  # Handle symbols with underscores
        timeframe = parts[-1]
    else:
        symbol = parts[1] if len(parts) > 1 else 'BTC/USDT'
        timeframe = '4h'
    
    perform_analysis_callback(query, context, symbol, timeframe)

def handle_select_pair_callback(query, context):
    """Handle select pair callback"""
    keyboard = [
        [InlineKeyboardButton("BTC/USDT", callback_data='analyze_BTC/USDT_4h'),
         InlineKeyboardButton("ETH/USDT", callback_data='analyze_ETH/USDT_4h')],
        [InlineKeyboardButton("BNB/USDT", callback_data='analyze_BNB/USDT_4h'),
         InlineKeyboardButton("ADA/USDT", callback_data='analyze_ADA/USDT_4h')],
        [InlineKeyboardButton("SOL/USDT", callback_data='analyze_SOL/USDT_4h'),
         InlineKeyboardButton("DOT/USDT", callback_data='analyze_DOT/USDT_4h')],
        [InlineKeyboardButton("MATIC/USDT", callback_data='analyze_MATIC/USDT_4h'),
         InlineKeyboardButton("AVAX/USDT", callback_data='analyze_AVAX/USDT_4h')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🔍 **Select Popular Token Pair:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def handle_timeframe_callback(query, context, data):
    """Handle timeframe selection callback"""
    symbol = data.replace('timeframe_', '')
    
    keyboard = [
        [InlineKeyboardButton("15m", callback_data=f'analyze_{symbol}_15m'),
         InlineKeyboardButton("1h", callback_data=f'analyze_{symbol}_1h')],
        [InlineKeyboardButton("4h", callback_data=f'analyze_{symbol}_4h'),
         InlineKeyboardButton("1d", callback_data=f'analyze_{symbol}_1d')],
        [InlineKeyboardButton("3d", callback_data=f'analyze_{symbol}_3d'),
         InlineKeyboardButton("1w", callback_data=f'analyze_{symbol}_1w')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"⏱️ **Select Timeframe for {symbol}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def handle_refresh_callback(query, context, data):
    """Handle refresh analysis callback"""
    parts = data.replace('refresh_', '').split('_')
    symbol = '_'.join(parts[:-1])
    timeframe = parts[-1]
    
    perform_analysis_callback(query, context, symbol, timeframe)

def perform_analysis_callback(query, context, symbol: str, timeframe: str):
    """Perform analysis and update message"""
    # Show loading
    query.edit_message_text(f"🔄 **Analyzing {symbol} {timeframe}...**", parse_mode='Markdown')
    
    try:
        # Import analysis function
        from services.analysis_utils import analyze_with_smc
        
        # Perform analysis using AdvancedSMC or mock
        result = analyze_with_smc(symbol, timeframe)
        
        if result.get('error'):
            query.edit_message_text(
                f"❌ **Analysis Error for {symbol}**\n\n"
                f"Details: {result.get('message', 'Unknown error')}",
                parse_mode='Markdown'
            )
            return
        
        # Format results
        formatted_result = format_analysis_result(result)
        
        # Create action buttons
        keyboard = [
            [InlineKeyboardButton("➕ Add to Watchlist", callback_data=f'watchlist_add_{symbol}_{timeframe}')],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f'refresh_{symbol}_{timeframe}')],
            [InlineKeyboardButton("⏱️ Change Timeframe", callback_data=f'timeframe_{symbol}')],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(formatted_result, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"💥 Error in perform_analysis_callback: {e}")
        query.edit_message_text(
            f"❌ **Analysis Error for {symbol}**\n\n"
            f"Details: {str(e)}",
            parse_mode='Markdown'
        )

def handle_watchlist_callback(query, context, data, scheduler_service):
    """Handle watchlist related callbacks"""
    user_id = query.from_user.id
    
    if data == 'watchlist_add':
        context.bot_data['user_states'][user_id] = {"waiting_for": "watchlist_add"}
        query.edit_message_text(
            "➕ **Add Token to Watchlist**\n\n"
            "Send the token name you want to monitor:\n"
            "• Example: BTC, ETH, PEPE\n"
            "• Or pairs: BTC/USDT, ETH/USDT\n\n"
            "💡 Will use 4h timeframe by default.",
            parse_mode='Markdown'
        )
    elif data.startswith('watchlist_add_'):
        # Extract symbol and timeframe from callback
        parts = data.replace('watchlist_add_', '').split('_')
        symbol = '_'.join(parts[:-1])
        timeframe = parts[-1]
        add_to_watchlist_callback(query, context, symbol, timeframe, scheduler_service)
    elif data == 'watchlist_view':
        handle_view_watchlist(query, context, scheduler_service)
    elif data == 'watchlist_remove':
        handle_remove_from_watchlist_menu(query, context, scheduler_service)
    elif data.startswith('watchlist_remove_'):
        # Handle individual token removal
        handle_remove_specific_token(query, context, data, scheduler_service)
    elif data == 'watchlist_clear':
        handle_clear_watchlist(query, context, scheduler_service)
    elif data == 'watchlist_toggle_notifications':
        handle_toggle_notifications(query, context, scheduler_service)
    elif data == 'watchlist_clear_confirm':
        # Handle confirmed clear
        handle_clear_watchlist_confirmed(query, context, scheduler_service)
    else:
        query.edit_message_text("⚠️ Watchlist feature under development...")

def add_to_watchlist_callback(query, context, symbol: str, timeframe: str, scheduler_service):
    """Add token to watchlist via callback"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text(
            "❌ **System Error**\n\n"
            "Scheduler service not available.",
            parse_mode='Markdown'
        )
        return
    
    success = scheduler_service.add_to_watchlist(user_id, symbol, timeframe)
    
    if success:
        query.edit_message_text(
            f"✅ **Added {symbol} ({timeframe}) to watchlist!**\n\n"
            "📋 Use Watchlist menu to manage your monitoring list.\n"
            "🔔 You will receive hourly notifications for new signals.",
            parse_mode='Markdown'
        )
    else:
        watchlist = scheduler_service.get_user_watchlist(user_id)
        current_count = len(watchlist.get('tokens', []))
        
        if current_count >= 10:
            query.edit_message_text(
                f"❌ **Watchlist limit reached!**\n\n"
                f"📊 Current: {current_count}/10 tokens\n"
                "🗑️ Please remove some tokens before adding new ones.",
                parse_mode='Markdown'
            )
        else:
            query.edit_message_text(
                f"❌ **Token {symbol} ({timeframe}) already in watchlist!**",
                parse_mode='Markdown'
            )

def handle_view_watchlist(query, context, scheduler_service):
    """Handle view watchlist"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text("❌ Scheduler service not available.")
        return
    
    watchlist = scheduler_service.get_user_watchlist(user_id)
    tokens = watchlist.get('tokens', [])
    notifications_enabled = watchlist.get('notifications_enabled', True)
    
    if not tokens:
        keyboard = [
            [InlineKeyboardButton("➕ Add Token", callback_data='watchlist_add')],
            [InlineKeyboardButton("🔙 Back", callback_data='watchlist_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "📋 **Watchlist Empty**\n\n"
            "➕ Use 'Add Token' to start monitoring.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    message = f"📋 **Your Watchlist ({len(tokens)}/10)**\n\n"
    
    for i, token in enumerate(tokens, 1):
        symbol = token['symbol']
        timeframe = token['timeframe']
        added_at = token.get('added_at', 'Unknown')[:10]  # Just date
        message += f"{i}. **{symbol}** ({timeframe}) - {added_at}\n"
    
    notification_status = "🔔 ON" if notifications_enabled else "🔕 OFF"
    message += f"\n📢 **Notifications:** {notification_status}\n"
    message += f"⏰ **Updates:** Every hour\n\n"
    message += "💡 Select action below:"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Token", callback_data='watchlist_add')],
        [InlineKeyboardButton("🗑️ Remove Token", callback_data='watchlist_remove')],
        [InlineKeyboardButton(f"{'🔕 Turn Off' if notifications_enabled else '🔔 Turn On'} Notifications", 
                             callback_data='watchlist_toggle_notifications')],
        [InlineKeyboardButton("🗂️ Clear All", callback_data='watchlist_clear')],
        [InlineKeyboardButton("🔙 Back", callback_data='watchlist_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

def handle_remove_from_watchlist_menu(query, context, scheduler_service):
    """Show menu to select token for removal"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text("❌ Scheduler service not available.")
        return
    
    watchlist = scheduler_service.get_user_watchlist(user_id)
    tokens = watchlist.get('tokens', [])
    
    if not tokens:
        query.edit_message_text(
            "📋 **Watchlist Empty**\n\n"
            "No tokens to remove.",
            parse_mode='Markdown'
        )
        return
    
    # Create keyboard with tokens to remove
    keyboard = []
    for token in tokens:
        symbol = token['symbol']
        timeframe = token['timeframe']
        button_text = f"❌ {symbol} ({timeframe})"
        callback_data = f"watchlist_remove_{symbol}_{timeframe}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='watchlist_view')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🗑️ **Select Token to Remove:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def handle_remove_specific_token(query, context, data, scheduler_service):
    """Remove specific token from watchlist"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text("❌ Scheduler service not available.")
        return
    
    # Parse callback data: watchlist_remove_{symbol}_{timeframe}
    parts = data.replace('watchlist_remove_', '').split('_')
    timeframe = parts[-1]
    symbol = '_'.join(parts[:-1])
    
    logger.info(f"🗑️ Removing {symbol} {timeframe} from user {user_id} watchlist")
    
    success = scheduler_service.remove_from_watchlist(user_id, symbol, timeframe)
    
    if success:
        query.edit_message_text(
            f"✅ **Removed {symbol} ({timeframe}) from watchlist!**\n\n"
            "📋 Use Watchlist menu to view current list.",
            parse_mode='Markdown'
        )
    else:
        query.edit_message_text(
            f"❌ **Error removing {symbol} ({timeframe})**\n\n"
            "Token not found in watchlist.",
            parse_mode='Markdown'
        )

def handle_clear_watchlist(query, context, scheduler_service):
    """Clear entire watchlist"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text("❌ Scheduler service not available.")
        return
    
    # Confirm clear action
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Clear", callback_data='watchlist_clear_confirm')],
        [InlineKeyboardButton("❌ Cancel", callback_data='watchlist_view')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "⚠️ **Confirm clear entire watchlist?**\n\n"
        "This action cannot be undone!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def handle_clear_watchlist_confirmed(query, context, scheduler_service):
    """Actually clear the watchlist after confirmation"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text("❌ Scheduler service not available.")
        return
    
    success = scheduler_service.clear_watchlist(user_id)
    
    if success:
        query.edit_message_text(
            "✅ **Cleared entire watchlist!**\n\n"
            "📋 Watchlist is now empty.\n"
            "➕ Use menu to add new tokens.",
            parse_mode='Markdown'
        )
    else:
        query.edit_message_text(
            "ℹ️ **Watchlist already empty**\n\n"
            "Nothing to clear.",
            parse_mode='Markdown'
        )

def handle_toggle_notifications(query, context, scheduler_service):
    """Toggle notifications for user"""
    user_id = query.from_user.id
    
    if not scheduler_service:
        query.edit_message_text("❌ Scheduler service not available.")
        return
    
    new_state = scheduler_service.toggle_notifications(user_id)
    status = "ON" if new_state else "OFF"
    
    query.edit_message_text(
        f"🔔 **Turned {status} watchlist notifications!**\n\n"
        f"📢 Status: {'🔔 ON' if new_state else '🔕 OFF'}\n\n"
        "💡 Use Watchlist menu to change again.",
        parse_mode='Markdown'
    )

def handle_back_to_main(query, context):
    """Handle back to main menu"""
    keyboard = [
        [InlineKeyboardButton("📊 Analyze BTC/USDT", callback_data='analyze_BTC/USDT_4h')],
        [InlineKeyboardButton("📈 Analyze ETH/USDT", callback_data='analyze_ETH/USDT_4h')],
        [InlineKeyboardButton("🔍 Select Available Pairs", callback_data='select_pair')],
        [InlineKeyboardButton("✏️ Enter Custom Token", callback_data='custom_token')],
        [InlineKeyboardButton("👁️ Watchlist", callback_data='watchlist_menu')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🚀 **SMC Trading Bot!**

Choose an option below to get started:

💡 **New Features:** 
• Enter any token available on Binance!
• Auto-monitoring with hourly updates!
    """
    
    query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def format_analysis_result(result: dict) -> str:
    """Format analysis results for display"""
    if result.get('error'):
        return f"❌ **Error:** {result.get('message')}"
    
    symbol = result.get('symbol', 'Unknown')
    timeframe = result.get('timeframe', '4h')
    analysis = result.get('analysis', {})
    
    # Extract analysis data
    smc_data = analysis.get('smc_analysis', {})
    current_price = analysis.get('current_price', 0)
    indicators = analysis.get('indicators', {})
    
    # Import format_price function
    try:
        from services.analysis_utils import format_price
    except ImportError:
        def format_price(price):
            return f"${price:.4f}" if price else "N/A"
    
    # Format signal emoji
    signal = smc_data.get('signal', 'NEUTRAL')
    signal_emoji = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"
    
    # Format price change
    price_change = indicators.get('price_change_pct', 0)
    change_emoji = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"
    
    # Format the message
    formatted_msg = f"""
📊 **SMC Analysis: {symbol} ({timeframe})**

💰 **Current Price:** {format_price(current_price)} {change_emoji} {price_change:+.2f}%

{signal_emoji} **Signal:** {signal}
📈 **Confidence:** {smc_data.get('confidence', 0)}%

🔲 **Order Blocks:** {smc_data.get('order_blocks', {}).get('status', 'N/A')}
⚡ **Fair Value Gaps:** {smc_data.get('fair_value_gaps', {}).get('status', 'N/A')}
📊 **Break of Structure:** {smc_data.get('break_of_structure', {}).get('status', 'N/A')}
💧 **Liquidity Zones:** {smc_data.get('liquidity_zones', {}).get('status', 'N/A')}

📊 **RSI:** {indicators.get('rsi', 0):.1f}
💹 **Volume 24h:** ${indicators.get('volume_24h', 0):,.0f}

⏰ **Updated:** {result.get('timestamp', 'N/A')}

⚠️ *For reference only, not financial advice.*
    """
    
    return formatted_msg.strip()

def show_watchlist_menu(query, context):
    """Show watchlist management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Token", callback_data='watchlist_add')],
        [InlineKeyboardButton("📋 View List", callback_data='watchlist_view')],
        [InlineKeyboardButton("🗑️ Remove Token", callback_data='watchlist_remove')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "👁️ **Watchlist Management**\n\n"
        "• Maximum 10 tokens\n"
        "• Auto-updates every hour\n"
        "• Notifications for new signals\n\n"
        "Select action:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def show_help(query):
    """Show help information"""
    help_text = """
ℹ️ **SMC Trading Bot User Guide**

**🎯 Main Features:**
• SMC (Smart Money Concepts) Analysis
• Order Blocks, Fair Value Gaps
• Break of Structure, Liquidity Zones
• Auto-updating Watchlist

**📱 How to Use:**
1️⃣ Select token from menu
2️⃣ Or enter custom token
3️⃣ View analysis results
4️⃣ Add to watchlist if desired

**⚡ Quick Commands:**
• /start - Show menu
• /analysis BTC/USDT 4h - Direct analysis
• /deletemydata - Delete all data

**⚠️ Disclaimer:**
Bot provides analysis only, not financial advice.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')