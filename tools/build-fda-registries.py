#!/usr/bin/env python3
"""Harvest the FDA's list of pregnancy exposure registries.

A pregnancy exposure registry follows people who take a medicine while pregnant and
records what happens, which is how the effect of a medicine on a pregnancy becomes known
at all. The FDA keeps the public list of them. For a family on this site the question is
narrower and more useful than the whole list: a registry is recruiting for the very
medicine I was exposed to, and here is who to contact.

So the harvest keeps the whole list, and the enrichment step matches it against the
substances already on the teratogens register.

The FDA is explicit that listing is not endorsement: registries appear at the request of
their sponsor or investigator, and the agency states that it does not endorse any of them
and is not responsible for their content. That sentence travels with the data and onto
the page.

Output: tools/fda-pregnancy-registries.json

Usage: python3 tools/build-fda-registries.py
"""
import html as html_mod
import json
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "fda-pregnancy-registries.json"
URL = "https://www.fda.gov/consumers/pregnancy-exposure-registries/list-pregnancy-exposure-registries"
UA = {"User-Agent": "dysnet-teratogens/1.0 (+https://www.dysnet.org/knowledge/teratogens/; info@dysnet.org)"}
DISCLAIMER = ("Registries are listed by the FDA at the request of their sponsor or investigator. "
              "The FDA states that it does not endorse any registry and is not responsible for the "
              "content of the registries listed.")


def clean(fragment):
    """Strip the markup, then decode the entities the markup left behind."""
    text = html_mod.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def links(html):
    out = []
    for m in re.finditer(r'href="(https?://[^"]+)"', html):
        u = html_mod.unescape(m.group(1)).rstrip(".,;")
        if u not in out:
            out.append(u)
    return out


def phones(text):
    return re.findall(r"\b1[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{4}\b", text)


def main():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        html = r.read().decode("utf-8", "replace")
    table = re.findall(r"<table.*?</table>", html, re.S)
    if not table:
        raise SystemExit("the FDA page no longer carries a table; check the layout before trusting this script")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table[0], re.S)
    out = []
    for tr in rows[1:]:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        if len(cells) < 3:
            continue
        medicine, condition, registry = clean(cells[0]), clean(cells[1]), clean(cells[2])
        contact_html = cells[3] if len(cells) > 3 else ""
        status = clean(cells[4]) if len(cells) > 4 else ""
        if not medicine:
            continue
        out.append({
            "medicine": medicine,
            "condition": condition,
            "registry": registry,
            "urls": links(contact_html),
            "phones": phones(clean(contact_html)),
            "contact": clean(contact_html),
            # the page writes "Ongoing", "Ongoing opened", "ongoing opened" and variants of each
            "status": "ongoing" if "ongoing" in status.lower() else (status.lower() or "unstated"),
        })
    doc = {
        "source": "U.S. Food and Drug Administration, List of Pregnancy Exposure Registries",
        "url": URL,
        "fetched": time.strftime("%Y-%m-%d"),
        "disclaimer": DISCLAIMER,
        "count": len(out),
        "registries": out,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    ongoing = sum(1 for x in out if x["status"] == "ongoing")
    print(f"{len(out)} registries ({ongoing} ongoing) written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
