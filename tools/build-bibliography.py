#!/usr/bin/env python3
"""Build tools/bibliography.json: a verified bibliography on dysmelia.

Sources of references (trusted, machine-readable):
  1. Every PubMed ID cited by Orphanet in its epidemiology data for our ORPHAcodes
     (tools/orphanet-prevalence.json, Orphadata product 9) — tagged with the condition(s).
  2. The publications already verified for the site (prevalence annex, registry page).
  3. DOIs / PubMed links published on DysNet member associations' own websites and on the
     official websites of the registries listed on Orphanet for our ORPHAcodes
     (tools/member-dois*.json, tools/registry-dois*.json, harvested by tools/harvest-member-dois.py), kept only when
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

# Papers cited by the "Causes of dysmelia" review (/knowledge/causes-of-dysmelia/) that none of the
# standing queries reaches: they answer questions families ask but do not name a limb condition in
# their title, so the causes query cannot see them. Seeded here so the review's citations resolve
# against the register. PMID -> (topics, note).
REVIEW_SEED = {
    "33043642": (("review",), "Limb development: the apical ectodermal ridge and the three axes"),
    "38497990": (("causes", "epidemiology"), "EURAP: major malformations after antiseizure medication monotherapy"),
    "37647086": (("causes", "meta", "review"), "Cochrane: malformation outcomes after antiepileptic monotherapy in pregnancy"),
    "35104296": (("causes", "meta", "epidemiology"), "Maternal diabetes and specific congenital anomalies, over 80 million births"),
    "12151147": (("causes", "epidemiology"), "Congenital varicella syndrome: frequency in a prospective cohort"),
    "9637807": (("causes", "clinical"), "Misoprostol in pregnancy and Möbius sequence"),
    "16750609": (("causes", "meta"), "Misoprostol and congenital anomalies: systematic review and meta-analysis"),
    "31218730": (("review", "clinical"), "Fetal akinesia deformation sequence: aetiology, diagnosis and management"),
    "27773741": (("causes",), "Cited by the Causes of dysmelia review"),
}
# Papers found on the websites of organisations the site names, or listed by them as their own
# research, that the standing queries do not reach. Seeded so that a full rebuild keeps them.
WEBSITE_SEED = {
    "39503467": (("epidemiology",), "Environmental scan of limb loss rehabilitation centres across Canada", "Holland Bloorview (hollandbloorview.ca)"),
    "34665069": (("living",), "Running-specific prosthesis use, qualitative study", "Holland Bloorview (hollandbloorview.ca)"),
    "33952260": (("clinical",), "GOAL-LD questionnaire for lower-limb differences", "Holland Bloorview (hollandbloorview.ca)"),
    "28286964": (("living",), "Participation in sports for children with limb absence", "Holland Bloorview (hollandbloorview.ca)"),
    "21515898": (("prosthetics",), "Prosthesis funding structures and their effect on use", "Holland Bloorview (hollandbloorview.ca)"),
    "33565281": (("causes", "epidemiology"), "REMERA's own analysis of the Ain cluster of transverse upper-limb agenesis", "REMERA (remera.fr)"),
    "21825994": (("clinical", "review"), "Ocular findings of thalidomide embryopathy, listed by Ex-Center", "Ex-Center (ex-center.org)"),
    "19639653": (("clinical", "review"), "Ophthalmological manifestations of thalidomide and misoprostol, listed by Ex-Center", "Ex-Center (ex-center.org)"),
    "39147010": (("living", "review"), "Terminology people with limb difference, clinicians and researchers prefer", "DysNet"),
    "21557466": (("clinical", "review"), "Anatomic and aetiological classification of congenital limb deficiencies", "DysNet"),
    "29241842": (("living", "clinical"), "Functional impact of congenital hand differences, first results of the CoULD registry", "DysNet"),
    "33158398": (("epidemiology", "prosthetics"), "Prevalence of lower-limb loss in children and the cost of their prostheses", "DysNet"),
    "18295618": (("epidemiology",), "Prevalence of limb loss in the United States, 2005 to 2050", "DysNet"),
    "39822203": (("epidemiology",), "US limb-loss prevalence re-estimated, with updated projections", "DysNet"),
    "34843420": (("living",), "Research agenda on exercise and physical activity for people with limb loss in Canada", "DysNet"),
}
for pmid, (topics, note, via) in WEBSITE_SEED.items():
    for topic in topics:
        add(pmid, None, topic, note, via=via)
    if pmid in ("21825994", "19639653"): seed[pmid]["codes"].add("thal")

for pmid, (topics, note) in REVIEW_SEED.items():
    for topic in topics:
        add(pmid, None, topic, note, via="DysNet")

# Every paper cited by the "Causes of dysmelia" review, pinned. The standing PubMed queries are live,
# so their result sets shift a little between runs: on 13 September 2026 a rebuild silently dropped two
# papers the review cites, and the site build failed rather than publishing a dangling citation. Pinning
# the cited set here means a rebuild can add references but can never remove one the review depends on.
# Provenance is not overwritten: add() unions via/notes, so a paper found by a query keeps that origin
# and gains this note. Regenerate with: grep -o 'cref(...)' in build-demo.py (see causes_sources_html).
REVIEW_CITED = (
    "1481865", "1805430", "3533366", "4025389", "7245088", "7856645", "7973488", "9637807", "10826630", "12620993",
    "12843316", "14632304", "14745921", "14872406", "15980115", "16463421", "16750609", "16906563", "17555519",
    "17676605", "18000913", "19067400", "19433787", "19672683", "21344627", "22434686", "22495965", "22821755",
    "22965740", "24134526", "24478176", "24480684", "24885342", "25131394", "25132072", "25344219", "26043938",
    "26347425", "26581570", "27751757", "27773741", "27801979", "27865944", "27884122", "28161597", "28504423",
    "28736902", "28846100", "29263794", "29377641", "30078491", "30190590", "30589520", "30856359", "31181251",
    "31218730", "31388035", "31395945", "31546130", "31591562", "32304852", "32335054", "32414180", "32591344",
    "32758259", "32877749", "32954639", "32991492", "33043642", "33470442", "33509875", "33565281", "33847750",
    "34060120", "34202629", "35104296", "35414337", "36369770", "36584346", "36804539", "37226469", "37285827",
    "37445217", "37647086", "38336121", "38497990", "38671254", "39168984", "39679807", "39937006", "40198353",
    "40233106", "41274663", "41554827", "41557582", "41951339",
)
for pmid in REVIEW_CITED:
    add(pmid, None, None, "cited by the Causes of dysmelia review", via="DysNet")

# ─── 3. Member association websites ─────────────────────────────────────────
# Vocabulary of the conditions described on the site (keyword → ORPHAcode or None for the family).
VOCAB = [  # keyword → the ORPHAcode used on the site (REG_CODE_NAMES in build-demo.py); None = the dysmelia family in general
    (r"\btetra-?amelia\b", "3301"), (r"\bamelia\b", "1027"), (r"\bphocomelia\b", "2879"), (r"\bmeromelia\b", None), (r"\bhemimelia\b", None),
    (r"\bectrodactyly|split[- ]hand|split[- ]foot|cleft hand|\bSHFM\b", "2440"), (r"\bsymbrachydactyly", "1570"), (r"\bbrachydactyly", None),
    (r"crossed polysyndactyly", "2935"), (r"\bpolydactyly", "2913"), (r"\bsyndactyly", "93458"),
    (r"\bpoland\W{0,3}s?\s*(syndrome|anomaly|sequence)", "2911"), (r"adams[- ]oliver", "974"), (r"holt[- ]oram", "392"), (r"roberts syndrome|SC phocomelia", "3103"),
    (r"cenani[- ]lenz", "3258"), (r"thrombocytopenia[- ]absent radius|\bTAR syndrome", "3320"), (r"microgastria", "2538"), (r"tibial aplasia[- ]ectrodactyly", "3329"),
    (r"amniotic band|constriction (ring|band)", "295000"),
    (r"radial (ray |longitudinal )?(deficien|aplasia|hypoplasia|dysplasia|club|hemimelia)", "93321"),
    (r"ulnar (ray |longitudinal )?(deficien|aplasia|hypoplasia|dysplasia|club|hemimelia)", "93320"),
    (r"tibial (deficien|aplasia|hemimelia|hypoplasia)", "93322"), (r"fibular? (deficien|aplasia|hemimelia|hypoplasia)", "93323"),
    (r"femoral (deficien|hypoplasia|focal)|proximal femoral", None),
    (r"limb[- ](reduction|deficienc|difference|anomal|malformation|defect|loss|absence)|reduction defect|transverse (deficienc|defect)|(below|above)[- ](elbow|knee) deficien|congenital (upper|lower)[- ]limb|congenital hand|hand difference|dysmelia|dysmelic", None),
]
VOCAB = [(re.compile(rx, re.I), code) for rx, code in VOCAB]
# thalidomide embryopathy: accepted only when the title itself is about the embryopathy or its survivors,
# so that papers on thalidomide as a drug (myeloma, lupus, bowel disease) stay out
THAL_TITLE = re.compile(r"thalidomide[- ](embryopathy|survivor|victim|damage|affected|syndrome|induced|impaired|exposed|related|teratogen)|thalidomide.{0,60}(embryopath|malformation|limb|phocomelia|birth defects?|teratogen|survivor|impaired)|contergan|softenon|neurosedyn", re.I)
TOPIC_RX = [("epidemiology", re.compile(r"prevalence|incidence|epidemiolog|population[- ]based|birth defects? (registry|surveillance)|surveillance|registry", re.I)),
            ("review", re.compile(r"\breview\b|overview|state of the art|guideline|consensus|recommendations", re.I)),
            ("genetics", re.compile(r"\bgene\b|genetic|mutation|deletion|copy number|chromosom|variant|inherit|heredit", re.I)),
            ("living", re.compile(r"quality of life|psycholog|psychosocial|body image|self[- ]esteem|self[- ]concept|coping|lived experience|experiences? of|daily (life|living)|participation|school|employment|opinions of", re.I)),
            ("prosthetics", re.compile(r"prosthe|orthos[ie]s|orthotic|bionic|myoelectric|3d[- ]print|assistive", re.I)),
            ("clinical", re.compile(r"surg|treatment|outcome|reconstruct|transfer|pollicization|lengthening|function|rehabilitat|therapy|management|classification|diagnos", re.I))]


CAUSES_RX = re.compile(r"aetiolog|etiolog|\bcauses? of\b|\bcaused by\b|\bcausation|teratogen|risk factors?|exposures?\b|environmental|pathogenesis|pathogenic|mechanism|vascular disruption|maternal|prenatal (drug|medication|exposure)|pesticide|pollut|\bcluster|origin of|genetic (basis|cause|aetiology|etiology)|mutations? in|\bloci\b|\blocus\b", re.I)


def screen(text, title=None, strict=False):
    """Return (codes, topics) if the text is about our conditions, else None.
    strict=True (hits harvested from websites): generic limb terms count only in the title;
    a named condition counts anywhere."""
    codes, hit = set(), False
    for rx, code in VOCAB:
        if rx.search(text):
            if code or not strict or (title and rx.search(title)):
                hit = True
            if code: codes.add(code)
    if THAL_TITLE.search(title if title is not None else text):
        hit = True; codes.add("thal")
    if not hit: return None
    hits = {t for t, rx in TOPIC_RX if rx.search(text)}
    # one main theme per paper, in priority order, plus "review" when it applies
    for main in ("epidemiology", "genetics", "living", "prosthetics", "clinical"):
        if main in hits:
            topics = {main} | ({"review"} & hits); break
    else:
        topics = {"review"} if "review" in hits else {"clinical"}
    if CAUSES_RX.search(title if title is not None else text): topics.add("causes")
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


MEMBER_FILES = sorted(HERE.glob("member-dois*.json")) + sorted(HERE.glob("registry-dois*.json"))  # member associations + registries' official websites
review, extra = [], []  # rejected/unresolved hits; Crossref-only accepted entries
if MEMBER_FILES:
    hits = [h for f in MEMBER_FILES for h in json.loads(f.read_text(encoding="utf-8"))["hits"]]
    print(f"member crawl files: {', '.join(f.name for f in MEMBER_FILES)} → {len(hits)} raw hits")
    def norm_doi(d):
        d = d.split("?")[0].rstrip(".,;:/")
        d = re.sub(r"\.(t|g|s)\d{3}$", "", d)  # PLOS table / figure / supplement DOIs → parent article
        return d.lower() if re.fullmatch(r"10\.\d{4,9}/[^\s(]{4,}", d) and not d.endswith(("/journal", "/journal.pone")) else None
    by_id = {}
    for h in hits:
        if h.get("doi"):
            d = norm_doi(h["doi"])
            if not d: continue
            k = ("doi", d)
        else:
            k = ("pmid", h["pmid"]) if h.get("pmid") else ("pmcid", h["pmcid"])
        by_id.setdefault(k, {"hit": h, "members": set()})["members"].add(f"{h['member']} ({h['country']})")
    print(f"member sites: {len(by_id)} distinct identifiers")
    resolved = {}  # pmid -> members ; Crossref-only handled inline
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
            resolved.setdefault(pmid, set()).update(members)
        elif meta:
            r = screen(meta["title"] + " " + meta["abstract"], meta["title"], strict=True)
            if not r:
                review.append({"id": ident, "title": meta["title"], "members": members, "status": "rejected: not about the site's conditions (Crossref)"}); continue
            codes, topics = r
            if re.search(r"meta-?analys|systematic review|pooled analysis|umbrella review|scoping review", meta["title"], re.I): topics.add("meta")
            meta.pop("abstract"); meta.update({"codes": sorted(codes), "topics": sorted(topics), "notes": [f"published on the website of {', '.join(members)}"], "via": members})
            extra.append(meta)
        else:
            review.append({"id": ident, "members": members, "status": "unresolved: no PubMed or Crossref record"})
    print(f"resolved to PubMed: {len(resolved)} records; screening titles and abstracts in batches")
    pm_list = sorted(resolved)
    for i in range(0, len(pm_list), 50):
        batch = pm_list[i:i + 50]
        xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
        for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
            pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
            if not pm or pm.group(1) not in resolved: continue
            pmid = pm.group(1); members = sorted(resolved[pmid])
            title = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)))
            abstract = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)))
            r = screen(title + " " + abstract, title, strict=True)
            if not r:
                review.append({"id": pmid, "pmid": pmid, "title": title.strip(), "members": members, "status": "rejected: not about the site's conditions"}); continue
            codes, topics = r
            for t in topics: add(pmid, None, t, f"published on the website of {', '.join(members)}", via=None)
            for c in codes: seed[pmid]["codes"].add(c)
            seed[pmid]["via"].update(members)
    print(f"member hits accepted: {sum(1 for v in seed.values() if v['via'] - {'Orphanet', 'DysNet'})} via PubMed + {len(extra)} via Crossref | set aside: {len(review)}")

# ─── 4. Thalidomide literature (PubMed, title-level query) ──────────────────
# Thalidomide caused the largest cluster of limb differences of the 20th century; many DysNet members
# are survivor associations. The query is fixed and title-restricted so the set is reproducible.
THAL_QUERY = ('thalidomide[Title] AND (teratogen*[Title] OR embryopath*[Title] OR "birth defects"[Title] OR phocomelia[Title] '
              'OR survivors[Title] OR "limb"[Title] OR malformation*[Title] OR Contergan[Title] OR victims[Title] OR disaster[Title] OR tragedy[Title])')
THAL_EXCL = re.compile(r"anticancer|immunomodulat|angiogenesis|myeloma|lupus|leprosy reaction|erythema nodosum|treatment (with|of)|analog|non-teratogenic|inhibit|therapy for|chemotherap|arteriovenous|vascular malformation|angiodysplasia|telangiectasia|bleeding|hemorrhag|haemorrhag|effect of thalidomide on", re.I)
THAL_KEEP = re.compile(r"embryopath|survivor|phocomelia|birth defect|teratogen|limb (malformation|defect|reduction|bud|defic|formation)|thalidomide[- ](children|damaged|affected|impaired)|embryo|victim|Contergan|disaster|tragedy", re.I)
thal_ids = json.loads(eget(f"{E}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(THAL_QUERY)}&retmode=json&retmax=2000"))["esearchresult"]["idlist"]
print(f"thalidomide query: {len(thal_ids)} PubMed records")
for i in range(0, len(thal_ids), 50):
    batch = thal_ids[i:i + 50]
    xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not pm: continue
        pmid = pm.group(1)
        title = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)))
        abstract = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)))
        if THAL_EXCL.search(title) and not (THAL_KEEP.search(title) and not re.search(r"non-teratogenic", title, re.I)):
            review.append({"id": pmid, "pmid": pmid, "title": title.strip(), "members": ["PubMed search"], "status": "rejected: thalidomide as a drug, not the embryopathy"}); continue
        r = screen(title + " " + abstract, title)
        codes, topics = (r if r else (set(), {"clinical"}))
        codes.add("thal")
        for t in topics: add(pmid, None, t, "PubMed title search on thalidomide embryopathy", via="PubMed search")
        for c in codes: seed[pmid]["codes"].add(c)

# ─── 5. Systematic reviews and meta-analyses on our conditions (PubMed, fixed query) ──────────
META_QUERY = ('(meta-analysis[pt] OR systematic review[pt] OR "systematic review"[ti] OR "meta-analysis"[ti]) AND '
              '("limb reduction"[tiab] OR "limb deficiency"[tiab] OR "limb deficiencies"[tiab] OR "limb difference"[tiab] OR "limb differences"[tiab] '
              'OR "limb defects"[tiab] OR "upper limb anomalies"[tiab] OR "congenital hand"[tiab] OR polydactyly[tiab] OR syndactyly[tiab] '
              'OR "Poland syndrome"[tiab] OR "Poland sequence"[tiab] OR symbrachydactyly[tiab] OR brachydactyly[tiab] OR ectrodactyly[tiab] OR "split hand"[tiab] '
              'OR amelia[tiab] OR phocomelia[tiab] OR hemimelia[tiab] OR "radial longitudinal deficiency"[tiab] OR "radial club hand"[tiab] '
              'OR "fibular deficiency"[tiab] OR "tibial deficiency"[tiab] OR "amniotic band"[tiab] OR "Adams-Oliver"[tiab] OR "Holt-Oram"[tiab] '
              'OR "thrombocytopenia-absent radius"[tiab] OR "thalidomide embryopathy"[tiab] OR dysmelia[tiab])')
meta_ids = json.loads(eget(f"{E}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(META_QUERY)}&retmode=json&retmax=1000"))["esearchresult"]["idlist"]
print(f"systematic-review query: {len(meta_ids)} PubMed records")
for i in range(0, len(meta_ids), 50):
    batch = meta_ids[i:i + 50]
    xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not pm: continue
        pmid = pm.group(1)
        title = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)))
        abstract = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)))
        r = screen(title + " " + abstract, title, strict=True)
        if not r:
            review.append({"id": pmid, "pmid": pmid, "title": title.strip(), "members": ["PubMed search"], "status": "rejected: systematic review not about the site's conditions"}); continue
        codes, topics = r
        add(pmid, None, "meta", "PubMed search for systematic reviews and meta-analyses on the site's conditions", via="PubMed search")
        for c in codes: seed[pmid]["codes"].add(c)

# ─── 6. Causes and risk factors of our conditions (PubMed, fixed title-level query, thalidomide excluded: covered by section 4) ──
CAUSES_QUERY = ('("limb reduction"[tiab] OR "limb deficiency"[tiab] OR "limb deficiencies"[tiab] OR "limb defects"[tiab] OR "limb malformations"[tiab] '
                'OR amelia[tiab] OR phocomelia[tiab] OR hemimelia[tiab] OR ectrodactyly[tiab] OR polydactyly[tiab] OR syndactyly[tiab] OR symbrachydactyly[tiab] '
                'OR "Poland syndrome"[tiab] OR "amniotic band"[tiab] OR "transverse limb"[tiab]) AND '
                '(etiology[ti] OR aetiology[ti] OR causes[ti] OR "risk factor"[ti] OR "risk factors"[ti] OR teratogen*[ti] OR maternal[ti] OR exposure[ti] '
                'OR environmental[ti] OR pesticide*[ti] OR cluster*[ti] OR "vascular disruption"[ti]) NOT thalidomide[ti]')
causes_ids = json.loads(eget(f"{E}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(CAUSES_QUERY)}&retmode=json&retmax=2000"))["esearchresult"]["idlist"]
print(f"causes query: {len(causes_ids)} PubMed records")
for i in range(0, len(causes_ids), 50):
    batch = causes_ids[i:i + 50]
    xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not pm: continue
        pmid = pm.group(1)
        title = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)))
        abstract = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)))
        r = screen(title + " " + abstract, title, strict=True)
        if not r:
            review.append({"id": pmid, "pmid": pmid, "title": title.strip(), "members": ["PubMed search"], "status": "rejected: causes query, not about the site's conditions"}); continue
        codes, topics = r
        topics.add("causes")
        for t in topics: add(pmid, None, t, "PubMed search for causes and risk factors of the site's conditions", via="PubMed search")
        for c in codes: seed[pmid]["codes"].add(c)

# ─── 7. Canada and the United States: national limb-loss and limb-difference data ─────────────
# Registry work outside Europe, where Orphanet's directory stops: the Canadian national strategy,
# the American registry already running, and the provincial surveillance that publishes on our conditions.
NORTH_AMERICA = {
    "41918893": ("epidemiology", "Delphi strategy for a Canadian limb loss and limb difference registry"),
}
for pmid, (topic, note) in NORTH_AMERICA.items():
    add(pmid, None, topic, note, via="PubMed search")
CANADA_QUERY = ('("Child Amputee Program"[All Fields] OR "Child Amputee Prosthetics Project"[All Fields] '
                'OR ("limb loss"[tiab] AND "limb difference"[tiab])) '
                'OR ((Canada[tiab] OR Canadian[tiab] OR Alberta[tiab] OR Ontario[tiab] OR Quebec[tiab] OR "British Columbia"[tiab] OR Toronto[tiab] OR Montreal[tiab]) '
                'AND ("limb deficiency"[tiab] OR "limb deficiencies"[tiab] OR "limb difference"[tiab] OR "limb differences"[tiab] OR "limb reduction"[tiab] '
                'OR "child amputee"[tiab] OR "child amputees"[tiab] OR "paediatric amputee"[tiab] OR "pediatric amputee"[tiab] OR dysmelia[tiab]))')
canada_ids = json.loads(eget(f"{E}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(CANADA_QUERY)}&retmode=json&retmax=1000"))["esearchresult"]["idlist"]
print(f"North America query: {len(canada_ids)} PubMed records")
for i in range(0, len(canada_ids), 50):
    batch = canada_ids[i:i + 50]
    xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not pm: continue
        pmid = pm.group(1)
        title = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)))
        abstract = re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)))
        r = screen(title + " " + abstract, title, strict=True)
        if not r:
            review.append({"id": pmid, "pmid": pmid, "title": title.strip(), "members": ["PubMed search"], "status": "rejected: Canada query, not about the site's conditions"}); continue
        codes, topics = r
        for t in topics: add(pmid, None, t, "PubMed search on Canadian limb difference and child amputee care", via="PubMed search")
        for c in codes: seed[pmid]["codes"].add(c)

# ─── 8. The countries of our member associations: national studies on our conditions ──────────
# Broad country × condition query, screened on the TITLE only: the condition must be the subject of the
# paper, not a passing mention. Veterinary work and the given name "Amelia" are filtered out explicitly.
COUNTRY_TERMS = ('Australia[tiab] OR Austria[tiab] OR Austrian[tiab] OR Belgium[tiab] OR Belgian[tiab] OR Chile[tiab] OR Chilean[tiab] '
                 'OR France[tiab] OR French[tiab] OR Germany[tiab] OR German[tiab] OR Ireland[tiab] OR Irish[tiab] OR Italy[tiab] OR Italian[tiab] '
                 'OR Netherlands[tiab] OR Dutch[tiab] OR Norway[tiab] OR Norwegian[tiab] OR Spain[tiab] OR Spanish[tiab] OR Sweden[tiab] OR Swedish[tiab] '
                 'OR "United Kingdom"[tiab] OR Britain[tiab] OR British[tiab] OR England[tiab] OR Scotland[tiab] OR Wales[tiab]')
LIMB_TERMS = ('"limb reduction"[tiab] OR "limb deficiency"[tiab] OR "limb deficiencies"[tiab] OR "limb difference"[tiab] OR "limb differences"[tiab] '
              'OR "limb defects"[tiab] OR "limb anomalies"[tiab] OR "limb malformations"[tiab] OR dysmelia[tiab] OR amelia[tiab] OR phocomelia[tiab] '
              'OR hemimelia[tiab] OR ectrodactyly[tiab] OR symbrachydactyly[tiab] OR "split hand"[tiab] OR "Poland syndrome"[tiab] OR "amniotic band"[tiab] '
              'OR "congenital hand"[tiab] OR "transverse limb"[tiab] OR "child amputee"[tiab] OR "child amputees"[tiab]')
COUNTRY_QUERY = f"({COUNTRY_TERMS}) AND ({LIMB_TERMS})"
VET_RX = re.compile(r"\b(calf|calves|cattle|bovine|buffalo|buffaloes|chicken|chickens|poultry|avian|canine|feline|equine|porcine|piglet|lamb|ovine|foal|puppy)\b", re.I)
NAME_RX = re.compile(r"Amelia\s*[\(,]|Amelia\s+[A-Z][a-z]+")
country_ids = json.loads(eget(f"{E}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(COUNTRY_QUERY)}&retmode=json&retmax=2000"))["esearchresult"]["idlist"]
print(f"member-country query: {len(country_ids)} PubMed records")
for i in range(0, len(country_ids), 50):
    batch = country_ids[i:i + 50]
    xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&rettype=abstract&retmode=xml").decode("utf-8", "replace")
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not pm: continue
        pmid = pm.group(1)
        title = " ".join(re.sub(r"<[^>]+>", " ", " ".join(re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S))).split())
        if VET_RX.search(title) or NAME_RX.search(title):
            review.append({"id": pmid, "pmid": pmid, "title": title, "members": ["PubMed search"], "status": "rejected: member-country query, veterinary or a personal name"}); continue
        r = screen(title, title, strict=True)
        if not r:
            review.append({"id": pmid, "pmid": pmid, "title": title, "members": ["PubMed search"], "status": "rejected: member-country query, the conditions are not the subject of the paper"}); continue
        codes, topics = r
        for t in topics: add(pmid, None, t, "PubMed search on studies from the countries of our member associations", via="PubMed search")
        for c in codes: seed[pmid]["codes"].add(c)

META_RX = re.compile(r"meta-?analys|systematic review|pooled analysis|umbrella review|scoping review", re.I)

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
        # publication type from the PubMed record itself: meta-analyses / systematic reviews and reviews
        pubtypes = set(d.get("pubtype", []))
        title = d.get("title", "").rstrip(".")
        if pubtypes & {"Meta-Analysis", "Systematic Review"} or META_RX.search(title): s["topics"].add("meta")
        if "Review" in pubtypes: s["topics"].add("review")
        if CAUSES_RX.search(title): s["topics"].add("causes")
        entries.append({"pmid": pmid, "doi": doi, "title": title, "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
                        "journal": d.get("fulljournalname") or d.get("source", ""), "year": year, "volume": d.get("volume", ""), "pages": d.get("pages", ""),
                        "pubtypes": sorted(pubtypes - {"Journal Article"}),
                        "codes": sorted(s["codes"]), "topics": sorted(s["topics"]), "notes": sorted(s["notes"]), "via": sorted(s["via"])})
    time.sleep(0.4)
entries.extend(extra)
entries.sort(key=lambda e: (-int(e["year"] or 0), e["title"]))
out = {"built": time.strftime("%Y-%m-%d"), "source": "PubMed IDs cited by Orphanet (Orphadata epidemiology) for the site's ORPHAcodes, publications verified on the site, DOIs published on member associations' websites, and a fixed title-level PubMed query on thalidomide embryopathy; metadata from NCBI E-utilities / Crossref", "thalidomide_query": THAL_QUERY, "systematic_review_query": META_QUERY, "causes_query": CAUSES_QUERY, "canada_query": CANADA_QUERY, "member_country_query": COUNTRY_QUERY, "entries": entries}
(HERE / "bibliography.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(entries)} references | with DOI: {sum(1 for e in entries if e['doi'])} | tagged to a condition: {sum(1 for e in entries if e['codes'])}")
(HERE / "bibliography-review.json").write_text(json.dumps({"built": time.strftime("%Y-%m-%d"), "items": review}, ensure_ascii=False, indent=1), encoding="utf-8")
