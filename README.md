# Weather Forecast ICS Calendar

Automatically generate and maintain a weather forecast calendar for any location. Works with Google Calendar, Apple Calendar, Outlook, and any app that supports iCalendar subscriptions.

## What It Does

- 📅 **Creates a daily weather calendar** with forecasts (min/max temp, precipitation, wind)
- 🔄 **Automatically updates every morning** via GitHub Actions (06:00 Athens time)
- 🌍 **Works worldwide** — configure any location & timezone
- 📱 **Syncs with all calendar apps** — Google Calendar, Apple Calendar, Outlook, etc.
- ✅ **RFC 5545 compliant** — proper iCalendar format

## Files

```
├── index.html                       # Your GitHub Pages homepage
├── forecast.ics                     # Calendar feed (auto-generated daily)
├── config.json                      # Configuration (edit this!)
├── scripts/generate_ics.py          # Generator script
├── .github/workflows/daily-forecast.yml  # Daily automation
└── requirements.txt                 # Dependencies (empty)
```

## Setup (5 minutes)

### 1. Edit config.json

Update with your location:

```json
{
  "location_name": "Athens",
  "latitude": 37.9838,
  "longitude": 23.7275,
  "timezone": "Europe/Athens",
  "event_time": "",
  "widget_page_url": "https://USERNAME.github.io/REPO/"
}
```

**Fields:**
- `location_name` — Display name in calendar events
- `latitude`, `longitude` — Get from [Google Maps](https://maps.google.com)
- `timezone` — IANA format: `Europe/Athens`, `America/New_York`, `Asia/Tokyo`, etc. — [Full list](https://www.iana.org/time-zones)
- `event_time` — Leave empty `""` for all-day events; or set time like `"07:30"` for timed events
- `widget_page_url` — Your GitHub Pages URL (see below)

### 2. Enable GitHub Pages

1. Go to repo **Settings** → **Pages**
2. Select **Branch:** `main`, folder: `/root`
3. Save and wait 1–2 minutes

### 3. Get Your URLs

After Pages is enabled, your URLs are:

- **Main page:** `https://USERNAME.github.io/REPO/`
- **Calendar feed:** `https://USERNAME.github.io/REPO/forecast.ics`

Update `config.json` `widget_page_url` with the main page URL.

### 4. Register with meteo.gr

1. Visit: https://w1.meteo.gr/dataconsumerregistration.cfm
2. Fill the form:
   - **Region:** Your location
   - **Name, Email, Phone:** Your info
   - **URL:** `https://USERNAME.github.io/REPO/` (your main page)
3. Submit

meteo.gr will send you an **`<iframe>` embed code**:

4. Go to your GitHub Pages site: `https://USERNAME.github.io/REPO/`
5. Paste the iframe code into the textarea on the page
6. Click **Save & Display**
7. The widget will load and store the information locally (in your browser)

The widget data is stored in browser localStorage, so it persists across page refreshes.

## Subscribe to Calendar

### Google Calendar

1. Open **Google Calendar**
2. Click **+ Other calendars** → **Subscribe to calendar**
3. Paste: `https://USERNAME.github.io/REPO/forecast.ics`
4. Click Subscribe

### Apple Calendar (macOS/iOS)

- **macOS:** Calendar app → **File** → **New Calendar Subscription**
- **iOS:** Settings → Calendar → **Add Account** → **Subscribed Calendar**
- Paste the URL above

### Outlook

1. Go to **calendar.microsoft.com**
2. **Add Calendar** → **Subscribe from web**
3. Paste the URL

**Refresh rate:** Calendar apps auto-refresh every ~24 hours. Your forecast updates every morning at 06:00 Athens time.

## Configuration

### Change Location

Edit `config.json`:

```json
{
  "location_name": "London",
  "latitude": 51.5074,
  "longitude": -0.1278,
  "timezone": "Europe/London"
}
```

Commit and push:

```bash
git add config.json forecast.ics
git commit -m "Change location to London"
git push
```

### Environment Variables

Override `config.json` (useful for CI/CD):

```bash
export LOCATION_NAME="Paris"
export LATITUDE=48.8566
export LONGITUDE=2.3522
export TIMEZONE="Europe/Paris"
export EVENT_TIME=""
export WIDGET_PAGE_URL="https://USERNAME.github.io/REPO/"

python scripts/generate_ics.py
```

### All-Day vs. Timed Events

**All-day events** (default):
```json
{
  "event_time": ""
}
```

**Timed events** (e.g., 7:30 AM):
```json
{
  "event_time": "07:30"
}
```

### Common Timezones

- `Europe/Athens` — Greece
- `Europe/London` — UK
- `Europe/Paris` — France
- `America/New_York` — Eastern Time (USA)
- `America/Los_Angeles` — Pacific Time (USA)
- `Asia/Tokyo` — Japan
- `Australia/Sydney` — Australia

[Complete timezone list](https://www.iana.org/time-zones)

## Troubleshooting

### Pages not deployed

1. Go to **Settings** → **Pages**
2. Check: branch is `main`, folder is `/root`
3. No build errors (green checkmark)
4. Wait another minute

### Workflow not running

1. Go to **Actions** tab
2. Check if **Daily Forecast Update** is enabled
3. Manually trigger: Click workflow → **Run workflow**

### ICS feed not valid

Test locally:

```bash
python scripts/generate_ics.py
cat forecast.ics | head -5  # Should start with BEGIN:VCALENDAR
tail -1 forecast.ics        # Should end with END:VCALENDAR
```

Validate: https://icalendar.org/validator.html

### Calendar not updating

- Calendar apps refresh every ~24 hours (not real-time)
- Try: Unsubscribe and re-subscribe (clears cache)
- Check `forecast.ics` file directly: visit `https://USERNAME.github.io/REPO/forecast.ics` in browser

### Wrong timezone

1. Check `config.json` has correct IANA timezone (not `GMT+2`, use `Europe/Athens`)
2. Update config, run: `python scripts/generate_ics.py`
3. Commit and push
4. Unsubscribe and re-subscribe calendar (old timezone cached)

### Weather data not updating

1. Check **Actions** tab → **Daily Forecast Update** for recent runs
2. If red (failed): Click to see error logs
3. Test manually:
   ```bash
   python scripts/generate_ics.py
   git log --oneline forecast.ics | head -3
   ```

## How It Works

```
Daily automation:
├─ 06:00 Europe/Athens (04:00 UTC)
├─ GitHub Actions triggers
├─ Fetches weather from Open-Meteo API (free, no API key)
├─ Generates forecast.ics (RFC 5545 iCalendar)
├─ Commits if changed (no noisy commits)
└─ Calendar apps auto-refresh ~24h later
```

Each calendar event includes:
- Min/max temperature
- Precipitation probability & amount
- Wind speed
- Link back to your GitHub Pages

## For Developers

### Test Generator Locally

```bash
python scripts/generate_ics.py
```

### Change Weather Provider

Edit `scripts/generate_ics.py` — modify `fetch_forecast()` function to call a different API. Return data in the same format.

### Dependencies

**None!** Uses Python stdlib:
- `urllib` — HTTP
- `json` — Parsing
- `datetime` — Dates
- `pathlib` — Files

Requires Python 3.7+ (tested with 3.11).

## FAQ

**Q: Is my location data sent anywhere?**
A: No. Weather is fetched from Open-Meteo's free API (public data). No tracking.

**Q: How often does it update?**
A: Once per day at 06:00 Athens time. Calendar apps refresh every ~24 hours.

**Q: Can I use a different weather API?**
A: Yes, edit `fetch_forecast()` in `scripts/generate_ics.py`.

**Q: Can I have multiple locations?**
A: Yes, modify the script to generate multiple ICS files.

**Q: Will this break if GitHub changes?**
A: Unlikely. Uses only standard GitHub Pages + Actions.

## License

MIT — Use freely, modify as needed.

---

**Questions?** Check the script comments or troubleshooting section above!
