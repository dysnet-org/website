#!/usr/bin/env python3
"""Ask PubMed, for each substance on the register, what has been published about its effect on development.

An earlier attempt answered a different question. It looked for substances named in the
site's own bibliography, and that bibliography is screened to papers about limb difference,
so a study of cadmium and neural tube defects was never in it to be found. 29 substances of
577 came back, which is not a fact about the evidence, only about the filter.

This asks PubMed instead, once per substance: is there literature on this substance and
harm to the unborn child, and if so what is the most recent of it, and is any of it a
Cochrane systematic review. The answer is a count, a handful of citations with their DOIs,
and a flag for Cochrane.


Matching is on the substance name in title or abstract, or on its CAS registry number,
which PubMed indexes. The CAS is the stronger of the two and is used whenever the register
holds one.

Output: tools/teratogen-papers.json

Usage: python3 tools/build-teratogen-papers.py [--limit N]
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
DATA = ROOT / "tools" / "teratogens.json"
OUT = ROOT / "tools" / "teratogen-papers.json"
E = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UA = {"User-Agent": "DysNet teratogens register (info@dysnet.org)"}
CAS_RX = re.compile(r"^\d{2,7}-\d{2}-\d$")
KEEP = 5

# What counts as literature about harm to the unborn child. MeSH first, because it is
# indexed rather than guessed at, then the words a title uses when MeSH has not caught up.
HARM = ('("abnormalities, drug-induced"[mh] OR teratogens[mh] '
        'OR "prenatal exposure delayed effects"[mh] '
        'OR teratogen[tiab] OR teratogens[tiab] OR teratogenic[tiab] OR teratogenicity[tiab] '
        'OR embryotoxic[tiab] OR embryotoxicity[tiab] OR "developmental toxicity"[tiab] '
        'OR "birth defect"[tiab] OR "birth defects"[tiab] OR "congenital malformation"[tiab] '
        'OR "congenital malformations"[tiab] OR "congenital anomaly"[tiab] OR "congenital anomalies"[tiab])')
COCHRANE = '"Cochrane Database Syst Rev"[Journal]'

# A paper can match on a MeSH heading alone and still be titled "Chylothorax in the course of
# squamous cell lung cancer". The count may include it, honestly, but nothing is shown to a
# reader unless its own title says it is about development, pregnancy or malformation.
# Cochrane withdraws a review but its earlier versions stay indexed under the same
# identifier, so a search still returns one. tools/cochrane-withdrawn.json holds every
# withdrawn review identifier, refreshed by the same one query, and none of them is shown.
WITHDRAWN = set(json.loads((ROOT / "tools" / "cochrane-withdrawn.json").read_text(encoding="utf-8"))["reviews"])


def withdrawn(paper):
    m = re.search(r"(CD\d+)", paper.get("doi") or "")
    return bool(m and m.group(1) in WITHDRAWN) or (paper.get("title") or "").upper().startswith("WITHDRAWN")


ON_TOPIC = re.compile(r"teratogen|embryo|fetal|foetal|fetus|foetus|pregnan|prenatal|maternal|gestation|"
                      r"birth defect|malformation|congenital|anomal|developmental|offspring|neonat|in utero", re.I)

LAST = [0.0]


def eget(url, timeout=60, tries=3):
    for attempt in range(tries):
        wait = 0.36 - (time.time() - LAST[0])
        if wait > 0:
            time.sleep(wait)
        LAST[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(2 + 3 * attempt)
                continue
            raise
        except Exception:
            if attempt < tries - 1:
                time.sleep(2)
                continue
            raise


def esearch(term, retmax=0):
    u = f"{E}/esearch.fcgi?db=pubmed&retmode=json&retmax={retmax}&term={urllib.parse.quote(term)}"
    return json.loads(eget(u))["esearchresult"]


def display_name(entry):
    """The name a search should use: the first clause, without the sources' annotations."""
    n = re.sub(r"\s*\[(?:Basis for listing[^\]]*|This substance is identified[^\]]*|\d)\]", "", entry["name"])
    n = re.split(r";", n)[0]
    n = re.sub(r"\(ISO\)|\(.*?\)", " ", n)
    return re.sub(r"\s+", " ", n).strip(" ,;.")


def subject(entry):
    """The PubMed clause that identifies this substance: its CAS if we hold one, and its name."""
    parts = []
    cas = (entry.get("cas") or "").strip()
    if CAS_RX.match(cas):
        parts.append(f'"{cas}"[rn]')
    name = display_name(entry)
    if 3 < len(name) < 70:
        parts.append(f'"{name}"[tiab]')
        parts.append(f'"{name}"[nm]')
    return "(" + " OR ".join(parts) + ")" if parts else ""


def summaries(pmids):
    if not pmids:
        return []
    res = json.loads(eget(f"{E}/esummary.fcgi?db=pubmed&retmode=json&id={','.join(pmids)}"))["result"]
    out = []
    for pid in res.get("uids", []):
        r = res[pid]
        doi = ""
        for aid in r.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
        out.append({
            "pmid": pid,
            "doi": doi,
            "title": (r.get("title") or "").strip().rstrip("."),
            "journal": r.get("source", ""),
            "year": (r.get("pubdate") or "")[:4],
            "cochrane": "cochrane" in (r.get("source") or "").lower(),
        })
    return out


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    entries = doc["entries"][:limit] if limit else doc["entries"]
    out, with_papers, with_cochrane = {}, 0, 0

    for i, e in enumerate(entries, 1):
        sub = subject(e)
        if not sub:
            continue
        key = e.get("cas") or e["name"]
        try:
            total = esearch(f"{sub} AND {HARM}")
            n = int(total["count"])
            if not n:
                continue
            top = esearch(f"{sub} AND {HARM}", retmax=KEEP * 4)["idlist"]
            coch = esearch(f"{sub} AND {HARM} AND {COCHRANE}", retmax=3)
            coch_ids = coch["idlist"]
            papers = summaries(list(dict.fromkeys(coch_ids + top))[:KEEP * 4 + len(coch_ids)])
        except Exception as ex:
            print(f"  ! {display_name(e)[:40]}: {ex}", flush=True)
            continue
        papers = [x for x in papers if ON_TOPIC.search(x["title"]) and not withdrawn(x)]
        if not papers:
            continue
        with_papers += 1
        if any(p["cochrane"] for p in papers):
            with_cochrane += 1
        out[key] = {
            "name": display_name(e),
            "count": n,
            "cochrane": sum(1 for x in papers[:KEEP] if x["cochrane"]),
            "papers": papers[:KEEP],
            "shown": len(papers[:KEEP]),
            "query": f"{sub} AND (harm to the unborn child)",
        }
        if i % 50 == 0:
            print(f"  {i}/{len(entries)} · with literature {with_papers} · with a Cochrane review {with_cochrane}", flush=True)

    doc_out = {
        "built": time.strftime("%Y-%m-%d"),
        "source": "PubMed (NCBI E-utilities)",
        "method": ("One search per substance: the substance, by CAS registry number where the register holds one and "
                   "by name in title or abstract, combined with the MeSH and title terms for harm to the unborn child."),
        "harm_terms": HARM,
        "kept_per_substance": KEEP,
        "substances": out,
    }
    OUT.write_text(json.dumps(doc_out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{with_papers} of {len(entries)} substances have published literature on harm to the unborn child")
    print(f"{with_cochrane} of them have a Cochrane systematic review")
    print(f"written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
