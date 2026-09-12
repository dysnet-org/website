#!/usr/bin/env python3
"""Build tools/researchers.json: research teams derived from the verified bibliography.

Orphanet's research-projects directory holds no project specific to our ORPHAcodes (checked
2026-09-12: 1 direct hit, misfiled; 39 generic rare-disease infrastructure projects), so the
register of researchers is built from the publications themselves: for every PubMed record in
tools/bibliography.json, the affiliation of the first and of the last (senior) author is read from
the PubMed XML, reduced to an institution, and institutions are aggregated. A team is listed when
it signs at least MIN_PAPERS publications of the bibliography. Listing is by documented activity.

Run: python3 tools/build-researchers.py   (network: NCBI E-utilities, 3 req/s)
"""
import html, json, pathlib, re, time, urllib.request
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).parent
E = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MIN_PAPERS = 2
BIB = json.loads((HERE / "bibliography.json").read_text(encoding="utf-8"))
ENTRIES = {e["pmid"]: e for e in BIB["entries"] if e.get("pmid")}

INST_RX = re.compile(r"universit|hospital|h[oô]pital|hospices|klinik|clinic|institut|center|centre|\bCHU\b|\bCHRU\b|school of medicine|medical school|college|foundation|fondazione|ospedale|azienda|inserm|cnrs|\bnhs\b|children'?s|infirmary|policlinico|krankenhaus|akademi|academy|research council|\bMRC\b|karolinska|charit[eé]", re.I)
DEPT_RX = re.compile(r"^(department|dept\.?|division|unit|service|laborator|lab\b|section|faculty|school|program|clinic for|klinik f[uü]r|abteilung|u\.?o\.?|servizio|unidad|servicio|équipe|team|group|graduate)", re.I)
COUNTRY_FIX = {"usa": "United States", "u.s.a.": "United States", "united states of america": "United States", "us": "United States",
               "uk": "United Kingdom", "u.k.": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom", "wales": "United Kingdom", "great britain": "United Kingdom",
               "deutschland": "Germany", "brasil": "Brazil", "españa": "Spain", "italia": "Italy", "nederland": "Netherlands", "the netherlands": "Netherlands",
               "schweiz": "Switzerland", "suisse": "Switzerland", "sverige": "Sweden", "norge": "Norway", "danmark": "Denmark", "österreich": "Austria",
               "republic of korea": "South Korea", "korea": "South Korea", "p.r. china": "China", "pr china": "China", "people's republic of china": "China",
               "russian federation": "Russia", "türkiye": "Turkey", "czech republic": "Czechia", "iran": "Iran", "islamic republic of iran": "Iran"}
COUNTRIES = {"United States", "United Kingdom", "Germany", "France", "Italy", "Spain", "Netherlands", "Belgium", "Switzerland", "Sweden", "Norway", "Denmark", "Finland", "Austria",
             "Poland", "Portugal", "Ireland", "Czechia", "Hungary", "Greece", "Turkey", "Russia", "Israel", "Iran", "India", "China", "Japan", "South Korea", "Taiwan", "Australia",
             "New Zealand", "Canada", "Brazil", "Argentina", "Chile", "Mexico", "Colombia", "South Africa", "Egypt", "Saudi Arabia", "Pakistan", "Thailand", "Singapore", "Malaysia",
             "Indonesia", "Nigeria", "Kenya", "Tunisia", "Morocco", "Croatia", "Serbia", "Slovenia", "Slovakia", "Romania", "Bulgaria", "Estonia", "Latvia", "Lithuania", "Iceland",
             "Luxembourg", "Cuba", "Peru", "Venezuela", "Uruguay", "Vietnam", "Philippines", "Bangladesh", "Sri Lanka", "Nepal", "Iraq", "Jordan", "Lebanon", "Qatar", "Kuwait",
             "United Arab Emirates", "Oman", "Ukraine", "Belarus", "Georgia", "Armenia", "Kazakhstan", "Cyprus", "Malta"}


def eget(url, timeout=90):
    time.sleep(0.4)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "DysNet researchers register builder (info@dysnet.org)"}), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def clean(seg):
    seg = re.sub(r"\S+@\S+", "", seg)  # e-mails
    seg = re.sub(r"\b(electronic address|e-?mail)\b.*$", "", seg, flags=re.I)
    seg = re.sub(r"\b\d{4,}\b|\b[A-Z]{1,2}-?\d{3,}\b", "", seg)  # postcodes
    return re.sub(r"\s+", " ", seg).strip(" .;:-")


def country_of(aff):
    segs = [clean(s) for s in re.split(r"[,;]", aff) if clean(s)]
    for seg in reversed(segs):
        s = seg.strip(". ").lower()
        if s in COUNTRY_FIX: return COUNTRY_FIX[s]
        for c in COUNTRIES:
            if s == c.lower() or s.endswith(" " + c.lower()) or re.search(r"\b" + re.escape(c.lower()) + r"\b", s): return c
    return ""


TOP_RX = re.compile(r"universit|hospital|h[oô]pital|hospices|klinikum|universitätsklinik|ospedale|azienda|policlinico|\bCHU\b|\bCHRU\b|medical (center|centre|school)|school of medicine|children'?s|infirmary|karolinska|charit[eé]|inail|\bnhs\b|health service|trust\b", re.I)


def institution_of(aff):
    aff = html.unescape(aff).split(";")[0]
    segs = [clean(s) for s in aff.split(",")]
    segs = [s for s in segs if s and not re.fullmatch(r"[\d\s-]+", s) and len(s) > 3]
    if not segs: return ""
    # rank: university / hospital level first, then institutes and centres, then anything that is not a department
    top = [s for s in segs if TOP_RX.search(s) and not DEPT_RX.search(s)]
    inst = [s for s in segs if INST_RX.search(s) and not DEPT_RX.search(s)]
    pick = top[0] if top else inst[0] if inst else next((s for s in segs if not DEPT_RX.search(s)), segs[0])
    # "X University School of Medicine" style: keep the university part
    pick = re.sub(r"^(the )", "", pick, flags=re.I)
    return pick[:120]


ALIASES = [(r"universit[aä]t zu k[oö]ln|university hospital (of )?cologne|uniklinik k[oö]ln", "university of cologne"), (r"g[oö]teborg", "gothenburg"),
           (r"universit[aä]ts?(klinikum|klinik)?", "university"), (r"universit[eé]|universidad|universidade|università|universiteit", "university"),
           (r"h[oô]pital|hospices civils|ospedale|krankenhaus|klinikum|hospitalet", "hospital"), (r"\bchu\b|\bchru\b", "university hospital")]


def norm_key(inst):
    k = inst.lower()
    for rx, rep in ALIASES: k = re.sub(rx, rep, k)
    k = re.sub(r"\b(the|of|for|and|de|del|della|di|du|des|la|le|für|und)\b", " ", k)
    k = re.sub(r"[^a-z0-9 ]", " ", k)
    return re.sub(r"\s+", " ", k).strip()


pmids = sorted(ENTRIES)
teams = defaultdict(lambda: {"names": Counter(), "papers": {}, "authors": Counter(), "countries": Counter()})
no_aff = 0
for i in range(0, len(pmids), 50):
    batch = pmids[i:i + 50]
    xml = eget(f"{E}/efetch.fcgi?db=pubmed&id={','.join(batch)}&retmode=xml")
    for art in re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        if not pm or pm.group(1) not in ENTRIES: continue
        pmid = pm.group(1)
        authors = re.findall(r"<Author[^>]*>(.*?)</Author>", art, re.S)
        picks = []
        for a in ([authors[0]] + ([authors[-1]] if len(authors) > 1 else [])) if authors else []:
            last = re.search(r"<LastName>(.*?)</LastName>", a); ini = re.search(r"<Initials>(.*?)</Initials>", a)
            aff = re.search(r"<Affiliation>(.*?)</Affiliation>", a, re.S)
            if not aff: continue
            inst = institution_of(re.sub(r"<[^>]+>", "", aff.group(1)))
            last_name = html.unescape(last.group(1)) if last else ""
            if not inst or len(inst) < 4: continue
            picks.append((inst, country_of(html.unescape(aff.group(1))), f"{last_name} {ini.group(1) if ini else ''}".strip() if last else ""))
        if not picks: no_aff += 1
        for inst, country, name in picks:
            t = teams[norm_key(inst)]
            t["names"][inst] += 1; t["papers"][pmid] = ENTRIES[pmid]
            if name: t["authors"][name] += 1
            if country: t["countries"][country] += 1

out = []
for key, t in teams.items():
    if len(t["papers"]) < MIN_PAPERS: continue
    papers = sorted(t["papers"].values(), key=lambda e: (-int(e["year"] or 0), e["title"]))
    codes = Counter(c for e in papers for c in e["codes"])
    out.append({"institution": t["names"].most_common(1)[0][0], "country": (t["countries"].most_common(1) or [("", 0)])[0][0],
                "papers": len(papers), "years": [min(int(e["year"]) for e in papers if e["year"]), max(int(e["year"]) for e in papers if e["year"])],
                "codes": [c for c, _ in codes.most_common(4)], "authors": [a for a, _ in t["authors"].most_common(3)],
                "representative": {"pmid": papers[0]["pmid"], "doi": papers[0]["doi"], "title": papers[0]["title"], "year": papers[0]["year"]},
                "pmids": [e["pmid"] for e in papers]})
out.sort(key=lambda t: (-t["papers"], -t["years"][1], t["institution"]))
(HERE / "researchers.json").write_text(json.dumps({"built": time.strftime("%Y-%m-%d"), "method": "Institutions of first and last authors of the bibliography's PubMed records (NCBI E-utilities affiliations), aggregated; listed from %d publications." % MIN_PAPERS,
                                                    "bibliography_size": len(ENTRIES), "records_without_affiliation": no_aff, "teams": out}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(ENTRIES)} records, {no_aff} without affiliation data; {len(teams)} institutions seen, {len(out)} teams with >= {MIN_PAPERS} papers")
print("countries:", Counter(t["country"] or "?" for t in out).most_common(12))
for t in out[:15]: print(f"  {t['papers']:3d} | {t['country'][:14]:14s} | {t['institution'][:70]} | {', '.join(t['authors'][:2])}")
