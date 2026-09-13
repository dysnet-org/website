#!/usr/bin/env python3
"""Build docs/assets/map/registry-zones.geojson: areas covered by a registry that records our conditions.

Declarative inputs:
  tools/registry-zones.json  France, registry → départements (Santé publique France surveillance report).
  tools/registry-areas.json  elsewhere, registry → country / admin-1 areas (Orphanet records and each registry's scope).
Geometry: IGN Admin Express COG via france-geojson (Licence Ouverte) for the départements, Natural Earth 10m
admin-0 and admin-1 (public domain) for the rest, downloaded once to tools/geo/ (git-ignored), then subset and
simplified (Douglas-Peucker, tolerance in degrees) so the layer stays small.
Run: python3 tools/build-registry-zones.py
"""
import json, math, pathlib, urllib.request

HERE = pathlib.Path(__file__).parent
GEO = HERE / "geo"; GEO.mkdir(exist_ok=True)
OUT = HERE.parent / "docs" / "assets" / "map" / "registry-zones.geojson"
ZONES = json.loads((HERE / "registry-zones.json").read_text(encoding="utf-8"))
AREAS = json.loads((HERE / "registry-areas.json").read_text(encoding="utf-8"))
NE_A1 = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"
NE_A0 = HERE / "ne10m" / "ne_10m_admin_0_countries.geojson"  # already in the repository's map data
BASE = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
FILES = {"metro": "departements-version-simplifiee.geojson", "971": "departements/971-guadeloupe/departement-971-guadeloupe.geojson",
         "972": "departements/972-martinique/departement-972-martinique.geojson", "974": "departements/974-la-reunion/departement-974-la-reunion.geojson"}
TOL = 0.004  # degrees ≈ 300-400 m: enough for a country-to-city map
TOL_WIDE = 0.05  # national polygons: coarser, they are only ever seen at low zoom


def fetch(name):
    p = GEO / pathlib.Path(FILES[name]).name
    if not p.exists():
        with urllib.request.urlopen(urllib.request.Request(BASE + FILES[name], headers={"User-Agent": "DysNet map builder (info@dysnet.org)"}), timeout=60) as r:
            p.write_bytes(r.read())
    return json.loads(p.read_text(encoding="utf-8"))


def dp(points, tol):
    if len(points) < 3: return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-12
    idx, dmax = 0, 0.0
    for i in range(1, len(points) - 1):
        x, y = points[i]; d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
        if d > dmax: idx, dmax = i, d
    if dmax > tol:
        return dp(points[:idx + 1], tol)[:-1] + dp(points[idx:], tol)
    return [points[0], points[-1]]


def simplify_ring(ring, tol=TOL):
    closed = ring[0] == ring[-1]
    pts = dp([tuple(p) for p in (ring[:-1] if closed else ring)], tol)
    if len(pts) < 3: return None
    pts = [[round(x, 4), round(y, 4)] for x, y in pts]
    return pts + [pts[0]]


def simplify_geom(g, tol=TOL):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    out = []
    for poly in polys:
        rings = [r for r in (simplify_ring(ring, tol) for ring in poly) if r]
        if rings: out.append(rings)
    return {"type": "MultiPolygon", "coordinates": out}


def features_of(obj):  # a FeatureCollection or a single Feature
    return obj["features"] if obj.get("type") == "FeatureCollection" else [obj]


feats = {}
for f in features_of(fetch("metro")): feats[f["properties"]["code"]] = f
for code in ("971", "972", "974"):
    for f in features_of(fetch(code)): feats[f["properties"]["code"]] = f

features = []
for z in ZONES["zones"]:
    for code in z["departements"]:
        f = feats.get(code)
        if not f: print("missing département", code); continue
        features.append({"type": "Feature", "geometry": simplify_geom(f["geometry"]),
                         "properties": {"registry": z["registry"], "label": z["label"], "country": z["country"], "status": z["status"], "dep": code,
                                        "area": f["properties"]["nom"], "dep_name": f["properties"]["nom"], "website": z.get("website"),
                                        "source": ZONES.get("source", "")}})

# ── coverage outside France: national and admin-1 areas ──────────────────────
a1_path = GEO / "ne_10m_admin_1.geojson"
if not a1_path.exists():
    print("downloading Natural Earth admin-1 (40 MB, once)")
    with urllib.request.urlopen(urllib.request.Request(NE_A1, headers={"User-Agent": "DysNet map builder (info@dysnet.org)"}), timeout=300) as r:
        a1_path.write_bytes(r.read())
A1 = json.loads(a1_path.read_text(encoding="utf-8"))["features"]
A0 = json.loads(NE_A0.read_text(encoding="utf-8"))["features"]
for a in AREAS["areas"]:
    names, regions = set(a.get("admin1") or []), set(a.get("region") or [])
    if names or regions:
        picked = [f for f in A1 if f["properties"].get("adm0_a3") == a["iso3"]
                  and ((f["properties"].get("name") in names) or (f["properties"].get("region") in regions))]
        tol = TOL
    else:
        picked = [f for f in A0 if f["properties"].get("ADM0_A3") == a["iso3"]]
        tol = TOL_WIDE
    if not picked:
        print("no geometry for", a["registry"]); continue
    for f in picked:
        g = simplify_geom(f["geometry"], tol)
        features.append({"type": "Feature", "geometry": g,
                         "properties": {"registry": a["registry"], "label": a["label"], "country": a["country"], "status": a["status"],
                                        "area": a["area"], "website": a.get("website") or a.get("orphanet_url"),
                                        "source": a.get("source") or AREAS.get("source", "")}})
    print(f"  {a['registry']}: {len(picked)} polygon(s)")
OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
print(f"wrote {OUT.relative_to(HERE.parent)}: {len(features)} areas, {OUT.stat().st_size // 1024} KB")
