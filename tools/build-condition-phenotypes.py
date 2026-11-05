#!/usr/bin/env python3
"""The clinical features and the functional consequences Orphanet records for each condition on the site.

Sources, both Orphadata (Orphanet's scientific knowledge base), licence CC BY 4.0:
  - Clinical signs and symptoms in rare diseases (product 4, en_product4.xml): for each disorder, the
    features coded in the Human Phenotype Ontology (HPO), each with its frequency (obligate, very
    frequent, frequent, occasional, very rare, excluded) and whether it is a diagnostic criterion.
  - Rare diseases and functional consequences (en_funct_consequences.xml): the activity limitations and
    participation restrictions of the Orphanet Functioning Thesaurus, built on the WHO's ICF, each with
    its frequency, severity and temporality.
And the HPO itself (hp.obo), for each term's plain-language synonym ("layperson" in HPO) and the body
systems it belongs to, so the finder can group features as a family would look for them.

Kept: every ORPHAcode the site's cards stand for (the card's code, the forms Orphanet files under it, and
the code a codeless card answers to). Raw files are cached in tools/orphadata-raw (git-ignored).
Output: tools/condition-phenotypes.json. Run: python3 tools/build-condition-phenotypes.py
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
RAW = HERE / "orphadata-raw"
OUT = HERE / "condition-phenotypes.json"
sys.path.insert(0, str(HERE))
import conditions as C  # noqa: E402

FILES = {"product4": "https://www.orphadata.com/data/xml/en_product4.xml",
         "functional": "https://www.orphadata.com/data/xml/en_funct_consequences.xml",
         "hpo": "http://purl.obolibrary.org/obo/hp.obo"}
# the frequency labels in Orphanet's order, most to least frequent
FREQ_ORDER = ["Obligate (100%)", "Very frequent (99-80%)", "Frequent (79-30%)", "Occasional (29-5%)",
              "Very rare (<4-1%)", "Excluded (0%)"]
# HPO's body systems (children of HP:0000118 Phenotypic abnormality), named as a family would
SYSTEMS = {"HP:0040064": "Limbs", "HP:0000924": "Skeleton", "HP:0001626": "Heart and blood vessels",
           "HP:0000152": "Head and neck", "HP:0000478": "Eyes", "HP:0000598": "Ears",
           "HP:0000707": "Brain and nerves", "HP:0000119": "Kidneys, bladder and genitals",
           "HP:0025031": "Digestive system", "HP:0001574": "Skin, hair and nails", "HP:0001871": "Blood",
           "HP:0002715": "Immune system", "HP:0001507": "Growth", "HP:0003011": "Muscles",
           "HP:0000818": "Hormones", "HP:0002086": "Breathing", "HP:0001939": "Metabolism",
           "HP:0001197": "Pregnancy and birth", "HP:0000769": "Breast", "HP:0001608": "Voice",
           "HP:0025142": "General", "HP:0033127": "Bones, joints and muscles", "HP:0002664": "Tumours", "HP:0025354": "Cells", "HP:0045027": "Chest", "HP:0040047": "Whole body"}
SYSTEM_PRIORITY = ["HP:0040064", "HP:0033127", "HP:0000924"]   # a limb feature is filed under Limbs first

# Revisions Orphanet has told us about before they reach Orphadata. Each says what changed and on whose word;
# the build applies it only while the downloaded file still disagrees, says so when Orphadata has caught up,
# and the entry must then go. A sign added without a frequency is filed under PENDING_FREQ; one whose name
# matches no HPO term is kept, in Orphanet's own words, under "named".
PENDING_FREQ = "Frequency to be published by Orphanet"
PENDING = {
    # Orphanet's clinical-signs team, email to Loïc Rigal received 5 November 2026 (working folder,
    # correspondence/261105 Orphanet - ORPHA 2440 clinical signs revision.md), citing PMIDs 24163146,
    # 24115638, 20556892, 21088720, 40964825 and 37628577.
    "2440": {
        "note": "Includes the revision Orphanet made in November 2026, ahead of its next data release: split hand is now frequent, aniridia (a sign of the syndromic forms) is removed, and four signs are added.",
        "frequency": {"HP:0001171": "Frequent (79-30%)"},   # Split hand, was occasional
        "remove": ["HP:0000526"],                            # Aniridia
        "add": ["HP:0010760", "HP:0001770"],                 # Absent toe, Toe syndactyly
        "named": ["Aplasia/hypoplasia of fingers and toes", "Thumb duplication"],   # no exact HPO term; codes asked of Orphanet
    },
}


def apply_pending(code, rows):
    """Orphanet's announced revision of a code, applied to its Orphadata rows while they still disagree."""
    p = PENDING.get(code)
    if not p:
        return rows, None
    have = {r[0]: r[1] for r in rows}
    caught_up = (all(have.get(hp) == fr for hp, fr in p["frequency"].items())
                 and not any(hp in have for hp in p["remove"]) and all(hp in have for hp in p["add"]))
    if caught_up:
        print(f"ORPHA:{code}: Orphadata now carries Orphanet's revision; remove its PENDING entry")
        return rows, None
    rows = [[hp, p["frequency"].get(hp, fr), dg] for hp, fr, dg in rows if hp not in p["remove"]]
    rows += [[hp, PENDING_FREQ, 0] for hp in p["add"] if hp not in {r[0] for r in rows}]
    return rows, {"note": p["note"], "named": p["named"]}


def raw(name):
    p = RAW / FILES[name].rsplit("/", 1)[-1]
    if not p.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        p.write_bytes(urllib.request.urlopen(urllib.request.Request(FILES[name], headers={"User-Agent": "DysNet conditions"}), timeout=300).read())
    return p


def hpo():
    """Each term: name, plain-language synonym, parents; and the release."""
    terms, cur, version = {}, None, ""
    for line in raw("hpo").read_text(encoding="utf-8").splitlines():
        if line.startswith("data-version:"):
            version = line.split(":", 1)[1].strip()
        if line == "[Term]":
            cur = {"is_a": [], "lay": [], "alt": []}
        elif line.startswith("[") and line != "[Term]":
            cur = None
        elif cur is not None and line.startswith("id: "):
            terms[line[4:]] = cur
        elif cur is not None and line.startswith("name: "):
            cur["name"] = line[6:]
        elif cur is not None and line.startswith("alt_id: "):
            cur["alt"].append(line[8:])
        elif cur is not None and line.startswith("is_a: "):
            cur["is_a"].append(line[6:16])
        elif cur is not None and line.startswith("synonym: ") and " layperson " in line:
            cur["lay"].append(re.match(r'synonym: "(.*?)"', line).group(1))
    alt = {a: t for t, v in terms.items() for a in v["alt"]}
    return terms, alt, version


def systems_of(term, terms, memo={}):
    """The body systems (direct children of HP:0000118) a term falls under."""
    if term in memo:
        return memo[term]
    out, seen, stack = set(), set(), [term]
    while stack:
        t = stack.pop()
        if t in seen:
            continue
        seen.add(t)
        for p in terms.get(t, {}).get("is_a", []):
            if p == "HP:0000118":
                out.add(t)
            else:
                stack.append(p)
    memo[term] = sorted(out, key=lambda s: (SYSTEM_PRIORITY.index(s) if s in SYSTEM_PRIORITY else 9, SYSTEMS.get(s, s)))
    return memo[term]


def main():
    ref = C.reference()
    hier = json.loads((HERE / "orphanet-hierarchy.json").read_text(encoding="utf-8"))
    codes = set()
    for e in ref["conditions"] + ref.get("registryOnly", []):
        if e.get("orphaCode"):
            codes.add(str(e["orphaCode"]))
            codes |= set(hier["conditions"].get(str(e["orphaCode"]), {}).get("descendants", []))
    codes |= set(ref.get("forms", {}).keys())
    codes |= {str(c) for c, _name in C.extra_codes()}   # codeless cards answer to these (symbrachydactyly: 1570)

    terms, alt, version = hpo()
    out_codes, used = {}, set()
    root = ET.parse(raw("product4")).getroot()
    p4date = root.get("date", "")[:10]
    for st in root.iter("HPODisorderSetStatus"):
        d = st.find("Disorder")
        code = d.findtext("OrphaCode")
        if code not in codes:
            continue
        rows = []
        for a in d.iter("HPODisorderAssociation"):
            hid = a.findtext("HPO/HPOId")
            hid = alt.get(hid, hid)
            rows.append([hid, a.findtext("HPOFrequency/Name") or "", 1 if a.find("DiagnosticCriteria") is not None and (a.findtext("DiagnosticCriteria/Name") or "") else 0])
        rows, pending = apply_pending(code, rows)
        used.update(r[0] for r in rows)
        rows.sort(key=lambda r: (FREQ_ORDER.index(r[1]) if r[1] in FREQ_ORDER else 9, terms.get(r[0], {}).get("name", r[0])))
        out_codes.setdefault(code, {})["name"] = d.findtext("Name")
        out_codes[code]["hpo"] = rows
        out_codes[code]["hpo_source"] = st.findtext("Source") or ""
        if pending:
            out_codes[code]["pending"] = pending
    root = ET.parse(raw("functional")).getroot()
    fdate = root.get("date", "")[:10]
    for st in root.iter("DisorderDisabilityRelevance"):
        d = st.find("Disorder")
        code = d.findtext("OrphaCode")
        if code not in codes:
            continue
        by = {}
        for a in d.iter("DisabilityDisorderAssociation"):
            name = a.findtext("Disability/Name")
            by.setdefault(name, []).append([a.findtext("FrequenceDisability/Name") or "", a.findtext("SeverityDisability/Name") or "",
                                            a.findtext("TemporalityDisability/Name") or ""])
        if by:
            out_codes.setdefault(code, {})["name"] = d.findtext("Name")
            out_codes[code]["functional"] = [[k, v] for k, v in sorted(by.items())]
    term_out = {}
    for t in sorted(used):
        v = terms.get(t, {})
        lay = next((x for x in v.get("lay", []) if x.lower() != v.get("name", "").lower()), "")
        term_out[t] = {"name": v.get("name", t), "lay": lay, "systems": [SYSTEMS.get(s, terms.get(s, {}).get("name", s)) for s in systems_of(t, terms)]}
    OUT.write_text(json.dumps({
        "source": {"label": "Orphadata, Orphanet's scientific knowledge base", "url": "https://sciences.orphadata.com/orphanet-scientific-knowledge-files/",
                   "licence": "CC BY 4.0", "phenotypes": FILES["product4"], "phenotypes_date": p4date,
                   "functional": FILES["functional"], "functional_date": fdate,
                   "hpo": "Human Phenotype Ontology, " + version, "hpo_url": "https://hpo.jax.org/"},
        "fetched": datetime.date.today().isoformat(), "frequencies": FREQ_ORDER, "pending_frequency": PENDING_FREQ,
        "terms": term_out, "codes": dict(sorted(out_codes.items(), key=lambda kv: int(kv[0])))},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{sum(1 for v in out_codes.values() if v.get('hpo'))} codes with features ({len(term_out)} HPO terms), "
          f"{sum(1 for v in out_codes.values() if v.get('functional'))} with functional consequences; Orphadata {p4date}, {version}")


if __name__ == "__main__":
    main()
