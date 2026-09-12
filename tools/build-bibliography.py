#!/usr/bin/env python3
"""Build tools/bibliography.json: a verified bibliography on dysmelia.

Sources of references (trusted, machine-readable):
  1. Every PubMed ID cited by Orphanet in its epidemiology data for our ORPHAcodes
     (tools/orphanet-prevalence.json, Orphadata product 9) — tagged with the condition(s).
  2. The publications already verified for the site (prevalence annex, registry page).
Metadata (title, authors, journal, year, DOI) comes from NCBI E-utilities, never from memory.
Run: python3 tools/build-bibliography.py   (needs network; E-utilities limit 3 req/s)
"""
import json, pathlib, re, time, urllib.request, urllib.parse

HERE = pathlib.Path(__file__).parent
PREV = json.loads((HERE / "orphanet-prevalence.json").read_text(encoding="utf-8"))
E = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# seed: PMID -> {codes, topics, note}
seed = {}
def add(pmid, code=None, topic=None, note=None):
    s = seed.setdefault(str(pmid), {"codes": set(), "topics": set(), "notes": set()})
    if code: s["codes"].add(str(code))
    if topic: s["topics"].add(topic)
    if note: s["notes"].add(note)

for code, c in PREV["conditions"].items():
    for p in c["prevalence"]:
        for pmid in re.findall(r"(\d{6,9})\[PMID\]", p.get("source", "")):
            add(pmid, code, "epidemiology", f"cited by Orphanet for {c['orphanet_name']} ({p['type'].lower()}, {p['geo']})")

# publications verified for the site (see the prevalence annex and the registry page)
SITE = {
    "22002956": ("epidemiology", "Amelia: ICBDSR multi-centre study"), "18554391": ("review", "Brachydactyly review (Orphanet J Rare Dis)"),
    "24237863": ("epidemiology", "Northern Netherlands, 30-year birth prevalence of limb defects"), "21601997": ("epidemiology", "Finland, upper limb deficiencies"),
    "23322606": ("epidemiology", "Finland, radial ray deficiencies"), "25410508": ("epidemiology", "Finland, lower limb deficiencies"),
    "33690710": ("epidemiology", "Korea, congenital upper limb anomalies"), "26254946": ("review", "Symbrachydactyly: diagnosis, function, treatment"),
}
for pmid, (topic, note) in SITE.items():
    add(pmid, None, topic, note)
# DOIs to resolve to PMIDs
DOIS = {"10.1002/bdr2.2123": ("epidemiology", "Finland, amelia and phocomelia"), "10.1186/s12884-023-05660-z": ("epidemiology", "China, syndactyly"),
        "10.1371/journal.pone.0219930": ("epidemiology", "Norway, limb reduction defects 1970-2016")}
for doi, (topic, note) in DOIS.items():
    q = urllib.parse.quote(f"{doi}[DOI]")
    with urllib.request.urlopen(f"{E}/esearch.fcgi?db=pubmed&term={q}&retmode=json", timeout=40) as r:
        ids = json.load(r)["esearchresult"]["idlist"]
    for pmid in ids[:1]:
        add(pmid, None, topic, note)
    time.sleep(0.4)

# metadata for all PMIDs (batched esummary)
pmids = sorted(seed)
entries = []
for i in range(0, len(pmids), 100):
    batch = pmids[i:i + 100]
    with urllib.request.urlopen(f"{E}/esummary.fcgi?db=pubmed&id={','.join(batch)}&retmode=json", timeout=60) as r:
        res = json.load(r)["result"]
    for pmid in batch:
        d = res.get(pmid)
        if not d or "error" in d: print("missing", pmid); continue
        doi = next((a["value"] for a in d.get("articleids", []) if a["idtype"] == "doi"), "")
        authors = [a["name"] for a in d.get("authors", [])]
        year = (d.get("pubdate") or "")[:4]
        s = seed[pmid]
        entries.append({"pmid": pmid, "doi": doi, "title": d.get("title", "").rstrip("."), "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
                        "journal": d.get("fulljournalname") or d.get("source", ""), "year": year, "volume": d.get("volume", ""), "pages": d.get("pages", ""),
                        "codes": sorted(s["codes"]), "topics": sorted(s["topics"]), "notes": sorted(s["notes"])})
    time.sleep(0.4)
entries.sort(key=lambda e: (-int(e["year"] or 0), e["title"]))
out = {"built": time.strftime("%Y-%m-%d"), "source": "PubMed IDs cited by Orphanet (Orphadata epidemiology) for the site's ORPHAcodes, plus publications verified on the site; metadata from NCBI E-utilities", "entries": entries}
(HERE / "bibliography.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(entries)} references | with DOI: {sum(1 for e in entries if e['doi'])} | tagged to a condition: {sum(1 for e in entries if e['codes'])}")
