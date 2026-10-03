#!/usr/bin/env python3
"""Which kinds of cosmetics a register teratogen is reported in, and examples by brand.

Source: the California Safe Cosmetics Program (California Department of Public Health), "Chemicals in
Cosmetics" open data on the California Health and Human Services open data portal. California law
(Health and Safety Code section 111792) requires a company that sells cosmetics in California to
report every product that contains a chemical listed as causing cancer or reproductive harm; the
dataset gives, for each report, the brand, the product name, its category and subcategory (for
example "Lip Color - Lipsticks, Liners, and Pencils"), the chemical, and the dates it was reported,
discontinued or reformulated.

A report says the company declared the chemical in the product, at an amount the dataset does not
give; it is not a test and it does not say the product harms. The register says exactly that.
Products are "current" when neither the product nor the chemical in it is marked discontinued or
removed. Examples are current products, one per brand, the most recently reported first.

Matching: by CAS number or by the California listing name, entry by entry, as checked for
tools/enrich-teratogens-exposure.py (MATCH below); an entry not listed here is not matched. Alcohol is
left out on purpose: the register tags it food and drink, because drinking is the exposure that harms,
not the ethanol in a lipstick or a lotion.

Output: tools/teratogen-cosmetic-products.json. The CSV is cached in tools/terato/cscp (git-ignored).
Run: python3 tools/build-teratogen-cosmetic-products.py
"""
import collections
import csv
import datetime
import json
import pathlib
import urllib.request

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
OUT = HERE / "teratogen-cosmetic-products.json"
CSV = HERE / "terato" / "cscp" / "cscpopendata.csv"
URL = "https://data.chhs.ca.gov/dataset/596b5eed-31de-4fd8-a645-249f3f9b19c4/resource/57da6c9a-41a7-44b0-ab8d-815ff2cd5913/download/cscpopendata.csv"
PAGE = "https://data.chhs.ca.gov/dataset/chemicals-in-cosmetics"
SEARCH = "https://cscpsearch.cdph.ca.gov/search/publicsearch"
EXAMPLES = 8

RETINOIDS = {"Retinol", "Retinol palmitate", "Retinyl acetate", "Acetic acid, retinyl ester", "Retinyl palmitate", "Vitamin A",
             "Vitamin A palmitate", "Retinol/retinyl esters, when in daily dosages in excess of 10,000 IU, or 3,000 retinol equivalents."}
# register entry (start of its name) -> the California chemical names that are the same substance
MATCH = {
    "toluene": {"Toluene"}, "styrene": {"Styrene"}, "Ethylene glycol (ingested)": {"Ethylene glycol"},
    "lead di(acetate)": {"Lead acetate"}, "All-trans retinoic acid": {"All-trans retinoic acid"},
    "benzo[a]pyrene": {"Benzo[a]pyrene"}, "Aspirin": {"Aspirin", "Acetylsalicylic acid"}, "Phenacemide": {"Phenacemide"},
    "Methanol": {"Methanol"}, "Benzene": {"Benzene"}, "Methyl chloride": {"Methyl chloride"},
    "lead powder": {"Lead"}, "Lead [Basis": {"Lead"}, "mercury": {"Mercury and mercury compounds"},
    "Mercury and mercury compounds": {"Mercury and mercury compounds"}, "ethylene oxide": {"Ethylene oxide"},
    "Acrylamide": {"Acrylamide"}, "Dichloroacetic acid": {"Dichloroacetic acid"}, "Bisphenol A (BPA)": {"Bisphenol A (BPA)"},
    "dibutyl phthalate": {"Di-n-butyl phthalate (DBP)"}, "N-methyl-2-pyrrolidone": {"N-Methylpyrrolidone"},
    "Chromium (hexavalent compounds)": {"Chromium (hexavalent compounds)"}, "Arsenic (inorganic oxides)": {"Arsenic (inorganic oxides)"},
    "Retinol/retinyl esters": RETINOIDS, "Cadmium": {"Cadmium and cadmium compounds"},
}


def ymd(d):
    m, dd, y = d.split("/")
    return f"{y}-{m}-{dd}"


def main():
    if not CSV.exists():
        CSV.parent.mkdir(parents=True, exist_ok=True)
        CSV.write_bytes(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "DysNet teratogens register"}), timeout=300).read())
    def line(b):   # the file is UTF-8 with a few Windows-1252 lines
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            return b.decode("cp1252", "replace")
    rows = list(csv.DictReader(line(b) for b in CSV.read_bytes().splitlines(keepends=True)))
    names = [e["name"] for e in json.loads(TERA.read_text(encoding="utf-8"))["entries"]]
    out = {}
    for prefix, chems in MATCH.items():
        hits = [n for n in names if n == prefix] or [n for n in names if n.startswith(prefix)]
        if len(hits) != 1:
            raise SystemExit(f"{prefix!r} matches {hits}")
        sel = [r for r in rows if r["ChemicalName"] in chems]
        if not sel:
            continue
        cur = [r for r in sel if not r["DiscontinuedDate"].strip() and not r["ChemicalDateRemoved"].strip()]
        cur_ids = {r["CDPHId"] for r in cur}
        types = collections.Counter()
        for pid, sub in {(r["CDPHId"], r["SubCategory"].strip()) for r in cur}:
            types[sub] += 1
        examples, seen = [], set()
        for r in sorted(cur, key=lambda r: ymd(r["MostRecentDateReported"]) if r["MostRecentDateReported"] else "", reverse=True):
            b = (r["BrandName"].strip() or r["CompanyName"].strip()).replace("Cosm\ufffdtiques", "Cosmétiques")
            if b.lower() in seen or "\ufffd" in b:   # a character the source file lost
                continue
            seen.add(b.lower())
            fix = lambda t: t.strip().replace("Cosm\ufffdtiques", "Cosmétiques").replace("Vernis \ufffd ongles", "Vernis à ongles").replace("\ufffd", "?")
            examples.append({"brand": b, "product": fix(r["ProductName"]), "type": r["SubCategory"].strip(),
                             "company": fix(r["CompanyName"]), "reported": ymd(r["MostRecentDateReported"]) if r["MostRecentDateReported"] else ""})
            if len(examples) == EXAMPLES:
                break
        ever_types = collections.Counter()
        for pid, sub in {(r["CDPHId"], r["SubCategory"].strip()) for r in sel}:
            ever_types[sub] += 1
        out[hits[0]] = {"california_names": sorted(chems & {r["ChemicalName"] for r in sel}),
                        "products_ever": len({r["CDPHId"] for r in sel}), "products_current": len(cur_ids),
                        "brands_current": len({(r["BrandName"].strip() or r["CompanyName"].strip()).lower() for r in cur}),
                        "types_current": types.most_common(6), "types_ever": ever_types.most_common(6), "examples": examples,
                        "last_report": max((ymd(r["MostRecentDateReported"]) for r in sel if r["MostRecentDateReported"]), default="")}
    data_until = max(ymd(r["MostRecentDateReported"]) for r in rows if r["MostRecentDateReported"])
    OUT.write_text(json.dumps({"read": datetime.date.today().isoformat(), "data_until": data_until,
                               "source": {"label": "California Safe Cosmetics Program, Chemicals in Cosmetics open data", "url": PAGE, "search": SEARCH,
                                          "authority": "California Department of Public Health"},
                               "entries": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out)} register entries reported in cosmetics; data until {data_until}")
    for n, v in sorted(out.items(), key=lambda kv: -kv[1]["products_current"]):
        print(f'{n[:40]:41} now {v["products_current"]:4} ever {v["products_ever"]:4} | {v["types_current"][:2]} | {[x["brand"] for x in v["examples"][:4]]}')


if __name__ == "__main__":
    main()
