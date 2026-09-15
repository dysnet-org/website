#!/usr/bin/env python3
"""Attach to each substance the decisions authorities have taken about it.

The register says what the law provides. This says what was decided, and by whom: the
Commission approved or refused this substance as a pesticide on this date; REACH forbids
supplying it to the public; a treaty eliminates it worldwide; these countries banned it.

Every decision carries the authority that took it, so a reader can see at a glance who
says what about a product, and in particular who has approved one that the same register
describes as harmful to the unborn child.

Sources come from tools/teratogens-legal.json (built by build-teratogens-legal.py) and
tools/terato-rotterdam.json. Substances are matched on CAS number, except for the two
treaty sources, which publish names rather than identifiers and are matched on a
normalised name.

Usage: python3 tools/enrich-teratogens-legal.py [--dry-run]
"""
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "teratogens.json"
LEGAL = ROOT / "tools" / "teratogens-legal.json"
PIC = ROOT / "tools" / "terato-rotterdam.json"
POPS = ROOT / "tools" / "terato-stockholm.json"
CAS_RX = re.compile(r"^\d{2,7}-\d{2}-\d$")

# a product is not a substance: the EU refuses ethanol as a pesticide, which says nothing
# useful on a card about drinking in pregnancy
SKIP_PESTICIDE = {"product"}


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\(iso\)|\bsalts?\b|\besters?\b|\(.*?\)", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def eu_date(d):
    """DG SANTE writes dd/mm/yyyy; the register writes it out."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (d or "").strip())
    if not m:
        return (d or "").strip()
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    return f"{int(m.group(1))} {months[int(m.group(2)) - 1]} {m.group(3)}"


def main():
    dry = "--dry-run" in sys.argv
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    legal = json.loads(LEGAL.read_text(encoding="utf-8"))
    pic = json.loads(PIC.read_text(encoding="utf-8"))
    entries = doc["entries"]

    ppp = legal["by_cas"]["eu-ppp"]
    xiv = legal["by_cas"]["reach-xiv"]
    xvii = legal["by_cas"]["reach-xvii"]
    # the convention's own annex listing, captured rather than inferred: reading the annex from
    # the text nearest a name on the page put four Annex A chemicals under Annex B
    popsdoc = json.loads(POPS.read_text(encoding="utf-8"))
    pops = {}
    for ann, blk in popsdoc["annexes"].items():
        for chem in blk["chemicals"]:
            pops.setdefault(norm(chem), {"annex": ann, "name": chem, "effect": blk["effect"],
                                         "status": {"A": "eliminated", "B": "restricted", "C": "unintentional"}[ann],
                                         "url": popsdoc["url"]})
    pic_by_norm = {norm(k): (k, v) for k, v in pic["decisions"].items()}

    counts = {"eu-ppp": 0, "eu-ppp-approved": 0, "reach-xiv": 0, "reach-xvii": 0,
              "stockholm": 0, "rotterdam": 0, "any": 0}

    for e in entries:
        e.pop("decisions", None)
        cas = (e.get("cas") or "").strip()
        out = []

        if CAS_RX.match(cas) and cas in ppp and e.get("kind") not in SKIP_PESTICIDE:
            r = ppp[cas]
            approved = r["status"] == "approved"
            out.append({
                "code": "eu-ppp",
                "authority": "European Commission",
                "where": "European Union",
                "verdict": r["status"],
                "tag": ("Approved as a pesticide" if approved else
                        "Refused as a pesticide" if r["status"] == "refused" else
                        "Pesticide decision pending"),
                "detail": (f"approved from {eu_date(r['from'])}" if approved and r.get("from") else "")
                          or (f"not approved, expired {eu_date(r['until'])}" if r.get("until") else "not approved"),
                "until": eu_date(r.get("until", "")),
                "substitution": r.get("substitution", False),
                "as": r.get("name", ""),
                "url": r.get("url", ""),
            })
            counts["eu-ppp"] += 1
            if approved:
                counts["eu-ppp-approved"] += 1

        if CAS_RX.match(cas) and cas in xvii:
            r = xvii[cas]
            out.append({
                "code": "reach-xvii",
                "authority": "European Commission",
                "where": "European Union",
                "verdict": "public_supply_banned",
                "tag": "Not to be sold to the public",
                "detail": f"reproductive toxicant category {r['category']}, REACH Annex XVII entry 30",
                "url": r.get("url", ""),
            })
            counts["reach-xvii"] += 1

        if CAS_RX.match(cas) and cas in xiv:
            r = xiv[cas]
            out.append({
                "code": "reach-xiv",
                "authority": "European Commission",
                "where": "European Union",
                "verdict": "authorisation_required",
                "tag": "Needs an EU authorisation",
                "detail": ("from " + r["until"]) if r.get("until") else "REACH Annex XIV",
                "url": r.get("url", ""),
            })
            counts["reach-xiv"] += 1

        key = next((norm(p) for p in re.split(r";", e["name"]) if norm(p) in pops), None)
        if key:
            r = pops[key]
            out.append({
                "code": "stockholm",
                "authority": "Stockholm Convention",
                "where": "Worldwide",
                "verdict": r["status"],
                "tag": ("Eliminated by treaty" if r["status"] == "eliminated" else
                        "Restricted by treaty" if r["status"] == "restricted" else
                        "Listed for unintentional release"),
                "detail": f"Annex {r['annex']}: {r['effect'].rstrip('.').lower()}",
                "as": r.get("name", ""),
                "url": r.get("url", ""),
            })
            counts["stockholm"] += 1

        hit = next((pic_by_norm[norm(p)] for p in re.split(r";", e["name"]) if norm(p) in pic_by_norm), None)
        if hit:
            name, acts = hit
            countries = sorted({a["country"] for a in acts})
            banned = sorted({a["country"] for a in acts if a["action"] == "Banned"})
            out.append({
                "code": "rotterdam",
                "authority": "national authorities, notified to the Rotterdam Convention",
                "where": "National decisions",
                "verdict": "banned_somewhere",
                "tag": (f"Banned in {len(banned)} countries" if len(banned) > 1 else
                        f"Banned in {banned[0]}" if banned else
                        f"Severely restricted in {len(countries)} countries"),
                "detail": ", ".join(countries),
                "countries": countries,
                "banned": banned,
                "actions": acts,
                "as": name,
                "url": pic["url"],
            })
            counts["rotterdam"] += 1

        if out:
            e["decisions"] = out
            counts["any"] += 1

    doc.setdefault("sources", {}).update({
        "eu-ppp": {"label": "EU Pesticides Database: approval of active substances", "url": "https://ec.europa.eu/food/plant/pesticides/eu-pesticides-database/start/screen/active-substances",
                   "authority": "European Commission, DG SANTE. Approval or refusal of a pesticide active substance under Regulation 1107/2009, by implementing regulation."},
        "reach-xvii": {"label": "REACH Annex XVII entry 30: reproductive toxicants not to be supplied to the public", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:" + legal.get("reach_celex", ""),
                       "authority": "Binding EU regulation. Appendices 5 and 6 name the category 1A and 1B reproductive toxicants that may not be placed on the market for supply to the general public."},
        "reach-xiv": {"label": "REACH Annex XIV: the authorisation list", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:" + legal.get("reach_celex", ""),
                      "authority": "Binding EU regulation. After the sunset date the substance may not be used or placed on the market at all unless the Commission grants an authorisation for a named use."},
        "stockholm": {"label": "Stockholm Convention on Persistent Organic Pollutants", "url": "https://www.pops.int/TheConvention/ThePOPs/AllPOPs/tabid/2509/Default.aspx",
                      "authority": "Treaty binding its parties: Annex A eliminates production and use, Annex B restricts it to accepted purposes."},
        "rotterdam": {"label": "Rotterdam Convention: national bans and severe restrictions", "url": pic["url"],
                      "authority": "Decisions taken by national authorities and notified to the convention. A notification records what one country decided, not a global status."},
    })
    doc["counts"].update({f"legal_{k}": v for k, v in counts.items()})
    doc["counts"]["legal_read"] = time.strftime("%Y-%m-%d")

    print(f"entries carrying at least one decision: {counts['any']} of {len(entries)}")
    for k in ("eu-ppp", "eu-ppp-approved", "reach-xvii", "reach-xiv", "stockholm", "rotterdam"):
        print(f"  {k:18} {counts[k]}")
    if dry:
        print("dry run, nothing written")
        return
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
