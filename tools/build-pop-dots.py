#!/usr/bin/env python3
"""Generate the "estimated people with a limb difference" dot layers.

Input : GHS-POP 2025, WGS84, 30 arc-second (~1 km) GeoTIFF (EU JRC, CC BY 4.0)
Output: newline-delimited GeoJSON in tools/pop/ (git-ignored), one file per zoom band:
          dots1.ndjson     1 base dot per 1,000 people, placed inside its 1 km cell   (z9)
          dots10.ndjson    1 base dot per 10,000 people, from 0.05° cells             (z6–8)
          dots100.ndjson   1 base dot per 100,000 people, from 0.25° cells            (z4–5)
          dots1000.ndjson  1 base dot per 1,000,000 people, from 1° cells             (z0–3)

Semantics. Base density is 1 dot per 1,000 people = 100 per 100,000. Every dot draws a
hidden u = uniform integer in [0, 10000); a condition of prevalence r per 100,000 is the
share r/100 of base dots, i.e. those with u < r*100. On the finest layer each kept dot
then stands for exactly one estimated person (pop/1000 * r/100 = pop*r/100000); on coarser
layers for 10, 100 and 1,000 people respectively.

u is not stored. Only the 17 thresholds round(r*100) of build-demo.py's DOT_RATES can ever
be compared against it, so each dot instead carries b = the rank of the lowest threshold
that admits it (bisect_right over the sorted distinct thresholds). The site keeps dots with
b <= rank(condition), which selects exactly the same dots. This costs one byte per dot in
place of a two-byte index into a 10,000-entry per-tile dictionary, and lets the 16% of dots
above the highest threshold -- which no condition could ever draw -- be dropped outright.
Together that is about 60% of the tileset. Adding a condition changes the ladder, so the
dot layers and tiles must be rebuilt whenever DOT_RATES gains an entry.

Deterministic (seeded), so the map does not shuffle between builds.
Run:  python3 tools/build-pop-dots.py tools/ghs/GHS_POP_*.tif
"""
import ast
import json
import pathlib
import sys

import numpy as np
import tifffile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).parent / "pop"
OUT.mkdir(exist_ok=True)
SEED = 20260906
STRIP = 1800  # rows per processing strip on the 1 km grid (memory bound ≈ 0.5 GB)


def thresholds():
    """The sorted distinct u-thresholds of build-demo.py's DOT_RATES, parsed from source so the
    rates stay defined in exactly one place. map-gl.js derives the same ladder from data.rates."""
    tree = ast.parse((ROOT / "build-demo.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "DOT_RATES" for t in node.targets
        ):
            return sorted({round(r * 100) for _, r, _ in ast.literal_eval(node.value)})
    raise SystemExit("DOT_RATES not found in build-demo.py")


T = np.array(thresholds())


GEO = {}  # filled from the GeoTIFF tags: origin (lon0, lat0) and pixel size (px, py)


def open_grid(path):
    print("opening", path, flush=True)
    tif = tifffile.TiffFile(path)
    page = tif.pages[0]
    sx, sy, _ = page.tags["ModelPixelScaleTag"].value
    _, _, _, lon0, lat0, _ = page.tags["ModelTiepointTag"].value
    GEO.update(lon0=lon0, lat0=lat0, px=sx, py=sy)
    print("  shape", page.shape, page.dtype, "| origin", (lon0, lat0), "| pixel", (sx, sy), flush=True)
    arr = page.asarray(out="memmap")          # LZW-decompressed once to a disk-backed memmap (needs imagecodecs)
    return arr


def dots_from_grid(grid_iter, factor, people_per_dot, name):
    """grid_iter yields (row0, block) where block is a 2-D population array whose rows start at row0
    (in cells of size cell_deg). Writes one NDJSON file; returns the dot count."""
    rng = np.random.default_rng(SEED + int(people_per_dot))
    path = OUT / f"{name}.ndjson"
    total = dropped = 0
    with path.open("w") as fh:
        for row0, block in grid_iter:
            block = np.where(block > 0, block, 0).astype(np.float32, copy=False)
            expected = block / np.float32(people_per_dot)
            count = np.floor(expected).astype(np.int32)
            count += (rng.random(expected.shape, dtype=np.float32) < (expected - count)).astype(np.int32)
            rows, cols = np.nonzero(count)
            if rows.size == 0:
                continue
            n = count[rows, cols]
            k = int(n.sum())
            rr = np.repeat(rows + row0, n).astype(np.float64)
            cc = np.repeat(cols, n).astype(np.float64)
            # rr/cc are aggregated-cell indices; convert to 1 km pixel space, then to degrees
            lon = GEO["lon0"] + (cc * factor + rng.random(k) * factor) * GEO["px"]
            lat = GEO["lat0"] - (rr * factor + rng.random(k) * factor) * GEO["py"]
            u = rng.integers(0, 10000, k)
            # b = rank of the lowest threshold admitting this dot; b == len(T) means no condition
            # can ever draw it, so it is not written at all (about 16% of dots).
            b = np.searchsorted(T, u, side="right")
            keep = b < len(T)
            lon, lat, b = lon[keep], lat[keep], b[keep]
            k = int(keep.sum())
            dropped += int(keep.size - k)
            fh.writelines(
                '{"type":"Feature","geometry":{"type":"Point","coordinates":[%.4f,%.4f]},"properties":{"b":%d}}\n' % (lon[j], lat[j], b[j])
                for j in range(k)
            )
            total += k
    print(f"  {name}: {total:,} dots (+{dropped:,} above every threshold, dropped) -> "
          f"{path.name} ({path.stat().st_size // 1_000_000} MB)", flush=True)
    return total


def strips(arr, factor):
    """Yield (row0_in_aggregated_cells, aggregated block) for the 1 km grid summed over factor×factor blocks."""
    h, w = arr.shape
    step = STRIP - (STRIP % factor)
    for r in range(0, h, step):
        block = np.asarray(arr[r:r + step], dtype=np.float32)
        block = np.where(block > 0, block, 0)
        bh = (block.shape[0] // factor) * factor
        bw = (w // factor) * factor                      # 43202 columns: drop the 2 spare columns
        if bh == 0:
            continue
        agg = block[:bh, :bw].reshape(bh // factor, factor, bw // factor, factor).sum(axis=(1, 3))
        yield r // factor, agg


def main():
    src = sys.argv[1]
    arr = open_grid(src)
    world = float(sum(np.where(b > 0, b, 0).sum() for _, b in strips(arr, 1)))
    print(f"  world population {world:,.0f}", flush=True)
    stats = {
        "dots1": dots_from_grid(strips(arr, 1), 1, 1_000, "dots1"),
        "dots10": dots_from_grid(strips(arr, 6), 6, 10_000, "dots10"),
        "dots100": dots_from_grid(strips(arr, 30), 30, 100_000, "dots100"),
        "dots1000": dots_from_grid(strips(arr, 120), 120, 1_000_000, "dots1000"),
    }
    (OUT / "stats.json").write_text(json.dumps(
        {"source": src, "world_population": world, "thresholds": T.tolist(), "dots": stats}, indent=1))
    print("done", stats)


if __name__ == "__main__":
    main()
