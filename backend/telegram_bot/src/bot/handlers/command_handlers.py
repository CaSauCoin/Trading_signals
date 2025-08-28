from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

def start_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Initialize user state if not exists
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    context.bot_data['user_states'][user_id] = {"waiting_for": None}
    
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
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def analysis_command(update: Update, context: CallbackContext):
    if context.args:
        symbol = context.args[0].upper()
        timeframe = context.args[1] if len(context.args) > 1 else '4h'
        
        update.message.reply_text(f"🔄 Analyzing {symbol} {timeframe}...")
        
        # TODO: Implement analysis logic
        try:
            from services.analysis_utils import analyze_with_smc
            
            result = analyze_with_smc(symbol, timeframe)
            
            if result.get('error'):
                update.message.reply_text(
                    f"❌ **Analysis Error for {symbol}**\n\n"
                    f"Details: {result.get('message', 'Unknown error')}",
                    parse_mode='Markdown'
                )
            else:
                # Format the analysis result
                from handlers.callback_handlers import format_analysis_result
                formatted_result = format_analysis_result(result)
                
                # Send analysis result
                update.message.reply_text(formatted_result, parse_mode='Markdown')
                
        except Exception as e:
            update.message.reply_text(
                f"❌ **System Error**\n\n"
                f"Failed to analyze {symbol}: {str(e)}",
                parse_mode='Markdown'
            )
    else:
        update.message.reply_text(
            "📖 **Usage:** `/analysis BTC/USDT 4h`\n\n"
            "• Symbol: BTC/USDT, ETH/USDT, etc.\n"
            "• Timeframe: 15m, 1h, 4h, 1d, 3d, 1w\n\n"
            "💡 Example: `/analysis SOL/USDT 1h`",
            parse_mode='Markdown'
        )

def delete_my_data_command(update: Update, context: CallbackContext):
    """Command to delete all user data"""
    user_id = update.effective_user.id
    
    # Get scheduler service if available
    scheduler_service = context.bot_data.get('scheduler_service')
    
    if scheduler_service:
        deleted = scheduler_service.delete_user_data(user_id)
        if deleted:
            update.message.reply_text(
                "✅ **All your data has been deleted!**\n\n"
                "• Watchlist cleared\n"
                "• Notification settings reset\n"
                "• Analysis history removed\n\n"
                "💡 Use /start to begin again.",
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text(
                "ℹ️ **No data to delete.**\n\n"
                "Your account has no saved data.",
                parse_mode='Markdown'
            )
    else:
        update.message.reply_text(
            "❌ **System Error**\n\n"
            "Cannot delete data at this time. Please try again later.",
            parse_mode='Markdown'
        )