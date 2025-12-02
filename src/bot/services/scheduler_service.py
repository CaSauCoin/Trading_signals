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
                    if 'watchlists' in data:
                        data['watchlists'] = {int(k): v for k, v in data['watchlists'].items()}
                    if 'watchlist_subscribers' in data:
                        data['watchlist_subscribers'] = {int(k): v for k, v in data['watchlist_subscribers'].items()}
                    if 'notification_states' in data:
                        data['notification_states'] = {int(k): v for k, v in data['notification_states'].items()}

                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading data from {PERSISTENCE_FILE}: {e}")

        return {
            "watchlists": {},
            "scanner_subscribers": {},
            "watchlist_subscribers": {},
            "notification_states": {}
        }

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
    def get_scanner_subscribers(self) -> Dict[int, str]:
        """Get dict of {user_id: timeframe}."""
        return self.db.get("scanner_subscribers", {})

    def get_user_scanner_subscription(self, user_id: int) -> str | None:
        """Get the specific timeframe a user is subscribed to."""
        return self.db.get("scanner_subscribers", {}).get(user_id)

    def add_scanner_subscriber(self, user_id: int, timeframe: str) -> bool:
        """Add or update user's subscription timeframe."""
        self.db.setdefault("scanner_subscribers", {})[user_id] = timeframe
        self._save_data()
        logger.info(f"User {user_id} subscribed to market scan ({timeframe}).")
        return True

    def remove_scanner_subscriber(self, user_id: int) -> bool:
        """Remove user from subscription list."""
        subscribers = self.get_scanner_subscribers()
        if user_id in subscribers:
            subscribers.pop(user_id)
            self._save_data()
            logger.info(f"User {user_id} unsubscribed from market scan.")
            return True
        return False

    def get_watchlist_subscribers(self) -> Dict[int, str]:
        """Get dict of {user_id: interval_timeframe} for watchlist notifications."""
        return self.db.get("watchlist_subscribers", {})

    def get_user_watchlist_subscription(self, user_id: int) -> str | None:
        """Get the specific interval a user is subscribed to for their watchlist."""
        return self.db.get("watchlist_subscribers", {}).get(user_id)

    def set_watchlist_subscription(self, user_id: int, interval: str) -> bool:
        """Add or update user's watchlist notification interval."""
        self.db.setdefault("watchlist_subscribers", {})[user_id] = interval
        self._save_data()
        logger.info(f"User {user_id} set watchlist notification interval to {interval}.")
        return True

    def remove_watchlist_subscription(self, user_id: int) -> bool:
        """Remove user from watchlist notification subscription."""
        subscribers = self.get_watchlist_subscribers()
        if user_id in subscribers:
            subscribers.pop(user_id)
            self._save_data()
            logger.info(f"User {user_id} unsubscribed from watchlist notifications.")
            return True
        return False

    def get_notification_state(self, user_id: int, symbol: str, timeframe: str) -> str | None:
        """Get the last sent suggestion for a specific user and token."""
        state_key = f"{symbol.upper()}_{timeframe.lower()}"
        return self.db.get("notification_states", {}).get(user_id, {}).get(state_key)

    def update_notification_state(self, user_id: int, symbol: str, timeframe: str, suggestion: str):
        """Update the last sent suggestion for a user and token."""
        state_key = f"{symbol.upper()}_{timeframe.lower()}"

        self.db.setdefault("notification_states", {}).setdefault(user_id, {})[state_key] = suggestion
        self._save_data()
        logger.info(f"Updated notification state for user {user_id}, {state_key}: {suggestion[:30]}...")