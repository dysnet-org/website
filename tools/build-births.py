#!/usr/bin/env python3
"""Build tools/births.json: live births a year, per country, for the incidence table.

A birth prevalence says how many children in 10,000 births are born with a condition. To turn that
into how many children a year a country can expect, you need that country's births. The World Bank
publishes the two series this needs, population (SP.POP.TOTL) and the crude birth rate
(SP.DYN.CBRT.IN, births per 1,000 people), both CC BY 4.0; births = population x rate / 1000, taken
from the most recent year in which a country has both. Aggregates (regions, income groups) are left
out, so the file holds countries only.
Run: python3 tools/build-births.py
"""
import json, pathlib, time, urllib.request

HERE = pathlib.Path(__file__).parent
API = "https://api.worldbank.org/v2"
UA = {"User-Agent": "DysNet register (info@dysnet.org)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def series(indicator):
    out, page = {}, 1
    while True:
        d = get(f"{API}/country/all/indicator/{indicator}?format=json&per_page=1000&date=2015:2025&page={page}")
        if len(d) < 2 or not d[1]: break
        for r in d[1]:
            if r["value"] is None: continue
            out.setdefault(r["countryiso3code"], {})[int(r["date"])] = r["value"]
        if page >= d[0]["pages"]: break
        page += 1; time.sleep(0.2)
    return out


meta = {c["id"]: c for c in get(f"{API}/country?format=json&per_page=400")[1] if c["region"]["value"] != "Aggregates"}
pop, cbr = series("SP.POP.TOTL"), series("SP.DYN.CBRT.IN")

rows = []
for iso3, c in meta.items():
    years = sorted(set(pop.get(iso3, {})) & set(cbr.get(iso3, {})), reverse=True)
    if not years: continue
    y = years[0]
    p, b = pop[iso3][y], cbr[iso3][y]
    rows.append({"name": c["name"], "iso3": iso3, "iso2": c["iso2Code"], "region": c["region"]["value"].strip(),
                 "year": y, "population": int(round(p)), "birth_rate": round(b, 2), "births": int(round(p * b / 1000))})
rows.sort(key=lambda r: -r["births"])
(HERE / "births.json").write_text(json.dumps({
    "built": time.strftime("%Y-%m-%d"),
    "source": "World Bank open data (CC BY 4.0): population SP.POP.TOTL and crude birth rate SP.DYN.CBRT.IN, most recent year with both.",
    "source_url": "https://data.worldbank.org/indicator/SP.DYN.CBRT.IN",
    "countries": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
total = sum(r["births"] for r in rows)
print(f"{len(rows)} countries, {total:,} births a year in total; years {min(r['year'] for r in rows)}-{max(r['year'] for r in rows)}")
for r in rows[:8]: print(f"  {r['name'][:28]:30} {r['births']:>12,}  ({r['year']}, rate {r['birth_rate']})")
