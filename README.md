# Weather Forecast ICS Calendar - Athens

Automatically generate and maintain a weather forecast calendar for Athens using okairos.gr. Users subscribe with a simple URL in their calendar app and receive daily weather updates.

## What It Does

- 📅 Daily weather calendar with forecasts from okairos.gr for Athens
- 🔄 Automatically updates every morning via GitHub Actions (06:00 Athens time)
- 📱 Syncs with Google Calendar, Apple Calendar, Outlook, and all calendar apps
- ✅ RFC 5545 compliant iCalendar format
- 🎨 Professional GitHub Pages site with live weather widget
- 🌤️ Embedded real-time weather widget from okairos.gr

## Quick Start

1. Fork this repository
2. Enable GitHub Pages (Settings → Pages → Branch: `main`, folder: `/root`)
3. Users subscribe to: `https://your-username.github.io/okairos-ics-feed/feeds/athens.ics`

Done! Athens weather updates automatically every morning.

## Want More Cities?

Users can [open a GitHub issue](https://github.com/tzoral/okairos-ics-feed/issues/new) to request additional cities or districts. If available on okairos.gr, they can be added to [locations.json](locations.json).

## How Users Subscribe

**Google Calendar:**
- Settings → Add other calendars → From URL → Paste the feed URL

**Apple Calendar:**
- File → New Calendar Subscription → Paste URL

**Outlook:**
- Add Calendar → Subscribe from web → Paste URL

**Auto-updates:** Calendar apps check the URL every 24 hours. GitHub Actions updates the feed every morning at 06:00 Athens time.

## Add More Cities (Advanced)

To add more Greek cities:

1. Get widget ID from [okairos.gr widget generator](https://www.okairos.gr/widget/)
2. Edit [locations.json](locations.json):

```json
{
  "name": "Thessaloniki",
  "name_greek": "Θεσσαλονίκη",
  "widget_id": "your_widget_id_here",
  "url": "https://www.okairos.gr/%CE%B8%CE%B5%CF%83%CF%83%CE%B1%CE%BB%CE%BF%CE%BD%CE%AF%CE%BA%CE%B7.html",
  "filename": "feeds/thessaloniki.ics"
}
```

3. Commit and push - the workflow automatically generates the new feed

## Troubleshooting

**Pages not deploying?**
- Settings → Pages → Check branch is `main`, folder is `/root`

**Workflow not running?**
- Actions tab → Check if "Daily Forecast Update" is enabled
- Manually trigger: Click workflow → Run workflow

**Calendar not updating?**
- Calendar apps refresh every ~24 hours
- Try unsubscribing and re-subscribing to clear cache

## How It Works

```
06:00 Athens time → GitHub Actions runs
                        ↓
                  Fetches weather from okairos.gr
                        ↓
                  Generates feeds/athens.ics
                        ↓
                  Commits if changed
                        ↓
Calendar apps (every ~24h) → Fetch new data → Update events
```

## License

MIT License - feel free to fork and customize!
