from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

def load_watchlists(file_path):
    """Load watchlists from a JSON file."""
    try:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading watchlists: {e}")
    return {}

def save_watchlists(file_path, watchlists):
    """Save watchlists to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(watchlists, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving watchlists: {e}")