"""Weather emoji and text utility functions."""

import re
from typing import Dict, Any, List


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


def create_day_description_google(config: Dict[str, Any], forecast: Dict[str, Any]) -> str:
    """Minimal per-day description optimized for Google Calendar display."""
    from datetime import datetime

    date_obj = forecast.get("date", datetime.now().date())
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()

    temp_min = forecast.get("temp_min", "N/A")
    temp_max = forecast.get("temp_max", "N/A")
    temp_cur = forecast.get("temp_current")
    desc = (forecast.get("description") or "").strip()

    lines: List[str] = []

    # Min/Max only
    if temp_min != "N/A" or temp_max != "N/A":
        lines.append(f"Min/Max: {temp_min} / {temp_max}")

    # Conditions (if meaningful)
    if desc and desc not in ["Check okairos.gr", "Check widget for details"]:
        lines.append(f"Conditions: {desc}")

    # If we have current temp, show it on its own line
    if temp_cur:
        lines.append(f"Current: {temp_cur}")

    # If no useful data, return a single line
    if not lines:
        return "See okairos.gr for details"

    return "\n".join(lines)
