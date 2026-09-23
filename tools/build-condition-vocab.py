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


def main():
    hier = C.hierarchy()
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
            for phrase in C.search_terms(n["term"], c, hier) if c != code else C.search_terms(card["name"], code, hier):
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
