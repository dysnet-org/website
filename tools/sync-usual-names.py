#!/usr/bin/env python3
"""Copy the everyday names of the conditions from the DysNet registry into the website.

The registry keeps, beside each ORPHAcode, the names families and the press actually use ("petit
bras", "webbed fingers", "mano piccola"): its condition question searches them and shows them as
common names. That list is DysNet's own, not Orphanet's, and the member associations extend and
correct it in the registry. The website shows the same names on its cards and finds them in its
search, so the registry stays the one place the list is edited and this copies it here, dated.

Source: ../dysnet/hds-data-collection/packages/dysnet-model/src/conditions-extra.json, key usualNames
Output: tools/condition-usual-names.json
Usage:  python3 tools/sync-usual-names.py            (skips, keeping the last copy, if the registry is absent)
"""
import datetime
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
SRC = HERE.parent.parent / "dysnet" / "hds-data-collection" / "packages" / "dysnet-model" / "src" / "conditions-extra.json"
OUT = HERE / "condition-usual-names.json"
LANGS = ("en", "fr", "it")


def main():
    if not SRC.exists():
        print(f"registry not found at {SRC}; keeping the last copy ({OUT.name})")
        return 0
    extra = json.loads(SRC.read_text(encoding="utf-8"))
    raw = extra.get("usualNames") or {}
    names = {}
    for key, per_lang in raw.items():
        if key.startswith("_"):
            continue
        clean = {l: [n.strip() for n in per_lang.get(l, []) if n and n.strip()] for l in LANGS}
        clean = {l: v for l, v in clean.items() if v}
        if clean:
            names[str(key)] = clean
    previous = json.loads(OUT.read_text(encoding="utf-8")).get("names") if OUT.exists() else None
    OUT.write_text(json.dumps({
        "synced": datetime.date.today().isoformat(),
        "source": "DysNet registry, packages/dysnet-model/src/conditions-extra.json (usualNames)",
        "note": ("Everyday names of the conditions, as families and the press use them: DysNet's own list, "
                 "extended and corrected by the member associations in the registry, and not Orphanet terms. "
                 "Keyed by ORPHAcode, or by the card's name where the registry keys it so. Edit the registry, "
                 "not this file, then run this script."),
        "names": names}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    changed = "unchanged" if previous == names else f"{len(names)} entries written"
    print(f"wrote {OUT.name}: {changed} ({sum(len(v) for e in names.values() for v in e.values())} names in {', '.join(LANGS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
