#!/usr/bin/env python3
"""Merge the register entries that Annex VI's multi-CAS rows split in two.

An Annex VI row covering several forms of a substance lists one CAS per line, each
followed by a footnote marker. The build used to read only the first line, which the CAS
validator then rejected, so the row was stored with no CAS at all and could not be merged
with the same substance arriving from another list. Warfarin, PFOS and abamectin each
ended up on the register twice, once with the EU classification and once with the
Californian listing, and for abamectin the two halves disagreed on the level of evidence.

tools/build-teratogens.py now reads every identifier in the cell, so a full rebuild would
not produce the split again. This script applies the same correction to the register as it
stands, which spares a re-run of the whole enrichment chain and the unreviewed drift that
a fresh crawl of Wikipedia and Wikidata would bring with it.

Two entries are merged only when they share a CAS number. Cadmium is left alone by that
rule without needing a special case: Annex VI classifies the pyrophoric and non-pyrophoric
forms separately and deliberately, both under CAS 7440-43-9, so its two Annex VI indexes are
named below and that one pair is left as it is.

Usage: python3 tools/merge-teratogens-dupes.py [--dry-run]
"""
import json
import pathlib
import re
import sys

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "teratogens.json"
ANNEX = ROOT / "tools" / "terato" / "annex_vi_clp_table_atp23_en.xlsx"
CAS_RX = re.compile(r"\d{2,7}-\d{2}-\d")
LEVEL_ORDER = {"known": 0, "presumed": 1, "suspected": 2}
# Annex VI gives these two rows separate classifications on purpose, so they stay separate
KEEP_APART = {("048-002-00-0", "048-011-00-X")}


def annex_cas_by_index():
    """index number -> every CAS the row lists, in order."""
    wb = openpyxl.load_workbook(ANNEX, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    out = {}
    for row in ws.iter_rows(values_only=True):
        vals = [str(v) if v is not None else "" for v in row]
        if not vals or not re.fullmatch(r"\d{3}-\d{3}-\d\d-[\dX]", vals[0].strip()):
            continue
        cas = CAS_RX.findall(vals[5] if len(vals) > 5 else "")
        if cas:
            out[vals[0].strip()] = cas
    return out


def level_of(entry):
    """The same rule the build applies: the strongest status wins."""
    levels = [v for v in entry["status"].values() if v in LEVEL_ORDER]
    if "p65" in entry["status"]:
        mech = next((x.get("mechanism", "") for x in entry["sources"] if x["code"] == "p65"), "")
        levels.append("presumed" if "authoritative body" in mech.lower() else "known")
    return min(levels, key=lambda l: LEVEL_ORDER[l]) if levels else "suspected"


def fold(keep, drop):
    """Fold drop into keep, preferring the value already present on keep."""
    for src in drop["sources"]:
        if src["code"] not in {s["code"] for s in keep["sources"]}:
            keep["sources"].append(src)
    for k, v in drop.get("status", {}).items():
        keep.setdefault("status", {}).setdefault(k, v)
    for k, v in drop.get("jurisdictions", {}).items():
        keep.setdefault("jurisdictions", {}).setdefault(k, v)
    for field in ("wiki", "ec", "cas", "medicinal", "atc", "medicine_evidence", "delisted", "efsa"):
        if not keep.get(field) and drop.get(field):
            keep[field] = drop[field]
    for field in ("uses", "use_evidence"):
        if not keep.get(field) and drop.get(field):
            keep[field] = drop[field]
    keep["source_codes"] = sorted({s["code"] for s in keep["sources"]})
    keep["level"] = level_of(keep)


def main():
    dry = "--dry-run" in sys.argv
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    entries = doc["entries"]
    by_index = annex_cas_by_index()

    # give every Annex VI entry that lost its CAS the one its row actually names
    recovered = 0
    for e in entries:
        if CAS_RX.fullmatch((e.get("cas") or "").strip()):
            continue
        src = next((s for s in e["sources"] if s.get("code") == "clp"), None)
        if not src:
            continue
        cas = by_index.get((src.get("index") or "").strip())
        if cas:
            e["cas"] = cas[0]
            recovered += 1

    # merge the pairs that now share one
    by_cas = {}
    merged, kept_apart = [], []
    for e in entries:
        cas = (e.get("cas") or "").strip()
        if not CAS_RX.fullmatch(cas):
            continue
        prev = by_cas.get(cas)
        if prev is None:
            by_cas[cas] = e
            continue
        idx = tuple(sorted(filter(None, (
            next((s.get("index") for s in prev["sources"] if s.get("code") == "clp"), None),
            next((s.get("index") for s in e["sources"] if s.get("code") == "clp"), None)))))
        if len(idx) == 2 and idx in KEEP_APART:
            kept_apart.append((prev["name"], e["name"]))
            continue
        # keep the entry whose name reads for a human: the shorter of the two
        keep, drop = (prev, e) if len(prev["name"]) <= len(e["name"]) else (e, prev)
        before = (keep["name"], keep["level"], list(keep["source_codes"]), drop["name"], drop["level"])
        fold(keep, drop)
        by_cas[cas] = keep
        merged.append((before, keep["level"], keep["source_codes"]))
        entries[:] = [x for x in entries if x is not drop]

    print(f"CAS numbers recovered from multi-form Annex VI rows: {recovered}")
    print(f"entries merged: {len(merged)}")
    for (kn, kl, ks, dn, dl), lvl, codes in merged:
        print(f"  {kn[:44]:46} ({kl}, {'+'.join(ks)})")
        print(f"    + {dn[:42]:44} ({dl})")
        print(f"    = {lvl}, {'+'.join(codes)}")
    for a, b in kept_apart:
        print(f"kept apart on purpose: {a[:40]} / {b[:40]}")
    print(f"entries: {len(entries)}")

    if dry:
        print("\ndry run, nothing written")
        return
    doc["counts"]["total"] = len(entries)
    doc["counts"]["both_clp_and_p65"] = sum(1 for e in entries if {"clp", "p65"} <= set(e["source_codes"]))
    for code in ("clp", "p65", "ema", "efsa"):
        doc["counts"][code] = sum(1 for e in entries if code in e["source_codes"])
    doc["counts"]["levels"] = {l: sum(1 for e in entries if e["level"] == l) for l in ("known", "presumed", "suspected")}
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
