#!/usr/bin/env bash
# Build docs/assets/map/ne10m.pmtiles from Natural Earth 10m (public domain).
# Sources: tools/ne10m/*.geojson from github.com/nvkelso/natural-earth-vector (git-ignored, ~50 MB).
# -r1 keeps every populated place at every zoom (7k curated points; Natural Earth
# already grades them with scalerank/min_zoom). Note: places/lakes/rivers use
# lowercase property names, admin0/admin1 uppercase.
# Requires tippecanoe ≥ 2.17 (brew install tippecanoe). Zoom 0–9: country → city level, no streets.
set -euo pipefail
cd "$(dirname "$0")/ne10m"
tippecanoe -o ../../docs/assets/map/ne10m.pmtiles --force \
  -Z0 -z9 --simplification=4 --detect-shared-borders \
  --coalesce-densest-as-needed --extend-zooms-if-still-dropping \
  -r1 \
  --include=ADM0_A3 --include=NAME --include=POP_EST --include=SCALERANK \
  --include=adm0_a3 --include=name --include=scalerank --include=pop_max --include=min_zoom \
  -L countries:ne_10m_admin_0_countries.geojson \
  -L admin1:ne_10m_admin_1_states_provinces_lines.geojson \
  -L places:ne_10m_populated_places_simple.geojson \
  -L lakes:ne_10m_lakes.geojson \
  -L rivers:ne_10m_rivers_lake_centerlines.geojson
ls -la ../../docs/assets/map/ne10m.pmtiles
