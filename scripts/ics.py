"""ICS calendar generation for weather forecasts."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from utils import escape_ics_text, fold_line, get_weather_emoji, create_day_description_google


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
