#!/usr/bin/env python3
"""Fetch where each condition sits in Orphanet's classification: its parent groups and, for a
group, the disorders it covers.

The card for "Terminal transverse limb defect" carries ORPHA:498461, which Orphanet holds as a
group of disorders rather than a disease. A family who know their child's diagnosis as acheiria,
apodia or absence of the forearm and hand need to see that the card covers them, and a registry
that codes those forms needs to know they add up to this group. Orphanet publishes the tree; this
fetches it for every coded condition on the site and keeps the relations, the terms and the ICD
codes, so the cards can state what a code covers instead of asserting it.

Output: tools/orphanet-hierarchy.json
Usage: python3 tools/build-orphanet-hierarchy.py
"""
import datetime
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
OUT = HERE / "orphanet-hierarchy.json"
API = "https://api.orphadata.com"
MAX_DOWN = 3   # levels of children to follow under a group


def codes_from_build():
    """The ORPHAcodes of the conditions, read from CONDITIONS in build-demo.py, plus the codes the
    code-name table adds by hand (symbrachydactyly's 1570)."""
    src = (HERE.parent / "build-demo.py").read_text(encoding="utf-8")
    blk = src[src.index("CONDITIONS = ["):]
    blk = blk[:blk.index("\n]\n")]
    codes = [c for c in re.findall(r'\(\s*"[^"]+",\s*"[^"]*",\s*(\d+)', blk)]
    codes += re.findall(r'REG_CODE_NAMES\["(\d+)"\] = ', src)
    return sorted(set(codes), key=int)


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json",
                                                       "User-Agent": "DysNet conditions builder (info@dysnet.org)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["data"]["results"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


NODES = {}


def node(code):
    """One Orphanet concept: term, level, ICD codes with their relation, parents and children.
    A code the API does not know is kept with status "not found", because a card carrying it
    needs to say so rather than fail silently."""
    code = str(code)
    if code in NODES:
        return NODES[code]
    x = get(f"/rd-cross-referencing/orphacodes/{code}?lang=en")
    h = get(f"/rd-classification/orphacodes/{code}/hchids?lang=en")
    time.sleep(0.15)
    if x is None:
        NODES[code] = {"status": "not found", "term": None, "parents": [], "children": []}
        print(f"  ORPHA:{code}: not found in Orphadata")
        return NODES[code]
    h0 = h[0] if isinstance(h, list) and h else {}
    # An entity Orphanet has excluded from its nomenclature keeps a page and a term, but sits in
    # no classification: the API answers the cross-reference call and 404s the classification
    # call. That is the signal a card carrying such a code needs.
    status = "ok" if isinstance(h, list) and h else "not classified"
    if status != "ok":
        print(f"  ORPHA:{code}: {x.get('Preferred term')} is in no Orphanet classification (excluded from the nomenclature?)")
    refs = x.get("ExternalReference") or []
    icd = lambda src: [{"code": e.get("Reference"), "relation": e.get("DisorderMappingRelation") or ""} for e in refs if e.get("Source") == src]
    NODES[code] = {"status": status, "term": x.get("Preferred term"), "level": x.get("DisorderGroup"),
                   "flag": [f.get("Value") for f in (x.get("DisorderFlag") or [])],
                   "synonyms": x.get("Synonym") or [], "icd10": icd("ICD-10"), "icd11": icd("ICD-11"),
                   "omim": [e.get("Reference") for e in refs if e.get("Source") == "OMIM"],
                   "parents": [str(p) for p in (h0.get("parents") or [])], "children": [str(c) for c in (h0.get("childs") or [])],
                   "classifications": [c.get("hch_tag") for c in h] if isinstance(h, list) else []}
    print(f"  ORPHA:{code}: {NODES[code]['term']} ({NODES[code]['level']}) parents {NODES[code]['parents']} children {NODES[code]['children']}")
    return NODES[code]


def descendants(code, depth=0):
    """Every code under a group, followed down MAX_DOWN levels, in tree order."""
    out = []
    if depth >= MAX_DOWN:
        return out
    for c in node(code)["children"]:
        out.append(c)
        out += descendants(c, depth + 1)
    return out


def main():
    codes = codes_from_build()
    print(f"{len(codes)} coded conditions")
    conditions = {}
    for code in codes:
        n = node(code)
        for p in n["parents"]:
            node(p)                 # the parent's own term and level, one level up
        conditions[code] = {"parents": n["parents"], "descendants": descendants(code)}
    OUT.write_text(json.dumps({
        "fetched": datetime.date.today().isoformat(),
        "source": "Orphadata REST API (rd-cross-referencing and rd-classification), licence CC BY 4.0; the three Orphanet classifications holding limb defects agree on every relation recorded here",
        "note": "conditions[code] gives the condition's parent groups and every code under it, down to three levels; nodes[code] gives each concept's term, level (Disorder or Group of disorders), ICD-10 and ICD-11 codes with Orphanet's mapping relation, OMIM ids, parents and children. A code the API does not know carries status \"not found\".",
        "conditions": conditions, "nodes": NODES}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    groups = [c for c in codes if NODES[c].get("level") == "Group of disorders"]
    print(f"wrote {OUT.name}: {len(NODES)} concepts; groups among our conditions: {groups}; not found: {[c for c in codes if NODES[c]['status'] != 'ok']}")


if __name__ == "__main__":
    main()
