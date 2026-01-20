"""Configuration management for weather forecast generator."""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any


# Default configuration (Athens)
DEFAULT_CONFIG = {
    "location_name": "Athens",
    "widget_id": "58322f1a515da1ca125f09b40b162890",  # okairos.gr widget ID
    "location_url": "https://www.okairos.gr/%CE%B1%CE%B8%CE%AE%CE%BD%CE%B1.html",  # Athens URL
    "timezone": "Europe/Athens",
    "event_time": "",  # Empty = all-day events
    "widget_page_url": "https://USERNAME.github.io/REPO/",
}


def load_config() -> Dict[str, Any]:
    """Load configuration from environment, config.json, or defaults."""
    config = DEFAULT_CONFIG.copy()

    # Try to load from config.json
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config.json: {e}", file=sys.stderr)

    # Environment variables take precedence
    env_mapping = {
        "LOCATION_NAME": "location_name",
        "WIDGET_ID": "widget_id",
        "LOCATION_URL": "location_url",
        "TIMEZONE": "timezone",
        "EVENT_TIME": "event_time",
        "WIDGET_PAGE_URL": "widget_page_url",
    }

    for env_var, config_key in env_mapping.items():
        if env_var in os.environ:
            config[config_key] = os.environ[env_var]

    return config
