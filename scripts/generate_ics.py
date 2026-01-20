#!/usr/bin/env python3
"""
Weather Forecast ICS Generator

Fetches weather forecast from okairos.gr and generates an RFC 5545-compliant
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
from typing import Optional, Dict, Any, List
import re


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


def create_text_widget(config: Dict[str, Any], forecast: Dict[str, Any]) -> str:
    """Create a beautiful text-based weather widget matching okairos.gr format."""
    location = config['location_name']
    temp_max = forecast.get('temp_max', 'N/A')
    temp_min = forecast.get('temp_min', 'N/A')
    description = forecast.get('description', '')
    emoji = get_weather_emoji(description, temp_max)
    date_obj = forecast.get('date', datetime.now().date())
    
    # Get day name in Greek (simplified)
    day_names_greek = {
        0: 'Δευτέρα',    # Monday
        1: 'Τρίτη',       # Tuesday
        2: 'Τετάρτη',     # Wednesday
        3: 'Πέμπτη',      # Thursday
        4: 'Παρασκευή',   # Friday
        5: 'Σάββατο',     # Saturday
        6: 'Κυριακή'      # Sunday
    }
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    # Check if it's today
    if date_obj == datetime.now().date():
        day_name = 'Σήμερα'  # Today
    elif date_obj == (datetime.now().date() + timedelta(days=1)):
        day_name = 'Αύριο'  # Tomorrow
    else:
        weekday = date_obj.weekday()
        day_name = day_names_greek.get(weekday, date_obj.strftime('%d/%m'))
    
    # Build widget in okairos.gr style
    widget_lines = []
    widget_lines.append("╔═════════════════════════════════╗")
    widget_lines.append(f"║  {emoji}  ΚΑΙΡΟΣ - {location.upper():<16} ║")
    widget_lines.append("╠═════════════════════════════════╣")
    widget_lines.append(f"║  {day_name:<29} ║")
    
    # Current/Max temperature
    if temp_max != "N/A":
        temp_display = temp_max.replace('°C', '°')
        widget_lines.append(f"║  🌡️  {temp_display:<26} ║")
    
    # Max/Min section
    if temp_max != "N/A" and temp_min != "N/A":
        max_temp = temp_max.replace('°C', '°')
        min_temp = temp_min.replace('°C', '°')
        widget_lines.append("║  ─────────────────────────────  ║")
        widget_lines.append(f"║   Max      Min                  ║")
        widget_lines.append(f"║   {max_temp:<8} {min_temp:<8}            ║")
    
    # Weather condition
    if description and description not in ["Check okairos.gr", "Check widget for details"]:
        widget_lines.append("║  ─────────────────────────────  ║")
        widget_lines.append(f"║  📋 {description:<26} ║")
    
    # Wind (placeholder - will be populated when scraped)
    widget_lines.append("║  ─────────────────────────────  ║")
    widget_lines.append("║  💨 Wind: Check widget          ║")
    
    # Sunrise/Sunset (placeholder - will be populated when scraped)
    widget_lines.append("║  ─────────────────────────────  ║")
    widget_lines.append("║  🌅 Ανατολή/Δύση: --:-- / --:-- ║")
    
    widget_lines.append("╠═════════════════════════════════╣")
    widget_lines.append("║  🔗 okairos.gr                  ║")
    widget_lines.append("╚═════════════════════════════════╝")
    
    return "\\n".join(widget_lines)


def create_text_widget_panel(config: Dict[str, Any], forecasts: List[Dict[str, Any]], days: int = 4) -> str:
    """
    Create a multi-day, horizontal, text widget similar to okairos.gr layout.

    Each column shows: day label, icon, main temp, Max/Min, wind, sunrise/sunset.
    """
    loc = config["location_name"]
    now = datetime.now().date()

    day_names_greek = {
        0: 'Δευτέρα', 1: 'Τρίτη', 2: 'Τετάρτη', 3: 'Πέμπτη',
        4: 'Παρασκευή', 5: 'Σάββατο', 6: 'Κυριακή'
    }

    def day_label(d):
        if d == now:
            return "Σήμερα"
        if d == now + timedelta(days=1):
            return "Αύριο"
        return day_names_greek.get(d.weekday(), d.strftime("%d/%m"))

    def norm_temp(t: str) -> str:
        # "13°C" -> "13°", "N/A" stays
        if not t or t == "N/A":
            return "N/A"
        return t.replace("°C", "°").strip()

    def col_lines(fc: Dict[str, Any]) -> List[str]:
        d = fc["date"]
        tmax = norm_temp(fc.get("temp_max", "N/A"))
        tmin = norm_temp(fc.get("temp_min", "N/A"))
        desc = fc.get("description", "") or ""
        emoji = get_weather_emoji(desc, fc.get("temp_max", ""))

        # "main" temp in the widget image is big; we'll use max as the prominent value.
        main_temp = tmax if tmax != "N/A" else "N/A"

        # Optional fields if you later scrape them:
        wind = fc.get("wind") or "-- bf"
        wind_dir = fc.get("wind_dir") or "—"
        sunrise = fc.get("sunrise") or "--:--"
        sunset = fc.get("sunset") or "--:--"

        # Keep each line short; the panel will pad them.
        return [
            f"{day_label(d)}",
            f"{emoji}",
            f"{main_temp}",
            f"Max/Min",
            f"{tmax} {tmin}",
            f"{wind}",
            f"{wind_dir}",
            f"{sunrise}",
            f"{sunset}",
        ]

    cols = [col_lines(fc) for fc in forecasts[:days]]

    # Panel formatting
    # Tune width to your taste; 14–18 works well for 4 columns.
    col_w = 16
    header = f"καιρός {loc}".center(col_w * len(cols))

    def pad(s: str) -> str:
        s = s if s is not None else ""
        # prevent overly long strings breaking alignment
        if len(s) > col_w:
            s = s[:col_w - 1] + "…"
        return s.center(col_w)

    # Build rows by zipping column line lists
    rows = []
    for r in range(len(cols[0])):
        row = " ".join(pad(cols[c][r]) for c in range(len(cols)))
        rows.append(row)

    top = "┌" + "─" * (len(rows[0]) - 2) + "┐"
    mid = "│" + header.center(len(rows[0]) - 2) + "│"
    sep = "├" + "─" * (len(rows[0]) - 2) + "┤"
    bottom = "└" + "─" * (len(rows[0]) - 2) + "┘"

    body = "\n".join("│" + r[1:-1] + "│" if r.startswith(" ") else "│" + r + "│" for r in rows)

    return "\n".join([top, mid, sep, body, bottom])


def get_weather_emoji(description: str, temp: str = "") -> str:
    """Return appropriate weather emoji based on description."""
    desc_lower = description.lower()
    
    # Temperature-based if no specific weather
    try:
        temp_val = int(re.search(r'\d+', temp).group()) if temp and re.search(r'\d+', temp) else 20
        if temp_val >= 30:
            return "🔥"
        elif temp_val <= 5:
            return "🥶"
    except (ValueError, AttributeError):
        pass
    
    # Weather condition emojis
    if any(word in desc_lower for word in ['καταιγίδα', 'βροχή', 'rain', 'thunderstorm']):
        return "⛈️"
    elif any(word in desc_lower for word in ['βροχ', 'νεροπ', 'drizzle', 'shower']):
        return "🌧️"
    elif any(word in desc_lower for word in ['χιόν', 'snow']):
        return "❄️"
    elif any(word in desc_lower for word in ['ομίχλη', 'fog', 'mist']):
        return "🌫️"
    elif any(word in desc_lower for word in ['νεφ', 'cloud', 'συννεφ']):
        return "☁️"
    elif any(word in desc_lower for word in ['αίθρι', 'ηλιόλ', 'sunny', 'clear', 'sun']):
        return "☀️"
    elif any(word in desc_lower for word in ['άνεμ', 'wind']):
        return "💨"
    else:
        return "🌤️"  # Default: partly cloudy


def fetch_forecast_from_widget(widget_id: str) -> List[Dict[str, Any]]:
    """
    Fetch weather forecast from okairos.gr widget API.
    
    Returns list of forecast data dictionaries with keys:
    - date: datetime.date object
    - temp_min: minimum temperature (str)
    - temp_max: maximum temperature (str)
    - temp_current: current temperature (str, optional)
    - description: weather description (str)
    - precipitation: precipitation info (str, optional)
    - wind: wind speed (str, optional)
    - wind_dir: wind direction (str, optional)
    - sunrise: sunrise time (str, optional)
    - sunset: sunset time (str, optional)
    """
    # The actual widget data is at /widget/get/ not /widget/loader/
    widget_url = f"https://www.okairos.gr/widget/get/{widget_id}"
    
    try:
        with urlopen(widget_url, timeout=10) as response:
            html = response.read().decode("utf-8")
        
        forecasts = []
        today = datetime.now().date()
        
        # Parse the HTML table structure
        # Extract all temperature values (main temps shown in day-icon row)
        main_temps = re.findall(r'<strong>(\d+)&deg;</strong>', html)
        
        # Extract max/min temps from the min-max-temp tables
        max_temps = re.findall(r'<td class="max-temp">(\d+)&deg;</td>', html)
        min_temps = re.findall(r'<td class="min-temp">(\d+)&deg;</td>', html)
        
        # Extract sunrise/sunset times
        sunrise_times = re.findall(r'<div class="rise">(\d{2}:\d{2})</div>', html)
        sunset_times = re.findall(r'<div class="set">(\d{2}:\d{2})</div>', html)
        
        # Extract weather condition icons (e.g., n300, d430, d300, d400)
        # n = night, d = day; numbers indicate condition codes
        icon_codes = re.findall(r'<div class="icon ([nd]\d+)"></div>', html)
        
        # Map icon codes to descriptions (simplified mapping)
        def icon_to_description(code):
            if not code:
                return "Clear"
            num = int(code[1:]) if len(code) > 1 else 0
            if num >= 500:  # Rain/storms
                return "Rain"
            elif num >= 400:  # Cloudy/overcast
                return "Cloudy"
            elif num >= 300:  # Partly cloudy
                return "Partly Cloudy"
            elif num >= 200:  # Snow
                return "Snow"
            else:  # Clear
                return "Clear"
        
        # The widget typically shows 4 days
        num_days = min(len(main_temps), len(max_temps), len(min_temps))
        
        for i in range(num_days):
            forecast_date = today + timedelta(days=i)
            forecasts.append({
                "date": forecast_date,
                "temp_current": f"{main_temps[i]}°C" if i < len(main_temps) else None,
                "temp_max": f"{max_temps[i]}°C" if i < len(max_temps) else "N/A",
                "temp_min": f"{min_temps[i]}°C" if i < len(min_temps) else "N/A",
                "description": icon_to_description(icon_codes[i]) if i < len(icon_codes) else "Clear",
                "precipitation": None,  # Not in widget
                "wind": None,  # Not in this widget format
                "wind_dir": None,  # Not in this widget format
                "sunrise": sunrise_times[i] if i < len(sunrise_times) else None,
                "sunset": sunset_times[i] if i < len(sunset_times) else None,
            })
        
        # If we got less than 7 days, fill in the rest with the last day's data
        while len(forecasts) < 7:
            last_forecast = forecasts[-1] if forecasts else None
            if last_forecast:
                forecast_date = today + timedelta(days=len(forecasts))
                forecasts.append({
                    "date": forecast_date,
                    "temp_current": None,
                    "temp_max": last_forecast["temp_max"],
                    "temp_min": last_forecast["temp_min"],
                    "description": last_forecast["description"],
                    "precipitation": None,
                    "wind": None,
                    "wind_dir": None,
                    "sunrise": last_forecast["sunrise"],
                    "sunset": last_forecast["sunset"],
                })
            else:
                break
        
        print(f"  Parsed {num_days} days from widget API", file=sys.stderr)
        return forecasts
        
    except (URLError, OSError) as e:
        print(f"Error fetching widget data: {e}", file=sys.stderr)
        # Fall back to minimal data
        today = datetime.now().date()
        return [{
            "date": today + timedelta(days=i),
            "temp_min": "N/A",
            "temp_max": "N/A",
            "description": "Check okairos.gr",
            "precipitation": None,
            "wind": None,
            "wind_dir": None,
            "sunrise": None,
            "sunset": None,
        } for i in range(7)]


def fetch_forecast(location_url: str, widget_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch weather forecast from okairos.gr.
    
    If widget_id is provided, fetches from widget API (preferred).
    Otherwise falls back to scraping the location page.
    
    Returns list of forecast data dictionaries with keys:
    - date: datetime.date object
    - temp_min: minimum temperature (str)
    - temp_max: maximum temperature (str)
    - description: weather description (str)
    - precipitation: precipitation info (str, optional)
    - wind: wind info (str, optional)
    """
    # Try widget API first if widget_id is available
    if widget_id and widget_id != "get_from_okairos_widget_generator":
        return fetch_forecast_from_widget(widget_id)
    
    # Fallback to page scraping
    try:
        with urlopen(location_url, timeout=10) as response:
            html = response.read().decode("utf-8")
            
        forecasts = []
        
        # Try to extract actual weather data from the HTML
        # Look for temperature patterns
        temp_patterns = [
            r'(\d+)°\s*[–-]\s*(\d+)°',  # "15° – 24°"
            r'(\d+)°C\s*[–-]\s*(\d+)°C',  # "15°C – 24°C"
            r'min[^\d]*(\d+)[^\d]*max[^\d]*(\d+)',  # min/max format
        ]
        
        # Look for weather description in Greek
        weather_keywords = {
            'αίθριος': 'Clear', 'αίθρια': 'Clear',
            'ηλιοφάνεια': 'Sunny', 'ηλιόλουστος': 'Sunny',
            'νεφώσεις': 'Cloudy', 'συννεφιά': 'Cloudy',
            'βροχή': 'Rain', 'βροχές': 'Rain',
            'καταιγίδα': 'Thunderstorm', 'καταιγίδες': 'Thunderstorms',
            'χιόνι': 'Snow', 'χιονόπτωση': 'Snow',
            'ομίχλη': 'Fog',
            'άνεμοι': 'Windy', 'άνεμος': 'Windy',
        }
        
        # Extract what we can, but provide sensible defaults
        temp_min = "N/A"
        temp_max = "N/A"
        description = "Check widget for details"
        
        # Try to find temperature data
        for pattern in temp_patterns:
            match = re.search(pattern, html)
            if match:
                temp_min = match.group(1) + "°C"
                temp_max = match.group(2) + "°C"
                break
        
        # Try to find weather description
        for greek_word, english in weather_keywords.items():
            if greek_word in html.lower():
                description = english
                break
        
        # Generate 7 days of forecast (with same data for all days as fallback)
        today = datetime.now().date()
        for i in range(7):
            forecast_date = today + timedelta(days=i)
            forecasts.append({
                "date": forecast_date,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "description": description,
                "precipitation": None,
                "wind": None,
                "wind_dir": None,
                "sunrise": None,
                "sunset": None,
            })
        
        return forecasts
        
    except (URLError, OSError) as e:
        print(f"Error fetching forecast from okairos.gr: {e}", file=sys.stderr)
        # Return minimal fallback data instead of exiting
        today = datetime.now().date()
        return [{
            "date": today + timedelta(days=i),
            "temp_min": "N/A",
            "temp_max": "N/A",
            "description": "Check okairos.gr",
            "precipitation": None,
            "wind": None,
            "wind_dir": None,
            "sunrise": None,
            "sunset": None,
        } for i in range(7)]


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


def generate_ics(config: Dict[str, Any], forecasts: List[Dict[str, Any]]) -> str:
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
    ics_lines.append("X-WR-CALDESC:Daily weather forecast from okairos.gr")
    
    # Generate events for each forecast day
    for forecast in forecasts:
        date_obj = forecast["date"]
        temp_min = forecast.get("temp_min", "N/A")
        temp_max = forecast.get("temp_max", "N/A")
        description_text = forecast.get("description", "")
        precipitation = forecast.get("precipitation")
        wind = forecast.get("wind")
        
        # Build description with text-based widget
        description_parts = []
        
        # Add beautiful multi-day widget at the top (only for first day's event)
        if date_obj == forecasts[0]["date"]:
            panel = create_text_widget_panel(config, forecasts, days=4)
            description_parts.append(panel)
            description_parts.append("")  # Blank line
        else:
            # Keep per-day compact widget for other days
            text_widget = create_text_widget(config, forecast)
            description_parts.append(text_widget)
            description_parts.append("")  # Blank line
        
        # Add detailed information with emojis
        if temp_min != "N/A" and temp_max != "N/A":
            description_parts.append(f"🌡️ Temperature Range: {temp_min} – {temp_max}")
        
        if description_text and description_text not in ["Check okairos.gr", "Check widget for details"]:
            description_parts.append(f"📋 Conditions: {description_text}")
        
        if precipitation:
            description_parts.append(f"💧 Precipitation: {precipitation}")
        
        if wind:
            description_parts.append(f"💨 Wind: {wind}")
        
        description_parts.append("")  # Blank line
        description_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        description_parts.append(f"📍 Live Widget: {config['widget_page_url']}")
        
        # Add widget URL for reference
        widget_id = config.get('widget_id', '')
        if widget_id:
            description_parts.append(f"🔗 Widget API: https://www.okairos.gr/widget/loader/{widget_id}")
        
        description_parts.append(f"🌐 Full Forecast: {config.get('location_url', 'https://www.okairos.gr/')}")
        
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
        
        # Event summary with emoji and weather info
        emoji = get_weather_emoji(description_text, temp_max)
        
        # Build summary: "[emoji] [temp] [description]"
        summary_parts = [emoji]
        
        if temp_max != "N/A":
            summary_parts.append(temp_max)
        
        if description_text and description_text != "Check okairos.gr for details":
            # Truncate description if too long
            desc_short = description_text if len(description_text) <= 30 else description_text[:27] + "..."
            summary_parts.append(desc_short)
        else:
            summary_parts.append(config['location_name'])
        
        summary = " ".join(summary_parts)
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
    # Check if locations.json exists for multi-location mode
    locations_path = Path(__file__).parent.parent / "locations.json"
    
    if locations_path.exists():
        # Multi-location mode
        print("Multi-location mode: Generating ICS files for all locations...", file=sys.stderr)
        with open(locations_path, "r", encoding="utf-8") as f:
            locations_config = json.load(f)
        
        for location in locations_config.get("locations", []):
            print(f"\n→ Generating {location['name']} ({location['name_greek']})...", file=sys.stderr)
            
            # Skip if widget_id not configured
            if location['widget_id'] == "get_from_okairos_widget_generator":
                print(f"  ⚠️  Skipping {location['name']}: widget_id not configured", file=sys.stderr)
                continue
            
            config = {
                "location_name": location["name"],
                "location_url": location["url"],
                "widget_id": location["widget_id"],
                "timezone": "Europe/Athens",
                "event_time": "",
                "widget_page_url": load_config().get("widget_page_url", "https://USERNAME.github.io/REPO/")
            }
            
            try:
                forecasts = fetch_forecast(config["location_url"], config.get("widget_id"))
                ics_content = generate_ics(config, forecasts)
                
                output_path = Path(__file__).parent.parent / location["filename"]
                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    f.write(ics_content)
                print(f"  ✓ Successfully wrote {location['filename']}", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ Error generating {location['name']}: {e}", file=sys.stderr)
    else:
        # Single-location mode (legacy)
        config = load_config()
        
        print(f"Fetching forecast for {config['location_name']} from okairos.gr...", file=sys.stderr)
        
        forecasts = fetch_forecast(config["location_url"], config.get("widget_id"))
        
        print("Generating ICS...", file=sys.stderr)
        ics_content = generate_ics(config, forecasts)
        
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
