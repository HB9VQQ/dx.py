# dx.py - HF DX Index CLI

Command-line tool for real-time HF propagation conditions.

## Installation

```bash
# Download
curl -O https://raw.githubusercontent.com/HB9VQQ/dx.py/main/dx.py

# Run
python3 dx.py
```

**Requirements:** Python 3.6+ (no dependencies)

## Usage

```bash
dx.py                    # Global band conditions
dx.py --region eu        # Regional DX conditions  
dx.py --compact          # One-line output
dx.py --watch            # Auto-refresh
dx.py -v                 # Version
dx.py -h                 # Help
```

## Global Mode

```
═══════════════════════════════════════════════════════
  HF DX INDEX - Current Conditions
═══════════════════════════════════════════════════════
  Updated: 2026-03-13 09:26 UTC

  Band   Now      Rating             Tomorrow    
  ────────────────────────────────────────────────
  10m    34.9     🔴 Poor             36.7 (Fair)
  15m    34.9     🔴 Poor             36.0 (Fair)
  20m    71.6     🔵 Excellent ⬆+65%  53.6 (Good)
  40m    45.7     🟠 Fair             32.3 (Poor)
  80m    47.1     🟠 Fair             21.4 (Poor)

  Solar: SFI 120 | Kp 2
  ⚠️  Storm: 60% probability → Kp 3
═══════════════════════════════════════════════════════
  Source: tinyurl.com/HFDXProp | 73 de HB9VQQ
```

## Regional Mode

Shows DX conditions from your region with best bands for Digi (WSPR) and SSB (DX Cluster) separately:

```bash
dx.py --region eu
```

```
═══════════════════════════════════════════════════════════════════
  HF DX INDEX - Europe DX Conditions
═══════════════════════════════════════════════════════════════════
  Updated: 2026-03-13 09:26 UTC

  Corridor     Digi           SSB             
  ────────────────────────────────────────────
  EU↔AF        20m:100        🔴 --
  EU↔OC        15m:100        🟢 20m:Moderate
  EU↔AS        20m:100        🟢 15m:Moderate
  EU↔NA        20m:100        🔴 --
  EU↔SA        20m:71         🔴 --

  Solar: SFI 120 | Kp 2
═══════════════════════════════════════════════════════════════════
  Source: dxmap.hb9vqq.ch | 73 de HB9VQQ
```

**Regions:** eu, na, sa, as, oc, af

**Columns:**
- **Digi** - Best band by WSPR DX Index (0-100)
- **SSB** - Best band by DX Cluster spots (Strong ≥3, Moderate ≥1)

## Compact Output

```bash
dx.py --compact
10m:Poor(35) | 15m:Poor(35) | 20m:Excellent(72)⬆65% | 40m:Fair(46) | 80m:Fair(47)

dx.py --region eu --compact
EU↔AF:20m:100 | EU↔OC:15m:100/20m:M | EU↔AS:20m:100/15m:M | EU↔NA:20m:100 | EU↔SA:20m:71
```

## Options

| Option | Description |
|--------|-------------|
| `--region`, `-r` | Regional mode (eu/na/sa/as/oc/af) |
| `--compact` | One-line output |
| `--json` | JSON output |
| `--watch` | Auto-refresh (default 60s) |
| `--interval N` | Refresh interval in seconds |
| `--alert RATING` | Exit 0 if any band ≥ rating |
| `--ascii` | No emoji |
| `-v`, `--version` | Version |
| `-h`, `--help` | Help |

## Web Version

[dxmap.hb9vqq.ch](https://dxmap.hb9vqq.ch)

## Author

73 de HB9VQQ
