#!/usr/bin/env python3
"""Fill the gaps in a self-hosted glyph range from a second font.

The map's labels come from Open Sans, and Open Sans has no glyph for the letters that transliterate
Arabic: Ḩ ḩ ḑ ḏ ṭ ṣ ẕ and their kin, U+1E00 to U+1EFF. MapLibre cannot lay out a label until it has
every glyph in it, so 124 city names in the Gulf, Egypt, Iraq and Afghanistan were drawn without the
letter or not at all. This takes the glyphs Open Sans does have, adds the missing ones from Noto Sans,
which is Open Sans's sibling by design and covers the whole block, and writes the range back under the
Open Sans fontstack name. The spliced letters are visibly Noto rather than Open Sans, which is the
price of drawing the name at all; the alternative was a gap in the middle of a word.

Mapbox glyph PBF, for reference:
  glyph     { id=1 uint32, bitmap=2 bytes, width=3 uint32, height=4 uint32, left=5 sint32, top=6 sint32, advance=7 uint32 }
  fontstack { name=1 string, range=2 string, glyphs=3 repeated glyph }
  glyphs    { stacks=1 repeated fontstack }

Usage: python3 tools/splice-glyph-range.py <base.pbf> <donor.pbf> <out.pbf>
"""
import sys
import pathlib

F = {1: "id", 2: "bitmap", 3: "width", 4: "height", 5: "left", 6: "top", 7: "advance"}


def read_varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7F) << s; s += 7
        if c < 0x80:
            return r, i


def fields(b):
    i = 0
    while i < len(b):
        key, i = read_varint(b, i)
        num, wire = key >> 3, key & 7
        if wire == 0:
            v, i = read_varint(b, i)
        elif wire == 2:
            ln, i = read_varint(b, i); v = b[i:i + ln]; i += ln
        elif wire == 5:
            v = b[i:i + 4]; i += 4
        elif wire == 1:
            v = b[i:i + 8]; i += 8
        else:
            raise ValueError(f"wire type {wire}")
        yield num, v


def zigzag_decode(n):
    return (n >> 1) ^ -(n & 1)


def zigzag_encode(n):
    return (n << 1) ^ (n >> 63) if n >= 0 else (-n << 1) - 1


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def tag(num, wire):
    return varint(num << 3 | wire)


def load(path):
    stacks = []
    for num, stack in fields(pathlib.Path(path).read_bytes()):
        if num != 1:
            continue
        name = rng = ""; glyphs = {}
        for n2, v in fields(stack):
            if n2 == 1:
                name = v.decode()
            elif n2 == 2:
                rng = v.decode()
            elif n2 == 3:
                g = {}
                for n3, v3 in fields(v):
                    g[F[n3]] = v3
                g["left"] = zigzag_decode(g.get("left", 0)); g["top"] = zigzag_decode(g.get("top", 0))
                g.setdefault("bitmap", b"")
                glyphs[g["id"]] = g
        stacks.append({"name": name, "range": rng, "glyphs": glyphs})
    return stacks[0]


def dump(stack, path):
    body = bytearray()
    body += tag(1, 2) + varint(len(stack["name"].encode())) + stack["name"].encode()
    body += tag(2, 2) + varint(len(stack["range"].encode())) + stack["range"].encode()
    for gid in sorted(stack["glyphs"]):
        g = stack["glyphs"][gid]
        gb = bytearray()
        gb += tag(1, 0) + varint(gid)
        if g.get("bitmap"):
            gb += tag(2, 2) + varint(len(g["bitmap"])) + g["bitmap"]
        gb += tag(3, 0) + varint(g["width"])
        gb += tag(4, 0) + varint(g["height"])
        gb += tag(5, 0) + varint(zigzag_encode(g["left"]))
        gb += tag(6, 0) + varint(zigzag_encode(g["top"]))
        gb += tag(7, 0) + varint(g["advance"])
        body += tag(3, 2) + varint(len(gb)) + bytes(gb)
    pathlib.Path(path).write_bytes(tag(1, 2) + varint(len(body)) + bytes(body))


def main():
    base_path, donor_path, out_path = sys.argv[1:4]
    base, donor = load(base_path), load(donor_path)
    added = sorted(set(donor["glyphs"]) - set(base["glyphs"]))
    for gid in added:
        base["glyphs"][gid] = donor["glyphs"][gid]
    dump(base, out_path)
    print(f"{base['name']} {base['range']}: {len(base['glyphs']) - len(added)} own + {len(added)} from "
          f"{donor['name']} -> {len(base['glyphs'])} glyphs, {pathlib.Path(out_path).stat().st_size:,} bytes")
    if added:
        print("  added:", "".join(chr(g) for g in added))


if __name__ == "__main__":
    main()
