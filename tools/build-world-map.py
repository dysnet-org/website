#!/usr/bin/env python3
"""Generate docs/assets/map/world.svg from Natural Earth 110m countries.

Source: tools/countries-110m.json (world-atlas 2.0.2, Natural Earth public-domain
data). Run once when the geometry needs refreshing; the output is committed so the
site build stays offline and dependency-free.

Projection: Natural Earth I (Šavrič et al. 2011), the same polynomial as
d3.geoNaturalEarth1. Antarctica is dropped for a cleaner landing map.
"""
import json
import math
import pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "countries-110m.json"
OUT = HERE.parent / "docs" / "assets" / "map" / "world.svg"
WIDTH = 1000.0
SKIP = {"010"}  # Antarctica


def natural_earth(lon, lat):
    l, p = math.radians(lon), math.radians(lat)
    p2 = p * p
    p4 = p2 * p2
    x = l * (0.8707 - 0.131979 * p2 + p4 * (-0.013791 + p4 * (0.003971 * p2 - 0.001529 * p4)))
    y = p * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4)))
    return x, -y


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def ring_coords(ring, arcs):
    pts = []
    for idx in ring:
        a = arcs[~idx] if idx < 0 else arcs[idx]
        seg = list(reversed(a)) if idx < 0 else a
        if pts:
            seg = seg[1:]
        pts.extend(seg)
    return pts


def main():
    topo = json.loads(SRC.read_text())
    arcs = decode_arcs(topo)
    countries = topo["objects"]["countries"]["geometries"]

    projected = []  # (id, name, [rings])
    for g in countries:
        # A few disputed territories carry no ISO numeric id; key them by name.
        cid = str(g["id"]).zfill(3) if "id" in g else "x-" + g["properties"]["name"].lower().replace(" ", "-").replace(".", "")
        if cid in SKIP:
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        rings = []
        for poly in polys:
            for ring in poly:
                rings.append([natural_earth(lon, lat) for lon, lat in ring_coords(ring, arcs)])
        projected.append((cid, g["properties"]["name"], rings))

    xs = [x for _, _, rs in projected for r in rs for x, _ in r]
    ys = [y for _, _, rs in projected for r in rs for _, y in r]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    scale = WIDTH / (maxx - minx)
    height = (maxy - miny) * scale

    def px(x, y):
        return (x - minx) * scale, (y - miny) * scale

    paths = []
    for cid, name, rings in projected:
        d = []
        for r in rings:
            pts = [px(x, y) for x, y in r]
            d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
        paths.append(f'<path id="c{cid}" data-name="{name}" d="{"".join(d)}"/>')

    # projection parameters so the page can place markers / region frames
    meta = {"minx": minx, "miny": miny, "scale": scale, "width": WIDTH, "height": round(height, 1)}
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {height:.1f}" '
           f'data-proj=\'{json.dumps(meta)}\' role="img" aria-label="World map">\n'
           '<g id="countries">\n' + "\n".join(paths) + "\n</g>\n</svg>\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.relative_to(HERE.parent)}: {len(paths)} countries, {OUT.stat().st_size // 1024} KB, viewBox 0 0 {WIDTH:.0f} {height:.1f}")
    print("projection meta:", json.dumps(meta))


if __name__ == "__main__":
    main()
