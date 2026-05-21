#!/usr/bin/env bash
# Download the latest Celestrak TLE catalog (free, public, refreshed every 6 hours).
#
# Usage: bash data/download_celestrak.sh
#
# Output: data/tle/active.tle  (a TLE catalog of all active satellites, ~9-10K objects)

set -euo pipefail

DATA_DIR="$(dirname "$0")/tle"
mkdir -p "$DATA_DIR"

echo "Downloading active satellite catalog from Celestrak..."
curl -fsSL \
  "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle" \
  -o "$DATA_DIR/active.tle"

LINES=$(wc -l < "$DATA_DIR/active.tle" | tr -d ' ')
SATS=$(( LINES / 3 ))
echo "Done. Got $SATS TLEs in $DATA_DIR/active.tle"
echo ""
echo "Other useful catalogs:"
echo "  Starlink only:   GROUP=starlink"
echo "  All Iridium:     GROUP=iridium-NEXT"
echo "  Geo:             GROUP=geo"
echo "Replace GROUP=active in the curl above to fetch them."
