from telegram import Update
from telegram.ext import CallbackContext
from src.bot import constants as const
from src.bot import keyboards
from src.bot.utils.state_manager import reset_user_state
from src.bot.utils.menu_manager import delete_active_menu, set_active_menu
from .callback_handlers import show_watchlist_menu, perform_analysis


def start_command(update: Update, context: CallbackContext):
    """Send welcome message and main menu."""
    user_id = update.effective_user.id
    reset_user_state(user_id, context)

    delete_active_menu(user_id, context)

    scheduler_service = context.bot_data['scheduler_service']
    current_sub = scheduler_service.get_user_scanner_subscription(user_id)

    reply_markup = keyboards.create_main_menu_keyboard(current_sub)
    new_menu_message = update.message.reply_text(
        const.WELCOME_TEXT,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    set_active_menu(user_id, context, new_menu_message.message_id)

def analysis_command(update: Update, context: CallbackContext):
    """Handle /analysis <SYMBOL> <TIMEFRAME> command."""
    if not context.args or len(context.args) < 1:
        usage_text = "📖 **Usage:** `/analysis BTC/USDT 4h`"
        update.message.reply_text(usage_text, parse_mode='Markdown')
        return

    symbol = context.args[0].upper()
    timeframe = context.args[1].lower() if len(context.args) > 1 else '4h'
    
    loading_msg = update.message.reply_text(f"🔄 Analyzing {symbol} {timeframe}...", parse_mode='Markdown')
    perform_analysis(loading_msg, context, symbol, timeframe)

def watchlist_command(update: Update, context: CallbackContext):
    """Show watchlist menu when user types command."""
    show_watchlist_menu(update, context)