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


# ── Entries Orphanet cannot give, kept here and not only in the output ────────────────────────
# Where Orphanet maps no ICD code, the code is read from the classification itself or from the CDC
# surveillance manual, and that is a judgement with a source rather than an API answer. These lived
# only in condition-icd.json until 21 September 2026, when a rebuild regenerated the file from the
# API and silently dropped all four, taking the ICD-10 codes off the commonest form of limb
# reduction. They are applied after the fetch on every run now, so a rebuild cannot lose them again.
CLASSIFICATION = "classification (not an Orphanet mapping)"
WHO = "WHO ICD-10, 2019 edition, chapter XVII block Q65-Q79"
CDC = ('CDC, National Birth Defects Prevention Network surveillance manual, chapter 4.9d '
       '"Limb Deficiency: Transverse Terminal (Q71.2, Q71.3, Q71.30, Q72.2, Q72.3, Q72.30)"')
MANUAL_ICD10 = {
    "Terminal transverse limb defect": [
        {"code": "Q71.2", "title": "Congenital absence of both forearm and hand", "relation": CLASSIFICATION, "source": CDC},
        {"code": "Q71.3", "title": "Congenital absence of hand and finger(s)", "relation": CLASSIFICATION, "source": CDC},
        {"code": "Q72.2", "title": "Congenital absence of both lower leg and foot", "relation": CLASSIFICATION, "source": CDC},
        {"code": "Q72.3", "title": "Congenital absence of foot and toe(s)", "relation": CLASSIFICATION, "source": CDC},
    ],
    "Polydactyly": [{"code": "Q69", "title": "Polydactyly", "relation": CLASSIFICATION, "source": WHO}],
}
MANUAL_NOTE = {
    "Brachydactyly": "ICD-10 has no code for brachydactyly as such; the shortened digit falls under other reduction deformities.",
    "Symbrachydactyly": "ICD-10 has no code for symbrachydactyly as such.",
}

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
    # the entries Orphanet cannot give, applied last so the API can never overwrite them
    for name, codes in MANUAL_ICD10.items():
        if name in rows and not rows[name].get("icd10"):
            rows[name]["icd10"] = codes
            print(f"  {name}: ICD-10 {', '.join(e['code'] for e in codes)} (from the classification, not Orphanet)")
    for name, note in MANUAL_NOTE.items():
        if name in rows and not rows[name].get("icd10"):
            rows[name]["icd10_note"] = note
    missing = [n for n in list(MANUAL_ICD10) + list(MANUAL_NOTE) if n not in rows]
    if missing:
        raise SystemExit(f"a hand-curated ICD entry names a condition the site no longer has: {missing}")

    OUT.write_text(json.dumps({
        "built": time.strftime("%Y-%m-%d"),
        "source": "Orphanet, Orphadata cross-referencing API (rd-cross-referencing), licence CC BY 4.0",
        "source_url": "https://api.orphadata.com/",
        "note": ("ICD-10 and ICD-11 codes as Orphanet maps them, with the mapping relation. An exact "
                 "mapping means the two concepts are the same thing; a narrower or broader mapping does not. "
                 "Where Orphanet maps nothing, the code is taken from the classification itself or from the CDC "
                 "surveillance manual, and each such entry carries its own source; those are held in "
                 "tools/build-condition-icd.py so that a rebuild cannot drop them."),
        "conditions": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(1 for v in rows.values() if v.get("icd10"))
    print(f"\nwrote {OUT.relative_to(HERE.parent)}: {n} of {len(rows)} conditions have an ICD-10 mapping")


if __name__ == "__main__":
    main()
