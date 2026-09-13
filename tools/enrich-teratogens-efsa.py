#!/usr/bin/env python3
"""Attach EFSA health-based guidance values to the teratogens register.

EFSA does not classify teratogens. It assesses substances in the food chain and derives the intake
considered tolerable, with the effect that figure rests on. This script adds that intake to the
substances of the register that EFSA has assessed, as a sixth source, without touching the level of
evidence, which stays with classification, medicines regulation and the WHO.

Input: tools/efsa-values.json (values quoted from EFSA, with the page and the date they were read).
When OpenFoodTox 3.0 (doi:10.5281/zenodo.19388272) is reachable, the same file can be generated from
it: match on CAS, keep the reference values whose critical effect is developmental or reproductive.
Run: python3 tools/enrich-teratogens-efsa.py
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
VALUES = HERE / "efsa-values.json"


def main():
    data = json.loads(TERA.read_text(encoding="utf-8"))
    spec = json.loads(VALUES.read_text(encoding="utf-8"))
    # start from a clean slate so a rerun never doubles the source
    for e in data["entries"]:
        e["sources"] = [s for s in e["sources"] if s["code"] != "efsa"]
        e.pop("efsa", None)
        e["source_codes"] = sorted({s["code"] for s in e["sources"]})

    n = 0
    for v in spec["values"]:
        cas = set(v.get("match_cas") or [])
        names = [x.lower() for x in (v.get("match_name") or [])]
        for e in data["entries"]:
            hit = (e.get("cas") and e["cas"] in cas) or any(e["name"].lower().startswith(x) for x in names)
            if not hit: continue
            e["sources"].append({"label": "EFSA health-based guidance value", "code": "efsa",
                                 "note": f'{v["label"]}: {v["value"]}. {v["note"]}', "url": v["url"]})
            e["efsa"] = {"label": v["label"], "value": v["value"], "url": v["url"], "read": v["read"]}
            e["source_codes"] = sorted({s["code"] for s in e["sources"]})
            n += 1
            print(f'  + {e["name"][:52]:54} {v["value"][:60]}')
    data["counts"]["efsa"] = n
    data["sources"]["efsa"] = {"label": "European Food Safety Authority, health-based guidance values",
                               "url": "https://www.efsa.europa.eu/en/data-report/chemical-hazards-database-openfoodtox",
                               "authority": "EU agency for risk assessment in the food chain. EFSA derives the intake considered tolerable and names the effect it rests on; it does not classify substances as teratogens, and its remit stops at food and feed."}
    TERA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n} entries carry an EFSA value")


if __name__ == "__main__":
    main()
