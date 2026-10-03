#!/usr/bin/env python3
"""The generic and brand names of every medicine in the teratogens register, from official registries,
so that a pharmacist, or a woman checking a box before she takes a medicine, finds the entry by the
name she has in front of her.

Sources, all public:
  - RxNorm, the US National Library of Medicine's drug nomenclature, through its RxNav API: the
    ingredient (IN), its precise forms and salts (PIN) and the brand names (BN) that contain it. RxNorm
    is also the nomenclature behind the coded medication items of the Health Data Safe data model
    (medication/coded-v1: RxNorm, SNOMED CT and ATC codes), so the register and the registry app
    name a drug the same way.
  - EMA, the medicines it authorises for the whole EU: its "medicines" data table (name of medicine,
    INN, active substance, status), reusable with acknowledgement.
  - Drugs@FDA, through openFDA (public domain): every US application with its products, brand names and
    marketing status, discontinued ones included, so a medicine withdrawn decades ago is still found by
    the brand a woman may have in an old cabinet or record.
  - Wikidata (CC0), matched on the RxNorm code (property P3345): the International Nonproprietary Name
    the WHO gives the substance (P2275), and the substance's name in French, German, Spanish, Italian,
    Dutch and Portuguese, so the register finds "Valproinsäure" or "ácido valproico" too.
  - ChEBI (EMBL-EBI, CC BY 4.0), through the ChEBI identifier Wikidata gives (P683): the INN in the
    languages ChEBI records it (Spanish, French, Latin), preferred to the Wikidata label in that language,
    and the English INN where Wikidata lacks it.
  - National registries matched on the substance's WHO ATC code, which RxNorm gives for each
    ingredient: AIFA, Italy (CC BY 4.0, the authorised packs with their ATC code); AEMPS CIMA, Spain
    (reuse with attribution to the Agencia Española de Medicamentos y Productos Sanitarios); Health
    Canada's Drug Product Database (Government of Canada terms, reuse with attribution).
  - ANSM, the French public medicines database (base de données publique des médicaments, Etalab 2.0
    open licence): the names of the medicines authorised in France that contain the substance.

Each register entry is resolved to its ingredients: a drug class (aminoglycosides, barbiturates,
benzodiazepines, tetracyclines, ACE inhibitors) to the members of its WHO ATC class as RxNorm lists
them; a combination (norethisterone with ethinyl estradiol) to the multi-ingredient concept; any other
entry to the ingredient its name gives. Raw downloads are cached in tools/terato/names (git-ignored).
Output: tools/teratogen-medicine-names.json. Run: python3 tools/build-teratogen-names.py
"""
import csv
import datetime
import io
import json
import pathlib
import re
import time
import unicodedata
import urllib.parse

from teratogen_names_util import skel
import urllib.request

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
INN_CHECKED = HERE / "teratogen-inn-checked.json"   # INNs checked by hand against the WHO list where Wikidata and ChEBI give none
OUT = HERE / "teratogen-medicine-names.json"
RAW = HERE / "terato" / "names"
UA = {"User-Agent": "DysNet teratogens register (info@dysnet.org)"}
RXNAV = "https://rxnav.nlm.nih.gov/REST/"
EMA_XLSX = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx"
ANSM = "https://base-donnees-publique.medicaments.gouv.fr/download/file/"
DRUGSFDA = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
WDQS = "https://query.wikidata.org/sparql"
CHEBI = "https://www.ebi.ac.uk/chebi/backend/api/public/compound/"
AIFA = "https://drive.aifa.gov.it/farmaci/confezioni_fornitura.csv"
CIMA = "https://cima.aemps.es/cima/rest/medicamentos"
DPD = "https://www.canada.ca/content/dam/hc-sc/documents/services/drug-product-database/allfiles.zip"
LANGS = ("fr", "de", "es", "it", "nl", "pt")

# register entries whose name is not an ingredient name RxNorm knows
OVERRIDES = {
    "Retinol/retinyl esters": ["vitamin A"],
    "Δ9-Tetrahydrocannabinol": ["dronabinol"],
    "All-trans retinoic acid": ["tretinoin"],
    "Actinomycin D": ["dactinomycin"],
    "Iodine-131": ["sodium iodide I-131"],
    "dinitrogen oxide": ["nitrous oxide"],
    "theophylline": ["theophylline"],
    "piperazine": ["piperazine"],
    "Nitrogen mustard": ["mechlorethamine"],
    "Mycophenolate mofetil and mycophenolic acid": ["mycophenolate mofetil", "mycophenolic acid"],
    "Aspirin": ["aspirin"],
    "1-(2-Chloroethyl)-3-cyclohexyl-1-nitrosourea": ["lomustine"],
    "Bischloroethyl nitrosourea": ["carmustine"],
    "1,4-Butanediol dimethanesulfonate": ["busulfan"],
    "Diphenylhydantoin": ["phenytoin"],
    "Doxorubicin hydrochloride": ["doxorubicin"],
    "Streptozocin": ["streptozocin"],
    "Uracil mustard": ["uracil mustard"],
    "Norethisterone (Norethindrone) /Ethinyl estradiol": ["ethinyl estradiol / norethindrone"],
    "Norethisterone (Norethindrone) /Mestranol": ["mestranol / norethindrone"],
    "Norethisterone acetate": ["norethindrone acetate"],
    "Norethisterone (Norethindrone)": ["norethindrone"],
    "Conjugated estrogens": ["estrogens, conjugated (USP)"],
    "Menotropins": ["menotropins"],
    "Urofollitropin": ["urofollitropin"],
    "Valproate": ["valproate", "valproic acid"],
}
# WHO ATC codes RxNorm does not attach to the ingredient an entry resolves to (lithium salts: N05AN01 lithium)
ATC_OVERRIDES = {"Lithium carbonate": ["N05AN01"], "Lithium citrate": ["N05AN01"]}
# ATC groups of medicines applied locally: stomatological, dermatological, eye and ear, gynaecological anti-infectives, nose and throat
LOCAL_ATC = ("A01", "D", "S", "G01", "R01", "R02")
# drug classes: the members of the WHO ATC classes, as RxNorm's RxClass lists them
GROUPS = {
    "Aminoglycosides": ["J01GA", "J01GB"],
    "Barbiturates": ["N03AA", "N05CA"],
    "Benzodiazepines": ["N05BA", "N05CD", "N03AE"],
    "Tetracyclines (internal use)": ["J01AA"],
    "Angiotensin converting enzyme": ["C09AA"],
}
# where the French name of a substance does not share the English root
FR_ALIASES = {"aspirin": ["acide acetylsalicylique"], "nitrous oxide": ["protoxyde d azote"],
              "norethindrone": ["norethisterone"], "norethindrone acetate": ["norethisterone acetate"],
              "ethinyl estradiol": ["ethinylestradiol"], "mechlorethamine": ["chlormethine"],
              "estrogens, conjugated (USP)": ["estrogenes conjugues"], "dronabinol": ["dronabinol"],
              "sodium iodide I-131": ["iodure 131i de sodium", "iodure de sodium 131i"]}
SALT = re.compile(r"\b(hydrochloride|sulfate|sulphate|sodium|acetate|citrate|phosphate|mesylate|tartrate|propionate|dipropionate|cypionate|enanthate|hyclate|monohydrate|calcium|dipotassium|glucuronate|anhydrous|hydrated)\b", re.I)


def get(url, cache=None, binary=False):
    if cache and cache.exists():
        return cache.read_bytes() if binary else cache.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(data)
    time.sleep(0.12)
    return data if binary else data.decode("utf-8")


def rx(path):
    key = re.sub(r"[^A-Za-z0-9]+", "_", path)[:150]
    return json.loads(get(RXNAV + path, RAW / "rxnav" / f"{key}.json"))


def rxcui(name):
    ids = rx(f"rxcui.json?name={urllib.parse.quote(name)}&search=2").get("idGroup", {}).get("rxnormId") or []
    return ids[0] if ids else None


def related(cui, ttys):
    out = {}
    for g in rx(f"rxcui/{cui}/related.json?tty={'+'.join(ttys)}").get("relatedGroup", {}).get("conceptGroup", []):
        out[g["tty"]] = [(c["rxcui"], c["name"]) for c in g.get("conceptProperties", [])]
    return out


def tty(cui):
    return rx(f"rxcui/{cui}/properties.json").get("properties", {}).get("tty")


def class_members(code):
    d = rx(f"rxclass/classMembers.json?classId={code}&relaSource=ATC&ttys=IN")
    return [(m["minConcept"]["rxcui"], m["minConcept"]["name"]) for m in d.get("drugMemberGroup", {}).get("drugMember", [])]


def candidates(name):
    for k, v in OVERRIDES.items():
        if name.startswith(k):
            return v
    n = re.sub(r"\[.*?\]|\(NOTE.*$|\(internal use\)|\(endothelin receptor antagonist\)|;.*$", "", name).strip()
    alts = re.findall(r"\(([^()]+)\)", n) + [re.sub(r"\(.*?\)", "", n).strip()]
    out = []
    for a in alts:
        for c in (a, SALT.sub("", a).strip(" ,")):
            if c and c.lower() not in [o.lower() for o in out]:
                out.append(c)
    return out


def resolve_one(c):
    cui = rxcui(c)
    if not cui:
        return []
    t = tty(cui)
    if t in ("IN", "MIN"):
        return [(cui, rx(f"rxcui/{cui}/properties.json")["properties"]["name"])]
    if t == "PIN":
        return related(cui, ["IN"]).get("IN", [])
    return []


def resolve(name):
    """The RxNorm ingredients (IN or MIN) an entry stands for."""
    for k, v in OVERRIDES.items():
        if name.startswith(k) and len(v) > 1:
            ins = []
            for c in v:
                ins += resolve_one(c)
            return list(dict.fromkeys(ins)), "RxNorm " + " + ".join(v)
    for k, codes in GROUPS.items():
        if name.startswith(k):
            members = []
            for c in codes:
                members += class_members(c)
            return list(dict.fromkeys(members)), "class " + ", ".join(codes)
    for c in candidates(name):
        cui = rxcui(c)
        if not cui:
            continue
        t = tty(cui)
        if t in ("IN", "MIN"):
            return [(cui, rx(f"rxcui/{cui}/properties.json")["properties"]["name"])], "RxNorm " + t
        if t == "PIN":
            ins = related(cui, ["IN"]).get("IN", [])
            if ins:
                return ins, "RxNorm PIN of " + ", ".join(n for _c, n in ins)
    return [], "not found in RxNorm"


def wikidata(cuis):
    """INN (P2275), ChEBI identifier (P683) and labels in LANGS of the Wikidata items that carry these
    RxNorm codes (cuis: code -> RxNorm name). Where two items carry one code, only the item whose English
    label is the RxNorm name is kept, so a mis-attached code cannot lend one substance another's names."""
    def ask(q, cache):
        body = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
        p = RAW / cache
        if not p.exists():
            req = urllib.request.Request(WDQS, data=body, headers={**UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                p.write_bytes(r.read())
        return json.loads(p.read_text(encoding="utf-8"))["results"]["bindings"]
    vals = " ".join(f'"{c}"' for c in sorted(cuis))
    items = {}   # (cui, item) -> {"inn", "chebi", "en", and LANGS}
    def it(b):
        return items.setdefault((b["cui"]["value"], b["item"]["value"].rsplit("/", 1)[-1]), {"inn": set(), "chebi": set(), "en": set(), **{l: set() for l in LANGS}})
    for b in ask('SELECT ?item ?cui ?chebi WHERE { VALUES ?cui { %s } ?item wdt:P3345 ?cui . ?item wdt:P683 ?chebi }' % vals, "wikidata-chebi-items.json"):
        it(b)["chebi"].add(b["chebi"]["value"])
    for b in ask('SELECT ?item ?cui ?inn WHERE { VALUES ?cui { %s } ?item wdt:P3345 ?cui . OPTIONAL { ?item wdt:P2275 ?inn . FILTER(LANG(?inn) = "en") } }' % vals, "wikidata-inn-en.json"):
        if "inn" in b:
            it(b)["inn"].add(b["inn"]["value"])
        else:
            it(b)
    langs = ", ".join(f'"{l}"' for l in LANGS + ("en",))
    for b in ask('SELECT ?item ?cui ?lab (LANG(?lab) AS ?lang) WHERE { VALUES ?cui { %s } ?item wdt:P3345 ?cui . ?item rdfs:label ?lab . FILTER(LANG(?lab) IN (%s)) }' % (vals, langs), "wikidata-labels-items.json"):
        it(b)[b["lang"]["value"]].add(b["lab"]["value"])
    out = {c: {"inn": set(), "item": set(), "chebi": set(), "inn_lang": {}, **{l: set() for l in LANGS}} for c in cuis}
    for c in cuis:
        mine = {q: v for (cc, q), v in items.items() if cc == c}
        if len(mine) > 1:
            same = {q: v for q, v in mine.items() if any(skel(x) == skel(cuis[c]) for x in v["en"] | v["inn"])}
            mine = same or {}
        for q, v in mine.items():
            o = out[c]
            o["item"].add(q)
            o["inn"] |= v["inn"]
            o["chebi"] |= v["chebi"]
            for l in LANGS:
                o[l] |= v[l]
    # ChEBI (EBI, CC BY 4.0) records the WHO INN as a name of type INN, often in Spanish, French and Latin;
    # where Wikidata lacks the English INN, ChEBI's own name is taken as it when ChEBI records an INN for the substance
    for c, o in out.items():
        for ch in sorted(o["chebi"]):
            d = json.loads(get(CHEBI + ch + "/", RAW / "chebi" / f"{ch}.json"))
            inns = (d.get("names") or {}).get("INN", [])
            for x in inns:
                o["inn_lang"].setdefault(x["language_code"], set()).add(x["name"])
            if inns and not o["inn"]:
                en = [x["name"] for x in inns if x["language_code"] == "en"]
                o["inn"] |= set(en) or {d["name"]}
    return out


def codes(cui):
    """The WHO ATC and SNOMED CT codes RxNorm gives an ingredient."""
    out = {"ATC": [], "SNOMEDCT": []}
    for p in rx(f"rxcui/{cui}/allProperties.json?prop=codes").get("propConceptGroup", {}).get("propConcept", []):
        if p["propName"] in out:
            out[p["propName"]].append(p["propValue"])
    return out


def brand(name):
    """A product name without its strength and form: what is printed large on the box."""
    return re.split(r"\s\S*\d|,", name.strip())[0].strip()


def aifa():
    """Italy: ATC code -> names of the authorised medicines."""
    out = {}
    for r in csv.DictReader(io.StringIO(get(AIFA, RAW / "aifa.csv", binary=True).decode("utf-8", "replace")), delimiter=";"):
        if r["STATO_AMMINISTRATIVO"] in ("Autorizzata", "Sospesa") and r["CODICE_ATC"]:
            out.setdefault(r["CODICE_ATC"].strip(), set()).add(r["DENOMINAZIONE"].strip())
    return out


def cima(atc):
    """Spain: names of the medicines CIMA lists under an ATC code, revoked ones left out."""
    names, page = set(), 1
    while True:
        d = json.loads(get(f"{CIMA}?atc={atc}&pagina={page}", RAW / "cima" / f"{atc}-{page}.json"))
        for r in d.get("resultados", []):
            if "rev" not in (r.get("estado") or {}):
                names.add(brand(r["nombre"]))
        if page * d.get("tamanioPagina", 200) >= d.get("totalFilas", 0):
            return names
        page += 1


def dpd():
    """Canada: ATC code -> brand names of the products marketed, approved or dormant."""
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(get(DPD, RAW / "dpd.zip", binary=True)))
    rd = lambda f: csv.reader(io.TextIOWrapper(z.open(f), encoding="latin-1"))
    live = {r[0] for r in rd("status.txt") if r[1] == "Y" and r[2] in ("MARKETED", "APPROVED", "DORMANT")}
    names = {r[0]: r[4].strip() for r in rd("drug.txt") if r[2] == "Human"}
    out = {}
    for r in rd("ther.txt"):
        if r[0] in live and r[0] in names and r[1]:
            out.setdefault(r[1].strip(), set()).add(brand(names[r[0]].split(" - ")[0]))
    return out


def drugsfda():
    """Drugs@FDA products, keyed by their active ingredients without salts: brand name and marketing status."""
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(get(DRUGSFDA, RAW / "drugsfda.json.zip", binary=True)))
    idx = {}
    for a in json.load(z.open(z.namelist()[0]))["results"]:
        for p in a.get("products", []):
            key = tuple(sorted({norm(SALT.sub("", i.get("name") or "")) for i in p.get("active_ingredients", [])}))
            if key and p.get("brand_name"):
                idx.setdefault(key, []).append((p["brand_name"].strip(), p.get("marketing_status", "")))
    return idx


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def stem_match(english, french):
    """Every significant word of the English name has a counterpart in the French one (shared INN roots)."""
    words = [w for w in norm(english).split() if len(w) > 3 and w not in ("acid", "sodium")]
    fr = norm(french).split()
    return bool(words) and all(any(f.startswith(w[:min(len(w), 7)]) for f in fr) for w in words)


def main():
    data = json.loads(TERA.read_text(encoding="utf-8"))
    meds = [e for e in data["entries"] if any(r["tag"] == "medicine" for r in e.get("exposure", []))]
    # EMA, centrally authorised medicines
    import openpyxl
    xb = get(EMA_XLSX, RAW / "ema-medicines.xlsx", binary=True)
    ws = openpyxl.load_workbook(io.BytesIO(xb), read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r and r[0] == "Category")
    H = {h: i for i, h in enumerate(rows[hdr]) if h}
    ema = [r for r in rows[hdr + 1:] if r and r[H["Category"]] == "Human"]
    INN_COL = next(h for h in H if h.startswith("International non-proprietary name"))
    # ANSM, medicines authorised in France
    spec = get(ANSM + "CIS_bdpm.txt", RAW / "CIS_bdpm.txt", binary=True).decode("latin-1")
    compo = get(ANSM + "CIS_COMPO_bdpm.txt", RAW / "CIS_COMPO_bdpm.txt", binary=True).decode("latin-1")
    cis_name = {}
    for line in spec.splitlines():
        f = line.split("\t")
        if len(f) > 4:
            cis_name[f[0]] = (f[1].strip(), f[4].strip())
    subst = {}
    for line in compo.splitlines():
        f = line.split("\t")
        if len(f) > 3:
            subst.setdefault(f[3].strip(), set()).add(f[0])
    fda = drugsfda()
    italy, canada = aifa(), dpd()
    resolved = {e["name"]: resolve(e["name"]) for e in meds}
    # the salt and acid forms (RxNorm PIN) too: where an ingredient has no Wikidata item, its acid form may
    pin_of = {c: related(c, ["PIN"]).get("PIN", []) for ins, _h in resolved.values() for c, _n in ins}
    wd = wikidata({**{pc: pn for v in pin_of.values() for pc, pn in v}, **{c: n for ins, _h in resolved.values() for c, n in ins}})
    checked = json.loads(INN_CHECKED.read_text(encoding="utf-8"))["entries"] if INN_CHECKED.exists() else {}
    out = {}
    for e in meds:
        ins, how = resolved[e["name"]]
        generic, brands, pins = [], [], []
        for cui, n in ins:
            generic.append(n)
            rel = related(cui, ["BN", "PIN"])
            generic += [p for _c, p in rel.get("PIN", [])]
            pins += [c for c, _p in rel.get("PIN", [])]
            brands += [b for _c, b in rel.get("BN", [])]
            for pcui, _p in rel.get("PIN", []):
                brands += [b for _c, b in related(pcui, ["BN"]).get("BN", [])]
        generic = sorted(set(generic), key=str.lower)
        us = sorted(set(brands), key=str.lower)
        # Drugs@FDA: brands RxNorm no longer carries, marketed or discontinued (a brand that is just the generic name is skipped)
        keys = set()
        for _c, n in ins:
            parts = [x.strip() for x in n.split(" / ")]
            keys.add(tuple(sorted(norm(SALT.sub("", x)) for x in parts)))
        for g in generic:
            if " / " not in g:
                keys.add((norm(SALT.sub("", g)),))
        gen_words = {w for k in keys for x in k for w in x.split()}
        fda_status = {}
        for k in keys:
            for b, st in fda.get(k, []):
                if set(norm(SALT.sub("", b)).split()) <= gen_words | {"and", "in", "with", "plus"}:
                    continue
                fda_status.setdefault(b.title() if b.isupper() else b, set()).add(st)
        have = {b.lower() for b in us}
        us_disc = sorted((b for b, st in fda_status.items() if st == {"Discontinued"} and b.lower() not in have), key=str.lower)
        us = sorted(set(us) | {b for b, st in fda_status.items() if st - {"Discontinued", "None (Tentative Approval)"} and b.lower() not in have}, key=str.lower)
        cds = [codes(c) for c, _n in ins] + [codes(c) for c in pins]
        atc = sorted({a for x in cds for a in x["ATC"]} | set(e.get("atc") or []) | set(next((v for k, v in ATC_OVERRIDES.items() if e["name"].startswith(k)), [])))
        snomed = sorted({a for x in cds for a in x["SNOMEDCT"]})
        if "internal use" in e["name"] or any(e["name"].startswith(k) for k in GROUPS):
            # the entry is the medicine taken by mouth or injection: leave out mouth, skin, eye, ear and vaginal forms
            atc = [a for a in atc if not a.startswith(LOCAL_ATC)]
        it = sorted({b for a in atc for b in italy.get(a, ())}, key=str.lower)
        es = sorted({b for a in atc for b in cima(a)}, key=str.lower)
        ca = sorted({b for a in atc for b in canada.get(a, ())}, key=str.lower)
        inn_names = sorted({x for c, _n in ins for x in wd.get(c, {}).get("inn", ())}, key=str.lower)
        chk = next((v for k, v in checked.items() if e["name"].startswith(k)), None)
        inn_note = {}
        if chk:
            inn_names = chk["inn"] if chk["status"] == "INN" else []
            inn_note = {"status": chk["status"], "source": chk["source"], "url": chk["url"]}
        # an ingredient without a Wikidata item borrows the names of its form that bears the INN (valproate: valproic acid)
        wd_src = []
        for c, n in ins:
            if wd.get(c, {}).get("item"):
                wd_src.append(c)
            else:
                keys = {skel(x) for x in inn_names or [n]}
                wd_src += [pc for pc, pn in pin_of.get(c, []) if skel(pn) in keys and wd.get(pc, {}).get("item")]
        langs = {l: sorted({x for c in wd_src for x in (wd.get(c, {}).get("inn_lang", {}).get(l) or wd.get(c, {}).get(l, ()))}, key=str.lower) for l in LANGS + ("la",)}
        if chk:
            for l in ("fr", "es", "la"):
                v = re.sub(r"\s*\(.*?\)$", "", chk.get(l) or "").strip()
                if v and v not in langs.get(l, []):
                    langs[l] = sorted(set(langs.get(l, [])) | {v}, key=str.lower)
        eu = []
        for r in ema:
            inn = " ".join(str(r[H[k]] or "") for k in (INN_COL, "Active substance"))
            if any(re.search(r"\b" + re.escape(g.lower()) + r"\b", inn.lower()) for g in generic):
                eu.append({"name": r[H["Name of medicine"]], "status": r[H["Medicine status"]], "url": r[H["Medicine URL"]] if "Medicine URL" in H else ""})
        # a French substance is this one when its whole name, salts aside, is the same in any spelling
        # (strict: "hydroxycarbamide" is hydroxyurea's INN; "hydroxychloroquine" is another medicine)
        ft = {}
        def fr_terms(n):
            if n in ft:
                return ft[n]
            cuis = [c for c, nn in ins if nn == n]
            extra = [x for c in cuis for x in list(wd.get(c, {}).get("inn", ())) + list(wd.get(c, {}).get("fr", ())) + list(wd.get(c, {}).get("inn_lang", {}).get("fr", ()))]
            pin_names = [p for c in cuis for _pc, p in related(c, ["PIN"]).get("PIN", [])]
            ft[n] = {skel(t) for t in FR_ALIASES.get(n, []) + [n] + extra + pin_names} - {""}
            return ft[n]
        def fr_match(n, s):
            return skel(s) in fr_terms(n)
        fr_subst = sorted(s for s in subst if any(fr_match(n, s) for _c, n in ins if " / " not in n)
                          and "homeopath" not in norm(s))
        # a combination: the French products that contain every one of its ingredients
        combo_cis = set()
        for _c, n in ins:
            if " / " in n:
                parts = [x.strip() for x in n.split(" / ")]
                sets = [set().union(*[subst[s] for s in subst if fr_match(pt, s) and "homeopath" not in norm(s)] or [set()]) for pt in parts]
                combo_cis |= set.intersection(*sets) if sets else set()
        if "131" in e["name"]:
            fr_subst = [s for s in fr_subst if "131" in s]
        if any(n.lower() == "vitamin a" for _c, n in ins):
            fr_subst = [s for s in fr_subst if re.search(r"\bvitamine a\b", norm(s))]
        fr = set()
        for cis in sorted(combo_cis):
            name, status = cis_name.get(cis, ("", ""))
            if name and "abrog" not in status.lower():
                fr.add(re.split(r"\s\d|,", name)[0].strip())
        for s in fr_subst:
            for cis in subst[s]:
                name, status = cis_name.get(cis, ("", ""))
                if name and "abrog" not in status.lower() and "homéo" not in status.lower() and "homeo" not in norm(status):
                    fr.add(re.split(r"\s\d|,", name)[0].strip())
        if e["name"].startswith("Retinol/retinyl esters"):
            us, us_disc, eu, fr, it, es, ca = [], [], [], set(), [], [], []
            note = "Brand names are not listed: vitamin A is in many multivitamins and prenatal vitamins, and California lists it only above 10,000 IU a day."
        else:
            note = ""
        out[e["name"]] = {
            "note": note,
            "resolved_as": how, "ingredients": [{"rxcui": c, "name": n} for c, n in ins], "generic": generic,
            "inn": inn_names, "inn_checked": inn_note, "wikidata": sorted({x for c in wd_src for x in wd.get(c, {}).get("item", ())}), "languages": langs,
            "brands_us": us, "brands_us_discontinued": us_disc, "brands_eu": sorted({x["name"] for x in eu}, key=str.lower),
            "brands_eu_status": {x["name"]: x["status"] for x in eu},
            "brands_eu_url": {x["name"]: x["url"] for x in eu if x.get("url")},
            "substances_fr": fr_subst, "brands_fr": sorted(fr, key=str.lower),
            "atc": atc, "snomed": snomed, "brands_it": it, "brands_es": es, "brands_ca": ca,
        }
        print(f'{e["name"][:44]:45} {how[:30]:31} inn {len(inn_names):2} gen {len(generic):3} us {len(us):3}+{len(us_disc):2} eu {len(eu):3} fr {len(fr):3} it {len(it):3} es {len(es):3} ca {len(ca):3}')
    OUT.write_text(json.dumps({"read": datetime.date.today().isoformat(),
                               "sources": {"rxnorm": "https://www.nlm.nih.gov/research/umls/rxnorm/", "ema": "https://www.ema.europa.eu/en/medicines/download-medicine-data",
                                           "ansm": "https://base-donnees-publique.medicaments.gouv.fr/", "drugsfda": "https://open.fda.gov/data/drugsfda/",
                                           "wikidata": "https://www.wikidata.org/wiki/Property:P2275", "chebi": "https://www.ebi.ac.uk/chebi/",
                                           "aifa": "https://www.aifa.gov.it/open-data", "cima": "https://cima.aemps.es/",
                                           "dpd": "https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/drug-product-database.html"},
                               "entries": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out)} medicine entries; {sum(1 for v in out.values() if v['ingredients'])} resolved in RxNorm")


if __name__ == "__main__":
    main()
