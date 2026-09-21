#!/usr/bin/env python3
"""Record, for every paper in the bibliography, the registries it rests on.

A registry-based study names its registry in the abstract far more often than in the title:
"Prevalence of congenital anomalies according to maternal race and ethnicity, Texas, 1999-2018"
rests on the Texas Birth Defects Registry, and the title never says so. The registries page used
to join the bibliography to the register by title alone, so a paper like that, or Siffel and
Czeizel's account of the Hungarian registry, counted for nothing. This step fetches each paper's
abstract from PubMed, matches title and abstract against the phrases each registry in
tools/registry-areas.json declares in its "match" list, and writes the registry keys into the
entry's "rests_on" field. build-demo.py reads that field; nothing else parses abstracts.

Run on its own after the register gains an entry or a phrase, or let build-bibliography.py call
it at the end of a rebuild. Usage: python3 tools/enrich-bibliography-registries.py
"""
import html
import json
import pathlib
import re
import time
import urllib.request

HERE = pathlib.Path(__file__).parent
BIB = HERE / "bibliography.json"
AREAS = HERE / "registry-areas.json"
E = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def phrase_hit(text, phrase):
    """The phrase as a substring; an acronym case-sensitively, or "CoULD" would match "could"."""
    if phrase.upper() == phrase or sum(c.isupper() for c in phrase) > len(phrase) / 2:
        return phrase in text
    return phrase.lower() in text.lower()


def abstracts(pmids):
    out = {}
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        url = f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "DysNet bibliography (info@dysnet.org)"}), timeout=120) as r:
                    xml = r.read().decode("utf-8", "replace")
                break
            except Exception as e:  # a transient PubMed error should not lose the whole run
                print("  retry", attempt + 1, e); time.sleep(3)
        for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
            pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
            if pm:
                text = " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S))
                out[pm.group(1)] = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)))
        time.sleep(0.4)
    return out


def main():
    bib = json.loads(BIB.read_text(encoding="utf-8"))
    entries = bib.get("entries", [])
    areas = json.loads(AREAS.read_text(encoding="utf-8"))["areas"]
    phrases = {}
    for a in areas:
        for p in a.get("match") or []:
            phrases.setdefault(a["registry"], set()).add(p)
    pmids = [str(e["pmid"]) for e in entries if str(e.get("pmid", "")).isdigit()]
    print(f"{len(entries)} entries, {len(phrases)} registries with phrases; fetching abstracts")
    ab = abstracts(pmids)
    hits = 0
    for e in entries:
        text = e.get("title", "") + " " + ab.get(str(e.get("pmid")), "")
        rests = sorted(k for k, ps in phrases.items() if any(phrase_hit(text, p) for p in ps))
        if rests:
            hits += 1
        e["rests_on"] = rests
    bib["registries_joined"] = time.strftime("%Y-%m-%d")
    BIB.write_text(json.dumps(bib, ensure_ascii=False, indent=1), encoding="utf-8")
    by_reg = {}
    for e in entries:
        for k in e.get("rests_on", []):
            by_reg[k] = by_reg.get(k, 0) + 1
    print(f"{hits} papers rest on a registry in the register:", dict(sorted(by_reg.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
