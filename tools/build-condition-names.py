#!/usr/bin/env python3
"""Fetch Orphanet's French and Italian names for every code the conditions use.

The DysNet registry asks families about their condition in English, French and Italian, and reads
the list from /data/conditions.json. A condition must therefore reach it with its name in all three,
and for a coded condition that name is not ours to write: Orphanet publishes the official term of
every ORPHAcode per language. This fetches it for each card's code, for each form Orphanet files
under a card (tools/orphanet-hierarchy.json), and for the registry-only entries of
tools/conditions.json, together with Orphanet's other names in those languages, which the
registry's questionnaire searches but does not show.

A condition with no code has no Orphanet name; tools/conditions.json gives DysNet's own
(dysnetNames), and the audit lists any that has neither.

Output: tools/condition-names.json
Usage:  python3 tools/build-condition-names.py   (network; a code Orphanet does not answer for
        keeps the names of the previous run)
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import conditions as C  # noqa: E402

OUT = C.HERE / "condition-names.json"
API = "https://api.orphacode.org/{lang}/ClinicalEntity/orphacode/{code}/{what}"
# The API refuses a request without this header and accepts any value; there is no registration.
HEADERS = {"apiKey": "dysnet-website", "Accept": "application/json",
           "User-Agent": "DysNet conditions builder (info@dysnet.org)"}
LANGS = ("fr", "it")


def get(lang, code, what):
    time.sleep(0.2)
    req = urllib.request.Request(API.format(lang=lang.upper(), code=code, what=what), headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404 and what == "Synonym":
            return {}
        raise


def names_of(code):
    out, other = {}, {}
    for lang in LANGS:
        term = get(lang, code, "Name").get("Preferred term")
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"no {lang} preferred term")
        out[lang] = term.strip()
        other[lang] = [s for s in get(lang, code, "Synonym").get("Synonym") or [] if isinstance(s, str) and s.strip()]
    return {**out, "synonyms": other}


def wanted_codes():
    """Every card's code, every form Orphanet files under one, and the registry-only entries' codes."""
    hier = C.hierarchy()
    cards = [c["code"] for c in C.conditions() if c["code"]]
    forms = [d for code in cards for d in C.descendants(code, hier)]
    extra = [str(e["orphaCode"]) for e in C.reference().get("registryOnly", []) if e.get("orphaCode")]
    return sorted(set(cards + forms + extra), key=int)


def main():
    previous = (C.load(OUT.name) or {}).get("names", {})
    names, failed = {}, []
    for code in wanted_codes():
        try:
            names[code] = names_of(code)
        except (urllib.error.URLError, ValueError, json.JSONDecodeError) as e:
            failed.append(code)
            print(f"  ORPHA:{code}: FAILED ({e}){'; keeping the previous names' if code in previous else ''}")
            if code in previous:
                names[code] = previous[code]
            continue
        print(f"  ORPHA:{code}: {names[code]['fr']} / {names[code]['it']}")
    OUT.write_text(json.dumps({
        "built": time.strftime("%Y-%m-%d"),
        "source": "Orphanet, ORPHAcodes API and Nomenclature Pack, licence CC BY 4.0",
        "source_url": "https://api.orphacode.org/",
        "note": ("Orphanet's preferred French and Italian term for each code the conditions use, a card's own, "
                 "a form's inside a card, or a registry-only entry's, with Orphanet's other names in those "
                 "languages, which the registry searches but does not show. Attribute Orphanet wherever they are "
                 "displayed."),
        "names": names}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    missing = [c for c in failed if c not in names]
    print(f"\nwrote {OUT.relative_to(C.ROOT)}: {len(names)} codes named in French and Italian"
          + (f"; {len(failed)} not answered this time" if failed else ""))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
