#!/usr/bin/env python3
"""Attach the published literature to each substance on the register.

This replaces an earlier attempt that searched the site's own bibliography. That
bibliography is screened to papers about limb difference, so asking it whether a substance
has been studied answered a question about the filter rather than about the evidence: it
found 29 substances of 577. tools/build-teratogen-papers.py asks PubMed directly instead,
once per substance, and this attaches the result.

Each substance gains the number of papers, up to five citations with their DOIs, and a flag
when one of them is a Cochrane systematic review.

The count is not a verdict. A paper may report harm, or report finding none. The register
says the literature exists and links it.

Usage: python3 tools/enrich-teratogens-papers.py [--dry-run]
"""
import json
import pathlib
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "teratogens.json"
PAPERS = ROOT / "tools" / "teratogen-papers.json"
PUBMED = "https://pubmed.ncbi.nlm.nih.gov/?term="


def main():
    dry = "--dry-run" in sys.argv
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    src = json.loads(PAPERS.read_text(encoding="utf-8"))
    found = src["substances"]

    hits = with_cochrane = shown = 0
    for e in doc["entries"]:
        for k in ("papers", "paper_count", "paper_doi", "paper_cochrane", "paper_query", "paper_cochrane_n"):
            e.pop(k, None)
        rec = found.get((e.get("cas") or "").strip()) or found.get(e["name"])
        if not rec:
            continue
        hits += 1
        shown += len(rec["papers"])
        e["paper_count"] = rec["count"]
        e["paper_cochrane_n"] = rec.get("cochrane", 0)
        e["paper_cochrane"] = bool(rec.get("cochrane"))
        e["paper_doi"] = any(p.get("doi") for p in rec["papers"])
        e["papers"] = rec["papers"]
        e["paper_query"] = PUBMED + urllib.parse.quote(rec["query"].replace(" AND (harm to the unborn child)", ""))
        if e["paper_cochrane"]:
            with_cochrane += 1

    doc["counts"].update({"papers_substances": hits, "papers_cochrane": with_cochrane,
                          "papers_shown": shown, "papers_built": src["built"]})
    doc.setdefault("sources", {})["pubmed"] = {
        "label": "PubMed: published literature on the substance and harm to the unborn child",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "authority": src["method"],
    }
    print(f"substances with published literature: {hits} of {len(doc['entries'])}")
    print(f"  with a Cochrane systematic review:  {with_cochrane}")
    print(f"  citations shown across all cards:   {shown}")
    top = sorted((x for x in doc["entries"] if x.get("paper_count")), key=lambda x: -x["paper_count"])[:8]
    for e in top:
        print(f'   {e["name"][:40]:42} {e["paper_count"]:>6} papers  cochrane={e["paper_cochrane_n"]}')
    if dry:
        print("dry run, nothing written")
        return
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
