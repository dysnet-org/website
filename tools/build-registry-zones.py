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


def crosses(p1, p2, p3, p4):
    def side(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)
    return side(p1, p2, p3) != side(p1, p2, p4) and side(p3, p4, p1) != side(p3, p4, p2)


def first_crossing(pts, window=60):
    """The first pair of ring edges that cross, or None. Douglas-Peucker only ever folds a ring
    onto itself locally, so comparing each edge with the next `window` is enough, and it keeps
    the check linear on the long coastlines (Alaska, Finland)."""
    n = len(pts) - 1
    for i in range(n):
        for j in range(i + 2, min(i + 2 + window, n)):
            if i == 0 and j == n - 1: continue
            if crosses(pts[i], pts[i + 1], pts[j], pts[j + 1]): return i, j
    return None


def unfold(pts):
    """Remove the vertices of a local fold: where two edges cross, the points between them are
    the spike. Returns None if the fold is too wide to be one, which asks for a finer tolerance."""
    for _ in range(400):
        hit = first_crossing(pts)
        if not hit: return pts
        i, j = hit
        if j - i > 6 or len(pts) - (j - i) < 4: return None
        pts = pts[:i + 1] + pts[j + 1:]
        if pts[0] != pts[-1]: pts = pts + [pts[0]]
    return None


def simplify_ring(ring, tol=TOL):
    """Simplify a closed ring without folding it onto itself.

    Douglas-Peucker is run on two halves split at the point farthest from the first, because
    running it on the ring as one open line uses a near-degenerate chord and folds the outline
    (that fold is what drew a wedge over the Baltic north of Poland). Folds that survive are
    unpicked vertex by vertex, and only a ring that stays folded is simplified less.
    """
    closed = ring[0] == ring[-1]
    base = [tuple(p) for p in (ring[:-1] if closed else ring)]
    if len(base) < 3: return None
    far = max(range(len(base)), key=lambda i: (base[i][0] - base[0][0]) ** 2 + (base[i][1] - base[0][1]) ** 2)
    t = tol
    for _ in range(4):
        pts = dp(base[:far + 1], t)[:-1] + dp(base[far:], t)[:-1] if far > 1 else list(base)
        if len(pts) < 3: return None
        pts = [[round(x, 4), round(y, 4)] for x, y in pts]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) < 3: return None
        fixed = unfold(pts + [pts[0]])
        if fixed and len(fixed) >= 4: return fixed
        t /= 2
    return [[round(x, 4), round(y, 4)] for x, y in base] + [[round(base[0][0], 4), round(base[0][1], 4)]]


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
                                        # the popup shows the short citation; the full one stays in the data file
                                        "source": ZONES.get("source_short") or ZONES.get("source", "")}})

# ── coverage outside France: national and admin-1 areas ──────────────────────
a1_path = GEO / "ne_10m_admin_1.geojson"
if not a1_path.exists():
    print("downloading Natural Earth admin-1 (40 MB, once)")
    with urllib.request.urlopen(urllib.request.Request(NE_A1, headers={"User-Agent": "DysNet map builder (info@dysnet.org)"}), timeout=300) as r:
        a1_path.write_bytes(r.read())
A1 = json.loads(a1_path.read_text(encoding="utf-8"))["features"]
A0 = json.loads(NE_A0.read_text(encoding="utf-8"))["features"]
for a in AREAS["areas"]:
    if a.get("map") is False or not a.get("iso3"):
        continue  # listed on the page, with no territory of its own to draw
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
                                        "source": a.get("source_short") or a.get("source") or AREAS.get("source_short") or AREAS.get("source", "")}})
    print(f"  {a['registry']}: {len(picked)} polygon(s)")
OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
print(f"wrote {OUT.relative_to(HERE.parent)}: {len(features)} areas, {OUT.stat().st_size // 1024} KB")
