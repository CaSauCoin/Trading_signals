import json
import os
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class FileStorage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.watchlist_file = self.data_dir / "watchlists.json"
        self.user_state_file = self.data_dir / "user_states.json"
    
    def load_watchlists(self) -> Dict[str, List[Dict]]:
        """Load user watchlists from file"""
        try:
            if self.watchlist_file.exists():
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading watchlists: {e}")
            return {}
    
    def save_watchlists(self, watchlists: Dict[str, List[Dict]]):
        """Save user watchlists to file"""
        try:
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(watchlists, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving watchlists: {e}")
    
    def load_user_states(self) -> Dict[str, Dict]:
        """Load user states from file"""
        try:
            if self.user_state_file.exists():
                with open(self.user_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading user states: {e}")
            return {}
    
    def save_user_states(self, user_states: Dict[str, Dict]):
        """Save user states to file"""
        try:
            with open(self.user_state_file, 'w', encoding='utf-8') as f:
                json.dump(user_states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving user states: {e}")