#!/usr/bin/env python3
"""Tell a family, on the card for the medicine itself, that a registry is recruiting.

The FDA keeps the public list of pregnancy exposure registries: studies that follow people
who took a medicine while pregnant and record what happened. That is how the effect of a
medicine on a pregnancy comes to be known in the first place, and taking part is one of the
few things a family can do with an exposure that has already happened.

The list is long and mostly about conditions this site does not cover, so it is matched
against the medicines already on the teratogens register. A registry is attached only when
the medicine matches, by its international non-proprietary name or by a brand name the FDA
prints beside it.

Matching is on name, so it is deliberately strict: an exact normalised match, and never a
substring, which would pair "Retin-A" with "tretinoin" or worse.

Usage: python3 tools/enrich-teratogens-registries.py [--dry-run]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "teratogens.json"
FDA = ROOT / "tools" / "fda-pregnancy-registries.json"


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def medicine_keys(medicine):
    """The FDA writes "Tegretol, Epitol (carbamazepine)": every brand, and the INN in brackets."""
    keys = []
    inn = re.findall(r"\(([^)]+)\)", medicine)
    for x in inn:
        # "(Medical Device)" and "(oral)" are not names
        if not re.search(r"device|oral|inject|tablet|capsule|topical|XR\b", x, re.I):
            keys.extend(re.split(r"\s+(?:and|or)\s+|,", x))
    brands = re.sub(r"\([^)]*\)", "", medicine)
    keys.extend(re.split(r",", brands))
    out = []
    for k in keys:
        n = norm(k.replace("®", "").replace("™", ""))
        if len(n) > 3 and n not in out:
            out.append(n)
    return out


def entry_keys(entry):
    """The register writes "carbendazim (ISO); methyl ...": take each clause, and the ATC name."""
    out = []
    for part in re.split(r"[;,]", entry["name"]):
        part = re.sub(r"\(ISO\)|\[.*?\]", "", part)
        n = norm(part)
        if len(n) > 3 and n not in out:
            out.append(n)
    return out


def main():
    dry = "--dry-run" in sys.argv
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    fda = json.loads(FDA.read_text(encoding="utf-8"))

    by_key = {}
    for r in fda["registries"]:
        for k in medicine_keys(r["medicine"]):
            by_key.setdefault(k, r)

    hits = 0
    for e in doc["entries"]:
        e.pop("registry", None)
        match = next((by_key[k] for k in entry_keys(e) if k in by_key), None)
        if not match:
            continue
        hits += 1
        e["registry"] = {
            "medicine": match["medicine"],
            "condition": match["condition"],
            "name": match["registry"],
            "status": match["status"],
            "url": match["urls"][0] if match["urls"] else fda["url"],
            "phone": match["phones"][0] if match["phones"] else "",
            "source": fda["source"],
            "source_url": fda["url"],
        }

    doc["counts"]["registries"] = hits
    doc["counts"]["registries_listed"] = fda["count"]
    doc["counts"]["registries_fetched"] = fda["fetched"]
    doc.setdefault("sources", {})["fda-registry"] = {
        "label": "FDA list of pregnancy exposure registries",
        "url": fda["url"],
        "authority": "A public list kept by the US Food and Drug Administration. " + fda["disclaimer"],
    }
    print(f"medicines on the register with a pregnancy registry recruiting: {hits} (of {fda['count']} listed)")
    for e in doc["entries"]:
        if e.get("registry"):
            print(f'   {e["name"][:34]:36} {e["registry"]["medicine"][:34]:36} {e["registry"]["condition"][:30]}')
    if dry:
        print("dry run, nothing written")
        return
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
