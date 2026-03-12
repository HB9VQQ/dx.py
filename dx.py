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
    dx              # Show all bands (global)
    dx 10m          # Show specific band
    dx --region eu  # Show Europe DX conditions
    dx --json       # JSON output for scripting
    dx --compact    # One-line summary
    dx --watch      # Auto-refresh every 60s

Examples:
    dx                      # Current conditions all bands
    dx 10m 15m              # Specific bands only
    dx --region eu          # Europe to DX conditions
    dx --region na          # North America to DX conditions
    dx --compact            # "10m:Fair(42) 15m:Good(58) 20m:Good(61) 40m:Fair(45)"
    dx --json | jq '.bands["10m"].rating'   # Parse with jq
    dx --watch              # Live updates
    dx --alert Good         # Exit 0 if any band >= Good, else exit 1

Regions:
    eu  - Europe
    na  - North America
    sa  - South America
    as  - Asia
    oc  - Oceania
    af  - Africa

Author: HB9VQQ
Version: 2.4 - Mar 12, 2026 - Fixed SSB thresholds (≥3=Strong), SSB tie-breaker for best band
Version: 2.3 - Mar 12, 2026 - Regional uses DX Index from dxmap (not spots_per_tx)
Version: 2.2 - Mar 12, 2026 - Added SSB column from DX cluster (dxmap.hb9vqq.ch)
Version: 2.1 - Mar 12, 2026 - Calibrated regional thresholds (50/25/10 spots_per_tx)
Version: 2.0 - Mar 12, 2026 - Added --region for regional DX conditions
Version: 1.4 - Mar 12, 2026 - Added User-Agent header for Cloudflare compatibility
Version: 1.3 - Dec 11, 2025 - Dynamic band discovery from API (no update needed for new bands)
Version: 1.2 - Dec 11, 2025 - Added 80m band support
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

# DXMap URL for SSB/cluster spot data
DXMAP_URL = "https://dxmap.hb9vqq.ch/data"

# Band display order (highest frequency first)
# Bands not in this list will be appended at the end
BAND_ORDER = ["10m", "12m", "15m", "17m", "20m", "30m", "40m", "60m", "80m", "160m"]

# Valid regions
VALID_REGIONS = ["eu", "na", "sa", "as", "oc", "af"]

# Region full names for display
REGION_NAMES = {
    "eu": "Europe",
    "na": "North America",
    "sa": "South America",
    "as": "Asia",
    "oc": "Oceania",
    "af": "Africa"
}


def get_available_bands(data: dict) -> list:
    """Get available bands from API response, sorted by frequency"""
    available = list(data.get("bands", {}).keys())
    
    # Sort by BAND_ORDER, unknown bands go to end
    def sort_key(band):
        try:
            return BAND_ORDER.index(band)
        except ValueError:
            return 999
    
    return sorted(available, key=sort_key)


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
        req = urllib.request.Request(url, headers={'User-Agent': 'DXIndex/2.1'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f"Error: Cannot reach API - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid API response - {e}", file=sys.stderr)
        sys.exit(1)


def fetch_regional_v4_data(region: str) -> dict:
    """
    Fetch full regional data from dxmap v4.json.
    Returns: {
        'corridors': {
            corridor: {
                'best_band': str,
                'best_index': float,
                'bands': {band: {'index': float, 'ssb': int}, ...}
            }, ...
        }
    }
    """
    url = f"{DXMAP_URL}/{region.lower()}_v4.json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'DXIndex/2.2'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return aggregate_v4_by_corridor(data, region)
    except:
        return {'corridors': {}}


def aggregate_v4_by_corridor(data: dict, region: str) -> dict:
    """
    Aggregate v4.json paths by corridor.
    Returns best band (by max DX Index, SSB spots as tie-breaker) and SSB per corridor.
    """
    corridors = {}
    paths = data.get("paths", [])
    
    for path in paths:
        corridor_raw = path.get("corridor", "")
        band = path.get("band", "")
        index = path.get("index", 0) or 0
        ssb = path.get("cluster_spots", 0) or 0
        
        if not corridor_raw or not band:
            continue
        
        # Normalize corridor format (EU-NA -> EU↔NA, region first)
        corridor = normalize_corridor(corridor_raw, region)
        
        if corridor not in corridors:
            corridors[corridor] = {'bands': {}}
        
        if band not in corridors[corridor]['bands']:
            corridors[corridor]['bands'][band] = {'max_index': 0, 'ssb': 0}
        
        # Track max index per band (best path)
        if index > corridors[corridor]['bands'][band]['max_index']:
            corridors[corridor]['bands'][band]['max_index'] = index
        
        # Use MAX for SSB (cluster_spots is already corridor-aggregated per path)
        if ssb > corridors[corridor]['bands'][band]['ssb']:
            corridors[corridor]['bands'][band]['ssb'] = ssb
    
    # Determine best band per corridor (highest max_index, prefer more SSB spots on ties)
    for corridor, cdata in corridors.items():
        best_band = None
        best_index = 0
        best_ssb = -1
        for band, bdata in cdata['bands'].items():
            # Higher index wins, or same index but more SSB spots
            if bdata['max_index'] > best_index or \
               (bdata['max_index'] == best_index and bdata['ssb'] > best_ssb):
                best_index = bdata['max_index']
                best_band = band
                best_ssb = bdata['ssb']
        cdata['best_band'] = best_band
        cdata['best_index'] = best_index
    
    # Sort corridors by best_index descending, filter out unknown and Antarctica
    sorted_corridors = dict(sorted(
        [(k, v) for k, v in corridors.items() 
         if not k.startswith('Unknown') and '↔AN' not in k and 'AN↔' not in k],
        key=lambda x: x[1].get('best_index', 0), 
        reverse=True
    ))
    
    return {'corridors': sorted_corridors}


def normalize_corridor(corridor_raw: str, region: str) -> str:
    """Normalize corridor format: EU-NA -> EU↔NA with user's region first."""
    if "-" in corridor_raw:
        parts = corridor_raw.split("-")
        region_upper = region.upper()
        if len(parts) == 2:
            if parts[1] == region_upper:
                return f"{parts[1]}↔{parts[0]}"
            else:
                return f"{parts[0]}↔{parts[1]}"
    return corridor_raw


def ssb_to_rating(spots: int) -> tuple:
    """
    Convert SSB cluster spots to rating and symbol.
    Thresholds match dxmap getSsbOutlookWspr():
    - ≥3: Strong
    - ≥1: Moderate
    - 0: --
    """
    if spots >= 3:
        return "Strong", "🔵"
    elif spots >= 1:
        return "Moderate", "🟢"
    else:
        return "--", "🔴"


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


def activity_to_rating(spots_per_tx: float) -> tuple:
    """
    Convert spots_per_tx to a rating and symbol.
    Based on best single WSPR path in the corridor.
    
    spots_per_tx = spots / tx_count per grid-pair (60-min rolling window)
    Corridor value = MAX of all grid-pairs in that corridor
    
    Calibrated from dx_index_regional_realtime_v4.py data:
    - ≥50: Exceptional path (e.g., VK→EU peak)
    - ≥25: Strong path, reliable QSOs
    - ≥10: Workable, may need patience
    - <10: Marginal/closed
    """
    if spots_per_tx >= 50:
        return "Excellent", "🔵"
    elif spots_per_tx >= 25:
        return "Good", "🟢"
    elif spots_per_tx >= 10:
        return "Fair", "🟠"
    else:
        return "Poor", "🔴"


def index_to_rating(dx_index: float) -> tuple:
    """
    Convert DX Index to rating and symbol.
    Matches dxmap thresholds.
    """
    if dx_index >= 70:
        return "Excellent", "🔵"
    elif dx_index >= 50:
        return "Good", "🟢"
    elif dx_index >= 35:
        return "Fair", "🟠"
    else:
        return "Poor", "🔴"


def format_regional(data: dict, region: str, use_ascii: bool = False) -> str:
    """Format regional DX conditions for terminal display using v4 data"""
    region_name = REGION_NAMES.get(region, region.upper())
    
    # Fetch v4 data from dxmap (has DX Index and SSB spots)
    v4_data = fetch_regional_v4_data(region)
    corridors = v4_data.get('corridors', {})
    
    if not corridors:
        lines = []
        lines.append("")
        lines.append("═══════════════════════════════════════════════════════════════════")
        lines.append(f"  HF DX INDEX - {region_name} DX Conditions")
        lines.append("═══════════════════════════════════════════════════════════════════")
        lines.append("")
        lines.append("  No active DX corridors at this time")
        lines.append("")
        lines.append("═══════════════════════════════════════════════════════════════════")
        return "\n".join(lines)
    
    lines = []
    lines.append("")
    lines.append("═══════════════════════════════════════════════════════════════════")
    lines.append(f"  HF DX INDEX - {region_name} DX Conditions")
    lines.append("═══════════════════════════════════════════════════════════════════")
    
    # Get timestamp from global data
    if "updated" in data:
        try:
            ts = datetime.fromisoformat(data["updated"].replace("Z", "+00:00"))
            lines.append(f"  Updated: {ts.strftime('%Y-%m-%d %H:%M')} UTC")
        except:
            pass
    lines.append("")
    
    # Header - Digi = WSPR DX Index, SSB = DX Cluster
    lines.append(f"  {'Corridor':<12} {'Best Band':<10} {'Digi':<18} {'SSB':<18}")
    lines.append("  " + "─" * 60)
    
    # Each corridor (already sorted by best_index)
    for corridor, cdata in corridors.items():
        best_band = cdata.get("best_band", "?")
        best_index = cdata.get("best_index", 0)
        digi_rating, digi_symbol = index_to_rating(best_index)
        
        # Get SSB spots for this corridor on best band
        ssb_spots = 0
        if best_band and best_band in cdata.get('bands', {}):
            ssb_spots = cdata['bands'][best_band].get('ssb', 0)
        ssb_rating, ssb_symbol = ssb_to_rating(ssb_spots)
        
        if use_ascii:
            digi_symbol = {"🔵": "[++++]", "🟢": "[+++ ]", "🟠": "[++  ]", "🔴": "[+   ]"}.get(digi_symbol, "[    ]")
            ssb_symbol = {"🔵": "[++++]", "🟢": "[+++ ]", "🟠": "[++  ]", "🔴": "[+   ]"}.get(ssb_symbol, "[    ]")
        
        digi_str = f"{digi_symbol} {digi_rating}"
        if ssb_spots > 0:
            ssb_str = f"{ssb_symbol} {ssb_rating}"
        else:
            ssb_str = f"{ssb_symbol} --"
        
        lines.append(f"  {corridor:<12} {best_band:<10} {digi_str:<18} {ssb_str}")
    
    lines.append("")
    
    # Solar data from main dx.json
    solar = data.get("solar", {})
    if solar.get("sfi") and solar.get("kp"):
        lines.append(f"  Solar: SFI {solar['sfi']:.0f} | Kp {solar['kp']:.1f}")
    
    lines.append("═══════════════════════════════════════════════════════════════════")
    lines.append(f"  Source: dxmap.hb9vqq.ch | 73 de HB9VQQ")
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


def format_compact_regional(data: dict, region: str) -> str:
    """One-line compact format for regional data using v4 data"""
    # Fetch v4 data from dxmap
    v4_data = fetch_regional_v4_data(region)
    corridors = v4_data.get('corridors', {})
    
    if not corridors:
        return f"No active corridors from {region.upper()}"
    
    parts = []
    for corridor, cdata in corridors.items():
        band = cdata.get("best_band", "?")
        best_index = cdata.get("best_index", 0)
        digi_rating, _ = index_to_rating(best_index)
        
        # Get SSB spots for this corridor on best band
        ssb = 0
        if band and band in cdata.get('bands', {}):
            ssb = cdata['bands'][band].get('ssb', 0)
        ssb_rating, _ = ssb_to_rating(ssb)
        
        parts.append(f"{corridor}:{band}(D:{digi_rating[:1]}/S:{ssb_rating[:1]})")
    
    return " | ".join(parts)


def format_json(data: dict, bands: list) -> str:
    """JSON output for scripting"""
    available = get_available_bands(data)
    
    # Filter to requested bands if subset specified
    if set(bands) != set(available):
        filtered = {
            "updated": data.get("updated"),
            "bands": {b: data.get("bands", {}).get(b) for b in bands if b in data.get("bands", {})},
            "solar": data.get("solar"),
        }
        if "storm" in data:
            filtered["storm"] = data["storm"]
        return json.dumps(filtered, indent=2)
    
    return json.dumps(data, indent=2)


def format_json_regional(data: dict, region: str) -> str:
    """JSON output for regional data"""
    region_upper = region.upper()
    regions_data = data.get("regions", {})
    
    filtered = {
        "updated": data.get("updated"),
        "region": region_upper,
        "corridors": regions_data.get(region_upper, {}).get("corridors", {}),
        "solar": data.get("solar"),
    }
    if "storm" in data:
        filtered["storm"] = data["storm"]
    
    return json.dumps(filtered, indent=2)


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


def check_alert_regional(data: dict, region: str, min_rating: str) -> bool:
    """Check if any corridor in region meets minimum rating threshold"""
    rating_order = ["VeryPoor", "Poor", "Fair", "Good", "Excellent"]
    
    if min_rating not in rating_order:
        return False
    
    min_level = rating_order.index(min_rating)
    region_upper = region.upper()
    
    regions_data = data.get("regions", {})
    if region_upper not in regions_data:
        return False
    
    corridors = regions_data[region_upper].get("corridors", {})
    for corridor, info in corridors.items():
        spots_per_tx = info.get("spots_per_tx", 0)
        rating, _ = activity_to_rating(spots_per_tx)
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
  dx                      Show all bands (global)
  dx 10m 15m              Show specific bands
  dx --region eu          Show Europe DX conditions
  dx --region na          Show North America DX conditions
  dx --compact            One-line output
  dx --json               JSON for scripting
  dx --watch              Auto-refresh every 60s
  dx --alert Good         Exit 0 if any band >= Good

Regions: eu (Europe), na (N. America), sa (S. America), as (Asia), oc (Oceania), af (Africa)

Data source: https://tinyurl.com/HFDXProp
73 de HB9VQQ
        """
    )
    
    parser.add_argument("bands", nargs="*", help="Specific bands to show (e.g., 10m 15m)")
    parser.add_argument("--region", "-r", type=str, metavar="REGION",
                       help="Show regional DX conditions (eu, na, sa, as, oc, af)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--compact", action="store_true", help="One-line compact output")
    parser.add_argument("--ascii", action="store_true", help="ASCII symbols (no emoji)")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh every 60s")
    parser.add_argument("--interval", type=int, default=60, help="Refresh interval for --watch (default: 60)")
    parser.add_argument("--alert", type=str, metavar="RATING", 
                       help="Exit 0 if any band/corridor >= RATING (VeryPoor/Poor/Fair/Good/Excellent)")
    parser.add_argument("--url", type=str, default=API_URL, 
                       help=f"API endpoint URL (default: {DEFAULT_API_URL}, or set DX_API_URL env var)")
    
    args = parser.parse_args()
    
    # Validate region if specified
    if args.region:
        args.region = args.region.lower()
        if args.region not in VALID_REGIONS:
            print(f"Error: Invalid region '{args.region}'. Valid: {', '.join(VALID_REGIONS)}", file=sys.stderr)
            sys.exit(1)
    
    # Override API URL if specified (for testing)
    api_url = args.url
    
    # User-requested bands (validated after fetching data)
    requested_bands = args.bands if args.bands else None
    
    def refresh():
        data = fetch_data(api_url)
        
        # Regional mode
        if args.region:
            if args.alert:
                return check_alert_regional(data, args.region, args.alert)
            
            if args.json:
                print(format_json_regional(data, args.region))
            elif args.compact:
                print(format_compact_regional(data, args.region))
            else:
                print(format_regional(data, args.region, use_ascii=args.ascii))
            
            return None
        
        # Global mode (original behavior)
        available = get_available_bands(data)
        
        # Determine which bands to show
        if requested_bands:
            bands = [b for b in requested_bands if b in available]
            if not bands:
                print(f"Error: No valid bands specified. Available: {', '.join(available)}", file=sys.stderr)
                sys.exit(1)
        else:
            bands = available
        
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
