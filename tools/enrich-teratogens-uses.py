#!/usr/bin/env python3
"""Tag the substances of the teratogens register with the everyday products they are used in.

Source: the plain text of each substance's Wikipedia article (the article already linked from the
register, resolved through Wikidata by CAS number). Only sentences that speak of a use are read
("used as", "found in", "applications", "ingredient in", "manufacture of"…), and a category is kept
only when such a sentence names it. One sentence per category is stored as evidence, so every tag on
the site can be checked against the article it came from.

Cache: tools/wikipedia-uses.json (categories + evidence per article title).
Run: python3 tools/enrich-teratogens-uses.py
"""
import json, pathlib, re, time, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
CACHE = HERE / "wikipedia-uses.json"
RAW = HERE / "terato" / "wiki"   # git-ignored copies of the article text, so the rules can be re-run offline
UA = {"User-Agent": "DysNet teratogens register (info@dysnet.org)"}
API = "https://en.wikipedia.org/w/api.php?"

# a sentence counts only when it says the substance is USED for something
USE_CONTEXT = re.compile(r"\b(is|are|was|were|been|being)\s+(widely\s+|commonly\s+|also\s+|mainly\s+|primarily\s+|previously\s+|formerly\s+)*(used|employed|applied|added|found|marketed|sold)\b"
                         r"|\buse[ds]?\s+(as|in|for|to)\b|\bapplications?\s+(include|are|of)\b|\bingredient\b|\bis a (solvent|plasticizer|plasticiser|preservative|additive|pigment|dye|propellant|refrigerant|fumigant|herbicide|insecticide|fungicide|pesticide|flame retardant)\b"
                         r"|\b(manufactur\w+|production) of\b", re.I)
# regulatory, exposure and contamination sentences are not statements of use
NOT_USE = re.compile(r"tolerable (daily|monthly|weekly) intake|exposure limit|occupational exposure|contaminant|contamination|residues?\b|banned|prohibited|phased out|withdrawn|recall|poisoning|accident|spill|emission|waste|landfill|carcinog|toxicity study|animal studies|no longer (used|permitted)|committee|regulation|directive|safety data|produced from|made from|derived from|feedstock|raw material for|by-?product of|occurs naturally|dietary supplement|insufficient evidence|precursor (to|for)|intermediate (in|for)|used to (make|produce|synthesi|manufactur)|starting material|monomer for|production of many|model compound|reaction medium|laboratory|reagent for|mistaken|erroneous|incorrectly|misidentif|\bmyth\b|never (been )?used|rumou?r", re.I)

CATEGORIES = {
    "food": (r"food additive|food packaging|food contact|in the food industry|flavou?ring (agent|substance)|sweetener|preservative in food|chewing gum|confectioner|baking|cooking oil|dietary supplement|infant formula|beverage", "Food and drink"),
    "construction": (r"\bpaints?\b|\bcoatings?\b|\bvarnish\w*|\blacquers?\b|\badhesives?\b|\bsealants?\b|\binsulation\b|\bcement\b|\bconcrete\b|\bmortar\b|wood preservative|\bflooring\b|\bPVC\b|\broofing\b|\bplaster\b|\bwallpaper\b|\bcaulk\w*|timber treatment|building material|construction material", "Building and construction"),
    "goods": (r"\bplastics?\b|\bpolymers?\b|\bresins?\b|\brubber\b|\btoys?\b|\belectronics?\b|\bbatter(y|ies)\b|\btextiles?\b|\bfabrics?\b|\bdyes?\b|\bpackaging\b|\bfurniture\b|consumer product|household product|\binks?\b|\bprinting\b|\bleather\b|\bphotographic\b|flame retardant", "Manufactured goods"),
    "cosmetics": (r"\bcosmetics?\b|\bshampoo\b|nail polish|hair dye|hair colour|\bfragrances?\b|\bperfumes?\b|\bsunscreen\b|\bdeodorant\b|skin care|skincare|\btoothpaste\b|\bsoaps?\b|\blipstick\b|personal care", "Cosmetics and personal care"),
    "cleaning": (r"detergent|cleaning (product|agent)|household cleaner|bleach|disinfectant|laundry|degreas|stain remover|dry cleaning", "Cleaning and household"),
    "agriculture": (r"pesticide|herbicide|insecticide|fungicide|rodenticide|fumigant|fertili[sz]er|crop protection|weed killer|\bcrops?\b", "Agriculture and pest control"),
    "fuel": (r"\bgasoline\b|\bpetrol\b|\bdiesel\b|jet fuel|fuel additive|motor oil|engine oil|\bantifreeze\b|brake fluid|engine coolant|\brefrigerant\b|automotive|\bvehicles?\b", "Fuel and vehicles"),
}
CATEGORIES = {k: (re.compile(rx, re.I), label) for k, (rx, label) in CATEGORIES.items()}


def article(title):
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / (re.sub(r"[^A-Za-z0-9._-]", "_", title)[:120] + ".txt")
    if f.exists(): return f.read_text(encoding="utf-8")
    u = API + urllib.parse.urlencode({"action": "query", "format": "json", "prop": "extracts",
                                      "explaintext": 1, "redirects": 1, "titles": title})
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
        pages = json.load(r)["query"]["pages"]
    text = ""
    for p in pages.values():
        text = p.get("extract", "") or ""
        break
    f.write_text(text, encoding="utf-8")
    time.sleep(0.25)
    return text


SECTION = re.compile(r"^==+ *(.+?) *==+$", re.M)
# the sentence must be about the substance itself, not about a derivative or a neighbouring compound
SUBJECT = re.compile(r"^(it|its|this (compound|substance|chemical|material|product|acid|salt|gas|liquid|solvent)|the compound|the substance|the chemical|the material)\b", re.I)
# a household or consumer signal, required before a cleaning tag: industrial degreasing is not household use
HOUSEHOLD = re.compile(r"household|domestic|home|consumer|laundry|dishwash|dry cleaning|cleaning product|detergent|bleach|soap|cleaner", re.I)
INDUSTRIAL_ONLY = re.compile(r"industrial|in industry|hospitals?|medical equipment|manufacturing plant", re.I)
USE_SECTION = re.compile(r"^(uses?|applications?|production and uses?|occurrence and uses?|consumer|industrial uses?|in (food|cosmetics|medicine))\b", re.I)
MAX_TAGS = 3
# entries whose exposure route is the product itself, whatever else the molecule is used for
OVERRIDES = {"cas:64-17-5": {"food": "Ethanol is the active ingredient in alcoholic beverages; that is the exposure this register is about."}, "smoking": {}}


def use_text(text):
    """The lead section plus any section about uses: where an article states what a substance is for."""
    parts = SECTION.split(text)
    keep = [parts[0]]                       # lead
    for i in range(1, len(parts) - 1, 2):
        if USE_SECTION.match(parts[i].strip()): keep.append(parts[i + 1])
    return " ".join(keep)


def about_subject(sent, title):
    """True when the SUBJECT of the sentence is the substance, not another compound."""
    sent = sent.strip()
    if SUBJECT.match(sent): return True
    head = re.split(r"\b(is|are|was|were|has|have|can|may|serves?|acts?)\b", sent, 1)[0][:120]
    words = [w for w in re.split(r"[^A-Za-z0-9-]+", title) if len(w) > 3]
    if any(re.search(r"\b" + re.escape(w) + r"\w{0,3}\b", head, re.I) for w in words): return True
    return bool(re.match(r"^[A-Z]{2,5}\b", sent))


def classify(text, title=""):
    out, score = {}, {}
    for sent in re.split(r"(?<=[.!?])\s+", use_text(text).replace("\n", " ")):
        if len(sent) < 25 or len(sent) > 400: continue
        if not USE_CONTEXT.search(sent) or NOT_USE.search(sent): continue
        if not about_subject(sent, title): continue
        for key, (rx, _) in CATEGORIES.items():
            if key == "cleaning" and (not HOUSEHOLD.search(sent) or (INDUSTRIAL_ONLY.search(sent) and not re.search(r"household|domestic|home use|consumer|laundry|dishwash", sent, re.I))): continue
            if rx.search(sent):
                score[key] = score.get(key, 0) + 1
                out.setdefault(key, " ".join(sent.split())[:220])
    top = sorted(out, key=lambda k: (-score[k], k))[:MAX_TAGS]
    return {k: out[k] for k in top}


def main():
    data = json.loads(TERA.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [e for e in data["entries"] if e.get("wiki")]
    titles = []
    for e in todo:
        t = urllib.parse.unquote(e["wiki"].rsplit("/", 1)[-1]).replace("_", " ")
        e["_title"] = t
        if t not in cache: titles.append(t)
    print(f"{len(todo)} entries with a Wikipedia article, {len(titles)} to read")
    for i, t in enumerate(sorted(set(titles))):
        try:
            cache[t] = classify(article(t), t)
        except Exception as ex:
            print("  !", t, ex); cache[t] = {}
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(set(titles))} read · tagged so far {sum(1 for v in cache.values() if v)}", flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    tagged = 0
    for e in data["entries"]:
        t = e.pop("_title", None)
        key = ("cas:" + e["cas"]) if e.get("cas") else e.get("name", "")
        uses = cache.get(t or "", {})
        if key in OVERRIDES or e.get("kind") == "product":
            allowed = OVERRIDES.get(key, OVERRIDES.get("smoking", {}))
            uses = {k: (allowed[k] or uses.get(k, "")) for k in allowed}
        if uses:
            e["uses"] = sorted(uses)
            e["use_evidence"] = uses
            tagged += 1
        else:
            e.pop("uses", None); e.pop("use_evidence", None)
    data["counts"]["with_uses"] = tagged
    data["use_labels"] = {k: label for k, (_, label) in CATEGORIES.items()}
    TERA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    c = Counter(u for e in data["entries"] for u in e.get("uses", []))
    print(f"{tagged} entries carry at least one everyday use")
    for k, n in c.most_common(): print(f"  {CATEGORIES[k][1]:30} {n}")


if __name__ == "__main__":
    main()
