#!/usr/bin/env python3
"""Check that every page agrees with the condition list, and say what is left to do by hand.

Run after the site is built. It imports build-demo.py, which is the build itself, so the objects it
checks are the ones the pages were written from, not a second reading of the same files.

Hard failures (exit 1) are things a reader would meet as an error: a card with no place in
Orphanet's classification, no ICD row, a rate that cannot be selected, a link to a card that does
not exist, a paper tagged with a code no card documents, a code the bibliography can never match.
Notes are the work that cannot be automated, listed so it is not forgotten: an OMT row to place, a
registry list to read on Orphanet, a rate to source for the map.

Usage: python3 tools/audit-conditions.py [--quiet]
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import conditions as C  # noqa: E402


def load_build():
    """build-demo.py as a module: running it is the build, and its names are what we check."""
    spec = importlib.util.spec_from_file_location("build_demo", ROOT / "build-demo.py")
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m


def manual_vocab_codes():
    """The codes the hand-written VOCAB in build-bibliography.py names."""
    src = (HERE / "build-bibliography.py").read_text(encoding="utf-8")
    blk = src[src.index("VOCAB = [  #"):]
    blk = blk[:blk.index("\n]\n")]
    return set(re.findall(r'"(\d+)"\)', blk))


def run():
    m = load_build()
    hard, notes = [], []
    cards = m.CONDITIONS
    names = [c[0] for c in cards]
    coded = [(c[0], str(c[2])) for c in cards if c[2]]

    # ── hard: the registers a card cannot do without ──────────────────────────────────────
    gone = [n for n, c in coded if (m.HIER["nodes"].get(c) or {}).get("status") != "ok"]
    if gone:
        hard.append(f"{len(gone)} card(s) have no place in Orphanet's classification (withdrawn code, or hierarchy not fetched): {gone}")
    no_icd = [n for n in names if n not in m.ICD]
    if no_icd:
        hard.append(f"{len(no_icd)} card(s) have no row in condition-icd.json: {no_icd}")
    sel = {m.DOT_ALIAS.get(l, l) for l, *_ in m.DOT_RATES}
    unsel = sorted(set(m.CONDITION_RATE) - sel)
    if unsel:
        hard.append(f"{len(unsel)} card(s) carry a rate but cannot be selected in the expected-births table or drawn on the map: {unsel}")
    # every link to a card resolves
    ids, dead = set(), {}
    pages = list((ROOT / "docs").rglob("index.html"))
    for f in pages:
        ids |= set(re.findall(r'id="(cond-[^"]+)"', f.read_text(encoding="utf-8")))
    for f in pages:
        for href in re.findall(r'href="([^"]*#cond-[^"]+)"', f.read_text(encoding="utf-8")):
            if href.split("#", 1)[1] not in ids:
                dead.setdefault(str(f.relative_to(ROOT)), set()).add(href)
    if dead:
        hard.append(f"links to a card that does not exist: {dict((k, sorted(v)) for k, v in dead.items())}")
    # a paper's code must answer to a card
    homeless = {}
    for e in m.BIB.get("entries", []):
        for c in e.get("codes", []):
            if c not in ("thal",) and str(c) not in m.CARD_FOR_CODE and str(c) not in m.REG_CODE_NAMES:
                homeless[c] = homeless.get(c, 0) + 1
    if homeless:
        hard.append(f"bibliography codes no card documents (papers per code): {homeless}")
    # every card code has a way of being recognised in a paper
    vocab = manual_vocab_codes() | {r["code"] for r in (C.load("condition-vocab.json") or {}).get("rules", [])}
    unmatched = [n for n, c in coded if c not in vocab]
    if unmatched:
        hard.append(f"{len(unmatched)} card(s) have no vocabulary rule, so no paper can ever be tagged to them: {unmatched}")

    # ── notes: what stays a person's job ───────────────────────────────────────────────────
    no_omt = [n for n in names if n not in m.OMT]
    if no_omt:
        stub = {n: {"group": None, "confidence": "to place: write the OMT row by hand, or state that OMT does not cover it"} for n in no_omt}
        notes.append(f"OMT: {len(no_omt)} card(s) have no row in tools/condition-omt.json; a hand surgeon's placement is needed. Stub:\n"
                     + json.dumps(stub, ensure_ascii=False, indent=1))
    generated_only = [n for n, c in coded if c not in manual_vocab_codes()]
    if generated_only:
        notes.append(f"Bibliography vocabulary: {len(generated_only)} card(s) rest on generated rules only; review them in condition-vocab.json: {generated_only}")
    unrated = [n for n in names if n not in m.CONDITION_RATE]
    if unrated:
        notes.append(f"Prevalence: {len(unrated)} card(s) have no birth prevalence from any source: {unrated}")
    dot_names = {m.DOT_ALIAS.get(l, l) for l, r, *_ in m.DOT_RATES if r}
    orphanet_only = [n for n in names if n in m.CONDITION_RATE and n not in dot_names]
    if orphanet_only:
        notes.append(f"Map: {len(orphanet_only)} card(s) carry an Orphanet rate but no verified DOT_RATES entry, so the map draws no dot for them; "
                     f"a sourced rate would add them: {orphanet_only}")
    unchecked = [(n, c) for n, c in coded if c not in m.REG_CHECKED]
    if unchecked:
        notes.append(f"Registries: {len(unchecked)} card code(s) not yet read on Orphanet's registry search (browser task, no API): "
                     + "; ".join(f"{n} https://www.orpha.net/en/disease/detail/{c}" for n, c in unchecked))
    zero = [n for n, c in coded if not any(str(c) in e.get("codes", []) for e in m.BIB.get("entries", []))]
    if zero:
        notes.append(f"Bibliography: {len(zero)} card(s) have no paper yet (rebuild with --bibliography after the vocabulary changed): {zero}")
    # search: every card and every documented form is findable
    idx = json.loads((ROOT / "docs" / "search-index.json").read_text(encoding="utf-8"))
    rows = idx["entries"] if isinstance(idx, dict) else []
    kinds = idx.get("kinds", []) if isinstance(idx, dict) else []
    found = {(kinds[r[0]], r[2].lower()) for r in rows}
    missing_kw = [n for n in names if ("Condition", n.lower()) not in found]
    missing_kw += [t for kids in m.SUBCONDITIONS.values() for _d, t in kids if ("Form", t.lower()) not in found]
    words = " ".join(r[4].lower() for r in rows if kinds[r[0]] == "Condition")
    missing_kw += [f"ORPHA:{c}" for _n, c in coded if f"orpha:{c}" not in words]
    if missing_kw:
        hard.append(f"the site search cannot find: {missing_kw}")
    # prose that names a condition by hand, page by page, so a renamed or removed card is reviewed there
    mention = {}
    for f in pages:
        s = f.read_text(encoding="utf-8")
        body = re.sub(r"<table.*?</table>|<div class=\"card cond\".*?<div class=\"cond-foot\">.*?</div></div>|<script.*?</script>", " ", s, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", body).lower()
        hits = [n for n in names if n.lower() in text]
        if hits:
            mention[str(f.relative_to(ROOT / "docs")).replace("/index.html", "/") or "/"] = hits
    notes.append("Prose naming conditions by hand (review these when a card is renamed or removed):\n"
                 + "\n".join(f"  {p:42} {', '.join(h)}" for p, h in sorted(mention.items())))
    return hard, notes, m


def main():
    quiet = "--quiet" in sys.argv
    hard, notes, m = run()
    print(f"audit: {len(m.CONDITIONS)} cards, {len(m.SUBCONDITIONS)} of them documenting {sum(len(v) for v in m.SUBCONDITIONS.values())} forms, "
          f"{m.RATED_N} with a birth prevalence, {len(m.BIB.get('entries', []))} references")
    for h in hard:
        print(f"FAIL  {h}")
    if not quiet:
        for n in notes:
            print(f"note  {n}")
    print("audit: " + ("FAILED" if hard else "passed") + f", {len(hard)} failure(s), {len(notes)} note(s)")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
