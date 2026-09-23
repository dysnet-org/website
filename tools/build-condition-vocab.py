#!/usr/bin/env python3
"""Generate the vocabulary the bibliography uses to recognise a condition in a title or abstract.

The bibliography builder keeps a hand-written list of patterns, one per condition, tuned over
time. That list cannot know a condition added to the site yesterday, so a new card used to sit in
the bibliography with no rule and no paper until someone wrote one. This reads Orphanet's term and
synonyms for every card and for every form documented inside a card (tools/orphanet-hierarchy.json)
and writes a rule for each, so a new condition is matched from the day it is added. The hand-written
rules stay first and win; these fill the gaps, and the audit lists which codes rest on them alone.

Output: tools/condition-vocab.json
Usage: python3 tools/build-condition-vocab.py   (offline: reads the hierarchy already fetched)
"""
import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import conditions as C  # noqa: E402

OUT = C.HERE / "condition-vocab.json"


def manual_rules():
    """The hand-written VOCAB of build-bibliography.py, as (compiled pattern, code)."""
    src = (C.HERE / "build-bibliography.py").read_text(encoding="utf-8")
    blk = src[src.index("VOCAB = [  #"):]
    blk = blk[:blk.index("\n]\n")]
    return [(re.compile(rx, re.I), code) for rx, code in re.findall(r'\(r"((?:[^"\\]|\\.)+)",\s*(?:"(\d+)"|None)\)', blk) if code]


def ancestors(code, nodes, seen=None):
    seen = set() if seen is None else seen
    for p in (nodes.get(str(code)) or {}).get("parents", []):
        if p not in seen:
            seen.add(p)
            ancestors(p, nodes, seen)
    return seen


def phrases(code, name, hier, manual):
    """The phrases for one code. Orphanet's "Isolated" or "Non-syndromic" is dropped, because the
    literature seldom writes it, unless the bare phrase already names another entity on this site
    that is not one of the code's own ancestors: "Isolated tetra-amelia" without its qualifier is
    "tetra-amelia", which is the syndrome ORPHA:3301, and a paper on the syndrome would be tagged as
    the isolated form. For such a code every phrase keeps its qualifier."""
    bare = C.search_terms(name, code, hier)
    up = ancestors(code, hier["nodes"])
    # only a phrase the qualifier was stripped from can change meaning, and only when what is left is,
    # whole, the name another entity goes by; a syndrome whose name merely contains another word
    # ("SC phocomelia", "Cenani-Lenz syndactyly") is not ambiguous, it is specific
    stripped = {C.PREFIX.sub("", w).strip().lower() for w in [name] + C.words_for(code, hier) if C.PREFIX.match(w)}
    def whole(rx, ph):
        m = rx.search(ph)
        return bool(m) and m.group(0).lower() == ph.lower()
    clash = [c for ph in bare if ph.lower() in stripped
             for rx, c in manual if c != str(code) and c not in up and whole(rx, ph)]
    if not clash:
        return bare
    words = [name] + C.words_for(code, hier)
    return list(dict.fromkeys(w for w in words if C.PREFIX.match(w) and len(w) > 6)) or []


def main():
    hier = C.hierarchy()
    manual = manual_rules()
    rules = []
    seen = set()
    for card in C.conditions():
        code = card["code"]
        if not code:
            continue
        # the card itself, then every form Orphanet files under it, each tagged with its own code
        for c in [code] + C.descendants(code, hier):
            n = hier["nodes"].get(str(c)) or {}
            if not n.get("term"):
                continue
            for phrase in phrases(c, n["term"] if c != code else card["name"], hier, manual):
                rx = C.phrase_pattern(phrase)
                if rx and (rx, c) not in seen:
                    seen.add((rx, c))
                    rules.append({"pattern": rx, "code": str(c), "from": phrase,
                                  "card": card["name"] if c == code else f"{card['name']} > {n['term']}"})
    for r in rules:
        re.compile(r["pattern"], re.I)   # a rule that does not compile stops the build here, not in the bibliography
    OUT.write_text(json.dumps({
        "built": datetime.date.today().isoformat(),
        "source": "Orphanet terms and synonyms (tools/orphanet-hierarchy.json), one pattern per phrase",
        "note": ("Generated. The bibliography builder applies its hand-written VOCAB first and these rules "
                 "only for codes no hand-written rule names. Edit build-bibliography.py, not this file."),
        "rules": rules}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    codes = {r["code"] for r in rules}
    print(f"wrote condition-vocab.json: {len(rules)} rules for {len(codes)} codes")


if __name__ == "__main__":
    main()
