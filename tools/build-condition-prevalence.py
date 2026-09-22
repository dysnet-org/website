#!/usr/bin/env python3
"""Fetch Orphanet's birth prevalence for every coded condition on the site.

The conditions page orders its cards from the commonest to the rarest, and an order needs a figure
per card. The site already keeps its own verified table of rates in DOT_RATES, but that covers the
conditions the map draws dots for, which is fewer than half of the page. Orphanet publishes a birth
prevalence for some of the rest, with a class, a mean, a territory and a validation status, and this
fetches it so the order rests on published figures rather than on an impression of what is common.

ValMoy is per 100,000 births, the same unit DOT_RATES uses, which the classes confirm: a mean of 43.5
sits inside the class 1-5 / 10 000, and a mean of 0.4 inside 1-9 / 1 000 000.

A condition with no figure here and none in DOT_RATES is not rare; it is uncounted, and the page says
so rather than placing it as though it were the rarest thing on the list.

Output: tools/condition-prevalence.json
Usage: python3 tools/build-condition-prevalence.py
"""
import datetime
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
OUT = HERE / "condition-prevalence.json"
API = "https://api.orphadata.com/rd-epidemiology/orphacodes/{}?lang=en"


def codes_from_build():
    src = (HERE.parent / "build-demo.py").read_text(encoding="utf-8")
    blk = src[src.index("CONDITIONS = ["):]
    blk = blk[:blk.index("\n]\n")]
    return [(n, c) for n, c in re.findall(r'\(\s*"([^"]+)",\s*"[^"]*",\s*(\d+)', blk)]


def fetch(code):
    req = urllib.request.Request(API.format(code), headers={
        "Accept": "application/json", "User-Agent": "DysNet conditions builder (info@dysnet.org)"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r).get("data", {}).get("results")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _row(p):
    mean = float(p.get("ValMoy") or 0) or None
    return {"per_100000": mean, "class": p.get("PrevalenceClass"), "geo": p.get("PrevalenceGeographic"),
            "qualification": p.get("PrevalenceQualification"), "status": p.get("PrevalenceValidationStatus"),
            "source": (p.get("Source") or "").strip() or None}


def resolve_pubmed(rows):
    """First author, year and journal for every PubMed identifier Orphanet cites, from NCBI E-utilities.

    Orphanet's source field is a string such as "8766141[PMID]_EUROCAT ...[OTHER]". A reader of the
    epidemiology page is owed the study, not the number, so the identifiers are resolved here, once,
    and the page prints them; a build never queries PubMed itself."""
    pmids = sorted({m for v in rows.values() for r in v["birth_rows"] + v["point_rows"]
                    for m in re.findall(r"(\d{5,9})\[PMID\]", r.get("source") or "")})
    if not pmids:
        return {}
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id="
           + ",".join(pmids))
    req = urllib.request.Request(url, headers={"User-Agent": "DysNet conditions builder (info@dysnet.org)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)["result"]
    out = {}
    for pmid in pmids:
        x = res.get(pmid) or {}
        if not x.get("sortfirstauthor"):
            continue
        out[pmid] = {"first_author": x["sortfirstauthor"], "year": (x.get("pubdate") or "")[:4],
                     "journal": x.get("source") or "", "title": x.get("title") or ""}
    print(f"  resolved {len(out)} of {len(pmids)} PubMed identifiers")
    return out


def main():
    rows = {}
    for name, code in codes_from_build():
        res = fetch(code)
        time.sleep(0.15)
        prev = (res or {}).get("Prevalence") or []
        births = [p for p in prev if p.get("PrevalenceType") == "Prevalence at birth"]
        # the most precise row first: a value and class beats a class on its own
        births.sort(key=lambda p: (p.get("PrevalenceQualification") != "Value and class",
                                   -(float(p.get("ValMoy") or 0))))
        # every row Orphanet publishes is kept as well, because the spread between territories is
        # itself a finding: the epidemiology page shows it, the card order uses the head row only
        entry = {"orphacode": code, "birth_prevalence": None,
                 "birth_rows": [_row(p) for p in births],
                 "point_rows": [_row(p) for p in prev if p.get("PrevalenceType") == "Point prevalence"],
                 "cases": next((int(float(p.get("ValMoy"))) for p in prev
                                if p.get("PrevalenceType") == "Cases/families" and float(p.get("ValMoy") or 0)), None),
                 "cases_unit": next(("families" if "amil" in (p.get("PrevalenceQualification") or "") else "cases"
                                     for p in prev if p.get("PrevalenceType") == "Cases/families"), None)}
        if births:
            entry["birth_prevalence"] = _row(births[0])
            print(f"  {name}: {entry['birth_prevalence']['per_100000']} per 100,000 "
                  f"({births[0].get('PrevalenceClass')}, {births[0].get('PrevalenceGeographic')}); {len(births)} row(s)")
        else:
            print(f"  {name}: none")
        rows[name] = entry
    sources = resolve_pubmed(rows)
    n = sum(1 for v in rows.values() if (v.get("birth_prevalence") or {}).get("per_100000"))
    OUT.write_text(json.dumps({
        "built": datetime.date.today().isoformat(),
        "source": "Orphanet, Orphadata epidemiology API (rd-epidemiology), licence CC BY 4.0",
        "source_url": "https://api.orphadata.com/",
        "note": ("Birth prevalence per 100,000 births, as Orphanet publishes it, with the class, the territory "
                 "and Orphanet's validation status. Where a condition has several rows the most precise is kept, "
                 "a value and class before a class alone. A null means Orphanet publishes no birth prevalence for "
                 "that code, which says nothing about how common the condition is."),
        "sources": sources,
        "conditions": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.name}: {n} of {len(rows)} conditions have a birth prevalence from Orphanet")


if __name__ == "__main__":
    main()
