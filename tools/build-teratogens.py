#!/usr/bin/env python3
"""Build tools/teratogens.json: substances and products with proven, presumed or suspected effects on the unborn child,
each tagged with the source that lists it and with its regulatory status per jurisdiction.

Sources (machine-readable or official pages, never memory):
  A. EU harmonised classification, CLP Annex VI Table 3 (ECHA Excel export, ATP23, tools/terato/annex_vi_clp_table_atp23_en.xlsx):
     entries classified Repr. 1A / 1B / 2 whose hazard statement concerns the unborn child (H360D, H360FD, H360Fd, H360Df,
     H361d, H361fd) or the undifferentiated H360 / H361. 1A = known human reproductive toxicant, 1B = presumed (animal data),
     2 = suspected. Status in the EU follows from the classification: mandatory labelling; Repr. 1A/1B not supplied to the
     general public (REACH Annex XVII entry 30), not approvable as pesticide active substances (Reg. 1107/2009, 3.6.4),
     banned in cosmetics (Reg. 1223/2009, Art. 15), covered at work by Directive 2004/37/EC as amended by 2022/431.
  B. California Proposition 65 list (OEHHA Excel export, tools/terato/p65chemicalslist.xlsx): entries whose type of toxicity
     includes "developmental". Effect: a clear and reasonable warning is required before exposure in California; no ban.
  C. Medicines under an EU pregnancy prevention programme or contraindicated in pregnancy for teratogenicity, from EMA
     referral or product pages (URLs checked at build time).
  D. Alcohol (WHO) and tobacco smoking (peer-reviewed meta-analysis in the DysNet bibliography).
Run: python3 tools/build-teratogens.py
"""
import datetime, json, pathlib, re, urllib.request, xml.etree.ElementTree as ET, zipfile

HERE = pathlib.Path(__file__).parent
T = HERE / "terato"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_xlsx(path, sheet_index=0):
    z = zipfile.ZipFile(path)
    ss = [''.join(t.text or '' for t in si.iter(NS + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si')] if 'xl/sharedStrings.xml' in z.namelist() else []
    sheet = sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet'))[sheet_index]
    rows = []
    for r in ET.fromstring(z.read(sheet)).iter(NS + 'row'):
        vals = {}
        for c in r.findall(NS + 'c'):
            col = re.match(r'[A-Z]+', c.get('r')).group(0); v = c.find(NS + 'v'); t = c.get('t')
            val = ss[int(v.text)] if (t == 's' and v is not None) else (v.text if v is not None else '')
            if t == 'inlineStr': val = ''.join(x.text or '' for x in c.iter(NS + 't'))
            vals[col] = val.strip()
        rows.append(vals)
    return rows


def excel_date(serial):
    try: return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(serial)))).isoformat()
    except Exception: return ""


def norm_cas(s):
    s = (s or "").strip()
    return s if re.fullmatch(r"\d{2,7}-\d{2}-\d", s) else ""


entries = {}  # key -> entry


def add(key, **kw):
    e = entries.setdefault(key, {"name": kw["name"], "cas": kw.get("cas", ""), "ec": kw.get("ec", ""), "kind": kw.get("kind", "chemical"),
                                 "sources": [], "status": {}, "jurisdictions": {}})
    e["sources"].append(kw["source"])
    for k, v in kw.get("status", {}).items(): e["status"][k] = v
    for k, v in kw.get("jurisdictions", {}).items(): e["jurisdictions"][k] = v
    if kw.get("kind") and e["kind"] == "chemical": e["kind"] = kw["kind"]
    return e


# ── A. EU CLP Annex VI ────────────────────────────────────────────────────────
DEV_H = re.compile(r"H360(D|FD|Fd|Df)?\b|H361(d|fd)?\b")
rows = read_xlsx(T / "annex_vi_clp_table_atp23_en.xlsx", 0)
hdr = next(i for i, r in enumerate(rows) if r.get("A") == "Index No")
n_clp = 0
for r in rows[hdr + 1:]:
    cls, hs = r.get("G", ""), r.get("H", "")
    if "Repr." not in cls or not DEV_H.search(hs): continue
    cat = re.search(r"Repr\.\s*(1A|1B|2)", cls); cat = cat.group(1) if cat else "?"
    dev_codes = sorted(set(m.group(0) for m in DEV_H.finditer(hs)))
    level = {"1A": "known", "1B": "presumed", "2": "suspected"}.get(cat, "suspected")
    specific = any(c in ("H360D", "H360FD", "H360Fd", "H360Df", "H361d", "H361fd") for c in dev_codes)
    cas = norm_cas(r.get("F", "").split("\n")[0]); key = ("cas:" + cas) if cas else ("clp:" + r.get("A", ""))
    eu = {"labelling": "Mandatory hazard classification and labelling of the substance and of mixtures containing it (CLP Annex VI, harmonised)."}
    if cat in ("1A", "1B"):
        eu["consumers"] = "Not to be supplied to the general public as a substance or in mixtures above the concentration limit (REACH Annex XVII, entry 30, where listed in Appendix 5 or 6)."
        eu["pesticides"] = "Cannot be approved as a pesticide active substance unless human exposure is negligible (Regulation 1107/2009, Annex II 3.6.4)."
        eu["cosmetics"] = "Prohibited in cosmetic products (Regulation 1223/2009, Article 15)."
        eu["work"] = "Reprotoxic substance under Directive 2004/37/EC as amended by Directive 2022/431: substitution, exposure limits and health surveillance at work."
    else:
        eu["consumers"] = "Labelling required; no general ban on supply to the public for category 2."
        eu["cosmetics"] = "Prohibited in cosmetics unless evaluated as safe by the SCCS (Regulation 1223/2009, Article 15(1))."
    add(key, name=r.get("D", "").split("\n")[0].strip(), cas=cas, ec=r.get("E", "").split("\n")[0].strip(), kind="chemical",
        source={"label": "EU harmonised classification (CLP Annex VI)", "code": "clp", "category": f"Repr. {cat}", "statements": dev_codes,
                "developmental_specific": specific, "atp": r.get("B", ""), "applies_from": excel_date(r.get("O", "")), "url": r.get("P", ""), "index": r.get("A", "")},
        status={"clp": level}, jurisdictions={"EU / EEA": eu})
    n_clp += 1
print(f"CLP Annex VI: {n_clp} entries with unborn-child hazard statements")

# ── B. California Proposition 65 ──────────────────────────────────────────────
rows = read_xlsx(T / "p65chemicalslist.xlsx", 0)
hdr = next(i for i, r in enumerate(rows) if r.get("A") == "Chemical")
MECH = {"AB": "authoritative body", "SQE": "State's Qualified Experts", "FR": "formally required to be labelled or identified", "LC": "Labor Code"}
n_p65 = 0
for r in rows[hdr + 1:]:
    tox = r.get("B", "").lower()
    if "developmental" not in tox or not r.get("A"): continue
    cas = norm_cas(r.get("D", "")); key = ("cas:" + cas) if cas else ("p65:" + r["A"].lower())
    add(key, name=r["A"], cas=cas, kind="chemical",
        source={"label": "California Proposition 65 (developmental toxicant)", "code": "p65", "toxicity": r.get("B", ""), "mechanism": MECH.get(r.get("C", ""), r.get("C", "")),
                "listed": excel_date(r.get("E", "")), "madl_ug_day": r.get("F", ""), "url": "https://oehha.ca.gov/proposition-65/proposition-65-list"},
        status={"p65": "known to the State of California to cause developmental toxicity"},
        jurisdictions={"California (USA)": {"warning": "A clear and reasonable warning is required before knowingly exposing anyone in California (Health and Safety Code 25249.6); listing does not ban the substance.",
                                            "enforcement": "Attorney General, district attorneys and private enforcers; civil penalties up to USD 2,500 per violation per day."}})
    n_p65 += 1
print(f"Proposition 65: {n_p65} developmental toxicants")

# ── C. Medicines under EU pregnancy prevention programmes (EMA pages, checked below) ───────
MEDS = [
    ("Thalidomide", "50-35-1", "Thalidomide BMS (Celgene): authorised for multiple myeloma with a pregnancy prevention programme; the reference teratogen.", "https://www.ema.europa.eu/en/medicines/human/EPAR/thalidomide-bms", "known",
     {"EU / EEA": "Authorised (multiple myeloma) only within a pregnancy prevention programme; contraindicated in pregnancy and in women of childbearing potential without the programme.", "USA": "Authorised under the FDA THALOMID REMS programme."}),
    ("Lenalidomide", "191732-72-6", "Thalidomide analogue (Revlimid): pregnancy prevention programme.", "https://www.ema.europa.eu/en/medicines/human/EPAR/revlimid", "presumed",
     {"EU / EEA": "Authorised within a pregnancy prevention programme; contraindicated in pregnancy.", "USA": "Authorised under an FDA REMS programme."}),
    ("Pomalidomide", "19171-19-8", "Thalidomide analogue (Imnovid): pregnancy prevention programme.", "https://www.ema.europa.eu/en/medicines/human/EPAR/imnovid", "presumed",
     {"EU / EEA": "Authorised within a pregnancy prevention programme; contraindicated in pregnancy.", "USA": "Authorised under an FDA REMS programme."}),
    ("Isotretinoin and other oral retinoids (acitretin, alitretinoin)", "4759-48-2", "Oral retinoids: EMA referral of 2018 harmonised the pregnancy prevention programme across the EU.", "https://www.ema.europa.eu/en/medicines/human/referrals/retinoid-containing-medicinal-products", "known",
     {"EU / EEA": "Authorised with a pregnancy prevention programme; contraindicated in pregnancy.", "USA": "Isotretinoin authorised under the iPLEDGE REMS programme."}),
    ("Valproate (valproic acid and related substances)", "99-66-1", "Antiepileptic: EMA referral of 2018 imposed a pregnancy prevention programme and new contraindications.", "https://www.ema.europa.eu/en/medicines/human/referrals/valproate-related-substances-0", "known",
     {"EU / EEA": "Authorised with a pregnancy prevention programme; contraindicated in pregnancy for epilepsy unless no alternative, and for bipolar disorder.", "USA": "Authorised with a boxed warning on foetal risk."}),
    ("Mycophenolate mofetil and mycophenolic acid", "128794-94-5", "Immunosuppressant: EMA referral of 2015 imposed pregnancy prevention measures.", "https://www.ema.europa.eu/en/documents/press-release/ema-recommends-additional-measures-prevent-use-mycophenolate-pregnancy_en.pdf", "known",
     {"EU / EEA": "Authorised with pregnancy prevention measures; contraindicated in pregnancy unless no suitable alternative.", "USA": "Authorised under an FDA REMS programme."}),
    ("Topiramate", "97240-79-4", "Antiepileptic and migraine medicine: EMA referral of 2023 imposed a pregnancy prevention programme.", "https://www.ema.europa.eu/en/medicines/human/referrals/topiramate", "known",
     {"EU / EEA": "Authorised with a pregnancy prevention programme; contraindicated in pregnancy for migraine prevention and in epilepsy unless no alternative."}),
    ("Methotrexate", "59-05-2", "Folate antagonist: EMA referral of 2018 harmonised warnings; contraindicated in pregnancy for non-oncology use.", "https://www.ema.europa.eu/en/medicines/human/referrals/methotrexate-containing-medicinal-products", "known",
     {"EU / EEA": "Authorised; contraindicated in pregnancy for non-oncology indications, with contraception requirements."}),
    ("Bosentan (endothelin receptor antagonist)", "147536-97-8", "Pulmonary arterial hypertension medicine (Tracleer); teratogenic in animals; monthly pregnancy testing.", "https://www.ema.europa.eu/en/medicines/human/EPAR/tracleer", "presumed",
     {"EU / EEA": "Authorised; contraindicated in pregnancy and in women of childbearing potential not using reliable contraception."}),
    ("Ambrisentan (endothelin receptor antagonist)", "177036-94-1", "Pulmonary arterial hypertension medicine (Volibris); teratogenic in animals.", "https://www.ema.europa.eu/en/medicines/human/EPAR/volibris", "presumed",
     {"EU / EEA": "Authorised; contraindicated in pregnancy."}),
    ("Macitentan (endothelin receptor antagonist)", "441798-33-0", "Pulmonary arterial hypertension medicine (Opsumit); teratogenic in animals.", "https://www.ema.europa.eu/en/medicines/human/EPAR/opsumit", "presumed",
     {"EU / EEA": "Authorised; contraindicated in pregnancy."}),
    ("Fingolimod", "162359-55-9", "Multiple sclerosis medicine (Gilenya): EMA measures of 2019 on the risk of congenital malformations.", "https://www.ema.europa.eu/documents/press-release/updated-restrictions-gilenya-multiple-sclerosis-medicine-not-be-used-pregnancy_en.pdf", "known",
     {"EU / EEA": "Authorised; contraindicated in pregnancy and in women of childbearing potential not using effective contraception."}),
]
ok = 0
for name, cas, note, url, level, jur in MEDS:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36", "Accept": "text/html,*/*"}), timeout=30) as r: status = r.status
    except Exception as e:
        status = getattr(e, "code", str(e))
    ok += status == 200
    add("cas:" + cas, name=name, cas=cas, kind="medicine",
        source={"label": "EMA: pregnancy prevention programme or contraindication for teratogenicity", "code": "ema", "note": note, "url": url, "url_status": status},
        status={"ema": level}, jurisdictions=jur)
print(f"EMA medicines: {len(MEDS)} ({ok} pages answered 200)")

# ── D. Alcohol and tobacco ───────────────────────────────────────────────────
add("cas:64-17-5", name="Alcohol (ethanol) in beverages", cas="64-17-5", kind="product",
    source={"label": "WHO fact sheet on congenital disorders", "code": "who", "note": "WHO names alcohol among harmful substances to avoid in pregnancy; foetal alcohol spectrum disorders are a recognised consequence of prenatal exposure.", "url": "https://www.who.int/news-room/fact-sheets/detail/birth-defects"},
    status={"who": "known"},
    jurisdictions={"EU / EEA": "Legal; no EU-wide pregnancy warning is mandatory on labels (Regulation 1169/2011 exempts alcoholic beverages from ingredient and nutrition labelling).",
                   "France": "Legal; a pregnancy warning message or pictogram is mandatory on every alcoholic beverage (arrêté of 2 October 2006)."})
add("smoking", name="Tobacco smoking in pregnancy", cas="", kind="product",
    source={"label": "DysNet bibliography (peer-reviewed meta-analysis)", "code": "bib", "note": "Maternal smoking is associated with a higher risk of limb reduction defects in the pooled analysis of Hackshaw, Rodeck and Boniface (2011), among the references of the DysNet bibliography.", "url": "/knowledge/research-library/?q=smoking"},
    status={"bib": "suspected"},
    jurisdictions={"EU / EEA": "Legal; health warnings on packs are mandatory (Directive 2014/40/EU), including pregnancy-related warnings among the rotating texts."})

# ── Wikipedia links: CAS → Wikidata (P231) → English Wikipedia sitelink; exact-title fallback for entries without a CAS ──
import urllib.parse
WCACHE_PATH = HERE / "wikidata-cache.json"
WCACHE = json.loads(WCACHE_PATH.read_text(encoding="utf-8")) if WCACHE_PATH.exists() else {}
UAH = {"User-Agent": "DysNetTeratogensBot/1.0 (https://www.dysnet.org; info@dysnet.org)"}


def sparql(query):
    req = urllib.request.Request("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query), headers=dict(UAH, Accept="application/sparql-results+json"))
    with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)["results"]["bindings"]


cas_all = sorted({e["cas"] for e in entries.values() if e.get("cas") and ("cas:" + e["cas"]) not in WCACHE})
for i in range(0, len(cas_all), 150):
    chunk = cas_all[i:i + 150]
    values = " ".join(f'"{c}"' for c in chunk)
    try:
        rows = sparql(f"""SELECT ?cas ?article WHERE {{ VALUES ?cas {{ {values} }} ?item wdt:P231 ?cas . ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}""")
    except Exception as ex:
        print("  wikidata chunk failed:", ex); rows = []
    found = {}
    for r in rows: found.setdefault(r["cas"]["value"], r["article"]["value"])
    for c in chunk: WCACHE["cas:" + c] = found.get(c)
    import time; time.sleep(1)


def wiki_exact(title):
    key = "title:" + title
    if key in WCACHE: return WCACHE[key]
    try:
        req = urllib.request.Request("https://en.wikipedia.org/w/api.php?action=query&redirects=1&format=json&titles=" + urllib.parse.quote(title), headers=UAH)
        with urllib.request.urlopen(req, timeout=30) as r: pages = json.load(r)["query"]["pages"]
        page = next(iter(pages.values()))
        WCACHE[key] = None if "missing" in page else "https://en.wikipedia.org/wiki/" + page["title"].replace(" ", "_")
    except Exception:
        WCACHE[key] = None
    import time; time.sleep(0.3)
    return WCACHE[key]


def wikidata_by_name(name, cas):
    """Search Wikidata by label; accept an item only if its CAS (P231) equals ours; return its English Wikipedia link."""
    key = f"search:{name}|{cas}"
    if key in WCACHE: return WCACHE[key]
    url = None
    try:
        req = urllib.request.Request("https://www.wikidata.org/w/api.php?action=wbsearchentities&language=en&format=json&limit=5&search=" + urllib.parse.quote(name), headers=UAH)
        with urllib.request.urlopen(req, timeout=30) as r: hits = json.load(r).get("search", [])
        ids = [h["id"] for h in hits]
        if ids:
            req = urllib.request.Request("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims|sitelinks&sitefilter=enwiki&ids=" + "|".join(ids), headers=UAH)
            with urllib.request.urlopen(req, timeout=30) as r: ents = json.load(r).get("entities", {})
            for qid in ids:
                ent = ents.get(qid, {})
                cas_vals = [c["mainsnak"]["datavalue"]["value"] for c in ent.get("claims", {}).get("P231", []) if "datavalue" in c.get("mainsnak", {})]
                title = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
                if title and (cas in cas_vals if cas else False):
                    url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"); break
    except Exception:
        url = None
    WCACHE[key] = url
    import time; time.sleep(0.4)
    return url


n_wiki = 0
for e in entries.values():
    url = WCACHE.get("cas:" + e["cas"]) if e.get("cas") else None
    if not url:
        base = e["name"].split(";")[0].split(" (")[0].strip()
        url = wiki_exact(base) or wiki_exact(base.capitalize())
    if not url and e.get("cas"):
        base = e["name"].split(";")[0].split(" (")[0].strip()
        url = wikidata_by_name(base, e["cas"])
    e["wiki"] = url
    n_wiki += bool(url)
WCACHE_PATH.write_text(json.dumps(WCACHE, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"Wikipedia links: {n_wiki} of {len(entries)} entries")

# ── merge, classify, write ────────────────────────────────────────────────────
LEVEL_ORDER = {"known": 0, "presumed": 1, "suspected": 2}
out = []
for key, e in entries.items():
    levels = [v for v in e["status"].values() if v in LEVEL_ORDER]
    if "p65" in e["status"]: levels.append("known")
    e["level"] = min(levels, key=lambda l: LEVEL_ORDER[l]) if levels else "suspected"
    e["source_codes"] = sorted({s["code"] for s in e["sources"]})
    out.append(e)
out.sort(key=lambda e: (LEVEL_ORDER[e["level"]], e["name"].lower()))
result = {"built": datetime.date.today().isoformat(),
          "sources": {"clp": {"label": "EU harmonised classification (CLP Annex VI, ATP23, Delegated Regulation (EU) 2025/1222)", "url": "https://echa.europa.eu/information-on-chemicals/annex-vi-to-clp", "authority": "Binding EU regulation: classification and labelling are mandatory for substances and mixtures; harmonised entries adopted by Commission delegated acts after ECHA RAC opinions."},
                      "p65": {"label": "California Proposition 65 list, developmental toxicants", "url": "https://oehha.ca.gov/proposition-65/proposition-65-list", "authority": "Binding Californian law: warnings required before exposure; the list is revised at least once a year by OEHHA."},
                      "ema": {"label": "EMA pregnancy prevention programmes and contraindications", "url": "https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/pharmacovigilance-post-authorisation/referral-procedures-human-medicines", "authority": "Binding in the EU through marketing authorisations and referral decisions; the medicines stay authorised but with conditions."},
                      "who": {"label": "WHO fact sheet on congenital disorders", "url": "https://www.who.int/news-room/fact-sheets/detail/birth-defects", "authority": "Guidance, not binding; WHO keeps no list of teratogens."},
                      "bib": {"label": "DysNet bibliography (peer-reviewed literature)", "url": "/knowledge/research-library/", "authority": "Scientific evidence, no regulatory effect."}},
          "counts": {"total": len(out), "clp": n_clp, "p65": n_p65, "ema": len(MEDS), "both_clp_and_p65": sum(1 for e in out if "clp" in e["source_codes"] and "p65" in e["source_codes"])},
          "entries": out}
(HERE / "teratogens.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"total {len(out)} substances | in both EU and California lists: {result['counts']['both_clp_and_p65']} | levels: known {sum(1 for e in out if e['level']=='known')}, presumed {sum(1 for e in out if e['level']=='presumed')}, suspected {sum(1 for e in out if e['level']=='suspected')}")
