def format_welcome_message():
    welcome_text = """
🚀 **Trading Bot SMC!**

Chọn một tùy chọn bên dưới để bắt đầu:

💡 **Mới:** 
• Nhập bất kỳ token nào trên Binance!
• Theo dõi tự động với cập nhật mỗi giờ!
    """
    return welcome_text

def format_watchlist_info(user_watchlist):
    watchlist_info = f"**📊 DANH SÁCH THEO DÕI**\n\n"
    watchlist_info += f"👁️ **Đang theo dõi:** {len(user_watchlist)}/5 tokens\n"
    watchlist_info += f"⏱️ **Cập nhật:** Mỗi giờ tự động\n\n"
    
    if user_watchlist:
        watchlist_info += "**Tokens đang theo dõi:**\n"
        for i, item in enumerate(user_watchlist, 1):
            watchlist_info += f"{i}. {item['symbol']} ({item['timeframe']})\n"
    else:
        watchlist_info += "📝 Chưa có token nào trong danh sách.\n"
        watchlist_info += "Nhấn ➕ để thêm token đầu tiên!"
    
    return watchlist_info

def format_analysis_result(symbol: str, timeframe: str, analysis_data: dict) -> str:
    """Format analysis results for Telegram message"""
    # TODO: Implement message formatting logic
    return f"📊 **Phân tích {symbol} - {timeframe}**\n\n⚠️ Chức năng đang được phát triển..."

def format_error_message(error_type: str, details: str = "") -> str:
    """Format error messages"""
    error_messages = {
        "invalid_token": "❌ Token không hợp lệ hoặc không tồn trên Binance",
        "api_error": "⚠️ Lỗi kết nối API, vui lòng thử lại sau",
        "analysis_error": "❌ Không thể phân tích token này"
    }
    
    base_message = error_messages.get(error_type, "❌ Đã xảy ra lỗi")
    if details:
        return f"{base_message}\n\n{details}"
    return base_message