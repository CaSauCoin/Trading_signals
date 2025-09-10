from telegram import Update
from telegram.ext import CallbackContext
from src.bot import constants as const
from src.bot import keyboards
from src.bot.utils.state_manager import reset_user_state
from src.bot.formatters import format_analysis_result
from .callback_handlers import show_watchlist_menu, perform_analysis

def start_command(update: Update, context: CallbackContext):
    """Send welcome message and main menu."""
    user_id = update.effective_user.id
    reset_user_state(user_id, context)
    
    reply_markup = keyboards.create_main_menu_keyboard()
    update.message.reply_text(const.WELCOME_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

def analysis_command(update: Update, context: CallbackContext):
    """Handle /analysis <SYMBOL> <TIMEFRAME> command."""
    if not context.args or len(context.args) < 1:
        usage_text = "📖 **Usage:** `/analysis BTC/USDT 4h`"
        update.message.reply_text(usage_text, parse_mode='Markdown')
        return

    symbol = context.args[0].upper()
    if '/' not in symbol:
        symbol += "/USDT"
    timeframe = context.args[1].lower() if len(context.args) > 1 else '4h'
    
    loading_msg = update.message.reply_text(f"🔄 Analyzing {symbol} {timeframe}...", parse_mode='Markdown')
    perform_analysis(loading_msg, context, symbol, timeframe)

def watchlist_command(update: Update, context: CallbackContext):
    """Show watchlist menu when user types command."""
    show_watchlist_menu(update, context)

def subscribe_scanner_command(update: Update, context: CallbackContext):
    """Subscribe to market scanner notifications."""
    user_id = update.effective_user.id
    scheduler_service = context.bot_data['scheduler_service']
    
    if scheduler_service.add_scanner_subscriber(user_id):
        update.message.reply_text("✅ You have successfully subscribed to market reversal notifications from the scanner!")
    else:
        update.message.reply_text("ℹ️ You are already subscribed to these notifications.")

def unsubscribe_scanner_command(update: Update, context: CallbackContext):
    """Unsubscribe from market scanner notifications."""
    user_id = update.effective_user.id
    scheduler_service = context.bot_data['scheduler_service']
    
    if scheduler_service.remove_scanner_subscriber(user_id):
        update.message.reply_text("🚫 You have unsubscribed from market scanner notifications.")
    else:
        update.message.reply_text("ℹ️ You are not subscribed to these notifications.")
