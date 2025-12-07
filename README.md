# DX Index CLI

A command-line tool for checking real-time HF radio propagation conditions.

```
═══════════════════════════════════════════════════════
  HF DX INDEX - Current Conditions
═══════════════════════════════════════════════════════
  Updated: 2025-12-07 12:45 UTC

  Band   Now      Rating       Tomorrow  
  ─────────────────────────────────────────────────────
  10m    28.7     🔴 Poor       28.7 (Poor)
  15m    31.1     🔴 Poor       29.8 (VeryPoor)
  20m    32.4     🔴 Poor       28.1 (VeryPoor)
  40m    38.4     🔴 Poor       28.8 (Poor)

  Solar: SFI 200 | Kp 1.0
═══════════════════════════════════════════════════════
  Source: wspr.hb9vqq.ch | 73 de HB9VQQ
```

## Installation

### Linux / macOS

```bash
# Download
curl -O https://raw.githubusercontent.com/HB9VQQ/dx/main/dx.py

# Make executable
chmod +x dx.py

# Optional: add to PATH
sudo mv dx.py /usr/local/bin/dx
```

### Windows

1. Download [dx.py](https://raw.githubusercontent.com/HB9VQQ/dx/main/dx.py)
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
10m:Poor(29) | 15m:Poor(31) | 20m:Poor(32) | 40m:Poor(38)
```

### JSON for scripting
```bash
$ dx --json | jq '.bands["10m"].rating'
"Poor"
```

### Notification when band opens
```bash
# Linux (notify-send)
dx --alert Good && notify-send "10m is open!"

# macOS
dx --alert Good && osascript -e 'display notification "10m is open!"'
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

## Rating Scale

| Rating | DX Index | Conditions |
|--------|----------|------------|
| 🔵 Excellent | ≥75 | Worldwide DX wide open |
| 🟢 Good | 50-75 | Reliable DX contacts |
| 🟠 Fair | 35-50 | Shorter openings, regional DX |
| 🔴 Poor | 25-35 | Few DX opportunities |
| ⚫ VeryPoor | <25 | Band likely closed |

## Web Version

Prefer a browser? View the full dashboard at [grafana.gafner.net](https://grafana.gafner.net/goto/_UcHBCWDg?orgId=1)

## License

MIT License - Free to use and modify.

## Author

73 de HB9VQQ

- Website: [wspr.hb9vqq.ch](https://wspr.hb9vqq.ch)
- GitHub: [github.com/HB9VQQ](https://github.com/HB9VQQ)
