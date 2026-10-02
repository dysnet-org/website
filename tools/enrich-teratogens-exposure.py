#!/usr/bin/env python3
"""Tag every substance of the teratogens register with the ways a pregnancy meets it, each with its
own level of evidence, and with the dose at which the effect is shown where a source states one.

A tag answers one question: through what does a pregnant woman receive this substance at a dose
that matters? It is not a list of every product the molecule occurs in. Lithium is a medicine,
and treatment is the exposure, so it is tagged Medicine.

Seven tags (labels and meanings in tools/teratogen-exposure.json): Medicine, Food and drink,
Tobacco and recreational drugs, Home and personal care, Air pollution, Pesticides and biocides,
Work and industry.

Which tags, in this order:
  1. tools/teratogen-exposure.json names the entry, with its tags and the reason: medicines, food
     contaminants, tobacco, cosmetics, air pollutants, and the substances the rules below would
     misread (carbon monoxide is in the EU pesticides database, but poisoning comes from boilers).
  2. Pesticides and biocides, when the EU Pesticides Database lists the substance (approved or
     refused), or when its name carries an ISO common name, the naming system for pesticides.
  3. Work and industry otherwise: an industrial chemical, which in the EU may not be sold to the
     public once classified Repr. 1A or 1B (REACH Annex XVII entry 30).

Each tag carries the level of evidence that applies to that way of meeting the substance, taken
from the authority that speaks to it, never set here:
  - a medicines regulator (EMA) and the ENTIS experts' list of known human teratogenic medicines
    speak to Medicine;
  - a chemical classification (EU CLP Annex VI, Japan's NITE) speaks to the substance as a chemical
    is handled: at work, as a pesticide, in home products, in air. When a medicine also carries one,
    the medicine is handled as a chemical where it is made, so a Work and industry tag (or Pesticides
    and biocides, for a rodenticide such as warfarin) is added at that classification's level. A
    NITE code gives no more than "presumed" (H360, category 1A or 1B) or "suspected" (H361);
  - California's Proposition 65 speaks to every way listed, except that its listing of a medicine
    rests on the medicine (and so not on the same substance in a cosmetic), and a listing made
    because a label is "formally required" rests on the product that carries the label;
  - the WHO and the DysNet bibliography speak to the ways listed.
A tag no authority speaks to takes the entry's own level, unless tools/teratogen-exposure.json
names the authority that rates that way of meeting it (the EU's scientific committee for vitamin A
on the skin). The file also gives each Home and personal care tag the evidence of cosmetic use and
its source: an EU Cosmetics Regulation annex entry, products reported to California's Safe
Cosmetics Program, a Cosmetic Ingredient Review or SCCS assessment, or a regulator's statement. So valproate shows Medicine, known (EMA,
California), and Work and industry, presumed (Japan), and toluene shows both California's "known"
and the EU's "suspected".

The doses come from the same file, each with its source and the tag it belongs to; none is
computed or inferred here. This step replaces the older kind, Medicine and Wikipedia-use tags,
which said what a substance is used for rather than how the unborn child is exposed, so it removes
those fields.

Run after the other enrichment steps: python3 tools/enrich-teratogens-exposure.py
"""
import json
import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).parent
TERA = HERE / "teratogens.json"
SPEC = HERE / "teratogen-exposure.json"
OLD_FIELDS = ("kind", "medicinal", "medicine_evidence", "uses", "use_evidence")
RANK = {"known": 0, "presumed": 1, "suspected": 2}
CHEMICAL = ("home", "air", "pesticide", "work")


def resolver(names):
    """An entry's name, or the start of it when that matches one entry only."""
    def find(key):
        if key in names:
            return key
        hits = [n for n in names if n.startswith(key)]
        return hits[0] if len(hits) == 1 else None
    return find


def is_pesticide(e):
    return any(d["code"] == "eu-ppp" for d in e.get("decisions", [])) or "(iso)" in e["name"].lower()


def rule(e):
    ppp = next((d for d in e.get("decisions", []) if d["code"] == "eu-ppp"), None)
    if ppp:
        state = "approved" if ppp["verdict"] == "approved" else "not approved"
        return ["pesticide"], f"The EU Pesticides Database lists it as an active substance, {state}."
    if "(iso)" in e["name"].lower():
        return ["pesticide"], "Its ISO common name, the international naming system for pesticides, marks it as a pesticide active substance."
    verdicts = {d["verdict"] for d in e.get("decisions", [])}
    if "public_supply_banned" in verdicts:
        return ["work"], "An industrial chemical: the EU bars its sale to the public (REACH Annex XVII entry 30), so exposure happens at work."
    if "authorisation_required" in verdicts:
        return ["work"], "An industrial chemical: each use needs an EU authorisation (REACH Annex XIV), so exposure happens at work."
    return ["work"], "An industrial chemical, met mainly where it is made or used."


def source_levels(e):
    """(code, level, label) for every source that sets a level of evidence."""
    out = []
    for s in e["sources"]:
        c = s["code"]
        if c == "clp" and e["status"].get("clp") in RANK:
            out.append((c, e["status"]["clp"], f"EU CLP {s['category']}"))
        elif c == "ema" and e["status"].get("ema") in RANK:
            out.append((c, e["status"]["ema"], "EMA"))
        elif c in ("who", "bib", "entis") and e["status"].get(c) in RANK:
            out.append((c, e["status"][c], {"who": "WHO", "bib": "DysNet bibliography", "entis": "ENTIS experts"}[c]))
        elif c == "p65" and "p65" in e["status"]:
            mech = s.get("mechanism", "").lower()
            out.append((c, "presumed" if "authoritative body" in mech else "known", "California Prop 65"))
        elif c == "nite":
            st = " ".join(s.get("statements", []))
            out.append((c, "presumed" if "H360" in st else "suspected", "Japan NITE " + ("category 1" if "H360" in st else "category 2")))
    return out


def routes_for(e, tags, why):
    """The tags with their levels, adding the chemical route of a medicine that a chemical classification covers."""
    tags = list(tags)
    chem = [t for t in tags if t in CHEMICAL]
    added = None
    levels = {t: [] for t in tags}
    for code, lvl, label in source_levels(e):
        mech = next((s.get("mechanism", "") for s in e["sources"] if s["code"] == "p65"), "").lower()
        if code in ("ema", "entis"):
            targets = ["medicine"] if "medicine" in tags else tags
        elif code == "p65":
            if "medicine" in tags and ("formally required" in mech or tags == ["medicine"]):
                targets = ["medicine"]
            elif "formally required" in mech and "pesticide" in tags:
                targets = ["pesticide"]
            elif "medicine" in tags:
                # California lists a medicine on its treatment doses: the listing does not speak to the
                # same substance in a cosmetic, which a chemical classification covers instead
                targets = [t for t in tags if t != "home"]
            else:
                targets = tags
        elif code in ("clp", "nite"):
            targets = list(chem)
            if "medicine" in tags:
                # a medicine is handled as a chemical where it is made, whatever else it is used in
                added = added or ("pesticide" if is_pesticide(e) else "work")
                if added not in tags:
                    levels.setdefault(added, [])
                if added not in targets:
                    targets.append(added)
            if not targets:
                targets = tags
        else:
            targets = tags
        for t in targets:
            levels[t].append((lvl, label))
    out = []
    for t, got in levels.items():
        if got:
            best = min(RANK[l] for l, _ in got)
            lvl = next(l for l, r in RANK.items() if r == best)
            by = sorted({lab for l, lab in got if l == lvl})
            others = sorted({f"{lab}: {l}" for l, lab in got if l != lvl})
        else:
            # no authority speaks to this way of meeting it: it takes the substance's own level
            lvl, others = e["level"], []
            by = sorted({lab for _c, l, lab in source_levels(e) if l == lvl})
        r = {"tag": t, "level": lvl, "by": by}
        if not got:
            r["inherited"] = True
        if others:
            r["also"] = others
        if t == added and t not in tags:
            r["why"] = ("As a chemical, it is handled where the medicine is made, and a chemical classification covers it."
                        if t == "work" else "It is also sold as a pesticide or biocide, and a chemical classification covers it.")
        out.append(r)
    return out


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    data = json.loads(TERA.read_text(encoding="utf-8"))
    names = [e["name"] for e in data["entries"]]
    find = resolver(names)
    missing, curated, medicines, doses = [], {}, set(), {}
    for key, v in spec["entries"].items():
        n = find(key)
        if n: curated[n] = v
        else: missing.append(key)
    for key in spec["medicines"]:
        n = find(key)
        if n: medicines.add(n)
        else: missing.append(key)
    for key, v in spec.get("doses", {}).items():
        n = find(key)
        if n: doses[n] = v
        else: missing.append(key)
    if missing:
        sys.exit(f"teratogen-exposure.json names {len(missing)} entry(ies) the register does not hold: {missing}")

    order = list(spec["tags"])
    for e in data["entries"]:
        for f in OLD_FIELDS:
            e.pop(f, None)
        if e["name"] in curated:
            tags, why = curated[e["name"]]["tags"], curated[e["name"]]["why"]
        elif e["name"] in medicines:
            tags = ["medicine"]
            why = "It is taken as a medicine, and treatment is how a pregnancy meets it" + (f" (WHO ATC {', '.join(e['atc'][:2])})." if e.get("atc") else ".")
        else:
            tags, why = rule(e)
        bad = [t for t in tags if t not in spec["tags"]]
        if bad:
            sys.exit(f"{e['name']}: unknown tag(s) {bad}")
        routes = sorted(routes_for(e, tags, why), key=lambda r: order.index(r["tag"]))
        # a way of meeting it can carry its own evidence and source, and, where the authority that
        # speaks to that way rates it differently, its own level (vitamin A on the skin, for example)
        for r in routes:
            note = (curated.get(e["name"], {}).get("routes") or {}).get(r["tag"])
            if not note:
                continue
            r.update({k: note[k] for k in ("why", "source", "url") if note.get(k)})
            if note.get("level"):
                r.update({"level": note["level"], "by": note["by"], "basis": note.get("basis", "")})
                r.pop("also", None); r.pop("inherited", None)
        dose = doses.get(e["name"])
        if dose:
            r = next((r for r in routes if r["tag"] == dose.get("tag")), None)
            if not r:
                sys.exit(f"{e['name']}: the dose belongs to tag {dose.get('tag')!r}, which the entry does not carry")
            r["dose"] = {k: v for k, v in dose.items() if k != "tag"}
        e["exposure"] = routes
        e["exposure_why"] = why

    c = Counter(r["tag"] for e in data["entries"] for r in e["exposure"])
    for k in ("medicinal", "with_uses", "atc_not_medicine"):
        data["counts"].pop(k, None)
    data["counts"]["exposure"] = {k: c.get(k, 0) for k in order}
    data["counts"]["doses"] = sum(1 for e in data["entries"] for r in e["exposure"] if r.get("dose"))
    data["counts"]["exposure_split"] = sum(1 for e in data["entries"] if len({r["level"] for r in e["exposure"]}) > 1)
    data.pop("use_labels", None)
    data["exposure_labels"] = spec["tags"]
    data["exposure_method"] = spec["_about"]
    TERA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(data['entries'])} entries tagged; {data['counts']['exposure_split']} with different levels by tag; {data['counts']['doses']} doses")
    for k in order:
        print(f"  {spec['tags'][k]['label']:32} {c.get(k, 0)}")


if __name__ == "__main__":
    main()
