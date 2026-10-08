#!/usr/bin/env python3
"""The bibliographic record of every article the site cites, so that every reference is written in one
style, Vancouver (ICMJE / US National Library of Medicine): authors (six, then et al.), title, journal
abbreviated as the NLM catalogue abbreviates it, year;volume(issue):pages, doi.

Sources: PubMed ESummary (NLM), which gives the NLM journal abbreviation, the issue and the full author
list, for every PMID in the bibliography register and the teratogens register's papers, and for every
DOI cited by hand in build-demo.py;
Crossref for a DOI PubMed does not index. Raw answers are cached in tools/terato/vancouver (git-ignored).

Output: tools/vancouver-meta.json, keyed "pmid:<n>" and "doi:<lowercase doi>".
Run: python3 tools/build-vancouver-meta.py
"""
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
OUT = HERE / "vancouver-meta.json"
CACHE = HERE / "terato" / "vancouver"
UA = {"User-Agent": "DysNet website references (info@dysnet.org)"}
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def get(url, cache):
    p = CACHE / cache
    if p.exists():
        return p.read_text(encoding="utf-8")
    time.sleep(0.4)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        t = r.read().decode("utf-8", "replace")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8")
    return t


def from_pubmed(s):
    authors = [a["name"] for a in s.get("authors", []) if a.get("authtype") == "Author"]
    doi = next((x["value"] for x in s.get("articleids", []) if x["idtype"] == "doi"), "")
    return {"authors": authors, "title": s.get("title", "").strip(), "journal": s.get("source", ""),
            "year": (s.get("pubdate") or "")[:4], "volume": s.get("volume", ""), "issue": s.get("issue", ""),
            "pages": s.get("pages", "") or (re.search(r"pii: ?(\S+?)\.?(?:\s|$)", s.get("elocationid", "")) or [None, ""])[1],
            "doi": doi, "pmid": s.get("uid", ""), "from": "PubMed"}


def esummary(pmids):
    out = {}
    pmids = sorted(set(pmids))
    for i in range(0, len(pmids), 200):
        chunk = pmids[i:i + 200]
        d = json.loads(get(EUTILS + "esummary.fcgi?db=pubmed&retmode=json&id=" + ",".join(chunk), f"esummary-{chunk[0]}-{len(chunk)}.json"))
        for u in d["result"].get("uids", []):
            out[u] = from_pubmed(d["result"][u])
    return out


def pmid_for_doi(doi):
    d = json.loads(get(EUTILS + "esearch.fcgi?db=pubmed&retmode=json&term=" + urllib.parse.quote(f'"{doi}"[doi]'), "esearch-" + re.sub(r"[^a-z0-9]+", "-", doi.lower())[:120] + ".json"))
    ids = d["esearchresult"].get("idlist", [])
    return ids[0] if len(ids) == 1 else ""


def from_crossref(doi):
    try:
        m = json.loads(get("https://api.crossref.org/works/" + urllib.parse.quote(doi), "crossref-" + re.sub(r"[^a-z0-9]+", "-", doi.lower())[:120] + ".json"))["message"]
    except Exception:
        return None
    authors = [f'{a.get("family", "")} {"".join(w[0] for w in re.split(r"[ -]", a.get("given", "")) if w)}'.strip() for a in m.get("author", [])]
    year = str(((m.get("published-print") or m.get("published-online") or m.get("issued") or {}).get("date-parts") or [[""]])[0][0])
    return {"authors": authors, "title": " ".join((m.get("title") or [""])[0].split()), "journal": (m.get("short-container-title") or m.get("container-title") or [""])[0],
            "year": year, "volume": m.get("volume", ""), "issue": m.get("issue", ""), "pages": m.get("page", "") or m.get("article-number", ""),
            "doi": doi, "pmid": "", "from": "Crossref"}


def main():
    bib = json.loads((HERE / "bibliography.json").read_text(encoding="utf-8"))["entries"]
    meta = {}
    # and the papers the teratogens register cites for its substances
    tera = json.loads((HERE / "teratogens.json").read_text(encoding="utf-8"))["entries"]
    pmids = [e["pmid"] for e in bib if e.get("pmid")] + [str(x["pmid"]) for t in tera for x in t.get("papers", []) if x.get("pmid")]
    for u, rec in esummary(pmids).items():
        meta["pmid:" + u] = rec
        if rec["doi"]:
            meta["doi:" + rec["doi"].lower()] = rec
    # the DOIs cited by hand in the page sources
    src = (ROOT / "build-demo.py").read_text(encoding="utf-8")
    dois = sorted({d.rstrip(".,;)") for d in re.findall(r"https://doi\.org/(10\.[^\s\"'<>]+)", src)})
    missing = []
    for doi in dois:
        if "doi:" + doi.lower() in meta:
            continue
        pmid = pmid_for_doi(doi)
        rec = esummary([pmid]).get(pmid) if pmid else from_crossref(doi)
        if rec:
            rec["doi"] = rec["doi"] or doi
            meta["doi:" + doi.lower()] = rec
            if rec.get("pmid"):
                meta["pmid:" + rec["pmid"]] = rec
        else:
            missing.append(doi)
    # an article PubMed gives no page or article number for: Crossref's article number, when it has one
    for rec in meta.values():
        if not rec["pages"] and rec.get("doi"):
            c = from_crossref(rec["doi"])
            if c and c.get("pages"):
                rec["pages"] = c["pages"]
    OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(meta)} records ({len(dois)} DOIs cited by hand); not found: {missing}")


if __name__ == "__main__":
    main()
