#!/usr/bin/env python3
"""Find, for each medicine on the register, the page that teratology information services publish on it.

Three services of the European Network of Teratology Information Services (ENTIS) publish one
public page per medicine; tools/teratogen-tis-centres.json records the survey of all its centres.
Their terms allow a link, not a copy, so the register links to them and quotes nothing:

- CRAT, Paris (lecrat.fr): its search, one query per French substance name (ANSM, and the French INN
  from Wikidata and ChEBI) and per English name (INN, RxNorm ingredient); the pages titled "<substance> – Grossesse" and "<substance> – Exposition
  paternelle", including those that name two substances ("Phénytoïne / Fosphénytoïne"). Links open in a new window,
  as its legal notice requires.
- Embryotox, Berlin (embryotox.de): its A to Z index of medicines, which also lists synonyms.
- UKTIS, Newcastle (medicinesinpregnancy.org, the bumps leaflets): its A to Z index.

A page is linked only when its title names the medicine itself, not its class. Lareb in the
Netherlands is left out: its search sits behind a CAPTCHA.

Inputs: tools/teratogen-medicine-names.json (generic and French substance names).
Output: tools/teratogen-tis-links.json. Raw pages are cached in tools/terato/tis (git-ignored).

Run: python3 tools/build-teratogen-tis-links.py
"""
import datetime
import html
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
NAMES = HERE / "teratogen-medicine-names.json"
OUT = HERE / "teratogen-tis-links.json"
CACHE = HERE / "terato" / "tis"
UA = {"User-Agent": "Mozilla/5.0 (DysNet teratogen register; links only)"}

SERVICES = {
    "crat": {"label": "CRAT (Paris)", "site": "https://www.lecrat.fr", "language": "fr",
             "about": "Centre de Référence sur les Agents Tératogènes, AP-HP, Paris"},
    "embryotox": {"label": "Embryotox (Berlin)", "site": "https://www.embryotox.de", "language": "de",
                  "about": "Pharmakovigilanz- und Beratungszentrum für Embryonaltoxikologie, Charité, Berlin"},
    "bumps": {"label": "UKTIS bumps (UK)", "site": "https://www.medicinesinpregnancy.org", "language": "en",
              "about": "best use of medicines in pregnancy, the public leaflets of the UK Teratology Information Service"},
}
# names a service uses that no rule below derives; checked by hand against the page
ALIASES = {"valproic acid": ["valproate", "valproinsaeure", "sodium valproate", "acide valproique"],
           "lithium carbonate": ["lithium", "lithiumsalze"], "lithium citrate": ["lithium", "lithiumsalze"],
           "aspirin": ["acetylsalicylsaeure", "acide acetylsalicylique"],
           "mycophenolate mofetil": ["mycophenolat", "mycophenolsaeure", "mycophenolate"],
           "mycophenolic acid": ["mycophenolat", "mycophenolsaeure", "mycophenolate"]}
from teratogen_names_util import SALTS, fold, skel


def get(url, cache):
    p = CACHE / cache
    if p.exists():
        return p.read_text(encoding="utf-8")
    time.sleep(1.0)                                                 # one request a second
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        t = r.read().decode("utf-8", "replace")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8")
    return t


def text(t):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def candidates(name, n):
    out = set(n["generic"]) | {i["name"] for i in n["ingredients"]} | {s.title() for s in n.get("substances_fr", [])} | set(n.get("inn", [])) | \
        {x for l in ("fr", "de", "es", "it", "la") for x in n.get("languages", {}).get(l, [])}
    m = re.search(r"\(([^()]+)\)\s*$", name)
    out.add(m.group(1) if m else name)
    for c in list(out):
        out |= set(ALIASES.get(c.lower(), []))
    return {c for c in out if c and " / " not in c}


def main():
    names = json.loads(NAMES.read_text(encoding="utf-8"))["entries"]
    # Embryotox and bumps: their A to Z indexes, every title (synonyms included) keyed by skeleton
    idx = {"embryotox": {}, "bumps": {}}
    for u, t in re.findall(r'href="([^"]*medikament/[a-z0-9_-]+)"[^>]*>(.*?)</a>',
                           get("https://www.embryotox.de/arzneimittel/", "embryotox-index.html"), re.S):
        idx["embryotox"].setdefault(skel(text(t)), {"url": urllib.parse.urljoin("https://www.embryotox.de", u), "title": text(t)})
    for u, t in re.findall(r'href="([^"]*leaflets-a-z/[a-z0-9-]+/)"[^>]*>(.*?)</a>',
                           get("https://www.medicinesinpregnancy.org/leaflets-a-z/", "bumps-index.html"), re.S):
        k = skel(text(t))
        if k:
            idx["bumps"].setdefault(k, []).append({"url": urllib.parse.urljoin("https://www.medicinesinpregnancy.org", u), "title": text(t)})
    entries = {}
    for name, n in names.items():
        cands = candidates(name, n)
        keys = {skel(c) for c in cands} - {""}
        rec = {}
        e = [idx["embryotox"][k] for k in keys if k in idx["embryotox"]]
        if e:
            rec["embryotox"] = sorted({x["url"]: x for x in e}.values(), key=lambda x: x["url"])
        b = [x for k in keys if k in idx["bumps"] for x in idx["bumps"][k]]
        if b:
            rec["bumps"] = sorted({x["url"]: x for x in b}.values(), key=lambda x: x["url"])
        # CRAT: search each French and English name, keep the pages whose title names this substance
        crat = {}
        # queried by its French substance names and by its English names (INN and RxNorm ingredient), since CRAT's
        # search matches words and a page may be titled with either spelling
        fr = [s for s in n.get("substances_fr", [])] + list(n.get("languages", {}).get("fr", [])) + list(n.get("inn", [])) + [i["name"] for i in n["ingredients"] if " / " not in i["name"]]
        fr = fr or [c for c in cands if c.lower() in [g.lower() for g in n["generic"]]] or sorted(cands)[:1]
        for q in sorted({" ".join(SALTS.sub(" ", fold(c)).split()) for c in fr} - {""}):
            q = " ".join(q.split())
            page = get("https://www.lecrat.fr/?s=" + urllib.parse.quote(q), "crat-" + re.sub(r"[^a-z0-9]+", "-", q) + ".html")
            for u, t in re.findall(r'href="(https://www\.lecrat\.fr/\d+/)"[^>]*>(.*?)</a>', page, re.S):
                t = text(t)
                # "Lithium – Grossesse", "Acénocoumarol- Grossesse", "Phénytoïne / Fosphénytoïne – Grossesse"
                m = re.match(r"(.+?)\s*[–-]\s*(Grossesse|Exposition paternelle)$", t)
                if m and any(skel(part) in keys for part in re.split(r"\s*/\s*", m.group(1))):
                    crat[u] = {"url": u, "title": t}
        if crat:
            rec["crat"] = sorted(crat.values(), key=lambda x: (not x["title"].endswith("Grossesse"), x["url"]))
        if rec:
            entries[name] = rec
    out = {"read": datetime.date.today().isoformat(), "services": SERVICES, "entries": entries}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = {s: sum(1 for r in entries.values() if s in r) for s in SERVICES}
    print(f"{len(entries)} of {len(names)} medicines linked: " + ", ".join(f"{k} {v}" for k, v in c.items()))


if __name__ == "__main__":
    main()
