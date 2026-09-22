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


def main():
    rows = {}
    for name, code in codes_from_build():
        res = fetch(code)
        time.sleep(0.15)
        births = [p for p in ((res or {}).get("Prevalence") or [])
                  if p.get("PrevalenceType") == "Prevalence at birth"]
        # the most precise row first: a value and class beats a class on its own
        births.sort(key=lambda p: (p.get("PrevalenceQualification") != "Value and class",
                                   -(float(p.get("ValMoy") or 0))))
        if not births:
            rows[name] = {"orphacode": code, "birth_prevalence": None}
            print(f"  {name}: none")
            continue
        p = births[0]
        mean = float(p.get("ValMoy") or 0) or None
        rows[name] = {"orphacode": code,
                      "birth_prevalence": {"per_100000": mean, "class": p.get("PrevalenceClass"),
                                           "geo": p.get("PrevalenceGeographic"),
                                           "qualification": p.get("PrevalenceQualification"),
                                           "status": p.get("PrevalenceValidationStatus")}}
        print(f"  {name}: {mean} per 100,000 ({p.get('PrevalenceClass')}, {p.get('PrevalenceGeographic')})")
    n = sum(1 for v in rows.values() if (v.get("birth_prevalence") or {}).get("per_100000"))
    OUT.write_text(json.dumps({
        "built": datetime.date.today().isoformat(),
        "source": "Orphanet, Orphadata epidemiology API (rd-epidemiology), licence CC BY 4.0",
        "source_url": "https://api.orphadata.com/",
        "note": ("Birth prevalence per 100,000 births, as Orphanet publishes it, with the class, the territory "
                 "and Orphanet's validation status. Where a condition has several rows the most precise is kept, "
                 "a value and class before a class alone. A null means Orphanet publishes no birth prevalence for "
                 "that code, which says nothing about how common the condition is."),
        "conditions": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.name}: {n} of {len(rows)} conditions have a birth prevalence from Orphanet")


if __name__ == "__main__":
    main()
