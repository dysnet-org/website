#!/usr/bin/env python3
"""The one place the tools read the condition list from.

CONDITIONS in build-demo.py is the single source of truth for what the site describes. Every
builder used to parse it with its own regular expression, which meant four copies of the same
assumption about the tuple's shape. They read it from here now, and so do the audit and the
orchestrator, so a change to the tuple is made once.

Also here: the registers a card depends on, loaded the same way the site build loads them, and the
words a condition is known by (Orphanet's term and synonyms), which the bibliography's vocabulary
and PubMed queries are generated from.
"""
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
BUILD = ROOT / "build-demo.py"

# (name, description, orphacode or None, orphanet_name or None, limbs, type, other, genetic)
TUPLE = re.compile(r'\(\s*"([^"]+)",\s*"([^"]*)",\s*(\d+|None),\s*(?:"([^"]*)"|None),'
                   r'\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\s*\)')


def source():
    return BUILD.read_text(encoding="utf-8")


def block(name, src=None):
    """The text of a top-level list literal in build-demo.py, from `NAME = [` to its closing `]`."""
    src = src or source()
    start = src.index(f"{name} = [")
    return src[start:src.index("\n]\n", start) + 2]


def conditions(src=None):
    """Every card, in the order of CONDITIONS, as a dict."""
    out = []
    for m in TUPLE.finditer(block("CONDITIONS", src)):
        name, desc, code, orpha, limbs, ctype, other, genetic = m.groups()
        out.append({"name": name, "desc": desc, "code": None if code == "None" else code,
                    "orphanet_name": orpha, "limbs": limbs, "type": ctype, "other": other, "genetic": genetic})
    if not out:
        raise SystemExit("conditions.py: CONDITIONS not found or its tuple shape changed")
    return out


def codes(src=None):
    """The ORPHAcodes of the cards, plus the codes REG_CODE_NAMES adds by hand (symbrachydactyly's 1570)."""
    src = src or source()
    out = [c["code"] for c in conditions(src) if c["code"]]
    out += re.findall(r'REG_CODE_NAMES\["(\d+)"\] = ', src)
    return sorted(set(out), key=int)


def extra_codes(src=None):
    """The codes REG_CODE_NAMES names by hand, with their names: codes the site uses without a card
    of their own, such as symbrachydactyly's 1570, which Orphanet reserves for the rare form."""
    src = src or source()
    return re.findall(r'REG_CODE_NAMES\["(\d+)"\] = "([^"]+)"', src)


def dot_rates(src=None):
    """The labels of DOT_RATES, the site's own verified table of rates, and their aliases to cards."""
    src = src or source()
    labels = re.findall(r'^\s*\("([^"]+)",\s*([0-9.]+|None)', block("DOT_RATES", src), re.M)
    alias = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', src[src.index("DOT_ALIAS = {"):src.index("}", src.index("DOT_ALIAS = {"))]))
    alias = {k: v.encode().decode("unicode_escape") for k, v in alias.items()}
    return [(lab, None if r == "None" else float(r)) for lab, r in labels], alias


def load(name):
    p = HERE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def hierarchy():
    return load("orphanet-hierarchy.json") or {"conditions": {}, "nodes": {}}


def words_for(code, hier=None):
    """Orphanet's term and synonyms for a code, the words a paper or a reader would use."""
    hier = hier or hierarchy()
    n = hier["nodes"].get(str(code)) or {}
    return [w for w in [n.get("term")] + list(n.get("synonyms") or []) if w]


def descendants(code, hier=None):
    hier = hier or hierarchy()
    return (hier["conditions"].get(str(code)) or {}).get("descendants") or []


# Words that name a condition in Orphanet's vocabulary but would match papers about something
# else if turned into a search rule on their own.
GENERIC = {"severe limb deficit", "hemimelia", "amelia", "polydactyly", "syndactyly", "phocomelia",
           "limb reduction defects", "congenital limb malformation"}
PREFIX = re.compile(r"^(isolated|non-syndromic|congenital)\s+", re.I)


def phrase_pattern(phrase):
    """A regular expression for a phrase as it appears in a title or abstract: case-insensitive,
    tolerant of a hyphen or a line break where the phrase has a space, and of a plural."""
    words = [re.escape(w) for w in re.split(r"[\s-]+", phrase.strip()) if w]
    if not words:
        return None
    return r"\b" + r"[\s-]+".join(words) + r"s?\b"


def search_terms(name, code, hier=None):
    """The phrases worth searching PubMed for, for one card: the site's name without its
    parenthesis, Orphanet's term without its qualifier, and its synonyms, each at least two words
    or one long word, none of them a word so generic it would flood the result."""
    out = []
    cands = [re.sub(r"\s*\([^)]*\)", "", name)]
    if code:
        cands += words_for(code, hier)
    for c in cands:
        c = PREFIX.sub("", c).strip().rstrip(".")
        if not c or c.lower() in GENERIC or c.isupper() or len(c) < 6:
            continue
        if c.lower() not in [o.lower() for o in out]:
            out.append(c)
    return out


if __name__ == "__main__":
    cs = conditions()
    print(f"{len(cs)} cards, {len(codes())} codes")
    for c in cs:
        print(f"  {c['name']:44} {c['code'] or '-':8} {', '.join(search_terms(c['name'], c['code']))[:100]}")
