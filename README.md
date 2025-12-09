# DX Index CLI

A command-line tool for checking real-time HF radio propagation conditions.

```
═══════════════════════════════════════════════════════
  HF DX INDEX - Current Conditions
═══════════════════════════════════════════════════════
  Updated: 2025-12-09 20:45 UTC

  Band   Now      Rating             Tomorrow
  ────────────────────────────────────────────────
  10m    78.7     🔵 Excellent ⬆+76%  45.3 (Fair)
  15m    43.6     🟠 Fair             38.4 (Fair)
  20m    38.6     🟠 Fair             37.0 (Fair)
  40m    52.0     🟢 Good ⬆+52%       43.6 (Fair)

  Solar: SFI 183 | Kp 1.0
═══════════════════════════════════════════════════════
  Source: wspr.hb9vqq.ch | 73 de HB9VQQ
```

## Features

- **Real-time DX Index** for 10m, 15m, 20m, and 40m bands
- **Tomorrow's forecast** based on NOAA solar predictions
- **Peak detection** - shows ⬆+XX% when a band exceeds 20% above its typical hourly performance
- **Storm warnings** when geomagnetic disturbances are predicted
- **Multiple output formats** - standard, compact, JSON
- **Alert mode** for scripting and notifications
- **No dependencies** - uses only Python standard library

## Installation

### Linux / macOS

```bash
# Download
curl -O https://raw.githubusercontent.com/HB9VQQ/dx.py/main/dx.py

# Run
python3 dx.py

# Optional: add to PATH
sudo mv dx.py /usr/local/bin/dx
```

### Windows

1. Download [dx.py](https://raw.githubusercontent.com/HB9VQQ/dx.py/main/dx.py)
2. Run: `python dx.py`

**Optional:** Create `dx.bat` in your PATH:

```batch
@echo off
python C:\path\to\dx.py %*
```

**Requirements:** Python 3.6+ (no external dependencies)

## Usage

```bash
# Show all bands
dx

# Show specific bands
dx 10m 15m

# Compact one-line output
dx --compact

# JSON output for scripting
dx --json

# Live auto-refresh (every 60s)
dx --watch

# Custom refresh interval
dx --watch --interval 30

# ASCII mode (no emoji)
dx --ascii

# Alert mode - exit 0 if condition met, exit 1 otherwise
dx --alert Good
dx --alert Fair
```

## Examples

### Quick check

```bash
$ dx
```

### One-liner for status bar / tmux

```bash
$ dx --compact
10m:Excellent(79)⬆76% | 15m:Fair(44) | 20m:Fair(39) | 40m:Good(52)⬆52%
```

### JSON for scripting

```bash
$ dx --json | jq '.bands["10m"].rating'
"Excellent"

# Check if any band is performing above typical
$ dx --json | jq '.bands | to_entries[] | select(.value.vs_typical > 30)'
```

### Notification when band opens

```bash
# Linux (notify-send)
dx --alert Good && notify-send "HF bands are open!"

# macOS
dx --alert Good && osascript -e 'display notification "HF bands are open!"'
```

### Cron job for alerts

```bash
# Check every 15 minutes, send pushover notification when any band is Good or better
*/15 * * * * /usr/local/bin/dx --alert Good && curl -s -X POST https://api.pushover.net/1/messages.json -d "token=xxx&user=xxx&message=HF bands are good!"
```

### Live monitor in terminal

```bash
$ dx --watch
```

## Understanding the Display

### Rating Scale

| Rating | DX Index | Conditions |
|--------|----------|------------|
| 🔵 Excellent | ≥70 | Worldwide DX wide open |
| 🟢 Good | 50-70 | Reliable DX contacts |
| 🟠 Fair | 35-50 | Shorter openings, regional DX |
| 🔴 Poor | 20-35 | Few DX opportunities |
| ⚫ VeryPoor | <20 | Band likely closed |

### Peak Indicator (⬆+XX%)

When you see `⬆+76%` next to a rating, it means that band is currently performing 76% better than its typical performance for this hour of day (based on a 30-day average). This highlights exceptional openings worth taking advantage of.

The indicator only appears when performance exceeds 20% above typical.

## Web Version

Prefer a browser? View the full dashboard at [wspr.hb9vqq.ch](https://wspr.hb9vqq.ch)

## API

Public JSON endpoint for integration into your own tools:

```
https://wspr.hb9vqq.ch/api/dx.json
```

### Example Response

```json
{
  "updated": "2025-12-09T20:45:07+00:00",
  "bands": {
    "10m": {
      "index": 78.7,
      "rating": "Excellent",
      "forecast": 45.3,
      "forecast_rating": "Fair",
      "vs_typical": 76
    },
    "15m": {
      "index": 43.6,
      "rating": "Fair",
      "forecast": 38.4,
      "forecast_rating": "Fair"
    },
    "20m": {
      "index": 38.6,
      "rating": "Fair",
      "forecast": 37.0,
      "forecast_rating": "Fair"
    },
    "40m": {
      "index": 52.0,
      "rating": "Good",
      "forecast": 43.6,
      "forecast_rating": "Fair",
      "vs_typical": 52
    }
  },
  "solar": {"sfi": 183.0, "kp": 1.0, "ap": 4.0},
  "storm": {"probability": 0.0, "predicted_kp": 0.8}
}
```

### API Fields

| Field | Description |
|-------|-------------|
| `index` | Current DX Index (0-100) |
| `rating` | Human-readable rating |
| `forecast` | Tomorrow's predicted DX Index |
| `forecast_rating` | Tomorrow's predicted rating |
| `vs_typical` | Percentage above hourly baseline (only present if >20%) |

### Usage Examples

**curl**

```bash
curl -s https://wspr.hb9vqq.ch/api/dx.json | jq '.bands["10m"].rating'
```

**Python**

```python
import urllib.request, json
data = json.loads(urllib.request.urlopen("https://wspr.hb9vqq.ch/api/dx.json").read())
for band, info in data['bands'].items():
    peak = f" (+{info['vs_typical']}%)" if 'vs_typical' in info else ""
    print(f"{band}: {info['rating']}{peak}")
```

**JavaScript**

```javascript
fetch("https://wspr.hb9vqq.ch/api/dx.json")
  .then(r => r.json())
  .then(d => {
    for (const [band, info] of Object.entries(d.bands)) {
      const peak = info.vs_typical ? ` (+${info.vs_typical}%)` : "";
      console.log(`${band}: ${info.rating}${peak}`);
    }
  });
```

Updates every 10 minutes.

## How It Works

The DX Index is calculated from real-time WSPR (Weak Signal Propagation Reporter) data:

1. **Data source**: WSPR spots with distance >3000km (true DX paths)
2. **Normalization**: Spots per active transmitter (removes participation bias)
3. **Hourly comparison**: Current performance vs. 30-day average for this hour
4. **Solar/geomagnetic factors**: SFI, Kp, and Ap indices influence the rating

This provides a more accurate picture than traditional propagation predictions based solely on solar indices.

## License

MIT License - Free to use and modify.

## Author

73 de HB9VQQ

- Website: [wspr.hb9vqq.ch](https://wspr.hb9vqq.ch)
- GitHub: [github.com/HB9VQQ](https://github.com/HB9VQQ)
