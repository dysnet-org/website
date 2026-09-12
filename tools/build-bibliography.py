#!/usr/bin/env python3
"""Build tools/bibliography.json: a verified bibliography on dysmelia.

Sources of references (trusted, machine-readable):
  1. Every PubMed ID cited by Orphanet in its epidemiology data for our ORPHAcodes
     (tools/orphanet-prevalence.json, Orphadata product 9) — tagged with the condition(s).
  2. The publications already verified for the site (prevalence annex, registry page).
  3. DOIs / PubMed links published on DysNet member associations' own websites
     (tools/member-dois.json, harvested by tools/harvest-member-dois.py), kept only when
     the article is about the conditions the site describes (keyword screen on
     title + abstract; rejected items are written to tools/bibliography-review.json).
Metadata (title, authors, journal, year, DOI) comes from NCBI E-utilities, never from memory.
Run: python3 tools/build-bibliography.py   (needs network; E-utilities limit 3 req/s)
"""
import json, pathlib, re, time, urllib.request, urllib.parse

HERE = pathlib.Path(__file__).parent
PREV = json.loads((HERE / "orphanet-prevalence.json").read_text(encoding="utf-8"))
E = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# seed: PMID -> {codes, topics, note}
seed = {}
def add(pmid, code=None, topic=None, note=None, via="Orphanet"):
    s = seed.setdefault(str(pmid), {"codes": set(), "topics": set(), "notes": set(), "via": set()})
    if code: s["codes"].add(str(code))
    if topic: s["topics"].add(topic)
    if note: s["notes"].add(note)
    if via: s["via"].add(via)


def eget(url, timeout=60):
    time.sleep(0.4)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "DysNet bibliography builder (info@dysnet.org)"}), timeout=timeout) as r:
        return r.read()


def esearch_ids(term):
    return json.loads(eget(f"{E}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(term)}&retmode=json"))["esearchresult"]["idlist"]

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
    add(pmid, None, topic, note, via="DysNet")
# DOIs to resolve to PMIDs
DOIS = {"10.1002/bdr2.2123": ("epidemiology", "Finland, amelia and phocomelia"), "10.1186/s12884-023-05660-z": ("epidemiology", "China, syndactyly"),
        "10.1371/journal.pone.0219930": ("epidemiology", "Norway, limb reduction defects 1970-2016")}
for doi, (topic, note) in DOIS.items():
    for pmid in esearch_ids(f"{doi}[DOI]")[:1]:
        add(pmid, None, topic, note, via="DysNet")

# ─── 3. Member association websites ─────────────────────────────────────────
# Vocabulary of the conditions described on the site (keyword → ORPHAcode or None for the family).
VOCAB = [
    (r"\bamelia\b", "294975"), (r"\bphocomelia\b", "2879"), (r"\bmeromelia\b", None), (r"\bhemimelia\b", None),
    (r"\bectrodactyly|split[- ]hand|split[- ]foot|cleft hand", "2440"), (r"\bsymbrachydactyly", None), (r"\bbrachydactyly", "1570"),
    (r"\bpolydactyly", "2917"), (r"\bsyndactyly", "1727"), (r"\bpoland\W{0,3}s?\s*syndrome|poland anomaly|poland sequence", "2911"),
    (r"adams[- ]oliver", "974"), (r"amniotic band|constriction (ring|band)", "1034"), (r"radial (ray |longitudinal )?(deficien|aplasia|hypoplasia|dysplasia|club)", "93321"),
    (r"ulnar (ray |longitudinal )?(deficien|aplasia|hypoplasia|dysplasia|club)|ulnar hemimelia", "93320"), (r"tibial (deficien|aplasia|hemimelia|hypoplasia)", "93322"),
    (r"fibular? (deficien|aplasia|hemimelia|hypoplasia)", "93323"), (r"femoral (deficien|hypoplasia|focal)|proximal femoral", "295000"),
    (r"limb[- ](reduction|deficienc|difference|anomal|malformation|defect|loss|absence)|reduction defect|transverse (deficienc|defect)|congenital (upper|lower)[- ]limb|congenital hand|dysmelia|dysmelic", None),
    (r"thalidomide", None),
]
VOCAB = [(re.compile(rx, re.I), code) for rx, code in VOCAB]
TOPIC_RX = [("epidemiology", re.compile(r"prevalence|incidence|epidemiolog|population[- ]based|birth defects? (registry|surveillance)|surveillance", re.I)),
            ("review", re.compile(r"\breview\b|overview|state of the art|guideline", re.I)),
            ("living", re.compile(r"quality of life|psycholog|psychosocial|participation|daily (life|living)|parents?|famil|school|employment|body image|self[- ]esteem|coping", re.I)),
            ("prosthetics", re.compile(r"prosthe|orthos|orthotic|bionic|myoelectric|3d[- ]print|assistive", re.I)),
            ("clinical", re.compile(r"surg|treatment|outcome|reconstruct|transfer|pollicization|lengthening|function|rehabilitat|therapy|management|classification", re.I))]


def screen(text):
    """Return (codes, topics) if the text is about our conditions, else None."""
    codes, hit = set(), False
    for rx, code in VOCAB:
        if rx.search(text):
            hit = True
            if code: codes.add(code)
    if not hit: return None
    topics = {t for t, rx in TOPIC_RX if rx.search(text)} or {"clinical"}
    if "epidemiology" in topics: topics = {"epidemiology"} | ({"review"} & topics)
    return codes, topics


def crossref(doi):
    try:
        w = json.loads(eget(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", 40))["message"]
    except Exception:
        return None
    if w.get("type") not in ("journal-article", "book-chapter", "proceedings-article"): return None
    title = " ".join(w.get("title") or []).strip()
    authors = [f"{a.get('family','')} {''.join(p[0] for p in a.get('given','').replace('-', ' ').split())}".strip() for a in w.get("author", []) if a.get("family")]
    year = str((w.get("issued", {}).get("date-parts") or [[""]])[0][0] or "")
    return {"pmid": "", "doi": doi, "title": re.sub(r"<[^>]+>", "", title).rstrip("."), "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
            "journal": " ".join(w.get("container-title") or []), "year": year, "volume": w.get("volume", ""), "pages": w.get("page", ""),
            "abstract": re.sub(r"<[^>]+>", " ", w.get("abstract", ""))}


MEMBER_HITS = HERE / "member-dois.json"
review, extra = [], []  # rejected/unresolved hits; Crossref-only accepted entries
if MEMBER_HITS.exists():
    hits = json.loads(MEMBER_HITS.read_text(encoding="utf-8"))["hits"]
    by_id = {}
    for h in hits:
        k = ("doi", h["doi"].lower()) if h.get("doi") else ("pmid", h["pmid"]) if h.get("pmid") else ("pmcid", h["pmcid"])
        by_id.setdefault(k, {"hit": h, "members": set()})["members"].add(f"{h['member']} ({h['country']})")
    print(f"member sites: {len(by_id)} distinct identifiers")
    for (kind, ident), v in by_id.items():
        members = sorted(v["members"])
        pmid, meta = None, None
        try:
            if kind == "pmid": pmid = ident
            elif kind == "pmcid": pmid = (esearch_ids(f"{ident}[pmc]") or [None])[0]
            else:
                pmid = (esearch_ids(f"{ident}[DOI]") or [None])[0]
                if not pmid: meta = crossref(ident)
        except Exception as e:
            review.append({"id": ident, "members": members, "status": f"lookup failed: {type(e).__name__}"}); continue
        if pmid:
            xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
            title = " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", xml, re.S))
            abstract = " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.S))
            text = re.sub(r"<[^>]+>", " ", title + " " + abstract)
            r = screen(text)
            if not r:
                review.append({"id": ident, "pmid": pmid, "title": re.sub(r"<[^>]+>", "", title), "members": members, "status": "rejected: not about the site's conditions"}); continue
            codes, topics = r
            for t in topics: add(pmid, None, t, f"published on the website of {', '.join(members)}", via=None)
            for c in codes: seed[pmid]["codes"].add(c)
            seed[pmid]["via"].update(members)
        elif meta:
            r = screen(meta["title"] + " " + meta["abstract"])
            if not r:
                review.append({"id": ident, "title": meta["title"], "members": members, "status": "rejected: not about the site's conditions (Crossref)"}); continue
            codes, topics = r
            meta.pop("abstract"); meta.update({"codes": sorted(codes), "topics": sorted(topics), "notes": [f"published on the website of {', '.join(members)}"], "via": members})
            extra.append(meta)
        else:
            review.append({"id": ident, "members": members, "status": "unresolved: no PubMed or Crossref record"})
    (HERE / "bibliography-review.json").write_text(json.dumps({"built": time.strftime("%Y-%m-%d"), "items": review}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"member hits accepted: {sum(1 for v in seed.values() if v['via'] - {'Orphanet', 'DysNet'})} via PubMed + {len(extra)} via Crossref | set aside: {len(review)}")

# metadata for all PMIDs (batched esummary)
pmids = sorted(seed)
entries = []
for i in range(0, len(pmids), 100):
    batch = pmids[i:i + 100]
    res = json.loads(eget(f"{E}/esummary.fcgi?db=pubmed&id={','.join(batch)}&retmode=json"))["result"]
    for pmid in batch:
        d = res.get(pmid)
        if not d or "error" in d: print("missing", pmid); continue
        doi = next((a["value"] for a in d.get("articleids", []) if a["idtype"] == "doi"), "")
        authors = [a["name"] for a in d.get("authors", [])]
        year = (d.get("pubdate") or "")[:4]
        s = seed[pmid]
        entries.append({"pmid": pmid, "doi": doi, "title": d.get("title", "").rstrip("."), "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
                        "journal": d.get("fulljournalname") or d.get("source", ""), "year": year, "volume": d.get("volume", ""), "pages": d.get("pages", ""),
                        "codes": sorted(s["codes"]), "topics": sorted(s["topics"]), "notes": sorted(s["notes"]), "via": sorted(s["via"])})
    time.sleep(0.4)
entries.extend(extra)
entries.sort(key=lambda e: (-int(e["year"] or 0), e["title"]))
out = {"built": time.strftime("%Y-%m-%d"), "source": "PubMed IDs cited by Orphanet (Orphadata epidemiology) for the site's ORPHAcodes, publications verified on the site, and DOIs published on member associations' websites; metadata from NCBI E-utilities / Crossref", "entries": entries}
(HERE / "bibliography.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(entries)} references | with DOI: {sum(1 for e in entries if e['doi'])} | tagged to a condition: {sum(1 for e in entries if e['codes'])}")
