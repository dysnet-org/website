#!/usr/bin/env bash
# Build docs/assets/map/dots.pmtiles from the four dot layers written by build-pop-dots.py.
# Each layer lives only at the zooms where it is drawn (keeps the file small):
#   dots1000  z0–3   1 dot = 1,000 people
#   dots100   z4–5   1 dot = 100 people
#   dots10    z6–8   1 dot = 10 people
#   dots1     z9     1 dot = 1 person (site draws the condition's share of base dots)
# Requires tippecanoe ≥ 2.17 (pmtiles output) — brew install tippecanoe
set -euo pipefail
cd "$(dirname "$0")"
OUT=../docs/assets/map/dots.pmtiles
TMP=$(mktemp -d)
COMMON=(-P --no-feature-limit --no-tile-size-limit -l dots --force)

tippecanoe -o "$TMP/a.pmtiles" -Z0 -z3 "${COMMON[@]}" pop/dots1000.ndjson
tippecanoe -o "$TMP/b.pmtiles" -Z4 -z5 "${COMMON[@]}" pop/dots100.ndjson
tippecanoe -o "$TMP/c.pmtiles" -Z6 -z8 "${COMMON[@]}" pop/dots10.ndjson
tippecanoe -o "$TMP/d.pmtiles" -Z9 -z9 "${COMMON[@]}" pop/dots1.ndjson
tile-join -o "$OUT" --force --no-tile-size-limit "$TMP"/a.pmtiles "$TMP"/b.pmtiles "$TMP"/c.pmtiles "$TMP"/d.pmtiles
rm -rf "$TMP"
ls -la "$OUT"
