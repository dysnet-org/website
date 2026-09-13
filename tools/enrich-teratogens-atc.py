#!/usr/bin/env python3
"""Flag the substances of the teratogens register that are also used as medicines.

Signal: an ATC code (WHO Anatomical Therapeutic Chemical classification) attached to the
substance's Wikidata item, matched by CAS number (P231 → P267). A substance with an ATC code
is, or has been, an active pharmaceutical ingredient, whatever else it is used for.
Results are cached in tools/wikidata-atc.json so the register can be rebuilt offline.
Run: python3 tools/enrich-teratogens-atc.py
"""
import json, pathlib, time, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
CACHE = HERE / "wikidata-atc.json"
UA = {"User-Agent": "DysNet teratogens register (info@dysnet.org)", "Accept": "application/sparql-results+json"}
ENDPOINT = "https://query.wikidata.org/sparql"


def sparql(cas_list):
    q = ("SELECT ?cas ?item ?atc WHERE { VALUES ?cas { %s } ?item wdt:P231 ?cas . OPTIONAL { ?item wdt:P267 ?atc } }"
         % " ".join('"%s"' % c for c in cas_list))
    u = ENDPOINT + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120) as r:
        return json.load(r)["results"]["bindings"]


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

    n = 0
    for e in data["entries"]:
        atc = cache.get(e.get("cas", ""), [])
        if atc:
            e["atc"] = atc
            e["medicinal"] = True
            n += 1
        elif e["kind"] == "medicine":
            e["medicinal"] = True
    data["counts"]["medicinal"] = sum(1 for e in data["entries"] if e.get("medicinal"))
    TERA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n} substances carry an ATC code; {data['counts']['medicinal']} entries are flagged as medicines")


if __name__ == "__main__":
    main()
