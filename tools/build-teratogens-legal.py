#!/usr/bin/env python3
"""Collect the decisions public authorities have actually taken about these substances.

The register already states the law: a substance with an EU harmonised Repr. 1
classification cannot be approved as a pesticide unless exposure is negligible, because
Regulation 1107/2009 says so. That is a rule. It does not say whether this substance was
approved, refused or withdrawn, on what date, or by whom. This script collects the
decisions themselves, so that a card can name the authority that took each one.

Four sources, all of them a government or a treaty body:

  eu-ppp     European Commission, DG SANTE. The EU Pesticides Database: every active
             substance with its status, approved or not approved or pending, the dates
             and the implementing regulation. Keyed on CAS.
  reach-xiv  REACH Annex XIV, the authorisation list: substances that may not be used
             after their sunset date unless the Commission grants an authorisation.
             Read from the consolidated regulation. Keyed on CAS.
  reach-xvii REACH Annex XVII entry 30, appendices 5 and 6: the reproductive toxicants of
             category 1A and 1B that may not be supplied to the general public. This is
             the decision behind the sentence the register currently states as a rule.
  stockholm  Stockholm Convention: Annex A eliminates a substance worldwide, Annex B
             restricts it. Matched on name, then checked by hand, because the convention
             publishes its CAS numbers inside prose.
  rotterdam  Rotterdam Convention, notifications of final regulatory action: one row per
             country per chemical, banned or severely restricted, with the date. This is
             the only source that answers "where" rather than "whether". Matched on name.

Output: tools/teratogens-legal.json, keyed by CAS where the source gives one and by
normalised name where it does not. Raw downloads are cached under tools/terato/legal/,
which git ignores.

Usage: python3 tools/build-teratogens-legal.py [--refresh]
"""
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / "terato" / "legal"
OUT = ROOT / "tools" / "teratogens-legal.json"
UA = {"User-Agent": "dysnet-teratogens/1.0 (+https://www.dysnet.org/knowledge/teratogens/; info@dysnet.org)"}
CAS_RX = re.compile(r"\d{2,7}-\d{2}-\d")

EU_PPP = "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/active-substances-download?format=json&api-version=v3.0"
REACH_CELEX = "http://publications.europa.eu/resource/celex/"
REACH_SPARQL = "http://publications.europa.eu/webapi/rdf/sparql"
POPS = "https://www.pops.int/TheConvention/ThePOPs/AllPOPs/tabid/2509/Default.aspx"
PIC_FRA = "https://www.pic.int/Procedures/NotificationsofFinalRegulatoryActions/Database/tabid/1368/language/en-US/Default.aspx"


def fetch(url, name, headers=None, timeout=240):
    """Download once and keep it; these are large documents and the sources are slow."""
    path = CACHE / name
    if path.exists() and "--refresh" not in sys.argv:
        return path.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = r.read().decode("utf-8", "replace")
    path.write_text(txt, encoding="utf-8")
    return txt


def rows_of(table_html):
    return [[re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
             for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.S)]


def norm(name):
    """A name reduced to what two sources are likely to agree on."""
    n = (name or "").lower().replace("\xa0", " ")
    n = re.sub(r"\(iso\)|\(commercial mixture[^)]*\)|\bsalts?\b|\besters?\b", " ", n)
    n = re.sub(r"[^a-z0-9]+", "", n)
    return n


# ── 1. EU pesticides ──────────────────────────────────────────────────────────
def eu_pesticides():
    txt = fetch(EU_PPP, "eu-active-substances.jsonl")
    out = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        cas = (r.get("as_cas_number") or "").strip()
        if not CAS_RX.fullmatch(cas):
            continue
        status = (r.get("substance_status") or "").strip()
        if status not in ("Approved", "Not approved", "Pending"):
            continue
        law = re.search(r'href="([^"]+)"', r.get("legislations_actives") or "")
        prev = out.get(cas)
        # a CAS can appear on several rows; an approval is the fact that matters most
        if prev and prev["status"] == "Approved" and status != "Approved":
            continue
        out[cas] = {
            "source": "eu-ppp",
            "authority": "European Commission, DG SANTE",
            "status": {"Approved": "approved", "Not approved": "refused", "Pending": "pending"}[status],
            "what": "use as a pesticide active substance in the EU",
            "name": r.get("substance_name") or "",
            "from": r.get("approval_date") or "",
            "until": r.get("expiry_date") or "",
            "substitution": (r.get("candidate_for_substitution") or "").strip().lower() == "yes",
            "url": law.group(1) if law else "https://ec.europa.eu/food/plant/pesticides/eu-pesticides-database/start/screen/active-substances",
        }
    return out


# ── 2 and 3. REACH, from the consolidated regulation ──────────────────────────
def reach_celex():
    q = ("PREFIX cdm: <http://publications.europa.eu/ontology/cdm#> SELECT ?id WHERE "
         "{ ?w cdm:resource_legal_id_celex ?id . FILTER(STRSTARTS(STR(?id),'02006R1907')) } ORDER BY DESC(?id) LIMIT 1")
    url = f"{REACH_SPARQL}?query={urllib.parse.quote(q)}&format=application%2Fsparql-results%2Bjson"
    d = json.loads(fetch(url, "reach-celex.json", timeout=90))
    return d["results"]["bindings"][0]["id"]["value"]


def reach():
    celex = reach_celex()
    html = fetch(REACH_CELEX + celex, f"reach-{celex}.html",
                 headers={"Accept": "application/xhtml+xml", "Accept-Language": "eng"})
    tables = re.findall(r"<table.*?</table>", html, re.S)
    starts = [m.start() for m in re.finditer(r"<table", html)]

    def caption_before(i):
        s = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html[max(0, starts[i] - 4000):starts[i]]))
        return s[-300:]

    xiv, xvii = {}, {}
    for i, tb in enumerate(tables):
        cap = caption_before(i)
        rows = rows_of(tb)
        if "Sunset date" in tb and "Entry Nr" in tb:
            # Annex XIV: the substance cell carries the name, the EC and CAS numbers
            for r in rows[1:]:
                blob = " | ".join(r)
                cas = CAS_RX.findall(blob)
                sunset = re.search(r"Sunset date[^0-9]*(\d{1,2} \w+ \d{4})", blob)
                if not cas:
                    continue
                for c in cas:
                    xiv[c] = {
                        "source": "reach-xiv",
                        "authority": "European Commission, REACH Annex XIV",
                        "status": "authorisation_required",
                        "what": "any use in the EU after the sunset date, unless the Commission authorises it",
                        "name": re.split(r"\d{3}-\d{3}-\d\d-\d|\(EC", r[1] if len(r) > 1 else r[0])[0].strip(" ,;"),
                        "until": sunset.group(1) if sunset else "",
                        "entry": (r[0] or "").strip(),
                        "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
                    }
        m = re.search(r"Appendix (\d).{0,80}?Entry 30 . Reproductive toxicants: Category 1 ([AB])", cap, re.S)
        if m and rows and rows[0][:1] == ["Substances"]:
            cat = "1A" if m.group(2) == "A" else "1B"
            for r in rows[1:]:
                for c in (CAS_RX.findall(" | ".join(r)) or []):
                    xvii[c] = {
                        "source": "reach-xvii",
                        "authority": "European Commission, REACH Annex XVII entry 30",
                        "status": "public_supply_banned",
                        "what": "supply to the general public in the EU, as a substance or in a mixture above the concentration limit",
                        "name": (r[0] or "").strip(),
                        "category": cat,
                        "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
                    }
    return xiv, xvii, celex


# ── 4. Stockholm Convention ───────────────────────────────────────────────────
def stockholm():
    html = fetch(POPS, "stockholm-pops.html", timeout=90)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)))
    tables = re.findall(r"<table.*?</table>", html, re.S)
    names = []
    for tb in tables:
        for r in rows_of(tb):
            for c in r:
                c = c.replace("&nbsp;", " ").strip()
                if 3 < len(c) < 70 and not CAS_RX.search(c) and re.match(r"^[A-Za-z(]", c):
                    names.append(c)
    out = {}
    for n in dict.fromkeys(names):
        i = text.find(n)
        if i < 0:
            continue
        ann = re.search(r"Annex ([ABC])", text[i:i + 1400])
        if not ann:
            continue
        out[norm(n)] = {
            "source": "stockholm",
            "authority": "Stockholm Convention on Persistent Organic Pollutants",
            "status": {"A": "eliminated", "B": "restricted", "C": "unintentional"}[ann.group(1)],
            "what": {"A": "production and use worldwide, by treaty",
                     "B": "production and use worldwide, restricted to accepted purposes",
                     "C": "unintentional release, to be reduced"}[ann.group(1)],
            "name": n,
            "annex": ann.group(1),
            "url": "https://www.pops.int/TheConvention/ThePOPs/AllPOPs/tabid/2509/Default.aspx",
        }
    return out


# ── 5. Rotterdam Convention ───────────────────────────────────────────────────
def rotterdam():
    html = fetch(PIC_FRA, "rotterdam-fra.html", timeout=120)
    acts = {}
    for tb in re.findall(r"<table.*?</table>", html, re.S):
        for r in rows_of(tb):
            cells = [c for c in r if c]
            if len(cells) < 4:
                continue
            country, chem, use, action = cells[0], cells[1], cells[2], cells[3]
            if action not in ("Banned", "Severely Restricted"):
                continue
            when = cells[4] if len(cells) > 4 else ""
            acts.setdefault(norm(chem), {"name": chem, "actions": []})["actions"].append(
                {"country": country, "use": use, "action": action, "date": when})
    for k, v in acts.items():
        v["actions"].sort(key=lambda a: (a["country"], a["action"]))
        v["source"] = "rotterdam"
        v["authority"] = "Rotterdam Convention, notifications of final regulatory action"
        v["banned"] = sum(1 for a in v["actions"] if a["action"] == "Banned")
        v["restricted"] = sum(1 for a in v["actions"] if a["action"] == "Severely Restricted")
        v["countries"] = len({a["country"] for a in v["actions"]})
        v["url"] = PIC_FRA
    return acts


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    print("EU pesticides…", flush=True)
    ppp = eu_pesticides()
    print(f"  {len(ppp)} active substances with a status", flush=True)
    print("REACH…", flush=True)
    xiv, xvii, celex = reach()
    print(f"  Annex XIV: {len(xiv)} substances · Annex XVII entry 30: {len(xvii)} · from {celex}", flush=True)
    print("Stockholm…", flush=True)
    pops = stockholm()
    print(f"  {len(pops)} listed substances", flush=True)
    print("Rotterdam…", flush=True)
    pic = rotterdam()
    print(f"  {len(pic)} chemicals, {sum(len(v['actions']) for v in pic.values())} national decisions", flush=True)

    OUT.write_text(json.dumps({
        "built": time.strftime("%Y-%m-%d"),
        "reach_celex": celex,
        "by_cas": {"eu-ppp": ppp, "reach-xiv": xiv, "reach-xvii": xvii},
        "by_name": {"stockholm": pops, "rotterdam": pic},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwritten to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
