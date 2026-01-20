"""Weather emoji and text utility functions."""

import re
from typing import Dict, Any, List


def get_weather_emoji(description: str, temp: str = "") -> str:
    """Return appropriate weather emoji based on detailed description and temperature."""
    desc_lower = (description or "").lower()

    # Temperature-based emoji (only for clear/stable conditions)
    try:
        m = re.search(r"\d+", temp or "")
        temp_val = int(m.group()) if m else 20
        if temp_val >= 35:
            return "🔥"
        elif temp_val <= 0:
            return "🥶"
    except Exception:
        pass

    # Detailed weather condition emojis
    # Thunderstorms (highest priority)
    if "thunderstorm" in desc_lower or "καταιγίδα" in desc_lower:
        return "⛈️"
    
    # Snow conditions
    if "snow" in desc_lower or "χιόν" in desc_lower:
        if "shower" in desc_lower or "μπόρες" in desc_lower:
            return "🌨️"  # Snow cloud
        elif "light" in desc_lower or "ασθενή" in desc_lower:
            return "🌨️"  # Light snow
        else:
            return "❄️"  # Heavy snow
    
    # Sleet (mixed precipitation)
    if "sleet" in desc_lower or "χιονόνερο" in desc_lower:
        return "🌨️"
    
    # Rain conditions
    if any(word in desc_lower for word in ["rain", "shower", "βροχ", "μπόρες"]):
        # Few clouds + rain
        if "few clouds" in desc_lower or "λίγες νεφώσεις" in desc_lower:
            return "🌦️"  # Sun behind rain cloud
        # Light rain
        elif "light" in desc_lower or "ασθενή" in desc_lower:
            return "🌦️"  # Light rain
        # Heavy rain/showers
        else:
            return "🌧️"  # Cloud with rain
    
    # Fog/Mist
    if "fog" in desc_lower or "mist" in desc_lower or "ομίχλη" in desc_lower:
        return "🌫️"
    
    # Cloudy conditions (no precipitation)
    if any(word in desc_lower for word in ["cloud", "νεφ", "συννεφ", "overcast"]):
        if "few" in desc_lower or "λίγες" in desc_lower:
            return "🌤️"  # Sun behind small cloud
        elif "partly" in desc_lower or "μερικώς" in desc_lower:
            return "⛅"  # Sun behind cloud
        elif "mostly" in desc_lower or "heavy" in desc_lower:
            return "☁️"  # Cloud
        else:
            return "🌥️"  # Sun behind large cloud
    
    # Clear/Sunny
    if any(word in desc_lower for word in ["clear", "sunny", "αίθρι", "ηλιόλ"]):
        return "☀️"
    
    # Wind
    if "wind" in desc_lower or "άνεμ" in desc_lower:
        return "💨"
    
    # Default
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
