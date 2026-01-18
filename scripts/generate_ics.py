#!/usr/bin/env python3
"""
Weather Forecast ICS Generator

Fetches weather forecast from Open-Meteo API and generates an RFC 5545-compliant
iCalendar file (forecast.ics) with daily weather events.

Configuration:
- Environment variables (highest priority)
- config.json in repository root
- Hardcoded defaults for Athens

Usage:
    python scripts/generate_ics.py
"""

import os
import json
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen
from urllib.error import URLError
from pathlib import Path
from typing import Optional, Dict, Any
import re


# Default configuration (Athens)
DEFAULT_CONFIG = {
    "location_name": "Athens",
    "latitude": 37.9838,
    "longitude": 23.7275,
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
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        "TIMEZONE": "timezone",
        "EVENT_TIME": "event_time",
        "WIDGET_PAGE_URL": "widget_page_url",
    }
    
    for env_var, config_key in env_mapping.items():
        if env_var in os.environ:
            value = os.environ[env_var]
            # Convert numeric strings for latitude/longitude
            if config_key in ("latitude", "longitude"):
                try:
                    value = float(value)
                except ValueError:
                    print(f"Warning: Invalid {env_var}, using default", file=sys.stderr)
                    continue
            config[config_key] = value
    
    return config


def fetch_forecast(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Fetch weather forecast from Open-Meteo API.
    
    Returns forecast data with keys: daily, daily_units, timezone
    """
    # Open-Meteo free API endpoint
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        f"&daily=temperature_2m_min,temperature_2m_max,"
        f"precipitation_sum,precipitation_probability_max,windspeed_10m_max"
        f"&timezone=auto"
        f"&forecast_days=7"
    )
    
    try:
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except (URLError, json.JSONDecodeError, OSError) as e:
        print(f"Error fetching forecast: {e}", file=sys.stderr)
        sys.exit(1)


def fold_line(line: str, max_length: int = 75) -> str:
    """
    Fold a line according to RFC 5545: lines longer than max_length
    are split with CRLF followed by a single space.
    """
    if len(line.encode("utf-8")) <= max_length:
        return line
    
    # For simplicity, we'll fold at character boundaries (not octet-perfect)
    # since most weather data is ASCII
    folded_lines = []
    current_line = ""
    
    for char in line:
        test_line = current_line + char
        if len(test_line.encode("utf-8")) > max_length:
            folded_lines.append(current_line)
            current_line = " " + char  # Continuation line starts with space
        else:
            current_line = test_line
    
    if current_line:
        folded_lines.append(current_line)
    
    return "\r\n".join(folded_lines)


def escape_ics_text(text: str) -> str:
    """Escape special characters in ICS text fields."""
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\n", "\\n")
    text = text.replace("\r", "")
    return text


def generate_ics(config: Dict[str, Any], forecast: Dict[str, Any]) -> str:
    """Generate RFC 5545-compliant iCalendar content."""
    ics_lines = []
    
    # Calendar header
    ics_lines.append("BEGIN:VCALENDAR")
    ics_lines.append("VERSION:2.0")
    ics_lines.append("PRODID:-//Weather Forecast Calendar//GitHub Pages//EN")
    ics_lines.append("CALSCALE:GREGORIAN")
    ics_lines.append("METHOD:PUBLISH")
    ics_lines.append(f"X-WR-CALNAME:Daily Weather Forecast - {config['location_name']}")
    ics_lines.append(f"X-WR-TIMEZONE:{config['timezone']}")
    ics_lines.append("X-WR-CALDESC:Daily weather forecast")
    
    # Get daily forecast data
    daily = forecast.get("daily", {})
    times = daily.get("time", [])
    temps_min = daily.get("temperature_2m_min", [])
    temps_max = daily.get("temperature_2m_max", [])
    precip_sum = daily.get("precipitation_sum", [])
    precip_prob = daily.get("precipitation_probability_max", [])
    wind_speed = daily.get("windspeed_10m_max", [])
    daily_units = forecast.get("daily_units", {})
    
    temp_unit = daily_units.get("temperature_2m_max", "°C")
    precip_unit = daily_units.get("precipitation_sum", "mm")
    wind_unit = daily_units.get("windspeed_10m_max", "km/h")
    
    # Generate events for each forecast day
    for idx, date_str in enumerate(times):
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, IndexError):
            continue
        
        temp_min = temps_min[idx] if idx < len(temps_min) else "N/A"
        temp_max = temps_max[idx] if idx < len(temps_max) else "N/A"
        precip = precip_sum[idx] if idx < len(precip_sum) else 0
        precip_p = precip_prob[idx] if idx < len(precip_prob) else 0
        wind = wind_speed[idx] if idx < len(wind_speed) else "N/A"
        
        # Build description
        description_parts = []
        
        if temp_min != "N/A" and temp_max != "N/A":
            description_parts.append(f"Temperature: {temp_min}{temp_unit} – {temp_max}{temp_unit}")
        
        if isinstance(precip_p, (int, float)) and precip_p >= 0:
            description_parts.append(f"Precipitation Probability: {int(precip_p)}%")
        
        if isinstance(precip, (int, float)) and precip > 0:
            description_parts.append(f"Precipitation: {precip}{precip_unit}")
        
        if wind != "N/A":
            description_parts.append(f"Wind: {wind}{wind_unit}")
        
        description_parts.append(f"\nVisit the weather widget: {config['widget_page_url']}")
        
        description = escape_ics_text("\\n".join(description_parts))
        
        # Create event
        ics_lines.append("BEGIN:VEVENT")
        
        # Stable UID based on date
        date_str_clean = date_obj.strftime("%Y%m%d")
        ics_lines.append(f"UID:weather-{date_str_clean}@github-pages")
        
        # DTSTAMP in UTC (current time)
        dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ics_lines.append(f"DTSTAMP:{dtstamp}")
        
        # DTSTART and DTEND
        if config["event_time"].strip():
            # Timed event
            try:
                from datetime import time
                time_parts = config["event_time"].split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                event_time = time(hour=hour, minute=minute)
                start_dt = datetime.combine(date_obj, event_time)
                end_dt = start_dt + timedelta(minutes=15)
                
                ics_lines.append(f"DTSTART;TZID={config['timezone']}:{start_dt.strftime('%Y%m%dT%H%M%S')}")
                ics_lines.append(f"DTEND;TZID={config['timezone']}:{end_dt.strftime('%Y%m%dT%H%M%S')}")
            except (ValueError, IndexError):
                # Fall back to all-day if time parsing fails
                ics_lines.append(f"DTSTART;VALUE=DATE:{date_str_clean}")
                next_day = date_obj + timedelta(days=1)
                ics_lines.append(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}")
        else:
            # All-day event
            ics_lines.append(f"DTSTART;VALUE=DATE:{date_str_clean}")
            next_day = date_obj + timedelta(days=1)
            ics_lines.append(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}")
        
        # Event summary
        summary = f"Today's Weather — {config['location_name']}"
        ics_lines.append(f"SUMMARY:{escape_ics_text(summary)}")
        
        # Event description (will be folded)
        ics_lines.append(f"DESCRIPTION:{description}")
        
        ics_lines.append("STATUS:CONFIRMED")
        ics_lines.append("TRANSP:TRANSPARENT")
        ics_lines.append("END:VEVENT")
    
    ics_lines.append("END:VCALENDAR")
    
    # Join with CRLF and apply line folding
    ics_content = "\r\n".join(ics_lines)
    
    # Apply line folding to each line
    folded_lines = []
    for line in ics_content.split("\r\n"):
        folded_lines.append(fold_line(line))
    
    final_ics = "\r\n".join(folded_lines) + "\r\n"
    
    return final_ics


def main():
    """Main entry point."""
    config = load_config()
    
    print(f"Fetching forecast for {config['location_name']} "
          f"({config['latitude']}, {config['longitude']})...", file=sys.stderr)
    
    forecast = fetch_forecast(config["latitude"], config["longitude"])
    
    print("Generating ICS...", file=sys.stderr)
    ics_content = generate_ics(config, forecast)
    
    # Write to forecast.ics in repo root
    output_path = Path(__file__).parent.parent / "forecast.ics"
    
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            f.write(ics_content)
        print(f"Successfully wrote {output_path}", file=sys.stderr)
    except IOError as e:
        print(f"Error writing ICS file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
