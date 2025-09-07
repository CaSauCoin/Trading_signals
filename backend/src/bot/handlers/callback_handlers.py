# src/bot/handlers/callback_handlers.py
import logging
from telegram import Update, Message
from telegram.ext import CallbackContext
from telegram.error import BadRequest

from src.bot import constants as const
from src.bot import keyboards
from src.bot import formatters
from src.bot.utils.state_manager import set_user_state

logger = logging.getLogger(__name__)

# --- Reusable Function ---
def show_watchlist_menu(update: Update, context: CallbackContext):
    """
    Show watchlist management menu. 
    This function can be called from command or callback.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    scheduler_service = context.bot_data['scheduler_service']
    
    watchlist = scheduler_service.get_user_watchlist(user_id)
    keyboard = keyboards.create_watchlist_menu_keyboard(watchlist)
    text = "👁️ **Watchlist Management**\n\nTrack your favorite tokens and receive automatic signal notifications."
    
    # If from button (callback), edit old message
    if query:
        try:
            query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Error editing watchlist menu: {e}")
    # If from typed command (/watchlist), send new message
    else:
        update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

# --- Main Router ---
def handle_callback(update: Update, context: CallbackContext):
    """Main router for all callback queries."""
    query = update.callback_query
    query.answer()
    
    parts = query.data.split(':', 3)
    action = parts[0]
    
    if action == const.CB_ANALYZE or action == const.CB_REFRESH:
        _, symbol, timeframe = parts
        perform_analysis(query.message, context, symbol, timeframe)
    elif action == const.CB_TIMEFRAME:
        _, symbol = parts
        handle_timeframe_selection(query, context, symbol)
    elif action == const.CB_WATCHLIST:
        handle_watchlist_router(update, context, parts)
    elif action == const.CB_BACK_MAIN:
        handle_back_to_main(query, context)
    elif action == const.CB_SELECT_PAIR:
        handle_select_pair(query, context)
    elif action == const.CB_CUSTOM_TOKEN:
        handle_custom_token(query, context)
    elif action == const.CB_HELP:
        show_help(query, context)
    else:
        query.edit_message_text("⚠️ Feature is under development...")

# --- Detailed Handlers ---

def perform_analysis(message: Message, context: CallbackContext, symbol: str, timeframe: str):
    """Perform analysis and update message."""
    message.edit_text(f"🔄 **Analyzing {symbol} {timeframe}...**", parse_mode='Markdown')
    analysis_service = context.bot_data['analysis_service']
    result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
    if result.get('error'):
        message.edit_text(f"❌ **Analysis Error**\n\n{result.get('message')}", parse_mode='Markdown')
        return
    formatted_result = formatters.format_analysis_result(result)
    keyboard = keyboards.create_analysis_options_keyboard(symbol, timeframe)
    message.edit_text(formatted_result, reply_markup=keyboard, parse_mode='Markdown')

def handle_watchlist_router(update: Update, context: CallbackContext, parts: list):
    """Route watchlist-related actions."""
    query = update.callback_query
    sub_action = parts[1]
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']

    if sub_action == 'menu':
        show_watchlist_menu(update, context)

    elif sub_action == 'view':
        watchlist = scheduler_service.get_user_watchlist(user_id)
        text = f"📋 **Your Watchlist ({len(watchlist)}/10):**\n\n"
        if not watchlist:
            text += "Your watchlist is empty."
        else:
            for i, item in enumerate(watchlist, 1):
                text += f"{i}. **{item['symbol']}** (Timeframe: {item['timeframe']})\n"
        
        keyboard = keyboards.create_watchlist_menu_keyboard(watchlist)
        query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    elif sub_action == 'add_prompt':
        set_user_state(user_id, context, const.STATE_ADD_WATCHLIST)
        text = "➕ **Add to Watchlist**\n\nEnter token and timeframe in the format:\n`TOKEN timeframe`\n\n*Example:*\n`PEPE 4h`\n`BTC/USDT 1d`"
        query.edit_message_text(text, parse_mode='Markdown')
        
    elif sub_action == 'add_direct':
        if len(parts) < 4:
            logger.error(f"Callback 'add_direct' insufficient parameters: {query.data}")
            return
        _, _, symbol, timeframe = parts
        result = scheduler_service.add_to_watchlist(user_id, symbol, timeframe)
        query.answer(result['message'], show_alert=True)
        if result['success']:
            keyboard = keyboards.create_post_add_watchlist_keyboard()
            text = f"✅ **Success!**\n\n{result['message']}\n\nWhat would you like to do next?"
            query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    elif sub_action == 'remove_menu':
        watchlist = scheduler_service.get_user_watchlist(user_id)
        if not watchlist:
            query.answer("Your watchlist is empty!", show_alert=True)
            return
        keyboard = keyboards.create_remove_token_keyboard(watchlist)
        query.edit_message_text("🗑️ Choose the token you want to remove from watchlist:", reply_markup=keyboard, parse_mode='Markdown')
        
    elif sub_action == 'remove_confirm':
        if len(parts) < 4:
            logger.error(f"Callback 'remove_confirm' insufficient parameters: {query.data}")
            return
        _, _, symbol, timeframe = parts
        success = scheduler_service.remove_from_watchlist(user_id, symbol, timeframe)
        if success:
            query.answer(f"Removed {symbol} ({timeframe})", show_alert=True)
            show_watchlist_menu(update, context)
            
def handle_back_to_main(query, context: CallbackContext):
    """Return to main menu."""
    keyboard = keyboards.create_main_menu_keyboard()
    try:
        query.edit_message_text(const.WELCOME_TEXT, reply_markup=keyboard, parse_mode='Markdown')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Undefined BadRequest error: {e}")

def handle_timeframe_selection(query, context, symbol):
    """Show timeframe selection menu."""
    keyboard = keyboards.create_timeframe_selection_keyboard(symbol)
    query.edit_message_text(f"⏱️ **Choose timeframe for {symbol}:**", reply_markup=keyboard, parse_mode='Markdown')
    
def handle_select_pair(query, context: CallbackContext):
    """Show popular token pairs selection menu."""
    keyboard = keyboards.create_popular_pairs_keyboard()
    query.edit_message_text("🔍 **Choose Popular Token Pair:**", reply_markup=keyboard, parse_mode='Markdown')

def handle_custom_token(query, context: CallbackContext):
    """Request user to enter custom token."""
    user_id = query.from_user.id
    set_user_state(user_id, context, const.STATE_CUSTOM_TOKEN)
    query.edit_message_text(
        "✏️ **Enter Custom Token**\n\nSend the token name you want to analyze (example: BTC, PEPE, SOL/USDT).",
        parse_mode='Markdown'
    )

def show_help(query, context: CallbackContext):
    """Show help message."""
    keyboard = keyboards.create_back_to_main_keyboard()
    query.edit_message_text(const.HELP_TEXT, reply_markup=keyboard, parse_mode='Markdown')