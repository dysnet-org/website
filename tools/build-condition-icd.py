#!/usr/bin/env python3
"""Fetch the ICD-10 and ICD-11 codes Orphanet maps to each condition this site describes.

The conditions page carried ORPHAcodes and no ICD code, which is the code a hospital, a
national registry and an insurer actually use. Orphanet publishes the mapping, and publishes
the relation with it: an exact mapping means the two concepts are the same, while a narrower
or broader one does not. That relation is kept here, because a code quoted without it invites
a reader to treat an approximation as an identity.

Conditions the site describes without an ORPHAcode get nothing: there is no mapping to fetch,
and guessing one would be worse than the blank.

Output: tools/condition-icd.json
Usage: python3 tools/build-condition-icd.py
"""
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
OUT = HERE / "condition-icd.json"
API = "https://api.orphadata.com/rd-cross-referencing/orphacodes/{}?lang=en"


def codes_from_build():
    """The ORPHAcodes of the conditions, read from CONDITIONS in build-demo.py."""
    src = (HERE.parent / "build-demo.py").read_text(encoding="utf-8")
    blk = src[src.index("CONDITIONS = ["):]
    blk = blk[:blk.index("\n]\n")]
    out = []
    for name, code in re.findall(r'\(\s*"([^"]+)",\s*"[^"]*",\s*(\d+|None)', blk):
        out.append((name, None if code == "None" else code))
    return out


def fetch(code):
    req = urllib.request.Request(API.format(code), headers={
        "Accept": "application/json", "User-Agent": "DysNet conditions builder (info@dysnet.org)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)["data"]["results"]


def rel_name(x):
    v = x.get("DisorderMappingRelation")
    return (v.get("name") if isinstance(v, dict) else v) or ""


def main():
    rows = {}
    for name, code in codes_from_build():
        if not code:
            rows[name] = {"orphacode": None, "note": "the site describes this condition without an ORPHAcode, so Orphanet has no mapping to give"}
            print(f"  {name}: no ORPHAcode")
            continue
        time.sleep(0.3)
        try:
            r = fetch(code)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            rows[name] = {"orphacode": code, "note": f"Orphanet did not answer ({e})"}
            print(f"  {name}: FAILED {e}")
            continue
        icd10, icd11 = [], []
        for x in r.get("ExternalReference") or []:
            src = str(x.get("Source") or "")
            entry = {"code": x.get("Reference"), "relation": rel_name(x)}
            if src.startswith("ICD-10"):
                icd10.append(entry)
            elif src.startswith("ICD-11"):
                icd11.append(entry)
        rows[name] = {"orphacode": code, "orphanet_name": r.get("Preferred term"),
                      "group": r.get("DisorderGroup"), "icd10": icd10, "icd11": icd11}
        shown = ", ".join(e["code"] for e in icd10) or "none"
        print(f"  {name}: ICD-10 {shown}")
    OUT.write_text(json.dumps({
        "built": time.strftime("%Y-%m-%d"),
        "source": "Orphanet, Orphadata cross-referencing API (rd-cross-referencing), licence CC BY 4.0",
        "source_url": "https://api.orphadata.com/",
        "note": ("ICD-10 and ICD-11 codes as Orphanet maps them, with the mapping relation. An exact "
                 "mapping means the two concepts are the same thing; a narrower or broader mapping does not."),
        "conditions": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(1 for v in rows.values() if v.get("icd10"))
    print(f"\nwrote {OUT.relative_to(HERE.parent)}: {n} of {len(rows)} conditions have an ICD-10 mapping")


if __name__ == "__main__":
    main()
