#!/usr/bin/env python3
"""Add Japan's government GHS classification to the teratogens register, read through PubChem.

The register's EU source is Annex VI of CLP, a Commission decision. This adds a second
public authority that classifies the same substances independently: the GHS classification
projects run by the Chemical Management Center of Japan's National Institute of Technology
and Evaluation for the Japanese ministries, to implement the labelling and safety-data-sheet
duties of the Industrial Safety and Health Act and the PRTR Law. Every classification names
the ministry that made it and the fiscal year, and revisions are published as such.

What is deliberately not taken: ECHA's Classification and Labelling Inventory, which is not
an assessment but the file of self-classifications each company notifies for the substance it
sells, and which the board has ruled out. Safe Work Australia's HCIS is left aside for now
too, because two of that agency's fifteen board seats represent employers' interests.

A NITE classification does not set an entry's level of evidence. The GHS hazard code alone
does not separate category 1A from 1B, so it cannot map onto the register's known, presumed
and suspected without guessing; it corroborates, and it adds a jurisdiction.

The classifications are read from the PubChem records already cached by the register's
PubChem lookup, so this script makes no network request of its own.

Usage: python3 tools/enrich-teratogens-nite.py [--dry-run]
"""
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "teratogens.json"
CACHE = ROOT / "tools" / "terato" / "pubchem"
SOURCE = "NITE-CMC"
CAS_RX = re.compile(r"^\d{2,7}-\d{2}-\d$")
REPR_RX = re.compile(r"^(H36[01][A-Za-z]*)\s*:\s*([^\[]+)")
FY_RX = re.compile(r"FY(\d{4})")
JAPAN = ("Classified by the Japanese government under the GHS. A substance so classified must carry GHS labelling "
         "and a safety data sheet under the Industrial Safety and Health Act and the PRTR Law; the classification "
         "itself does not ban the substance.")


def statements(rec):
    """The reproductive-toxicity codes NITE gave, with the reference that carries them."""
    refs = [r for r in rec.get("Reference", []) if r.get("SourceName") == SOURCE]
    if not refs:
        return None
    nums = {r.get("ReferenceNumber") for r in refs}
    items = []

    def walk(n):
        if isinstance(n, dict):
            for i in n.get("Information", []) or []:
                if i.get("ReferenceNumber") in nums:
                    items.append(i)
            for s in n.get("Section", []) or []:
                walk(s)
        elif isinstance(n, list):
            for x in n:
                walk(x)

    walk(rec)
    codes, signal = [], ""
    for i in items:
        strings = [s.get("String", "") for s in (i.get("Value") or {}).get("StringWithMarkup", []) if isinstance(s, dict)]
        if i.get("Name") == "GHS Hazard Statements":
            for s in strings:
                m = REPR_RX.match(s.strip())
                if m and m.group(1) not in codes:
                    codes.append(m.group(1))
        elif i.get("Name") == "Signal" and strings and not signal:
            signal = strings[0].strip()
    if not codes:
        return None
    ref = refs[0]
    name = ref.get("Name") or ""
    fy = FY_RX.search(name)
    return {"codes": codes, "signal": signal, "jp_name": name, "year": fy.group(1) if fy else "", "url": ref.get("URL") or ""}


def main():
    dry = "--dry-run" in sys.argv
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    entries = doc["entries"]
    cid_of = {}
    for f in CACHE.glob("cid-*.txt"):
        v = f.read_text().strip()
        if v:
            cid_of[f.name[4:-4]] = v

    hits = 0
    for e in entries:
        cas = (e.get("cas") or "").strip()
        e["sources"] = [s for s in e["sources"] if s.get("code") != "nite"]
        e["source_codes"] = [c for c in e.get("source_codes", []) if c != "nite"]
        e.get("jurisdictions", {}).pop("Japan", None)
        if not CAS_RX.match(cas) or cas not in cid_of:
            continue
        p = CACHE / f"ghs-{cid_of[cas]}.json"
        if not p.exists():
            continue
        try:
            rec = (json.loads(p.read_text()) or {}).get("Record") or {}
        except ValueError:
            continue
        got = statements(rec)
        if not got:
            continue
        hits += 1
        e["sources"].append({
            "label": "Japan: GHS classification by the government (NITE)",
            "code": "nite",
            "statements": got["codes"],
            "signal": got["signal"],
            "classified": got["year"],
            "jp_name": got["jp_name"],
            "url": got["url"],
            "via": "PubChem",
        })
        e["source_codes"] = sorted(set(e["source_codes"]) | {"nite"})
        e.setdefault("jurisdictions", {})["Japan"] = JAPAN

    doc.setdefault("sources", {})["nite"] = {
        "label": "Japan: GHS classification by the National Institute of Technology and Evaluation (NITE)",
        "url": "https://www.chem-info.nite.go.jp/chem/english/ghs/ghs_index.html",
        "via": "Read through PubChem (US National Library of Medicine), which republishes the classifications.",
        "authority": "Classification made for the Japanese government to implement GHS labelling and safety-data-sheet duties under the Industrial Safety and Health Act and the PRTR Law. Each result names the ministry and the fiscal year. It corroborates a classification; it does not set an entry's level on this page, because a GHS hazard code does not separate category 1A from 1B.",
    }
    doc["counts"]["nite"] = hits
    doc["counts"]["nite_read"] = time.strftime("%Y-%m-%d")
    doc["counts"]["nite_not_in_clp"] = sum(1 for e in entries if "nite" in e["source_codes"] and "clp" not in e["source_codes"])
    print(f"entries with a Japanese government classification for fertility or the unborn child: {hits}")
    print(f"of those, with no EU harmonised entry: {doc['counts']['nite_not_in_clp']}")
    if dry:
        print("dry run, nothing written")
        return
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
