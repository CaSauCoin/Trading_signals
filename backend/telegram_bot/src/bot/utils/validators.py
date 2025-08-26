import re

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

def validate_timeframe(timeframe: str) -> bool:
    """Validate timeframe format"""
    valid_timeframes = ['15m', '1h', '4h', '1d', '3d', '1w']
    return timeframe.lower() in valid_timeframes

def is_within_watchlist_limit(user_watchlist):
    """Check if the user has reached the watchlist limit."""
    return len(user_watchlist) < 5

def is_token_in_watchlist(user_watchlist, token):
    """Check if the token is already in the user's watchlist."""
    return any(item['symbol'] == token for item in user_watchlist)

def is_valid_symbol_on_binance(symbol):
    """Validate if the symbol exists on Binance."""
    # This function should implement the logic to check the symbol on Binance
    pass  # Placeholder for actual implementation