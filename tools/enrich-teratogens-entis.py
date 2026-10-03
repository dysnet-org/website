#!/usr/bin/env python3
"""Add the ENTIS expert list of known human structural teratogens to the register, with the
pregnancy facts documented for each of its 24 medicines.

Source of the list: experts of the European Network of Teratology Information Services, in
Bluett-Duncan et al., Birth Defects Res 2025;117(9):e2497, Table 1 (CC BY). The paper calls them
"known" and "confirmed" structural teratogens, so the list sets the level "known".

Source of the facts: tools/teratogen-medicine-facts.json. For each medicine, when in pregnancy
the harm occurs, the dose, the effects and the absolute risk, each with a verbatim quote from a
regulator's product information (US FDA, EMA, ANSM, MHRA), a systematic review, a large registry
or cohort study, or the ENTIS paper, read for that file and checked by two independent readers.
Nothing here is computed or inferred: a fact the file does not hold is absent from the page.

Nine of the 24 were not on the register (fosphenytoin, phenobarbital, primidone, acenocoumarol,
phenindione, carbimazole, acitretin, alitretinoin, bexarotene); they are added with the ENTIS
list as their source. The step is idempotent: rerun it after the other enrichment steps and
before tools/enrich-teratogens-exposure.py, which tags the new entries as medicines.

Run: python3 tools/enrich-teratogens-entis.py
"""
import json
import pathlib

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
FACTS = HERE / "teratogen-medicine-facts.json"
NAMES = HERE / "teratogen-medicine-names.json"   # tools/build-teratogen-names.py: RxNorm, EMA, ANSM
TIS = HERE / "teratogen-tis-links.json"           # tools/build-teratogen-tis-links.py: CRAT, Embryotox, bumps
RANK = {"known": 0, "presumed": 1, "suspected": 2}
# what a pharmacist advising a pregnant woman needs, each field a quoted fact or absent
PREG_FIELDS = ("regulatory", "window", "dose", "effects", "other_effects", "absolute_risk", "before_after", "paternal", "monitoring", "evidence_base")


# ATC groups of medicines applied or acting locally, and the route they stand for; every other code is systemic use
LOCAL_ROUTES = [("S01", "eye"), ("S02", "ear"), ("S03", "eye and ear"), ("D", "skin"), ("A01", "mouth"), ("G01", "vagina"),
                ("R01", "nose"), ("R02", "throat"), ("A07A", "gut, not absorbed"), ("C05", "rectum and veins, local")]


SYSTEMIC_D = ("D01B", "D05B", "D10B")   # antifungals, antipsoriatics and anti-acne medicines for systemic use


def atc_route(code):
    if code.startswith(SYSTEMIC_D):
        return "systemic"
    return next((r for p, r in LOCAL_ROUTES if code.startswith(p)), "systemic")


def level(e):
    """The entry's level: the strongest of its sources, as tools/build-teratogens.py computes it."""
    levels = [v for k, v in e["status"].items() if v in RANK]
    if "p65" in e["status"]:
        mech = next((x.get("mechanism", "") for x in e["sources"] if x["code"] == "p65"), "")
        levels.append("presumed" if "authoritative body" in mech.lower() else "known")
    return min(levels, key=lambda l: RANK[l]) if levels else "suspected"


def main():
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    data = json.loads(TERA.read_text(encoding="utf-8"))
    by_name = {e["name"]: e for e in data["entries"]}
    for n in facts["new_entries"]:
        if n["name"] not in by_name:
            e = {"name": n["name"], "cas": n["cas"], "ec": "", "sources": [], "status": {}, "jurisdictions": {}, "wiki": ""}
            data["entries"].append(e)
            by_name[n["name"]] = e
    src = facts["entis"]
    for e in data["entries"]:
        e["sources"] = [s for s in e["sources"] if s["code"] != "entis"]
        e["status"].pop("entis", None)
        e.pop("pregnancy", None)
    for e in data["entries"]:
        e.pop("cosmetic", None)
    for name, rec in facts["medicines"].items():
        e = by_name[name]
        if name in facts.get("entis_list", []):
            e["sources"].append({"label": src["label"], "code": "entis", "url": src["url"],
                                 "note": f'{rec["entis_name"]} is on the list of medicines that ENTIS experts identify as known human structural teratogens ({src["citation"]}).'})
            e["status"]["entis"] = "known"
        e["pregnancy"] = {k: v for k, v in rec.items() if k not in ("entis_name", "documented_as")}
        if rec.get("documented_as"):
            e["pregnancy"]["documented_as"] = rec["documented_as"]
    for name, rec in facts.get("cosmetics", {}).items():
        by_name[name]["cosmetic"] = rec
    # the generic and brand names a medicine is sold under, so it can be found by the name on the box
    names = json.loads(NAMES.read_text(encoding="utf-8")) if NAMES.exists() else {"entries": {}}
    for e in data["entries"]:
        e.pop("names", None)
        n = names["entries"].get(e["name"])
        if n and (n["generic"] or n["brands_us"] or n["brands_eu"] or n["brands_fr"] or n.get("brands_it") or n.get("brands_es") or n.get("brands_ca") or n.get("inn") or n.get("note")):
            own = e["name"].lower()
            inn = n.get("inn", [])
            langs = {l: [x for x in v if x.lower() not in own and x.lower() not in [i.lower() for i in inn]] for l, v in n.get("languages", {}).items()}
            e["names"] = {"inn": inn, "inn_checked": n.get("inn_checked", {}), "languages": {l: v for l, v in langs.items() if v}, "us_discontinued": n.get("brands_us_discontinued", []),
                          "wikidata": n.get("wikidata", []), "atc_codes": n.get("atc", []), "snomed": n.get("snomed", []),
                          "eu_url": n.get("brands_eu_url", {}), "eu_status": n.get("brands_eu_status", {}),
                          "it": n.get("brands_it", []), "es": n.get("brands_es", []), "ca": n.get("brands_ca", []),
                          "generic": [g for g in n["generic"] if g.lower() not in own and g.lower() not in [i.lower() for i in inn]], "us": n["brands_us"], "eu": n["brands_eu"],
                          "fr": n["brands_fr"], "rxcui": [i["rxcui"] for i in n["ingredients"]][:3], "resolved_as": n["resolved_as"], "read": names["read"], "note": n.get("note", "")}
    # the WHO ATC codes of each medicine, each with the route it stands for: RxNorm, Wikidata, or the WHO index checked by hand
    chk = json.loads((HERE / "teratogen-atc-checked.json").read_text(encoding="utf-8")) if (HERE / "teratogen-atc-checked.json").exists() else {"entries": {}}
    for e in data["entries"]:
        e.pop("atc_list", None); e.pop("atc_none", None)
        codes = {}
        for c in (e.get("names") or {}).get("atc_codes", []):
            codes.setdefault(c, "RxNorm")
        for c in e.get("atc") or []:
            codes.setdefault(c, "Wikidata")
        w = chk["entries"].get(e["name"])
        if w:
            for c, _n in w["codes"]:
                codes.setdefault(c, "WHO ATC/DDD Index")
            if not w["codes"] and not codes:
                e["atc_none"] = {"source": chk["source"], "url": w["url"], "read": chk["read"]}
        if codes:
            e["atc_list"] = sorted(({"code": c, "route": atc_route(c), "source": v} for c, v in codes.items()),
                                   key=lambda x: (x["route"] != "systemic", x["code"]))
    # the kinds of cosmetics, and brands, that companies reported to California as containing it
    cp = HERE / "teratogen-cosmetic-products.json"
    cpd = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {"entries": {}}
    for e in data["entries"]:
        e.pop("cosmetic_products", None)
        x = cpd["entries"].get(e["name"])
        if x:
            e["cosmetic_products"] = {**x, "data_until": cpd["data_until"], "source": cpd["source"]}
    # the page each teratology information service publishes on the medicine: linked, never copied
    tis = json.loads(TIS.read_text(encoding="utf-8"))["entries"] if TIS.exists() else {}
    for e in data["entries"]:
        e.pop("tis", None)
        links = tis.get(e["name"])
        if links:
            e["tis"] = [{"s": code, "t": x["title"], "u": x["url"]} for code in ("crat", "embryotox", "bumps") for x in links.get(code, [])]
    for e in data["entries"]:
        e["source_codes"] = sorted({s["code"] for s in e["sources"]})
        e["level"] = level(e)
    data["entries"].sort(key=lambda e: (RANK[e["level"]], e["name"].lower()))
    c = data["counts"]
    c["total"] = len(data["entries"])
    c["entis"] = len(facts.get("entis_list", []))
    c["pregnancy_documented"] = len(facts["medicines"])
    c["cosmetic_documented"] = len(facts.get("cosmetics", {}))
    c["entis_added"] = sum(1 for n in facts["new_entries"])
    c["pregnancy_facts"] = sum(1 for r in facts["medicines"].values() for f in PREG_FIELDS if r.get(f))
    c["with_names"] = sum(1 for e in data["entries"] if e.get("names"))
    c["brand_names"] = sum(len(e["names"]["us"]) + len(e["names"]["us_discontinued"]) + len(e["names"]["eu"]) + len(e["names"]["fr"]) + len(e["names"]["it"]) + len(e["names"]["es"]) + len(e["names"]["ca"]) for e in data["entries"] if e.get("names"))
    c["with_inn"] = sum(1 for e in data["entries"] if e.get("names", {}).get("inn"))
    centres = HERE / "teratogen-tis-centres.json"   # the survey of ENTIS member services
    c["tis_centres"] = len(json.loads(centres.read_text(encoding="utf-8"))["centres"]) if centres.exists() else 0
    c["cosmetic_products"] = sum(1 for e in data["entries"] if e.get("cosmetic_products"))
    c["with_atc"] = sum(1 for e in data["entries"] if e.get("atc_list"))
    c["epar_links"] = sum(len(e["names"]["eu_url"]) for e in data["entries"] if e.get("names"))
    c["tis_linked"] = sum(1 for e in data["entries"] if e.get("tis"))
    c["cosmetic_facts"] = sum(1 for r in facts.get("cosmetics", {}).values() for f in ("limit", "basis_dose", "effects", "conclusion") if r.get(f))
    for k in ("known", "presumed", "suspected"):
        if k in c:
            c[k] = sum(1 for e in data["entries"] if e["level"] == k)
    data["sources"]["entis"] = {"label": src["label"], "url": src["url"], "citation": src["citation"], "doi": src["doi"],
                                "authority": "Experts of the European Network of Teratology Information Services, the services families and doctors consult about exposures in pregnancy. The list names the medicines they identify as known human structural teratogens."}
    TERA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f'{c["entis"]} ENTIS medicines ({c["entis_added"]} added to the register); {c["pregnancy_facts"]} pregnancy facts; register now {c["total"]} entries')


if __name__ == "__main__":
    main()
