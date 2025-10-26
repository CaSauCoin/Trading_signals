import logging
import json
from typing import Dict, List, Any
import os

logger = logging.getLogger(__name__)

# Define file path and watchlist limit
PERSISTENCE_FILE = 'bot_data.json'
WATCHLIST_LIMIT = 3

class SchedulerService:
    """Manage Watchlist and Subscribers list with file persistence."""

    def __init__(self):
        self.db = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file on startup."""
        if os.path.exists(PERSISTENCE_FILE):
            try:
                with open(PERSISTENCE_FILE, 'r') as f:
                    data = json.load(f)
                    # Convert watchlist keys to int
                    if 'watchlists' in data:
                        data['watchlists'] = {int(k): v for k, v in data['watchlists'].items()}
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading data from {PERSISTENCE_FILE}: {e}")
        # Return default structure if file doesn't exist
        return {"watchlists": {}, "scanner_subscribers": []}

    def _save_data(self):
        """Save current state to JSON file."""
        try:
            with open(PERSISTENCE_FILE, 'w') as f:
                json.dump(self.db, f, indent=4)
        except IOError as e:
            logger.error(f"Cannot save data to {PERSISTENCE_FILE}: {e}")

    # --- Watchlist Methods ---
    def get_user_watchlist(self, user_id: int) -> List[Dict[str, Any]]:
        return self.db.get("watchlists", {}).get(user_id, [])

    def add_to_watchlist(self, user_id: int, symbol: str, timeframe: str) -> Dict[str, Any]:
        watchlist = self.get_user_watchlist(user_id)
        if len(watchlist) >= WATCHLIST_LIMIT:
            return {'success': False, 'message': f'Watchlist is full! (Maximum {WATCHLIST_LIMIT} tokens).'}
        if any(item['symbol'] == symbol and item['timeframe'] == timeframe for item in watchlist):
            return {'success': False, 'message': f'Token {symbol} ({timeframe}) already exists in watchlist.'}
        
        self.db.setdefault("watchlists", {}).setdefault(user_id, []).append({'symbol': symbol, 'timeframe': timeframe})
        self._save_data()
        logger.info(f"User {user_id} added {symbol} ({timeframe}) to watchlist.")
        return {'success': True, 'message': f'Added {symbol} ({timeframe}) to watchlist.'}

    def remove_from_watchlist(self, user_id: int, symbol: str, timeframe: str) -> bool:
        # Logic remains the same, just need to save
        watchlist = self.get_user_watchlist(user_id)
        item_to_remove = next((item for item in watchlist if item['symbol'] == symbol and item['timeframe'] == timeframe), None)
        if item_to_remove:
            watchlist.remove(item_to_remove)
            self._save_data()
            return True
        return False
        
    def get_all_watchlists(self) -> Dict[int, List[Dict[str, Any]]]:
        return self.db.get("watchlists", {})

    # --- Scanner Subscriber Methods ---
    def get_scanner_subscribers(self) -> List[int]:
        """Get list of user IDs who have subscribed."""
        return self.db.get("scanner_subscribers", [])

    def add_scanner_subscriber(self, user_id: int) -> bool:
        """Add user to subscription list."""
        subscribers = self.get_scanner_subscribers()
        if user_id not in subscribers:
            subscribers.append(user_id)
            self.db["scanner_subscribers"] = subscribers
            self._save_data()
            logger.info(f"User {user_id} subscribed to market scan notifications.")
            return True
        return False # Already subscribed

    def remove_scanner_subscriber(self, user_id: int) -> bool:
        """Remove user from subscription list."""
        subscribers = self.get_scanner_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            self.db["scanner_subscribers"] = subscribers
            self._save_data()
            logger.info(f"User {user_id} unsubscribed from market scan notifications.")
            return True
        return False # Not in the list