#!/usr/bin/env python3
"""
DX Index CLI - Quick HF propagation check from command line

Queries the public API for current HF band conditions.
Default server: tinyurl.com/HFDXProp

Configuration:
    API endpoint can be changed via:
    - Environment variable: export DX_API_URL="https://your-server/api/dx.json"
    - Command line: dx --url https://your-server/api/dx.json

Usage:
    dx              # Show all bands
    dx 10m          # Show specific band
    dx --json       # JSON output for scripting
    dx --compact    # One-line summary
    dx --watch      # Auto-refresh every 60s

Examples:
    dx                      # Current conditions all bands
    dx 10m 15m              # Specific bands only
    dx --compact            # "10m:Fair(42) 15m:Good(58) 20m:Good(61) 40m:Fair(45)"
    dx --json | jq '.bands["10m"].rating'   # Parse with jq
    dx --watch              # Live updates
    dx --alert Good         # Exit 0 if any band >= Good, else exit 1

Author: HB9VQQ
Version: 1.1 - Dec 10, 2025 - Added vs_typical peak percentage display
Version: 1.0 - Dec 7, 2025
"""

import sys
import argparse
import time
import urllib.request
import urllib.error
import json
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================
# Default API endpoint - can be overridden with:
#   - Environment variable: DX_API_URL
#   - Command line: dx --url https://your-server/api/dx.json

import os

DEFAULT_API_URL = "https://wspr.hb9vqq.ch/api/dx.json"
API_URL = os.environ.get("DX_API_URL", DEFAULT_API_URL)

ALL_BANDS = ["10m", "15m", "20m", "40m"]

# Rating symbols for terminal
SYMBOLS = {
    "Excellent": "🔵",
    "Good": "🟢", 
    "Fair": "🟠",
    "Poor": "🔴",
    "VeryPoor": "⚫",
}

# ASCII fallback for terminals without emoji support
SYMBOLS_ASCII = {
    "Excellent": "[++++]",
    "Good": "[+++ ]",
    "Fair": "[++  ]", 
    "Poor": "[+   ]",
    "VeryPoor": "[    ]",
}


def fetch_data(url: str = API_URL) -> dict:
    """Fetch current conditions from public API"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f"Error: Cannot reach API - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid API response - {e}", file=sys.stderr)
        sys.exit(1)


def format_standard(data: dict, bands: list, use_ascii: bool = False) -> str:
    """Format output for terminal display"""
    if "error" in data:
        return f"Error: {data['error']}"
    
    symbols = SYMBOLS_ASCII if use_ascii else SYMBOLS
    
    lines = []
    lines.append("")
    lines.append("═══════════════════════════════════════════════════════")
    lines.append("  HF DX INDEX - Current Conditions")
    lines.append("═══════════════════════════════════════════════════════")
    
    # Parse timestamp
    if "updated" in data:
        try:
            ts = datetime.fromisoformat(data["updated"].replace("Z", "+00:00"))
            lines.append(f"  Updated: {ts.strftime('%Y-%m-%d %H:%M')} UTC")
        except:
            pass
    lines.append("")
    
    # Header
    lines.append(f"  {'Band':<6} {'Now':<8} {'Rating':<18} {'Tomorrow':<12}")
    lines.append("  " + "─" * 48)
    
    # Each band
    band_data = data.get("bands", {})
    for band in bands:
        if band in band_data:
            d = band_data[band]
            idx = d.get("index", 0)
            rating = d.get("rating", "?")
            symbol = symbols.get(rating, "?")
            fcst = d.get("forecast", 0)
            fcst_rating = d.get("forecast_rating", "?")
            
            # Add peak indicator if significant (>20% above typical)
            vs_typical = d.get("vs_typical")
            if vs_typical and vs_typical > 20:
                if use_ascii:
                    rating_str = f"{symbol} {rating} +{vs_typical}%"
                else:
                    rating_str = f"{symbol} {rating} ⬆+{vs_typical}%"
            else:
                rating_str = f"{symbol} {rating}"
            
            lines.append(f"  {band:<6} {idx:<8.1f} {rating_str:<18} {fcst:.1f} ({fcst_rating})")
    
    lines.append("")
    
    # Solar data
    solar = data.get("solar", {})
    if solar.get("sfi") and solar.get("kp"):
        lines.append(f"  Solar: SFI {solar['sfi']:.0f} | Kp {solar['kp']:.1f}")
    
    # Storm prediction
    storm = data.get("storm")
    if storm and storm.get("probability") is not None:
        prob = storm["probability"]
        kp = storm.get("predicted_kp", 0)
        if prob >= 50:
            if use_ascii:
                lines.append(f"  [!] Storm: {prob:.0f}% probability -> Kp {kp:.1f}")
            else:
                lines.append(f"  ⚠️  Storm: {prob:.0f}% probability → Kp {kp:.1f}")
        elif prob >= 30:
            lines.append(f"  Storm: {prob:.0f}% probability → Kp {kp:.1f}")
    
    lines.append("═══════════════════════════════════════════════════════")
    source = data.get("source", "wspr.hb9vqq.ch")
    # Strip protocol for display
    if source.startswith("https://"):
        source = source[8:]
    elif source.startswith("http://"):
        source = source[7:]
    lines.append(f"  Source: {source} | 73 de HB9VQQ")
    lines.append("")
    
    return "\n".join(lines)


def format_compact(data: dict, bands: list) -> str:
    """One-line compact format"""
    if "error" in data:
        return f"Error: {data['error']}"
    
    parts = []
    band_data = data.get("bands", {})
    for band in bands:
        if band in band_data:
            d = band_data[band]
            idx = d.get("index", 0)
            rating = d.get("rating", "?")
            vs_typical = d.get("vs_typical")
            
            if vs_typical and vs_typical > 20:
                parts.append(f"{band}:{rating}({idx:.0f})⬆{vs_typical}%")
            else:
                parts.append(f"{band}:{rating}({idx:.0f})")
    
    return " | ".join(parts)


def format_json(data: dict, bands: list) -> str:
    """JSON output for scripting"""
    # Filter to requested bands
    if bands != ALL_BANDS:
        filtered = {
            "updated": data.get("updated"),
            "bands": {b: data.get("bands", {}).get(b) for b in bands if b in data.get("bands", {})},
            "solar": data.get("solar"),
        }
        if "storm" in data:
            filtered["storm"] = data["storm"]
        return json.dumps(filtered, indent=2)
    
    return json.dumps(data, indent=2)


def check_alert(data: dict, bands: list, min_rating: str) -> bool:
    """Check if any band meets minimum rating threshold"""
    rating_order = ["VeryPoor", "Poor", "Fair", "Good", "Excellent"]
    
    if min_rating not in rating_order:
        return False
    
    min_level = rating_order.index(min_rating)
    
    band_data = data.get("bands", {})
    for band in bands:
        if band in band_data:
            rating = band_data[band].get("rating", "VeryPoor")
            if rating in rating_order:
                if rating_order.index(rating) >= min_level:
                    return True
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="DX Index CLI - Quick HF propagation check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dx                      Show all bands
  dx 10m 15m              Show specific bands
  dx --compact            One-line output
  dx --json               JSON for scripting
  dx --watch              Auto-refresh every 60s
  dx --alert Good         Exit 0 if any band >= Good

Data source: https://tinyurl.com/HFDXProp
73 de HB9VQQ
        """
    )
    
    parser.add_argument("bands", nargs="*", help="Specific bands to show (e.g., 10m 15m)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--compact", action="store_true", help="One-line compact output")
    parser.add_argument("--ascii", action="store_true", help="ASCII symbols (no emoji)")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh every 60s")
    parser.add_argument("--interval", type=int, default=60, help="Refresh interval for --watch (default: 60)")
    parser.add_argument("--alert", type=str, metavar="RATING", 
                       help="Exit 0 if any band >= RATING (VeryPoor/Poor/Fair/Good/Excellent)")
    parser.add_argument("--url", type=str, default=API_URL, 
                       help=f"API endpoint URL (default: {DEFAULT_API_URL}, or set DX_API_URL env var)")
    
    args = parser.parse_args()
    
    # Override API URL if specified (for testing)
    api_url = args.url
    
    # Filter bands if specified
    bands = ALL_BANDS
    if args.bands:
        bands = [b for b in args.bands if b in ALL_BANDS]
        if not bands:
            print("Error: No valid bands specified. Use: 10m, 15m, 20m, 40m", file=sys.stderr)
            sys.exit(1)
    
    def refresh():
        data = fetch_data(api_url)
        
        if args.alert:
            return check_alert(data, bands, args.alert)
        
        if args.json:
            print(format_json(data, bands))
        elif args.compact:
            print(format_compact(data, bands))
        else:
            print(format_standard(data, bands, use_ascii=args.ascii))
        
        return None
    
    if args.watch:
        try:
            while True:
                # Clear screen
                print("\033[2J\033[H", end="")
                refresh()
                print(f"[Auto-refresh every {args.interval}s - Ctrl+C to exit]")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
    else:
        result = refresh()
        if args.alert:
            sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
