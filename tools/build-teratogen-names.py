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
import urllib.request

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
OUT = HERE / "teratogen-medicine-names.json"
RAW = HERE / "terato" / "names"
UA = {"User-Agent": "DysNet teratogens register (info@dysnet.org)"}
RXNAV = "https://rxnav.nlm.nih.gov/REST/"
EMA_XLSX = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx"
ANSM = "https://base-donnees-publique.medicaments.gouv.fr/download/file/"

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
    "Valproate": ["valproate"],
}
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
    out = {}
    for e in meds:
        ins, how = resolve(e["name"])
        generic, brands = [], []
        for cui, n in ins:
            generic.append(n)
            rel = related(cui, ["BN", "PIN"])
            generic += [p for _c, p in rel.get("PIN", [])]
            brands += [b for _c, b in rel.get("BN", [])]
            for pcui, _p in rel.get("PIN", []):
                brands += [b for _c, b in related(pcui, ["BN"]).get("BN", [])]
        generic = sorted(set(generic), key=str.lower)
        us = sorted(set(brands), key=str.lower)
        eu = []
        for r in ema:
            inn = " ".join(str(r[H[k]] or "") for k in (INN_COL, "Active substance"))
            if any(re.search(r"\b" + re.escape(g.lower()) + r"\b", inn.lower()) for g in generic):
                eu.append({"name": r[H["Name of medicine"]], "status": r[H["Medicine status"]], "url": r[H["Medicine URL"]] if "Medicine URL" in H else ""})
        def fr_terms(n):
            return FR_ALIASES.get(n, [n])
        def fr_match(n, s):
            return any(stem_match(t, s) for t in fr_terms(n))
        fr_subst = sorted(s for s in subst if any(fr_match(n, s) for _c, n in ins if " / " not in n)
                          and "homeopath" not in norm(s))
        # a combination: the French products that contain every one of its ingredients
        combo_cis = set()
        for _c, n in ins:
            if " / " in n:
                parts = [x.strip() for x in n.split(" / ")]
                sets = [set().union(*[subst[s] for s in subst if fr_match(pt, s) and "homeopath" not in norm(s)] or [set()]) for pt in parts]
                combo_cis |= set.intersection(*sets) if sets else set()
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
            us, eu, fr = [], [], set()
            note = "Brand names are not listed: vitamin A is in many multivitamins and prenatal vitamins, and California lists it only above 10,000 IU a day."
        else:
            note = ""
        out[e["name"]] = {
            "note": note,
            "resolved_as": how, "ingredients": [{"rxcui": c, "name": n} for c, n in ins], "generic": generic,
            "brands_us": us, "brands_eu": sorted({x["name"] for x in eu}, key=str.lower),
            "brands_eu_status": {x["name"]: x["status"] for x in eu},
            "brands_eu_url": {x["name"]: x["url"] for x in eu if x.get("url")},
            "substances_fr": fr_subst, "brands_fr": sorted(fr, key=str.lower),
        }
        print(f'{e["name"][:44]:45} {how[:30]:31} gen {len(generic):3} us {len(us):3} eu {len(eu):3} fr {len(fr):3}')
    OUT.write_text(json.dumps({"read": datetime.date.today().isoformat(),
                               "sources": {"rxnorm": "https://www.nlm.nih.gov/research/umls/rxnorm/", "ema": "https://www.ema.europa.eu/en/medicines/download-medicine-data",
                                           "ansm": "https://base-donnees-publique.medicaments.gouv.fr/"},
                               "entries": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out)} medicine entries; {sum(1 for v in out.values() if v['ingredients'])} resolved in RxNorm")


if __name__ == "__main__":
    main()
