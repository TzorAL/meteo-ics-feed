#!/usr/bin/env python3
"""
Weather Forecast ICS Generator (Google Calendar-friendly)

Fetches weather forecast from okairos.gr and generates an RFC 5545-compliant
iCalendar file (forecast.ics) with daily weather events.

Google Calendar optimization:
- DESCRIPTION contains ONLY the current day's compact details (no big ASCII panels).
- SUMMARY prefers current temperature (if available), otherwise max temp.

Configuration priority:
- Environment variables (highest)
- config.json in repository root
- Hardcoded defaults (Athens)

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
from typing import Dict, Any, List, Optional
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


def get_weather_emoji(description: str, temp: str = "") -> str:
    """Return appropriate weather emoji based on description and/or temperature."""
    desc_lower = (description or "").lower()

    # Temperature-based if no specific weather
    try:
        m = re.search(r"\d+", temp or "")
        temp_val = int(m.group()) if m else 20
        if temp_val >= 30:
            return "🔥"
        elif temp_val <= 5:
            return "🥶"
    except Exception:
        pass

    if any(word in desc_lower for word in ["καταιγίδα", "βροχή", "rain", "thunderstorm"]):
        return "⛈️"
    if any(word in desc_lower for word in ["βροχ", "νεροπ", "drizzle", "shower"]):
        return "🌧️"
    if any(word in desc_lower for word in ["χιόν", "snow"]):
        return "❄️"
    if any(word in desc_lower for word in ["ομίχλη", "fog", "mist"]):
        return "🌫️"
    if any(word in desc_lower for word in ["νεφ", "cloud", "συννεφ"]):
        return "☁️"
    if any(word in desc_lower for word in ["αίθρι", "ηλιόλ", "sunny", "clear", "sun"]):
        return "☀️"
    if any(word in desc_lower for word in ["άνεμ", "wind"]):
        return "💨"
    return "🌤️"


def create_day_description_google(config: Dict[str, Any], forecast: Dict[str, Any]) -> str:
    """Compact per-day description optimized for Google Calendar display."""
    date_obj = forecast.get("date", datetime.now().date())
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()

    now = datetime.now().date()
    day_names_greek = {
        0: "Δευτέρα",
        1: "Τρίτη",
        2: "Τετάρτη",
        3: "Πέμπτη",
        4: "Παρασκευή",
        5: "Σάββατο",
        6: "Κυριακή",
    }

    if date_obj == now:
        day_label = "Σήμερα"
    elif date_obj == now + timedelta(days=1):
        day_label = "Αύριο"
    else:
        day_label = day_names_greek.get(date_obj.weekday(), date_obj.strftime("%d/%m"))

    temp_min = forecast.get("temp_min", "N/A")
    temp_max = forecast.get("temp_max", "N/A")
    temp_cur = forecast.get("temp_current")  # may be None
    desc = (forecast.get("description") or "").strip()

    wind = forecast.get("wind")
    wind_dir = forecast.get("wind_dir")
    sunrise = forecast.get("sunrise")
    sunset = forecast.get("sunset")

    emoji = get_weather_emoji(desc, temp_max)

    lines: List[str] = []

    # First line (GC preview-friendly)
    headline_bits = [emoji, config["location_name"], "—", day_label, f"({date_obj.strftime('%d/%m/%Y')})"]
    if temp_cur:
        headline_bits += ["•", f"Τώρα {temp_cur}"]
    lines.append(" ".join([b for b in headline_bits if b]))

    # Second line: min/max early
    if temp_min != "N/A" or temp_max != "N/A":
        lines.append(f"Min/Max: {temp_min} / {temp_max}")

    # Conditions
    if desc and desc not in ["Check okairos.gr", "Check widget for details"]:
        lines.append(f"Συνθήκες: {desc}")

    # Wind (only if present)
    if wind or wind_dir:
        w = wind or ""
        d = wind_dir or ""
        lines.append(f"Άνεμος: {w} {d}".strip())

    # Sunrise/Sunset (only if present)
    if sunrise or sunset:
        sr = sunrise or "--:--"
        ss = sunset or "--:--"
        lines.append(f"Ανατολή/Δύση: {sr} / {ss}")

    # Links at the end (won't clutter preview much)
    if config.get("widget_page_url"):
        lines.append(f"Widget: {config['widget_page_url']}")
    if config.get("location_url"):
        lines.append(f"Σελίδα: {config['location_url']}")

    return "\n".join(lines)


def fetch_forecast_from_widget(widget_id: str) -> List[Dict[str, Any]]:
    """
    Fetch forecast from okairos widget endpoint and parse the returned HTML.

    NOTE: okairos commonly serves widget data at /widget/get/<id>.
    This parser is based on the typical HTML structure of that response.
    """
    widget_url = f"https://www.okairos.gr/widget/get/{widget_id}"

    try:
        with urlopen(widget_url, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")

        today = datetime.now().date()

        # Main temps (often the prominent temp shown per day)
        main_temps = re.findall(r"<strong>(-?\d+)&deg;</strong>", html)

        # Max/min temps
        max_temps = re.findall(r'<td class="max-temp">(-?\d+)&deg;</td>', html)
        min_temps = re.findall(r'<td class="min-temp">(-?\d+)&deg;</td>', html)

        # Sunrise/sunset times
        sunrise_times = re.findall(r'<div class="rise">(\d{2}:\d{2})</div>', html)
        sunset_times = re.findall(r'<div class="set">(\d{2}:\d{2})</div>', html)

        # Icon codes (heuristic; depends on widget template)
        icon_codes = re.findall(r'<div class="icon ([nd]\d+)"></div>', html)

        def icon_to_description(code: str) -> str:
            if not code:
                return "Clear"
            try:
                num = int(code[1:])  # drop leading 'n'/'d'
            except Exception:
                return "Clear"
            # very rough mapping; tweak if you discover real mapping
            if num >= 500:
                return "Rain"
            if num >= 400:
                return "Cloudy"
            if num >= 300:
                return "Partly Cloudy"
            if num >= 200:
                return "Snow"
            return "Clear"

        # Determine how many day-cards are present (often 4)
        num_days = min(
            len(main_temps) if main_temps else 10**9,
            len(max_temps) if max_temps else 10**9,
            len(min_temps) if min_temps else 10**9,
        )
        if num_days == 10**9:
            num_days = 0

        forecasts: List[Dict[str, Any]] = []
        for i in range(num_days):
            forecasts.append(
                {
                    "date": today + timedelta(days=i),
                    "temp_current": f"{main_temps[i]}°C" if i < len(main_temps) else None,
                    "temp_max": f"{max_temps[i]}°C" if i < len(max_temps) else "N/A",
                    "temp_min": f"{min_temps[i]}°C" if i < len(min_temps) else "N/A",
                    "description": icon_to_description(icon_codes[i]) if i < len(icon_codes) else "Clear",
                    "precipitation": None,
                    "wind": None,       # this widget template often doesn’t include wind
                    "wind_dir": None,   # same
                    "sunrise": sunrise_times[i] if i < len(sunrise_times) else None,
                    "sunset": sunset_times[i] if i < len(sunset_times) else None,
                }
            )

        # If fewer than 7 days, extend by repeating last known day (keeps calendar consistent)
        while forecasts and len(forecasts) < 7:
            last = forecasts[-1]
            forecasts.append(
                {
                    "date": today + timedelta(days=len(forecasts)),
                    "temp_current": None,
                    "temp_max": last.get("temp_max", "N/A"),
                    "temp_min": last.get("temp_min", "N/A"),
                    "description": last.get("description", "Check widget for details"),
                    "precipitation": None,
                    "wind": None,
                    "wind_dir": None,
                    "sunrise": last.get("sunrise"),
                    "sunset": last.get("sunset"),
                }
            )

        if forecasts:
            print(f"  Parsed {min(num_days, 7)} days from widget API", file=sys.stderr)
            return forecasts

        # If parsing got nothing, fall through to fallback
        raise ValueError("No days parsed from widget HTML")

    except Exception as e:
        print(f"Error fetching/parsing widget data: {e}", file=sys.stderr)
        today = datetime.now().date()
        return [
            {
                "date": today + timedelta(days=i),
                "temp_min": "N/A",
                "temp_max": "N/A",
                "temp_current": None,
                "description": "Check okairos.gr",
                "precipitation": None,
                "wind": None,
                "wind_dir": None,
                "sunrise": None,
                "sunset": None,
            }
            for i in range(7)
        ]


def fetch_forecast(location_url: str, widget_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch weather forecast from okairos.gr.

    If widget_id is provided, fetches from widget API (preferred).
    Otherwise falls back to scraping the location page (coarse fallback).
    """
    if widget_id and widget_id != "get_from_okairos_widget_generator":
        return fetch_forecast_from_widget(widget_id)

    # Fallback: basic scrape from location page (may not yield per-day data)
    try:
        with urlopen(location_url, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")

        temp_min = "N/A"
        temp_max = "N/A"
        description = "Check widget for details"

        for pattern in [
            r"(\d+)°\s*[–-]\s*(\d+)°",
            r"(\d+)°C\s*[–-]\s*(\d+)°C",
            r"min[^\d]*(\d+)[^\d]*max[^\d]*(\d+)",
        ]:
            match = re.search(pattern, html)
            if match:
                temp_min = match.group(1) + "°C"
                temp_max = match.group(2) + "°C"
                break

        for greek_word, english in {
            "αίθριος": "Clear",
            "αίθρια": "Clear",
            "ηλιοφάνεια": "Sunny",
            "ηλιόλουστος": "Sunny",
            "νεφώσεις": "Cloudy",
            "συννεφιά": "Cloudy",
            "βροχή": "Rain",
            "βροχές": "Rain",
            "καταιγίδα": "Thunderstorm",
            "καταιγίδες": "Thunderstorms",
            "χιόνι": "Snow",
            "χιονόπτωση": "Snow",
            "ομίχλη": "Fog",
            "άνεμοι": "Windy",
            "άνεμος": "Windy",
        }.items():
            if greek_word in html.lower():
                description = english
                break

        today = datetime.now().date()
        return [
            {
                "date": today + timedelta(days=i),
                "temp_min": temp_min,
                "temp_max": temp_max,
                "temp_current": None,
                "description": description,
                "precipitation": None,
                "wind": None,
                "wind_dir": None,
                "sunrise": None,
                "sunset": None,
            }
            for i in range(7)
        ]

    except (URLError, OSError) as e:
        print(f"Error fetching forecast from okairos.gr: {e}", file=sys.stderr)
        today = datetime.now().date()
        return [
            {
                "date": today + timedelta(days=i),
                "temp_min": "N/A",
                "temp_max": "N/A",
                "temp_current": None,
                "description": "Check okairos.gr",
                "precipitation": None,
                "wind": None,
                "wind_dir": None,
                "sunrise": None,
                "sunset": None,
            }
            for i in range(7)
        ]


def fold_line(line: str, max_length: int = 75) -> str:
    """
    Fold a line according to RFC 5545: lines longer than max_length
    are split with CRLF followed by a single space.
    """
    if len(line.encode("utf-8")) <= max_length:
        return line

    folded_lines: List[str] = []
    current_line = ""

    for ch in line:
        test = current_line + ch
        if len(test.encode("utf-8")) > max_length:
            folded_lines.append(current_line)
            current_line = " " + ch  # continuation line starts with space
        else:
            current_line = test

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
    ics_lines: List[str] = []

    # Calendar header
    ics_lines.append("BEGIN:VCALENDAR")
    ics_lines.append("VERSION:2.0")
    ics_lines.append("PRODID:-//Weather Forecast Calendar//GitHub Pages//EN")
    ics_lines.append("CALSCALE:GREGORIAN")
    ics_lines.append("METHOD:PUBLISH")
    ics_lines.append(f"X-WR-CALNAME:Daily Weather Forecast - {config['location_name']}")
    ics_lines.append(f"X-WR-TIMEZONE:{config['timezone']}")
    ics_lines.append("X-WR-CALDESC:Daily weather forecast from okairos.gr")

    for forecast in forecasts:
        date_obj = forecast["date"]
        temp_min = forecast.get("temp_min", "N/A")
        temp_max = forecast.get("temp_max", "N/A")
        description_text = forecast.get("description", "") or ""

        # Google Calendar-friendly: description only for THIS day
        description_block = create_day_description_google(config, forecast)
        description = escape_ics_text(description_block)

        ics_lines.append("BEGIN:VEVENT")

        # Stable UID based on date
        date_str_clean = date_obj.strftime("%Y%m%d")
        ics_lines.append(f"UID:weather-{date_str_clean}@github-pages")

        # DTSTAMP in UTC (current time)
        dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ics_lines.append(f"DTSTAMP:{dtstamp}")

        # DTSTART / DTEND
        if config["event_time"].strip():
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
            except Exception:
                ics_lines.append(f"DTSTART;VALUE=DATE:{date_str_clean}")
                next_day = date_obj + timedelta(days=1)
                ics_lines.append(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}")
        else:
            ics_lines.append(f"DTSTART;VALUE=DATE:{date_str_clean}")
            next_day = date_obj + timedelta(days=1)
            ics_lines.append(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}")

        # SUMMARY (Google Calendar title)
        emoji = get_weather_emoji(description_text, temp_max)
        summary_parts = [emoji]

        temp_cur = forecast.get("temp_current")
        if temp_cur:
            summary_parts.append(temp_cur)
        elif temp_max != "N/A":
            summary_parts.append(temp_max)

        if description_text and description_text not in ["Check okairos.gr", "Check widget for details"]:
            desc_short = description_text if len(description_text) <= 30 else description_text[:27] + "..."
            summary_parts.append(desc_short)
        else:
            summary_parts.append(config["location_name"])

        summary = " ".join(summary_parts)
        ics_lines.append(f"SUMMARY:{escape_ics_text(summary)}")

        ics_lines.append(f"DESCRIPTION:{description}")
        ics_lines.append("STATUS:CONFIRMED")
        ics_lines.append("TRANSP:TRANSPARENT")
        ics_lines.append("END:VEVENT")

    ics_lines.append("END:VCALENDAR")

    # Join with CRLF and apply folding
    ics_content = "\r\n".join(ics_lines)
    folded = [fold_line(line) for line in ics_content.split("\r\n")]
    return "\r\n".join(folded) + "\r\n"


def main() -> None:
    """Main entry point."""
    locations_path = Path(__file__).parent.parent / "locations.json"

    if locations_path.exists():
        print("Multi-location mode: Generating ICS files for all locations...", file=sys.stderr)
        with open(locations_path, "r", encoding="utf-8") as f:
            locations_config = json.load(f)

        base = load_config()
        for location in locations_config.get("locations", []):
            print(f"\n→ Generating {location['name']} ({location.get('name_greek','')})...", file=sys.stderr)

            if location.get("widget_id") == "get_from_okairos_widget_generator":
                print(f"  ⚠️  Skipping {location['name']}: widget_id not configured", file=sys.stderr)
                continue

            config = {
                "location_name": location["name"],
                "location_url": location["url"],
                "widget_id": location.get("widget_id"),
                "timezone": "Europe/Athens",
                "event_time": "",
                "widget_page_url": base.get("widget_page_url", "https://USERNAME.github.io/REPO/"),
            }

            try:
                forecasts = fetch_forecast(config["location_url"], config.get("widget_id"))
                ics_content = generate_ics(config, forecasts)

                output_path = Path(__file__).parent.parent / location["filename"]
                with open(output_path, "w", encoding="utf-8", newline="") as f_out:
                    f_out.write(ics_content)
                print(f"  ✓ Successfully wrote {location['filename']}", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ Error generating {location['name']}: {e}", file=sys.stderr)

    else:
        # Single-location mode
        config = load_config()
        print(f"Fetching forecast for {config['location_name']} from okairos.gr...", file=sys.stderr)

        forecasts = fetch_forecast(config["location_url"], config.get("widget_id"))

        print("Generating ICS...", file=sys.stderr)
        ics_content = generate_ics(config, forecasts)

        output_path = Path(__file__).parent.parent / "forecast.ics"
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as f_out:
                f_out.write(ics_content)
            print(f"Successfully wrote {output_path}", file=sys.stderr)
        except IOError as e:
            print(f"Error writing ICS file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
