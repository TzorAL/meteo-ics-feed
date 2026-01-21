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

import json
import sys
from pathlib import Path
from datetime import datetime

from config import load_config
from weather import fetch_forecast
from ics import generate_ics


def main() -> None:
    """Main entry point."""
    print(f"\n=== Weather ICS Generation Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===", file=sys.stderr)
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
                print(f"  📊 Fetched {len(forecasts)} days of forecast data", file=sys.stderr)
                
                ics_content = generate_ics(config, forecasts)

                output_path = Path(__file__).parent.parent / location["filename"]
                
                # Check if content actually changed to avoid unnecessary commits
                content_changed = True
                if output_path.exists():
                    with open(output_path, "r", encoding="utf-8") as f_in:
                        existing_content = f_in.read()
                        # Compare ignoring DTSTAMP/LAST-MODIFIED/SEQUENCE which always change
                        existing_lines = [l for l in existing_content.split('\n') if not l.startswith(('DTSTAMP:', 'LAST-MODIFIED:', 'SEQUENCE:'))]
                        new_lines = [l for l in ics_content.split('\n') if not l.startswith(('DTSTAMP:', 'LAST-MODIFIED:', 'SEQUENCE:'))]
                        content_changed = existing_lines != new_lines
                
                if content_changed:
                    with open(output_path, "w", encoding="utf-8", newline="") as f_out:
                        f_out.write(ics_content)
                    print(f"  ✓ Successfully wrote {location['filename']} (content updated)", file=sys.stderr)
                else:
                    # Still write to update timestamps
                    with open(output_path, "w", encoding="utf-8", newline="") as f_out:
                        f_out.write(ics_content)
                    print(f"  ✓ Updated timestamps in {location['filename']} (no forecast changes)", file=sys.stderr)
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
    
    print(f"\n=== Generation Complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===", file=sys.stderr)


if __name__ == "__main__":
    main()
