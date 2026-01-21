"""Weather data fetching from okairos.gr widget and location pages."""

import sys
import re
import time
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
from typing import Dict, Any, List, Optional


def fetch_with_retry(url: str, max_retries: int = 3, timeout: int = 10) -> str:
    """Fetch URL with retry logic and proper User-Agent header."""
    for attempt in range(max_retries):
        try:
            req = Request(url, headers={
                'User-Agent': 'WeatherCalendar/1.0 (https://github.com/tzoral/meteo-ics-feed)'
            })
            with urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except URLError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise


def fetch_forecast_from_widget(widget_id: str) -> List[Dict[str, Any]]:
    """
    Fetch forecast from okairos widget endpoint and parse the returned HTML.

    NOTE: okairos commonly serves widget data at /widget/get/<id>.
    This parser is based on the typical HTML structure of that response.
    """
    widget_url = f"https://www.okairos.gr/widget/get/{widget_id}"
    print(f"Fetching widget data from: {widget_url}", file=sys.stderr)

    try:
        html = fetch_with_retry(widget_url)
        print(f"Successfully fetched {len(html)} bytes from widget", file=sys.stderr)

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
            """Map Foreca icon codes to detailed weather descriptions based on okairos.gr FAQ."""
            if not code:
                return "Clear"
            try:
                # Code format: [n|d]NNN[s]
                # n/d = night/day, NNN = number, s = severe
                num_str = code.lstrip('nd').rstrip('s')
                num = int(num_str)
            except Exception:
                return "Clear"
            
            # Detailed Foreca icon mapping from okairos.gr FAQ
            # 100 range: Clear/Almost clear
            if num == 100:
                return "Clear"
            elif num == 110:
                return "Mostly Clear"
            
            # 120-140 range: Few clouds variations
            elif num == 120:
                return "Few Clouds"
            elif num == 121:
                return "Few Clouds Light Rain"
            elif num == 122:
                return "Few Clouds Sleet"
            elif num == 123:
                return "Few Clouds Light Snow"
            elif num == 124:
                return "Few Clouds Showers"
            elif num == 125:
                return "Few Clouds Sleet Showers"
            elif num == 126:
                return "Few Clouds Snow Showers"
            elif num == 127:
                return "Few Clouds Thunderstorms"
            
            # 200 range: Partly cloudy variations
            elif num == 200:
                return "Partly Cloudy"
            elif num == 210:
                return "Partly Cloudy Light Rain"
            elif num == 211:
                return "Partly Cloudy Sleet"
            elif num == 212:
                return "Partly Cloudy Light Snow"
            elif num == 220:
                return "Partly Cloudy Showers"
            elif num == 221:
                return "Partly Cloudy Sleet Showers"
            elif num == 222:
                return "Partly Cloudy Snow Showers"
            elif num == 230:
                return "Partly Cloudy Thunderstorms"
            
            # 300 range: Overcast/Cloudy variations
            elif num == 300:
                return "Cloudy"
            elif num == 310:
                return "Cloudy Light Rain"
            elif num == 311:
                return "Cloudy Sleet"
            elif num == 312:
                return "Cloudy Light Snow"
            elif num == 320:
                return "Cloudy Showers"
            elif num == 321:
                return "Cloudy Sleet Showers"
            elif num == 322:
                return "Cloudy Snow Showers"
            elif num == 330:
                return "Cloudy Rain"
            elif num == 331:
                return "Cloudy Sleet"
            elif num == 332:
                return "Cloudy Snow"
            elif num == 340:
                return "Cloudy Thunderstorms"
            
            # Generic fallback ranges
            elif 100 <= num < 120:
                return "Clear"
            elif 120 <= num < 200:
                return "Few Clouds"
            elif 200 <= num < 300:
                return "Partly Cloudy"
            elif 300 <= num < 400:
                return "Cloudy"
            elif 400 <= num < 430:
                return "Light Rain"
            elif 430 <= num < 470:
                return "Rain"
            elif num >= 470:
                return "Heavy Rain"
            else:
                return "Clear"

        # Determine how many day-cards are present (often 4)
        num_days = min(
            len(main_temps) if main_temps else 10**9,
            len(max_temps) if max_temps else 10**9,
            len(min_temps) if min_temps else 10**9,
        )
        if num_days == 10**9:
            num_days = 0
        
        print(f"Parsed {num_days} days from widget (main_temps={len(main_temps)}, max={len(max_temps)}, min={len(min_temps)})", file=sys.stderr)

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
                    "wind": None,       # this widget template often doesn't include wind
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
            print(f"  ✓ Parsed {min(num_days, 7)} days from widget API\", file=sys.stderr)
            for i, fc in enumerate(forecasts[:3]):  # Log first 3 days
                print(f"    Day {i}: {fc['date']} - {fc['temp_max']}/{fc['temp_min']}, {fc['description']}\", file=sys.stderr)
            return forecasts

        # If parsing got nothing, fall through to fallback
        raise ValueError("No days parsed from widget HTML")

    except Exception as e:
        print(f\"⚠️  Error fetching/parsing widget data: {e}\", file=sys.stderr)
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
        html = fetch_with_retry(location_url)

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
