# DX Index CLI

A command-line tool for checking real-time HF radio propagation conditions.

```
═══════════════════════════════════════════════════════════════════
  HF DX INDEX - Current Conditions
═══════════════════════════════════════════════════════════════════
  Updated: 2026-03-12 20:30 UTC

  Band   Now      Rating             Tomorrow
  ────────────────────────────────────────────────────────────
  10m    62.4     🟢 Good            58.2 (Good)
  15m    71.3     🔵 Excellent       65.1 (Good)
  20m    68.9     🟢 Good            62.4 (Good)
  40m    45.2     🟠 Fair            42.8 (Fair)

  Solar: SFI 121 | Kp 2.0
═══════════════════════════════════════════════════════════════════
  Source: tinyurl.com/HFDXProp | 73 de HB9VQQ
```

## Installation

### Linux / macOS

```bash
# Download
curl -O https://raw.githubusercontent.com/HB9VQQ/dx.py/main/dx.py

# Make executable
chmod +x dx.py

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
# Show all bands (global)
dx

# Show specific bands
dx 10m 15m

# Regional DX conditions
dx --region eu
dx --region na

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

## Regional Mode

Check DX conditions from your region with both **Digi** (WSPR) and **SSB** (DX Cluster) indicators:

```bash
dx --region eu
```

```
═══════════════════════════════════════════════════════════════════
  HF DX INDEX - Europe DX Conditions
═══════════════════════════════════════════════════════════════════
  Updated: 2026-03-12 20:30 UTC

  Corridor     Best Band  Digi               SSB
  ────────────────────────────────────────────────────────────
  EU↔NA        20m        🔵 Excellent        🔵 Strong
  EU↔SA        10m        🔵 Excellent        🟢 Moderate
  EU↔AF        15m        🔵 Excellent        🔴 --
  EU↔OC        20m        🔵 Excellent        🔴 --
  EU↔AS        20m        🔵 Excellent        🔴 --

  Solar: SFI 121 | Kp 2.0
═══════════════════════════════════════════════════════════════════
  Source: dxmap.hb9vqq.ch | 73 de HB9VQQ
```

### Available Regions

| Code | Region |
|------|--------|
| `eu` | Europe |
| `na` | North America |
| `sa` | South America |
| `as` | Asia |
| `oc` | Oceania |
| `af` | Africa |

### Columns Explained

- **Digi**: WSPR-based DX Index (normalized propagation quality)
- **SSB**: DX Cluster spot activity (confirmed voice contacts)
- **Best Band**: Band with highest DX Index (SSB activity as tie-breaker)

## Examples

### Quick check

```bash
$ dx
```

### One-liner for status bar / tmux

```bash
$ dx --compact
10m:Good(62) | 15m:Excellent(71) | 20m:Good(69) | 40m:Fair(45)
```

### Regional compact

```bash
$ dx --region eu --compact
EU↔NA:20m(D:E/S:S) | EU↔SA:10m(D:E/S:M) | EU↔AF:15m(D:E/S:-) | EU↔OC:20m(D:E/S:-)
```

### JSON for scripting

```bash
$ dx --json | jq '.bands["10m"].rating'
"Good"
```

### Notification when band opens

```bash
# Linux (notify-send)
dx --alert Good && notify-send "HF bands are good!"

# macOS
dx --alert Good && osascript -e 'display notification "HF bands are good!"'
```

### Cron job for alerts

```bash
# Check every 15 minutes, send notification when any band is Good or better
*/15 * * * * /usr/local/bin/dx --alert Good && curl -s -X POST https://api.pushover.net/1/messages.json -d "token=xxx&user=xxx&message=HF bands are good!"
```

### Live monitor in terminal

```bash
$ dx --watch
```

## Rating Scale

### Global (DX Index)

| Rating | DX Index | Conditions |
|--------|----------|------------|
| 🔵 Excellent | ≥70 | Worldwide DX wide open |
| 🟢 Good | 50-70 | Reliable DX contacts |
| 🟠 Fair | 35-50 | Shorter openings, regional DX |
| 🔴 Poor | 20-35 | Few DX opportunities |
| ⚫ VeryPoor | <20 | Band likely closed |

### SSB (DX Cluster)

| Rating | Spots | Meaning |
|--------|-------|---------|
| 🔵 Strong | ≥3 | Active SSB contacts confirmed |
| 🟢 Moderate | 1-2 | Some SSB activity |
| 🔴 -- | 0 | No recent SSB spots |

## Web Version

Prefer a browser? View the full dashboard at [dxmap.hb9vqq.ch](https://dxmap.hb9vqq.ch)

## API

Public JSON endpoint for integration into your own tools:

```
https://wspr.hb9vqq.ch/api/dx.json
```

### Example Response

```json
{
  "updated": "2026-03-12T20:30:07+00:00",
  "bands": {
    "10m": {"index": 62.4, "rating": "Good", "forecast": 58.2, "forecast_rating": "Good"},
    "15m": {"index": 71.3, "rating": "Excellent", "forecast": 65.1, "forecast_rating": "Good"},
    "20m": {"index": 68.9, "rating": "Good", "forecast": 62.4, "forecast_rating": "Good"},
    "40m": {"index": 45.2, "rating": "Fair", "forecast": 42.8, "forecast_rating": "Fair"}
  },
  "solar": {"sfi": 121.0, "kp": 2.0, "ap": 7.0},
  "storm": {"probability": 15, "predicted_kp": 2.5}
}
```

Updates every 10 minutes.

## Data Sources

- **DX Index**: Derived from WSPR (Weak Signal Propagation Reporter) spots >3000km
- **SSB Outlook**: DX Cluster spots aggregated by corridor
- **Solar Data**: NOAA Space Weather Prediction Center

## License

MIT License - Free to use and modify.

## Author

73 de HB9VQQ

- Website: [dxmap.hb9vqq.ch](https://dxmap.hb9vqq.ch)
- GitHub: [github.com/HB9VQQ](https://github.com/HB9VQQ)
