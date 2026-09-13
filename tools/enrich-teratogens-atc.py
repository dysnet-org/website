#!/usr/bin/env python3
"""Flag the substances of the teratogens register that are also used as medicines.

Signal: an ATC code (WHO Anatomical Therapeutic Chemical classification) attached to the
substance's Wikidata item, matched by CAS number (P231 → P267). A substance with an ATC code
is, or has been, an active pharmaceutical ingredient, whatever else it is used for.
Results are cached in tools/wikidata-atc.json so the register can be rebuilt offline.
Run: python3 tools/enrich-teratogens-atc.py
"""
import json, pathlib, re, time, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
CACHE = HERE / "wikidata-atc.json"
RAW = HERE / "terato" / "wiki"    # article text cached by enrich-teratogens-uses.py

# An ATC code alone over-tags: ethanol, DDT and dibutyl phthalate all carry one for a marginal or
# historical medical use. The article's own opening must also present the substance as a medicine.
MEDICINE = re.compile(r"\b(medication|medicine|medically|pharmaceutical|prescription drug|used to treat|used in the treatment|therapeutic|clinical use|used in surgery|used in dentistry|chemotherap\w+|antineoplastic|antibiotic|antiviral|antifungal|antimalarial|anthelmintic|analgesic|an(a)?esthetic|anticonvulsant|anti-?seizure|antidepressant|antipsychotic|anxiolytic|benzodiazepine|barbiturate|opioid|corticosteroid|glucocorticoid|steroid hormone|estrogen|oestrogen|progest\w+|androgen|anticoagulant|antihypertensive|beta blocker|calcium channel blocker|diuretic|immunosuppress\w+|immunomodulat\w+|monoclonal antibody|vaccine|NSAID|nonsteroidal anti-inflammatory|contrast agent|antiretroviral|antiemetic|antihistamine|stimulant|sedative|hormone|anthelmintic|antiseptic used|drug used|administered to patients|indicated for)\b", re.I)
# ATC classes that are technical rather than therapeutic: an antiseptic or an ectoparasiticide code
# does not make an industrial chemical a medicine (ethanol, DDT, dibutyl phthalate all carry one).
TECHNICAL_ATC = re.compile(r"^(D08|V03|V07|A01AB|P03)")
INDUSTRIAL = re.compile(r"\b(plasticizer|plasticiser|industrial solvent|industrial chemical|insecticide|pesticide|herbicide|fungicide used|refrigerant|degreaser|flame retardant|fuel additive|dry cleaning)\b", re.I)
UA = {"User-Agent": "DysNet teratogens register (info@dysnet.org)", "Accept": "application/sparql-results+json"}
ENDPOINT = "https://query.wikidata.org/sparql"


def sparql(cas_list):
    q = ("SELECT ?cas ?item ?atc WHERE { VALUES ?cas { %s } ?item wdt:P231 ?cas . OPTIONAL { ?item wdt:P267 ?atc } }"
         % " ".join('"%s"' % c for c in cas_list))
    u = ENDPOINT + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120) as r:
        return json.load(r)["results"]["bindings"]


def lead(entry):
    """The opening of the substance's Wikipedia article, as cached by enrich-teratogens-uses.py."""
    if not entry.get("wiki"): return ""
    title = urllib.parse.unquote(entry["wiki"].rsplit("/", 1)[-1]).replace("_", " ")
    f = RAW / (re.sub(r"[^A-Za-z0-9._-]", "_", title)[:120] + ".txt")
    if not f.exists(): return ""
    return " ".join(f.read_text(encoding="utf-8").split("==")[0].split())


def medicinal(entry, atc):
    """True when the substance is presented as a medicine, not merely holding an ATC code."""
    if entry.get("kind") == "medicine": return True, entry.get("name", "")
    if entry.get("cas") == "64-17-5": return False, ""      # our entry is alcohol in beverages
    if not atc: return False, ""
    therapeutic = [c for c in atc if not TECHNICAL_ATC.match(c)]
    text = lead(entry)
    if therapeutic and not INDUSTRIAL.search(" ".join(re.split(r"(?<=[.!?])\s+", text)[:1])):
        return True, ""
    if not text: return False, ""
    # only a technical ATC code: the article must open by presenting the substance as a medicine
    first = re.split(r"(?<=[.!?])\s+", text)[0]
    if MEDICINE.search(first) and not INDUSTRIAL.search(first):
        return True, " ".join(first.split())[:220]
    return False, ""


def main():
    data = json.loads(TERA.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    cas_all = sorted({e["cas"] for e in data["entries"] if e.get("cas")})
    todo = [c for c in cas_all if c not in cache]
    print(f"{len(cas_all)} CAS numbers, {len(todo)} to look up")
    for i in range(0, len(todo), 90):
        chunk = todo[i:i + 90]
        try:
            rows = sparql(chunk)
        except Exception as ex:
            print("  ! query failed, retrying once:", ex); time.sleep(20)
            rows = sparql(chunk)
        found = {}
        for b in rows:
            atc = b.get("atc", {}).get("value")
            found.setdefault(b["cas"]["value"], set())
            if atc: found[b["cas"]["value"]].add(atc)
        for c in chunk:
            cache[c] = sorted(found.get(c, []))
        print(f"  {min(i+90, len(todo))}/{len(todo)} · with an ATC code so far: {sum(1 for v in cache.values() if v)}", flush=True)
        time.sleep(1.5)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")

    dropped = []
    for e in data["entries"]:
        atc = cache.get(e.get("cas", ""), [])
        keep, why = medicinal(e, atc)
        if keep:
            if atc: e["atc"] = atc
            e["medicinal"] = True
            if why: e["medicine_evidence"] = why
        else:
            if atc: dropped.append((e["name"], ",".join(atc[:2])))
            e.pop("atc", None); e.pop("medicinal", None); e.pop("medicine_evidence", None)
    data["counts"]["medicinal"] = sum(1 for e in data["entries"] if e.get("medicinal"))
    data["counts"]["atc_not_medicine"] = len(dropped)
    TERA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{data['counts']['medicinal']} entries flagged as medicines; {len(dropped)} carried an ATC code but are not presented as medicines:")
    for name, codes in dropped: print(f"  - {name[:60]:62} ATC {codes}")


if __name__ == "__main__":
    main()
