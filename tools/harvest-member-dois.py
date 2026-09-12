#!/usr/bin/env python3
"""Crawl DysNet member-association websites for DOIs / PubMed links.

Usage: python3 tools/harvest-member-dois.py [--max-pages N] [--out tools/member-dois.json]

Polite same-host crawl (robots.txt Disallow honoured for '*', 1 req/s per host,
HTML + small PDFs when `pdftotext` is installed). Output: every DOI / PMID found,
with the member site and page where it was found. Resolution and verification of
the references happens in build-bibliography.py, never here.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request, urllib.robotparser
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).parent
UA = "Mozilla/5.0 (compatible; DysNetBibliographyBot/1.0; +https://www.dysnet.org/contact/)"
DOI_RE = re.compile(r'\b(10\.\d{4,9}/[^\s"<>\'\)\]]+)')
PMID_RE = re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,9})|ncbi\.nlm\.nih\.gov/pubmed/(\d{5,9})')
PMC_RE = re.compile(r'ncbi\.nlm\.nih\.gov/pmc/articles/(PMC\d+)|pmc\.ncbi\.nlm\.nih\.gov/articles/(PMC\d+)')
SKIP_EXT = re.compile(r'\.(jpe?g|png|gif|svg|webp|ico|css|js|mp4|mp3|zip|docx?|xlsx?|pptx?|woff2?|ttf)(\?|$)', re.I)
PDFTOTEXT = shutil.which("pdftotext")


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v: self.links.append(v)
    def handle_data(self, d): self.text.append(d)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get("Content-Type", "")
        data = r.read(6_000_000)
        return r.geturl(), ctype, data


def clean_doi(d):
    d = d.rstrip(".,;:")
    d = re.sub(r'(&amp;|&quot;|\\).*$', "", d)
    return d


def crawl(start, max_pages, robots_cache, delay=1.0):
    host = urllib.parse.urlparse(start).netloc.lower()
    rp = robots_cache.get(host)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(f"{urllib.parse.urlparse(start).scheme}://{host}/robots.txt"); rp.read()
        except Exception:
            rp = None
        robots_cache[host] = rp
    seen, queue, found = set(), [start], []
    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        key = url.split("#")[0]
        if key in seen: continue
        seen.add(key)
        if rp and not rp.can_fetch(UA, key): continue
        try:
            final, ctype, data = fetch(key)
        except Exception as e:
            code = getattr(e, "code", "")
            print(f"    ! {key}: {type(e).__name__} {code}", file=sys.stderr)
            if code == 429: time.sleep(max(delay * 5, 10)); queue.insert(0, key); seen.discard(key)  # back off and retry once
            continue
        time.sleep(delay)
        text = ""
        if "pdf" in ctype or key.lower().endswith(".pdf"):
            if PDFTOTEXT and len(data) < 6_000_000:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f: f.write(data); tmp = f.name
                try: text = subprocess.run([PDFTOTEXT, "-q", tmp, "-"], capture_output=True, text=True, timeout=60).stdout
                except Exception: text = ""
                pathlib.Path(tmp).unlink(missing_ok=True)
        elif "html" in ctype or "xml" in ctype or not ctype:
            html = data.decode("utf-8", "replace")
            p = Links();
            try: p.feed(html)
            except Exception: pass
            text = html
            for l in p.links:
                u = urllib.parse.urljoin(final, l).split("#")[0]
                pu = urllib.parse.urlparse(u)
                if pu.scheme not in ("http", "https"): continue
                same = pu.netloc.lower().removeprefix("www.") == host.removeprefix("www.")
                if same and not SKIP_EXT.search(pu.path) and u not in seen: queue.append(u)
                # external DOI / PubMed links count even though we don't follow them
                for m in DOI_RE.finditer(urllib.parse.unquote(u)):
                    found.append({"doi": clean_doi(m.group(1)), "page": key})
                for m in PMID_RE.finditer(u):
                    found.append({"pmid": m.group(1) or m.group(2), "page": key})
                for m in PMC_RE.finditer(u):
                    found.append({"pmcid": m.group(1) or m.group(2), "page": key})
        for m in DOI_RE.finditer(text): found.append({"doi": clean_doi(m.group(1)), "page": key})
        for m in PMID_RE.finditer(text): found.append({"pmid": m.group(1) or m.group(2), "page": key})
        for m in PMC_RE.finditer(text): found.append({"pmcid": m.group(1) or m.group(2), "page": key})
    # dedupe per identifier
    uniq = {}
    for f in found:
        k = f.get("doi") or f.get("pmid") or f.get("pmcid")
        uniq.setdefault(k, f)
    return len(seen), list(uniq.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests to one host")
    ap.add_argument("--out", default=str(HERE / "member-dois.json"))
    ap.add_argument("--sites", default=str(HERE / "member-sites.json"), help="JSON list of {name, country, url}")
    a = ap.parse_args()
    sites = json.loads(pathlib.Path(a.sites).read_text(encoding="utf-8"))
    out, robots = [], {}
    for s in sites:
        if not s.get("url") or "facebook.com" in s["url"]: continue
        print(f"→ {s['name']} ({s['country']}): {s['url']}", file=sys.stderr)
        n, hits = crawl(s["url"], a.max_pages, robots, a.delay)
        print(f"   {n} pages, {len(hits)} identifiers", file=sys.stderr)
        for h in hits: h.update({"member": s["name"], "country": s["country"]})
        out.extend(hits)
    pathlib.Path(a.out).write_text(json.dumps({"harvested": time.strftime("%Y-%m-%d"), "hits": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {a.out}: {len(out)} identifiers from {len(sites)} sites", file=sys.stderr)


if __name__ == "__main__":
    main()
