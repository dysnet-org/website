#!/usr/bin/env python3
"""Build the DysNet demo site into docs/ (GitHub Pages source folder).

Architecture mirrors the HDS website (Astro BaseLayout pattern):
one layout carrying SEO head + header + footer, page bodies injected.
Run:  python3 build-demo.py
"""
import html
import json
import os
import pathlib
import re
import urllib.parse

ROOT = pathlib.Path(__file__).parent / "docs"

def _asset_version():
    import hashlib
    h = hashlib.sha1()
    for f in ("assets/css/site.css", "assets/js/site.js"):
        p = ROOT / f
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]

ASSET_V = _asset_version()

# ── Deployment target ────────────────────────────────────────────────
# GitHub Pages serves this repo's docs/ folder. Today that is the project
# URL https://dysnet-org.github.io/website/, so every internal link needs
# the /website prefix. The site now lives on www.dysnet.org (DEPLOY=prod,
# the default); DEPLOY=pages still builds for the github.io project URL.
DEPLOY = os.environ.get("DEPLOY", "prod")
ORIGIN, BASE = {
    "pages": ("https://dysnet-org.github.io", "/website"),
    "prod": ("https://www.dysnet.org", ""),
}[DEPLOY]
SITE = ORIGIN + BASE

# ── Analytics and consent ────────────────────────────────────────────
# Google Analytics 4 behind Consent Mode v2, mirroring the HDS website:
# every storage purpose starts denied, the banner flips it on Accept, and
# the stored grant is re-applied before the first pageview of later visits.
# Localhost is skipped so tools/serve.py previews never reach the property.
GA_ID = "G-NN0QH61XFV"
CONSENT_KEY = "dysnet-consent"

ANALYTICS_HEAD = """<script>
(function () {
  var h = location.hostname;
  if (h === "localhost" || h === "127.0.0.1" || h === "::1" || h === "" || h.slice(-6) === ".local") return;
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied",
    functionality_storage: "denied",
    personalization_storage: "denied",
    security_storage: "granted",
    wait_for_update: 500
  });
  try {
    if (localStorage.getItem("__KEY__") === "granted") {
      gtag("consent", "update", {
        analytics_storage: "granted",
        functionality_storage: "granted",
        personalization_storage: "granted"
      });
    }
  } catch (e) {}
  gtag("js", new Date());
  gtag("config", "__GA__", { anonymize_ip: true });
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=__GA__";
  document.head.appendChild(s);
})();
</script>""".replace("__KEY__", CONSENT_KEY).replace("__GA__", GA_ID)

CONSENT_BANNER = """<div id="consent" class="consent" role="dialog" aria-live="polite" aria-label="Measurement consent" hidden>
  <div class="consent-inner">
    <p class="consent-msg"><strong>Help us see which pages are used</strong>
      We would like to count visits with Google Analytics, so we can tell which registers families actually reach. Nothing is shared for advertising, and declining changes nothing about what you can read here. Our <a href="/privacy/">privacy notice</a> says what is recorded.</p>
    <div class="consent-actions">
      <button type="button" class="btn btn-primary" id="consent-yes">Accept</button>
      <button type="button" class="btn btn-ghost" id="consent-no">Decline</button>
    </div>
  </div>
</div>
<script>
(function () {
  var b = document.getElementById("consent");
  if (!b) return;
  var KEY = "__KEY__", prior = null;
  document.addEventListener("click", function (ev) {
    var t = ev.target && ev.target.closest ? ev.target.closest("[data-consent-reset]") : null;
    if (!t) return;
    ev.preventDefault();
    try { localStorage.removeItem(KEY); } catch (e) {}
    location.reload();
  });
  try { prior = localStorage.getItem(KEY); } catch (e) {}
  if (prior === "granted" || prior === "denied") return;
  b.hidden = false;
  function choose(state) {
    try { localStorage.setItem(KEY, state); } catch (e) {}
    b.hidden = true;
    if (typeof window.gtag === "function") {
      var ok = state === "granted";
      window.gtag("consent", "update", {
        analytics_storage: ok ? "granted" : "denied",
        functionality_storage: ok ? "granted" : "denied",
        personalization_storage: ok ? "granted" : "denied"
      });
    }
  }
  document.getElementById("consent-yes").addEventListener("click", function () { choose("granted"); });
  document.getElementById("consent-no").addEventListener("click", function () { choose("denied"); });
})();
</script>""".replace("__KEY__", CONSENT_KEY)

# Internal links are written root-absolute ("/knowledge/"); rebase() prefixes
# them with BASE at write time, so page bodies stay prefix-agnostic.
_ABS_ATTR = re.compile(r'\b(href|src)="(/(?!/)[^"]*)"')

def rebase(html):
    if not BASE:
        return html
    return _ABS_ATTR.sub(lambda m: f'{m.group(1)}="{BASE}{m.group(2)}"', html)

BRAND = "DysNet"
# the meta description is cut by search engines at about 155 characters; the schema one is not
DESC_DEFAULT = ("The global network for people with congenital limb differences: five maintained "
                "registers, a map of specialist care, and a patient-owned registry.")
ORG_DESC = ("DysNet is the global network for people affected by congenital limb differences (dysmelia): "
            "a curated bibliography, registries and studies, a researcher register, a map of specialist "
            "care centres worldwide, and an international patient-owned registry.")

FAVICON = "/assets/img/favicon-64.png"

ORG_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "NGO",
    "name": "DysNet",
    "legalName": "DysNet Ideell Förening",
    "alternateName": "EDRIC – European Dysmelia Reference Information Centre",
    "url": SITE,
    "logo": f"{SITE}/assets/img/dysnet-logo-512.png",
    "description": ORG_DESC,
    "foundingDate": "2009-01-07",
    "foundingLocation": "Stockholm, Sweden",
    "identifier": {"@type": "PropertyValue", "propertyID": "Swedish organisation number",
                   "value": "802444-3015"},
    "address": [
        {"@type": "PostalAddress", "streetAddress": "Nybodagatan 1",
         "postalCode": "171 42", "addressLocality": "Solna", "addressCountry": "SE"},
        {"@type": "PostalAddress", "streetAddress": "Rue du Chantier 2",
         "postalCode": "1000", "addressLocality": "Brussels", "addressCountry": "BE"},
    ],
    "contactPoint": {"@type": "ContactPoint", "contactType": "general enquiries",
                     "email": "info@dysnet.org", "availableLanguage": ["English"]},
    "areaServed": "Worldwide",
    "memberOf": [
        {"@type": "Organization", "name": "EURORDIS – Rare Diseases Europe",
         "url": "https://www.eurordis.org/"},
        {"@type": "Organization", "name": "European Disability Forum",
         "url": "https://www.edf-feph.org/"},
    ],
    "knowsAbout": [
        "dysmelia", "congenital limb differences", "limb reduction deficiency",
        "rare diseases", "patient registries", "prosthetics", "assistive technology",
        "patient advocacy", "European Reference Networks",
    ],
    "sameAs": ["https://www.facebook.com/DysNet",
               "https://www.linkedin.com/company/dysnet/",
               "https://www.youtube.com/user/DysmeliaNetwork",
               "https://www.orpha.net/en/patient-organisations/federations-alliances/646248",
               "https://www.edf-feph.org/our-members/european-dysmelia-reference-information-centre/",
               "https://www.lobbyfacts.eu/datacard/dysnet?rid=047603512537-13&sid=183440",
               "https://www.eurordis.org/eurordis_member/volup-speculum-carpo/",
               "https://www.wikidata.org/wiki/Q131894541"],
}

NAV = [
    ("/about/", "About"),
    ("/knowledge/", "Knowledge"),
    ("/registry/", "Registry"),
    ("/voice/", "Voice"),
    ("/contact/", "Contact"),
]


# Subject-first <title> per page (under 60 characters); page["title"] stays the short label for breadcrumbs and search.
SEO_TITLES = {
    "/": "DysNet · the international dysmelia network",
    "/knowledge/": "Knowledge on congenital limb difference · DysNet",
    "/knowledge/bibliography/": "Bibliography on dysmelia and limb difference · DysNet",
    "/knowledge/ongoing-studies/": "Studies on limb difference you can join · DysNet",
    "/knowledge/registries/": "Registries recording congenital limb difference · DysNet",
    "/knowledge/resources/": "Resources on dysmelia: guides, surveys, reports · DysNet",
    "/knowledge/researchers/": "Researchers working on limb difference · DysNet",
    "/knowledge/care-centres/": "Care centres for congenital limb difference · DysNet",
    "/knowledge/teratogens/": "Teratogens register: substances of concern · DysNet",
    "/knowledge/understanding-dysmelia/": "Understanding dysmelia: conditions and ORPHAcodes · DysNet",
    "/knowledge/causes-of-dysmelia/": "Causes of dysmelia: what the evidence shows · DysNet",
    "/knowledge/epidemiology/": "Epidemiology of dysmelia: birth prevalence and expected births · DysNet",
    "/knowledge/guides/patient-owned-registry/": "What is a patient-owned registry? · DysNet",
    "/registry/": "Patient-owned registry of limb malformations · DysNet",
    "/voice/": "Our voice: five demands for people with dysmelia · DysNet",
    "/voice/reports/": "Reports from our seats in rare-disease bodies · DysNet",
    "/about/": "About DysNet, the dysmelia network since 2009",
    "/about/members/": "Member associations for limb difference · DysNet",
    "/about/transparency/": "Transparency: documents and accounts · DysNet",
    "/about/statutes/": "Statutes of DysNet, the dysmelia network",
    "/contact/": "Contact the dysmelia network · DysNet",
    "/donate/": "Support DysNet, the dysmelia network",
    "/privacy/": "Privacy notice: cookies, rights, registers · DysNet",
    "/accessibility/": "Accessibility of this site, measured · DysNet",
    "/404/": "Page not found · DysNet",
}
PEOPLE_LD = []  # filled by person_card() as the People page is defined

# Referenced, dated long-form pieces: Article schema and published/modified dates, like the /guides/ series.
ARTICLE_PATHS = {"/knowledge/causes-of-dysmelia/", "/knowledge/epidemiology/"}


# One preview image per section rather than the board photograph on every page: a link shared into a
# chat or a feed should look like the thing it points at. Photographs the site already owns; a page
# that sets its own "og" keeps it.
SECTION_OG = {
    "/knowledge/": "/assets/img/inail-lab-tour.jpg",
    "/registry/": "/assets/img/dysnet-banner-2012.jpg",
    "/voice/": "/assets/img/limbloss-day-2012.jpg",
    "/about/": "/assets/img/board-inail-2024.jpg",
    "/contact/": "/assets/img/board-inail-2024.jpg",
    "/donate/": "/assets/img/inail-lab-2.jpg",
}


# ── Link previews ────────────────────────────────────────────────────────────
# A link to the bibliography used to preview a photograph of a prosthetics lab, because one
# photo served as the preview for twelve pages. A reader sharing the teratogens register got
# a picture of something else entirely. So each page gets a card of its own, drawn here at
# build time: the section, the page title, and where there is one, the number that says what
# the page holds. Photographs stay on the pages themselves, where they have a caption.
OG_DIR = ROOT / "assets" / "og"
OG_ACCENT = {"Knowledge": (147, 51, 234), "Registry": (22, 163, 74), "Voice": (37, 99, 235),
             "About": (234, 88, 12), "Support": (147, 51, 234), "Contact": (234, 88, 12)}
OG_FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
OG_FONTS_R = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
# what each page can say about itself in one line, filled from the registers so it stays true
OG_STAT = {
    "/knowledge/teratogens/": lambda: f'{TERA.get("counts", {}).get("total", 0)} substances · {TERA.get("counts", {}).get("legal_any", 0)} with a decision by an authority',
    "/knowledge/bibliography/": lambda: f'{len(BIB.get("entries", [])):,} references, screened and sourced',
    "/knowledge/care-centres/": lambda: f'{len(CARE_CENTRES)} centres across {len({c["country"] for c in CARE_CENTRES})} countries',
    "/knowledge/registries/": lambda: f'{len(ORPHA_REGS.get("registries", []))} registries that already record our conditions',
    "/knowledge/researchers/": lambda: f'{len(RESEARCHERS.get("teams", []))} research teams publishing on limb difference',
    "/knowledge/epidemiology/": lambda: f'Birth prevalence and expected cases, {len(BIRTHS["countries"])} countries',
    "/knowledge/understanding-dysmelia/": lambda: f'{len(CONDITIONS)} conditions, described for families',
}


def og_font(size, bold=True):
    from PIL import ImageFont
    for p in (OG_FONTS if bold else OG_FONTS_R):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return None


def og_wrap(draw, text, font, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        t = (line + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            line = t
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def build_og_card(path, title, section):
    """Write assets/og/<slug>.png and return its URL, or None if no font is available."""
    from PIL import Image, ImageDraw
    f_title = og_font(64)
    if f_title is None:
        return None
    f_eyebrow, f_stat, f_foot = og_font(26), og_font(30, bold=False), og_font(26, bold=False)
    slug = (path.strip("/").replace("/", "-") or "home")
    W, H, pad = 1200, 630, 84
    img = Image.new("RGB", (W, H), (250, 247, 254))
    d = ImageDraw.Draw(img)
    accent = OG_ACCENT.get(section, (147, 51, 234))
    d.rectangle([0, 0, 18, H], fill=accent)

    logo_path = ROOT / "assets" / "img" / "dysnet-logo.png"
    logo_h = 64
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo = logo.resize((int(logo.width * logo_h / logo.height), logo_h), Image.LANCZOS)
        img.paste(logo, (pad, pad), logo)

    lines = og_wrap(d, title, f_title, W - pad * 2)[:3]
    stat = OG_STAT.get(path)
    stat_txt = ""
    if stat:
        try:
            stat_txt = stat()
        except Exception:
            stat_txt = ""
    # the text block is centred between the logo and the footer, so a one-line title and a
    # three-line one both sit where the eye lands rather than stranding a void underneath
    block = 46 + len(lines) * 78 + (46 if stat_txt else 0)
    top, bottom = pad + logo_h + 30, H - pad - 34
    y = top + max(0, (bottom - top - block) // 2)

    d.text((pad, y), section.upper(), font=f_eyebrow, fill=accent)
    y += 46
    for line in lines:
        d.text((pad, y), line, font=f_title, fill=(36, 26, 51))
        y += 78
    if stat_txt:
        d.text((pad, y + 8), stat_txt, font=f_stat, fill=(93, 84, 112))
    d.text((pad, H - pad - 10), "www.dysnet.org", font=f_foot, fill=(93, 84, 112))

    OG_DIR.mkdir(parents=True, exist_ok=True)
    out = OG_DIR / f"{slug}.png"
    tmp = out.with_suffix(".tmp.png")
    img.save(tmp, "PNG", optimize=True)
    # only rewrite when the bytes change, so the build stays quiet and git stays clean
    if out.exists() and out.read_bytes() == tmp.read_bytes():
        tmp.unlink()
    else:
        tmp.replace(out)
    return f"/assets/og/{slug}.png"


def og_card_for(path, title):
    """The card this page should preview with, drawn once and cached on disk."""
    section = next((label for prefix, label in (
        ("/knowledge/", "Knowledge"), ("/registry/", "Registry"), ("/voice/", "Voice"),
        ("/about/", "About"), ("/donate/", "Support"), ("/contact/", "Contact"))
        if path.startswith(prefix)), "DysNet")
    name = title.split(" · ")[0].strip()
    if path == "/":
        name, section = "The international network for limb difference", "DysNet"
    try:
        return build_og_card(path, name, section)
    except Exception:
        return None       # a missing font must not fail the build; the photo still serves


def section_og(path):
    for prefix, img in SECTION_OG.items():
        if path.startswith(prefix): return img
    return None


def head(title, desc, path, is_home=False, og=None, extra_ld=None, dates=None):
    full = SEO_TITLES.get(path) or (title if BRAND in title else f"{title} · {BRAND}")
    _og_img = og or og_card_for(path, title) or section_og(path) or "/assets/img/board-inail-2024.jpg"
    canonical = SITE + path
    dates = dates or {}
    is_article = "/guides/" in path or path in ARTICLE_PATHS
    page_ld = {"@context": "https://schema.org", "@type": "Article" if is_article else "WebPage", "name": full.split(" · ")[0], "headline": full.split(" · ")[0],
               "url": canonical, "description": desc, "inLanguage": "en", "isPartOf": {"@type": "WebSite", "url": SITE + "/", "name": BRAND},
               "publisher": {"@type": "NGO", "name": BRAND, "url": SITE + "/"}, "author": {"@type": "Organization", "name": "DysNet documentation team", "url": SITE + "/about/#board"}}
    if dates.get("published"): page_ld["datePublished"] = dates["published"]
    if dates.get("modified"): page_ld["dateModified"] = dates["modified"]
    ld = [ORG_SCHEMA] if is_home else [{
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
        ]}]
    if is_home:
        ld.append({"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": SITE + "/", "inLanguage": "en",
                   "potentialAction": {"@type": "SearchAction", "target": {"@type": "EntryPoint", "urlTemplate": SITE + "/?q={search_term_string}"}, "query-input": "required name=search_term_string"}})
    ld.append(page_ld)
    if extra_ld:
        ld.extend(extra_ld)
    ld_json = "\n".join(
        f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>'
        for x in ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#2a0d47">
<title>{full}</title>
<meta name="description" content="{desc}">{'<meta name="robots" content="noindex">' if path == "/404/" else ""}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{"article" if is_article else "website"}">{f'<meta property="article:published_time" content="{dates["published"]}"><meta property="article:modified_time" content="{dates["modified"]}">' if is_article and dates.get("published") else ""}
<meta property="og:site_name" content="DysNet">
<meta property="og:title" content="{full}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}{_og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{title.split(" · ")[0]} on dysnet.org">
<meta name="twitter:image" content="{SITE}{_og_img}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="{FAVICON}">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_V}">
<script>window.SITE_BASE={json.dumps(BASE)};</script>
{ANALYTICS_HEAD}
{ld_json}
</head>"""


def header_html(active):
    links = "".join(
        f'<a href="{href}"{" aria-current=\"true\"" if active.startswith(href) else ""}>{label}</a>'
        for href, label in NAV)
    return f"""<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site">
  <div class="container site-bar">
    <a class="logo" href="/" aria-label="DysNet home"><img src="/assets/img/dysnet-logo.png" alt="DysNet — The Online Dysmelia Community" width="269" height="176"></a>
    <button type="button" class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="main-nav">Menu</button>
    <nav class="main" id="main-nav" aria-label="Main">
      <span class="nav-links">{links}<a class="nav-join" href="/about/members/">Join us</a></span>
      <button id="search-btn" type="button" class="search-trigger" aria-label="Search the site">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <span class="search-label">Search</span> <kbd>⌘K</kbd>
      </button>
      <span class="nav-ctas">
        <a class="btn btn-donate" href="/donate/">Donate</a>
        <a class="btn btn-primary" href="/about/members/">Join us</a>
      </span>
    </nav>
  </div>
</header>
<div id="search-overlay" class="search-overlay" hidden>
  <div class="search-modal" role="dialog" aria-modal="true" aria-label="Search">
    <div class="search-row">
      <input type="search" placeholder="Search the site…" aria-label="Search the site">
      <button type="button" class="search-close">ESC</button>
    </div>
    <ul class="search-results"></ul>
  </div>
</div>
<main id="main" tabindex="-1">"""


FOOTER = f"""</main>
<footer class="site">
  <div class="container">
    <div class="cols">
      <div>
        <h2>DysNet · the dysmelia network</h2>
        <p style="max-width:26rem;font-size:var(--text-small)">The global network connecting anyone personally or professionally affected by congenital limb differences. Registered in Sweden since 2009 (org. no. 802444-3015).</p>
        <ul>
          <li>DysNet Ideell Förening · Nybodagatan 1 · 171 42 Solna · Sweden</li>
          <li>Brussels office · Rue du Chantier 2 · B-1000 Brussels · Belgium</li>
          <li><a href="mailto:info@dysnet.org">info@dysnet.org</a></li>
        </ul>
      </div>
      <div>
        <h2>Knowledge</h2>
        <ul>
          <li><a href="/knowledge/bibliography/">Bibliography</a></li>
          <li><a href="/knowledge/registries/">Registries</a></li>
          <li><a href="/knowledge/researchers/">Researchers</a></li>
          <li><a href="/knowledge/care-centres/">Care centres</a></li>
          <li><a href="/knowledge/teratogens/">Teratogens register</a></li>
          <li><a href="/knowledge/ongoing-studies/">Studies</a></li>
          <li><a href="/knowledge/resources/">Resources</a></li>
          <li><a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a></li>
          <li><a href="/knowledge/causes-of-dysmelia/">Causes of dysmelia</a></li>
          <li><a href="/knowledge/epidemiology/">Epidemiology</a></li>
        </ul>
      </div>
      <div>
        <h2>Network</h2>
        <ul>
          <li><a href="/registry/">The registry</a></li>
          <li><a href="/voice/">Where DysNet sits</a></li>
          <li><a href="/voice/reports/">Reports</a></li>
          <li><a href="/about/members/">Member associations</a></li>
          <li><a href="/about/transparency/">Transparency</a></li>
          <li><a href="/donate/">Support DysNet</a></li>
        </ul>
      </div>
      <div>
        <h2>Follow</h2>
        <ul>
          <li><a href="https://www.facebook.com/DysNet">Facebook</a></li>
          <li><a href="https://www.linkedin.com/company/dysnet/">LinkedIn</a></li>
          <li><a href="https://www.youtube.com/user/DysmeliaNetwork">YouTube</a></li>
          <li><a href="https://www.youtube.com/watch?v=P8M2n7Gr3V0">The chair’s address</a></li>
        </ul>
      </div>
    </div>
    <div class="legal">
      © 2026 DysNet Ideell Förening · <a href="/privacy/">Privacy</a> · <a href="/accessibility/">Accessibility</a> · <a href="/about/statutes/">Statutes</a> · <a href="/about/transparency/">Transparency</a>
    </div>
  </div>
  <p class="page-date container">Page updated __PAGE_DATE__ · Written by the DysNet documentation team, reviewed by the board.</p>\n</footer>
{CONSENT_BANNER}
<script src="/assets/js/site.js?v={ASSET_V}" defer></script>
</body>
</html>"""


def crumbs(*pairs):
    items = ['<a href="/">Home</a>']
    for href, label in pairs[:-1]:
        items.append(f'<a href="{href}">{label}</a>')
    items.append(f'<span aria-current="page">{pairs[-1][1]}</span>')
    sep = " › "
    return f'<nav class="crumbs container" aria-label="Breadcrumb">{sep.join(items)}</nav>'


def updated_text(iso):
    """`updated Sep 2026` as plain text, for the cards that carry no badge."""
    if not iso: return ""
    import datetime
    try: return "updated " + datetime.date.fromisoformat(iso[:10]).strftime("%b %Y")
    except ValueError: return ""


def updated_badge(iso):
    """`updated Sep 2026`, from the date the register itself was built, so the badge cannot go stale."""
    if not iso: return ""
    import datetime
    try: d = datetime.date.fromisoformat(iso[:10])
    except ValueError: return ""
    return f'<span class="badge live">updated {d.strftime("%b %Y")}</span>'


def opener(num, label, heading, acc=None, big=False, toc=None):
    """toc: a short label for the contents list, where a full heading would not fit."""
    style = f' style="--acc:var(--acc-{acc});--acc-text:var(--acc-{acc}-text)"' if acc else ""
    h = "h2-lg" if big else "h2"
    short = f' data-toc="{toc}"' if toc else ""
    return f"""<div{style}>
      <div class="tick"></div>
      <p class="eyebrow">{num} · {label}</p>
      <h2 class="{h}"{short}>{heading}</h2>
    </div>"""


_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]


def spell(n):
    """Numbers under 100 in words, so a sentence can open on one; digits above that."""
    if n >= 100: return f"{n:,}"
    if n < 20: return _UNITS[n]
    return _TENS[n // 10] + (f"-{_UNITS[n % 10]}" if n % 10 else "")


# (name, description, ORPHAcode or None, Orphanet preferred name, limbs, type, other-signs)
# Codes carried from the old dysnet.org encyclopedia, verified on Orphanet 2026-08-10.
# The last three fields feed the condition finder (plain-language triage tags):
#   limbs: arms / legs / several   type: reduction / fusion / extra / band   other: other / limbsonly
ORPHA_URL = "https://www.orpha.net/en/disease/detail/{}"
CONDITIONS = [
    ("Adams-Oliver syndrome", "limb differences combined with scalp and skull defects.", 974, "Adams-Oliver syndrome", "arms legs several", "reduction", "other", "genetic"),
    ("Amelia", "complete absence of one or more limbs.", 294925, "Non-syndromic amelia", "arms legs several", "reduction", "limbsonly", "nongenetic"),
    ("Amelia of the upper limb", "complete or near-complete absence of one or both arms, without other malformations.", 294967, "Isolated amelia of upper limb", "arms", "reduction", "limbsonly", "nongenetic"),
    ("Amelia of the lower limb", "complete or near-complete absence of one or both legs, without other malformations.", 294969, "Isolated amelia of lower limb", "legs", "reduction", "limbsonly", "nongenetic"),
    ("Amniotic band syndrome", "bands of amnion constrict developing limbs before birth.", 295000, "Amniotic band syndrome", "arms legs several", "band reduction", "limbsonly", "nongenetic"),
    ("Brachydactyly", "disproportionately short fingers or toes.", None, None, "arms legs", "reduction", "limbsonly", "genetic"),
    ("Cenani-Lenz syndrome", "fused fingers and forearm bones give the hand a mitten-like form.", 3258, "Cenani-Lenz syndrome", "arms", "fusion", "other limbsonly", "genetic"),
    ("Crossed polysyndactyly", "combined webbing and extra digits on hands and feet.", 2935, "Crossed polysyndactyly", "arms legs several", "extra fusion", "limbsonly", "genetic"),
    ("Ectrodactyly (SHFM)", "split hand–foot malformation of the central rays.", 2440, "Isolated split hand-split foot malformation", "arms legs", "reduction", "limbsonly", "genetic"),
    ("Fibular hemimelia", "partial or complete absence of the fibula.", 93323, "Isolated fibular hemimelia", "legs", "reduction", "limbsonly", "nongenetic"),
    ("Holt-Oram syndrome", "upper-limb differences with congenital heart defects.", 392, "Holt-Oram syndrome", "arms", "reduction", "other", "genetic"),
    ("Microgastria–limb reduction", "a small stomach together with limb reduction defects.", 2538, "Microgastria-limb reduction defect syndrome", "arms several", "reduction", "other", "nongenetic"),
    ("Phocomelia", "intercalary limb deficiency; the hands or feet attach close to the trunk.", 2879, "Phocomelia, Schinzel type", "arms legs several", "reduction", "other", "genetic"),
    ("Poland syndrome", "underdeveloped chest muscle with hand differences on the same side.", 2911, "Poland syndrome", "arms", "reduction fusion", "other", "genetic nongenetic"),
    ("Polydactyly", "more than the usual number of fingers or toes.", 2913, "Non-syndromic polydactyly", "arms legs", "extra", "limbsonly", "genetic"),
    ("Radial aplasia", "the radius is underdeveloped or absent.", 93321, "Isolated radial hemimelia", "arms", "reduction", "limbsonly", "nongenetic"),
    ("Roberts syndrome", "symmetric limb reduction with growth delay (SC phocomelia).", 3103, "Roberts syndrome", "arms legs several", "reduction", "other", "genetic"),
    ("Symbrachydactyly", "short, webbed or missing fingers, usually on one hand; not inherited.", None, None, "arms", "reduction fusion", "limbsonly", "nongenetic"),
    ("Syndactyly", "webbing between two or more fingers or toes.", 90025, "Non-syndromic syndactyly", "arms legs", "fusion", "limbsonly", "genetic"),
    ("Terminal transverse limb defect", "the limb forms and then stops: everything beyond one level is missing, most often the hand or the forearm, with the parts above it normally formed.", 498461, "Non-syndromic terminal transverse limb defect", "arms legs", "reduction", "limbsonly", "nongenetic"),
    ("Tetra-amelia", "absence of all four limbs, with other malformations.", 3301, "Tetraamelia-multiple malformations syndrome", "several", "reduction", "other", "genetic"),
    ("Thrombocytopenia-absent radius (TAR)", "absent radius with low platelet counts.", 3320, "Thrombocytopenia-absent radius syndrome", "arms", "reduction", "other", "genetic"),
    ("Tibial aplasia–ectrodactyly", "tibial deficiency together with split hand–foot.", 3329, "Tibial aplasia-ectrodactyly syndrome", "legs several", "reduction", "limbsonly", "genetic"),
    ("Tibial hemimelia", "deficiency of the tibia with an intact fibula.", 93322, "Isolated tibial hemimelia", "legs", "reduction", "limbsonly", "nongenetic"),
    ("Ulnar hemimelia", "partial or complete absence of the ulna.", 93320, "Isolated ulnar hemimelia", "arms", "reduction", "limbsonly", "nongenetic"),

    # ── The forms Orphanet files under our three group codes ──────────────────────────────
    # Our cards carried ORPHA:498461, 2913 and 93458, each a group of disorders, and the forms
    # inside them were nowhere on the site. Every entry below is one of those forms, its code and
    # Orphanet's preferred name taken from the classification, its description written from
    # Orphanet's own definition. The "genetic" tag follows Orphanet's OMIM cross-reference: a form
    # with an OMIM entry is marked genetic, one without it non-genetic, which is a rule and not a
    # judgement about any one family. Subtypes below the disorder level (zygodactyly 1 to 4,
    # synpolydactyly 1 to 3) are left to the tree on each card rather than given cards of their own.

    # Intercalary: the middle of the limb is missing, the end of it is formed (ORPHA:294927)
    ("Intercalary limb defect", "the middle segment of the limb is missing or short, while the hand or foot beyond it is formed.", 294927, "Non-syndromic intercalary limb defects", "arms legs several", "reduction", "limbsonly", "nongenetic"),

    # Longitudinal: a bone along the length of the limb is missing (ORPHA:498457)
    ("Longitudinal limb defect", "a bone along the length of the limb is missing or short, while the segments above and below it are present.", 498457, "Non-syndromic longitudinal limb defect", "arms legs several", "reduction", "limbsonly", "nongenetic"),

    # Terminal transverse: the limb forms and then stops (ORPHA:498461)

    # Syndactyly, the numbered types (ORPHA:90025)
    ("Hyperphalangy", "an extra bone inside a finger or toe, with the usual number of digits.", 295002, "Isolated hyperphalangy", "arms legs", "extra", "limbsonly", "nongenetic"),

    # Polydactyly, by the axis the extra digit sits on (ORPHA:2913)
]


# Card names for our ORPHAcodes, derived from CONDITIONS so that a condition added there reaches the
# bibliography's labels, the coverage tables and the map in the same build. Two entries are set by
# hand: the short label the epidemiology tables use for TAR, and ORPHA:1570, the only Orphanet entity
# for symbrachydactyly, which the card describes without carrying as its own code.
REG_CODE_NAMES = {str(c[2]): c[0] for c in CONDITIONS if c[2]}
REG_CODE_NAMES["3320"] = "TAR syndrome"
REG_CODE_NAMES["1570"] = "Symbrachydactyly"
REG_CODE_NAMES = dict(sorted(REG_CODE_NAMES.items(), key=lambda kv: kv[1].lower()))


# ── ICD-10, as Orphanet maps it (tools/build-condition-icd.py) ───────────────
# The ORPHAcode is the identifier a rare-disease registry uses; the ICD-10 code is the one a
# hospital, a national registry and an insurer use, and the conditions page carried only the
# first. Orphanet publishes the mapping together with its relation, and the relation is the
# load-bearing part: Q87.2 is the ICD-10 code for four of these conditions at once, so quoting
# it bare would tell a reader the four are the same thing.
# The three plain-language facets of a condition, in the words the finder puts to a reader. The
# finder's chips and each card's chips are both built from this, so the two cannot drift apart.
FACETS = {
    "limbs": [("", "Not sure / any"), ("arms", "Arms or hands"), ("legs", "Legs or feet"), ("several", "Several or all four")],
    "type": [("", "Not sure / any"), ("reduction", "A part is missing or shorter"), ("fusion", "Fingers or toes joined"),
             ("extra", "Extra fingers or toes"), ("band", "Ring-shaped constriction marks")],
}
FACET_SHORT = {"arms": "Arms or hands", "legs": "Legs or feet", "several": "Several or all four",
               "reduction": "A part is missing", "fusion": "Joined digits", "extra": "Extra digits",
               "band": "Constriction marks"}


def facet_chips(q):
    """The finder's buttons for one facet, from FACETS."""
    return "".join(f'<button type="button" data-v="{v}" aria-pressed="{"true" if v == "" else "false"}">{lab}</button>'
                   for v, lab in FACETS[q])


ICD_PATH = pathlib.Path(__file__).parent / "tools" / "condition-icd.json"
ICD = json.loads(ICD_PATH.read_text(encoding="utf-8"))["conditions"] if ICD_PATH.exists() else {}
# How many conditions carry an ICD-10 code at all: the pages that count on it say so from here, because
# eleven of ours are Orphanet groups that ICD-10 gives no single code to.
ICD_COUNTED = sum(1 for c in CONDITIONS if (ICD.get(c[0]) or {}).get("icd10"))


def _icd_relation(codes):
    """The one word a card puts on a set of codes for one edition."""
    rels = [str(e.get("relation", "")) for e in codes]
    if not rels:
        return None
    if any(r.startswith("classification") for r in rels):
        return "classification"
    if all(r.startswith("E ") for r in rels):
        return "exact"
    if all(r.startswith(("BTNT", "E ")) for r in rels):
        return "narrower"
    return "broader"


# What the two editions actually achieve across our conditions, counted here so the notes under the
# grid cannot drift from the cards above them.
# Counted over the cards the page shows, not over every row the register holds: the register keeps a
# row for each form documented inside a card, and a sentence about "the conditions on this page" that
# counted those would be describing something the reader cannot see.
ICD_CARDS = {c[0]: (ICD.get(c[0]) or {}) for c in CONDITIONS}
ICD_STATS = {}
for _ed, _key in (("icd10", "icd10"), ("icd11", "icd11")):
    _c = {}
    for _v in ICD_CARDS.values():
        _r = _icd_relation((_v or {}).get(_key) or [])
        if _r:
            _c[_r] = _c.get(_r, 0) + 1
    ICD_STATS[_ed] = {"rows": sum(_c.values()), **_c}
_shared = {}
for _v in ICD_CARDS.values():
    for _e in (_v or {}).get("icd11") or []:
        _shared[_e["code"]] = _shared.get(_e["code"], 0) + 1
ICD11_WIDEST = max(_shared.items(), key=lambda kv: kv[1]) if _shared else ("", 0)
# The ICD-10 code that stands for most of the cards at once, and an example of the reverse relation,
# both read from the register so that the sentences quoting them cannot go stale when the list changes.
_shared10 = {}
for _v in ICD_CARDS.values():
    for _e in (_v or {}).get("icd10") or []:
        _shared10[_e["code"]] = _shared10.get(_e["code"], 0) + 1
ICD10_WIDEST = max(_shared10.items(), key=lambda kv: kv[1]) if _shared10 else ("", 0)
ICD10_NARROWER = [n for n, v in ICD_CARDS.items() if _icd_relation((v or {}).get("icd10") or []) == "narrower"]


# ── Oberg-Manske-Tonkin, the surgeons' classification (tools/condition-omt.json) ──
# A third vocabulary, and the one the four clinical registries of congenital upper limb
# difference all use. Our conditions carry ORPHAcodes and ICD codes; a hand surgeon reading
# this page had no way to see where any of it sits in the classification they work in. This
# mapping is DysNet's own and is marked provisional on the page, because a wrong placement
# would cost more with those registries than a missing one.
OMT_PATH = pathlib.Path(__file__).parent / "tools" / "condition-omt.json"
OMT_ALL = json.loads(OMT_PATH.read_text(encoding="utf-8")) if OMT_PATH.exists() else {}
# Where each code sits in Orphanet's classification, fetched by tools/build-orphanet-hierarchy.py:
# the parent groups of a disorder, and for a group every entity it covers. Three of our codes are
# groups rather than diseases, and a card that carries a group code owes the reader the list.
# ── How common each condition is, for the order the cards are shown in ───────────────────────
# Two sources, in this order. DOT_RATES is the site's own table, each figure verified against its
# paper and carrying the basis it rests on, and it is what the map's dots are drawn from. Orphanet's
# birth prevalence (tools/build-condition-prevalence.py) fills in conditions the map draws no dots
# for. Both are per 100,000 births. A condition in neither is uncounted rather than rare, and the
# page says that where it shows it.
PREV_PATH = pathlib.Path(__file__).parent / "tools" / "condition-prevalence.json"
ORPHA_PREV = json.loads(PREV_PATH.read_text(encoding="utf-8"))["conditions"] if PREV_PATH.exists() else {}
# DOT_RATES labels that are not the card's name, resolved once and asserted below
DOT_ALIAS = {"Amelia, all forms": "Amelia", "Phocomelia, all forms": "Phocomelia",
             "Symbrachydactyly (undergrowth)": "Symbrachydactyly", "TAR syndrome": "Thrombocytopenia-absent radius (TAR)",
             "Microgastria-limb reduction": "Microgastria\u2013limb reduction",
             "Tibial aplasia-ectrodactyly": "Tibial aplasia\u2013ectrodactyly"}
HIER_PATH = pathlib.Path(__file__).parent / "tools" / "orphanet-hierarchy.json"
HIER = json.loads(HIER_PATH.read_text(encoding="utf-8")) if HIER_PATH.exists() else {"conditions": {}, "nodes": {}}


# What each card stands for, beyond its own code: every entity Orphanet files under it. The cards
# describe the groups, and the forms inside them are documented in the card rather than given one
# each, so these names, synonyms and codes have to travel with the card, into its search text, into
# the page's search keywords, and into the bibliography's labels.
SUBCONDITIONS = {}       # card code -> [(code, term)], in Orphanet's order
for _n, _d, _c, *_r in CONDITIONS:
    if not _c:
        continue
    _desc = (HIER["conditions"].get(str(_c)) or {}).get("descendants") or []
    SUBCONDITIONS[str(_c)] = [(d, (HIER["nodes"].get(d) or {}).get("term") or d) for d in _desc]
SUBCONDITION_WORDS = {
    c: " ".join(f"{t} ORPHA:{d} {d} " + " ".join((HIER["nodes"].get(d) or {}).get("synonyms") or [])
                for d, t in kids)
    for c, kids in SUBCONDITIONS.items() if kids}
# Which card documents a code, for the registers that still carry the finer codes
CARD_FOR_CODE = {str(c): str(c) for _n, _d, c, *_r in CONDITIONS if c}
for _card, _kids in SUBCONDITIONS.items():
    for _d, _t in _kids:
        CARD_FOR_CODE.setdefault(_d, _card)

# The register keeps the finer codes, because papers and registries are tagged with them. Each one is
# named by Orphanet's own term and answers to the card that documents it, so a filter never shows a
# bare number and a card's reference count covers the forms it stands for.
REG_CODE_NAMES.update({d: t for kids in SUBCONDITIONS.values() for d, t in kids if d not in REG_CODE_NAMES})
REG_CODE_NAMES = dict(sorted(REG_CODE_NAMES.items(), key=lambda kv: kv[1].lower()))



# Dot-map selector: (label, prevalence per 100,000 births, source note). Base dot density is 100 per 100,000,
# so each entry is drawn as the share rate/100 of the base dots. Figures are those of the annex table.
# Birth prevalence per 100,000 births, with the basis for each figure stated, because a number
# without its provenance invites a reader to treat an estimate as a count. The bases are:
#   measured  a population-based study of a defined population over a defined period
#   pooled    several registries combined
#   reported  a figure quoted in the literature with no population study behind it
#   derived   a parent rate multiplied by a published proportion; the arithmetic is in the note
#   none      no published rate. The condition is still listed, because a blank row is evidence
#             of a gap and an omitted row is invisible.
# (label, rate, source, basis, note)
DOT_RATES = [
    ("All limb reduction defects", 45, "EUROCAT, Europe 2003-2012", "pooled", ""),
    ("Polydactyly", 84, "northern Netherlands 1981-2010", "measured", ""),
    ("Syndactyly", 47, "northern Netherlands 1981-2010", "measured", ""),
    ("Radial ray deficiency, all forms", 18.3, "Finland (Pakkasjärvi et al.)", "measured",
     "A second Finnish population-based study, Syvänen and Raitio 2021, reports 12.2 per 100,000 "
     "(1.22 per 10,000 births) for the same country, so read this as a range of roughly 12 to 18."),
    ("Symbrachydactyly (undergrowth)", 12, "Finland", "measured", ""),
    ("Terminal transverse limb defect", 10, "REMERA (Gnansia et al. 2021)", "reported",
     "The figure REMERA states for the unilateral isolated upper-limb form, one case in 10,000 births. It is "
     "a prevalence quoted in that paper rather than measured by it, and it does not cover every terminal "
     "transverse defect, so read it as the order of magnitude for the commonest form."),
    ("Ectrodactyly (SHFM)", 5.4, "EUROCAT, Europe", "pooled", ""),
    ("Amniotic band syndrome", 5.3, "Orphanet, Europe", "pooled", ""),
    ("Ulnar hemimelia", 4.4, "Finland", "measured", ""),
    ("Poland syndrome", 1.5, "EUROCAT, Europe 2005-2012", "pooled", ""),
    ("Amelia, all forms", 1.41, "ICBDSR, 20 registries", "pooled",
     "Froster-Iskenius and Baird (Teratology, 1990) report 1.5 per 100,000 livebirths in a whole-population "
     "registry, which is the same figure within rounding."),
    ("Fibular hemimelia", 1.1, "Orphanet, worldwide", "reported", ""),
    ("Amelia of the upper limb", 0.71, "derived from ICBDSR and Froster-Iskenius & Baird 1990", "derived",
     "No study measures upper-limb amelia on its own. Froster-Iskenius and Baird found amelia to affect upper "
     "and lower limbs about equally, so half of the 1.41 per 100,000 for amelia is taken here: 0.71. It is an "
     "estimate built from two sources, not a measurement."),
    ("Amelia of the lower limb", 0.71, "derived from ICBDSR and Froster-Iskenius & Baird 1990", "derived",
     "As for the upper limb: half of amelia's 1.41 per 100,000, on the same finding of roughly equal involvement."),
    ("Phocomelia, all forms", 0.74, "Finland", "measured", ""),
    ("Holt-Oram syndrome", 0.7, "EUROCAT, Europe", "pooled", ""),
    ("TAR syndrome", 0.5, "EUROCAT, Europe", "pooled", ""),
    ("Adams-Oliver syndrome", 0.44, "Orphanet, worldwide", "reported",
     "Orphanet publishes this as a point prevalence, the share of a living population, not as a birth prevalence; "
     "it stands in here for want of any birth figure, and it comes from a case review rather than a registry."),
    ("Tibial hemimelia", 0.1, "Europe", "reported", ""),
    ("Tibial aplasia-ectrodactyly", 0.1, "Europe", "reported", ""),
    ("Tetra-amelia", 0.024, "Schwickert and Dame 2021", "reported",
     "Quoted as 2.4 per 10,000,000 births in a case report, with no population study behind it."),
    ("Cenani-Lenz syndrome", None, "", "none",
     "46 papers in PubMed and not one reports a birth prevalence."),
    ("Microgastria-limb reduction", None, "", "none",
     "Fewer than a dozen papers, all of them case reports or small series."),
    ("Radial aplasia", 2.5, "Orphanet, worldwide", "reported",
     "Orphanet's class is 1-9 per 100,000 births, of which 2.5 is the midpoint. Finnish data measure the "
     "wider group of radial ray deficiencies and find 13% of them isolated, which is close to this figure."),
    ("Roberts syndrome", None, "", "none",
     "236 papers in PubMed and not one reports a birth prevalence; about 150 cases have been described."),
]


CONDITION_RATE = {}   # card name -> (rate per 100,000 births, where it comes from)
for _lab, _r, _src, _basis, _note in DOT_RATES:
    _nm = DOT_ALIAS.get(_lab, _lab)
    if _r not in (None, "") and _nm in {c[0] for c in CONDITIONS}:
        CONDITION_RATE[_nm] = (float(_r), _src)
# Two of the map's dot classes are wider than any single card and deliberately match none:
# the total for every limb reduction defect, and the radial ray class, of which our radial
# aplasia card is the isolated part. Every other label must reach a card or the build stops.
DOT_NOT_A_CARD = {"All limb reduction defects", "Radial ray deficiency, all forms"}
_unresolved = [l for l, *_ in DOT_RATES if l not in DOT_ALIAS and l not in {c[0] for c in CONDITIONS}
               and l not in DOT_NOT_A_CARD]
if _unresolved:
    raise SystemExit(f"DOT_RATES labels that match no condition and have no alias: {_unresolved}")
_CARD_NAMES = {c[0] for c in CONDITIONS}
for _nm, _v in ORPHA_PREV.items():
    _bp = (_v or {}).get("birth_prevalence") or {}
    if _nm in _CARD_NAMES and _nm not in CONDITION_RATE and _bp.get("per_100000"):
        CONDITION_RATE[_nm] = (float(_bp["per_100000"]), f"Orphanet, {_bp.get('geo', '')}".rstrip(", "))


def _one_in(rate):
    """A rate per 100,000 births as the odds a family is actually told: one in so many births."""
    n = 100000 / rate
    step = 10 ** max(0, len(f"{int(n)}") - 2)
    return f"{int(round(n / step) * step):,}"


def condition_rate_html(name):
    """How common the condition is, in the words a family hears, with the figure behind it."""
    hit = CONDITION_RATE.get(name)
    if not hit:
        return ('<p class="cond-rate cond-rate-none">No published birth prevalence'
                '<span class="cc-rel" title="Neither our own table nor Orphanet publishes a figure for this '
                'condition. That is a gap in what has been counted, not a statement that it is the rarest thing '
                'here, and it is why these cards come last.">uncounted</span></p>')
    rate, src = hit
    return (f'<p class="cond-rate">About <strong>1 in {_one_in(rate)}</strong> births'
            f'<span class="cc-rel" title="{rate:g} per 100,000 births &middot; {html.escape(src, quote=True)}">{src}</span></p>')


# The order the cards are shown in: commonest first, and the uncounted last in alphabetical order,
# because a missing figure is not a small one.
CONDITIONS_BY_RATE = sorted(CONDITIONS, key=lambda c: (-CONDITION_RATE.get(c[0], (0,))[0], c[0]))
RATED_N = sum(1 for c in CONDITIONS if c[0] in CONDITION_RATE)
OMT = OMT_ALL.get("conditions", {})
# A card whose registers were built for an older list is a card the page half-describes. The build
# goes on, because a missing OMT row is a hand surgeon's job and must not stop a deploy, but it says
# so, and names the command that brings the fetched registers up to date.
_LAG = {
    "no place in Orphanet's classification (tools/build-orphanet-hierarchy.py)": [c[0] for c in CONDITIONS if c[2] and str(c[2]) not in HIER["nodes"]],
    "no ICD row (tools/build-condition-icd.py)": [c[0] for c in CONDITIONS if c[0] not in ICD],
    "no Orphanet prevalence row (tools/build-condition-prevalence.py)": [c[0] for c in CONDITIONS if c[2] and c[0] not in ORPHA_PREV],
    "no OMT row (tools/condition-omt.json, placed by hand)": [c[0] for c in CONDITIONS if c[0] not in OMT],
}
for _what, _names in _LAG.items():
    if _names:
        print(f"WARNING: {len(_names)} card(s) with {_what}: {_names}. Run python3 tools/update-conditions.py")



MEMBERS = [
    ("Australia", [("Aussiehands", "https://aussiehands.org/"), ("Thalidomide Australia", "https://thalidomidegroupaustralia.com")]),
    ("Austria", [("Contergan Austria", None)]),
    ("Belgium", [("A.V.S.B.", None), ("Dysmelia ASBL", "https://www.facebook.com/DysmeliaBelgium")]),
    ("Chile", [("Vitachi – Talidomida en Chile", "https://www.facebook.com/Vitachi2015/")]),
    ("France", [("Assedea", "https://www.assedea.fr")]),
    ("Germany", [("Contergan NRW", "https://www.contergan-nrw.eu/"), ("HICOHA Hamburg", "https://www.hicoha.de/"), ("Interessenverband Contergangeschädigter, Köln", "http://www.conterganverband-koeln.de/"), ("Contergangeschädigte Hessen", "https://www.contergan-hessen.de", "https://contergan-hessen.de/helfen/")]),
    ("Ireland", [("Irish Thalidomide Survivors Society", "https://irish-thalidomide.blogspot.com/")]),
    ("Italy", [("Raggiungere", "https://www.raggiungere.it", "https://www.raggiungere.it/index.php/come-aiutarci-2020/331-donazioni"), ("Thalidomidici Italiani (TAI onlus)", "https://www.taionlus.it/"), ("V.I.TA – Vittime Talidomide Italia", "https://www.vittimetalidomideitalia.it"), ("AISP – Sindrome di Poland", "https://www.sindromedipoland.org/")]),
    ("Netherlands", [("Stichting NESOS", "https://www.softenon.nl")]),
    ("Norway", [("Den Norske Thalidomide Forening", None)]),
    ("Spain", [("AVITE", "https://www.avite.org")]),
    ("Sweden", [("FfdN, the Swedish Thalidomide Society (Föreningen för de Neurosedynskadade)", "https://www.thalidomide.org/", "https://www.thalidomide.org/web/kontakt/"), ("FfdN Stockholm", "https://www.thalidomide.org/web/ffdn-stockholm-1/"), ("FfdN Väst/Skåne", "https://www.thalidomide.org/web/ffdn-vastsverigeskane/"), ("Svensk Dysmeliförening", "https://www.dysmeli.se")]),
    ("United Kingdom", [("Thalidomide Trust", "https://thalidomidetrust.org"), ("Reach", "https://www.reach.org.uk/", "https://www.reach.org.uk/support-us"), ("In Our Hands", None), ("PiP UK", "https://www.pip-uk.org"), ("Thalidomide Society", "https://thalidomidesociety.org"), ("Steps Charity", "https://steps-charity.org.uk/")]),
]

# Every sentence that counts the members is computed from MEMBERS, so a change to the list reaches
# the home page, the members page and its description in the same build. A member in a country
# this table does not know stops the build rather than being counted on the wrong continent.
CONTINENT = {"Australia": "Oceania", "Chile": "South America", "Canada": "North America", "United States": "North America",
             **{c: "Europe" for c in ("Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Ireland", "Italy",
                                      "Netherlands", "Norway", "Poland", "Portugal", "Spain", "Sweden", "Switzerland", "United Kingdom")}}
_unmapped = sorted({c for c, _ in MEMBERS} - set(CONTINENT))
if _unmapped:
    raise SystemExit(f"CONTINENT has no entry for {_unmapped}; add it so the member counts stay right")
# The associations piloting the registry under the AGM mandate of 26 August 2026. Named once, here,
# and read by the map card, the legend and the country tooltip; a name not in MEMBERS stops the build.
PILOTS = ("Assedea", "Raggiungere")
_member_names = {(o[0] if isinstance(o, (list, tuple)) else o) for _, orgs in MEMBERS for o in orgs}
_unknown_pilots = [n for n in PILOTS if not any(n.lower() in m.lower() for m in _member_names)]
if _unknown_pilots:
    raise SystemExit(f"PILOTS names {_unknown_pilots}, which MEMBERS does not list")
MEMBER_STATS = {"orgs": sum(len(v) for _, v in MEMBERS), "countries": len({c for c, _ in MEMBERS}),
                "continents": len({CONTINENT[c] for c, _ in MEMBERS}), "pilots": len(PILOTS)}
MEMBER_SENTENCE = (f"{spell(MEMBER_STATS['orgs'])} organisations across {spell(MEMBER_STATS['countries'])} countries, "
                   f"on {spell(MEMBER_STATS['continents'])} continents")

# ─────────── Bibliography (tools/bibliography.json, built by tools/build-bibliography.py) ───────────
BIB_PATH = pathlib.Path(__file__).parent / "tools" / "bibliography.json"
BIB = json.loads(BIB_PATH.read_text(encoding="utf-8")) if BIB_PATH.exists() else {"entries": []}
# A paper tagged to one of the forms is a paper about the card that documents it, so the card's code
# is added here rather than in the register: the tagging stays as the builder found it, and the site
# decides what a card covers.
for _e in BIB.get("entries", []):
    _own = [c for c in _e.get("codes", []) if c != "thal"]
    for _c in _own:
        _card = CARD_FOR_CODE.get(str(_c))
        if _card and _card not in _e["codes"]:
            _e["codes"].append(_card)
BIB_TOPIC_LABEL = {"epidemiology": "Epidemiology", "causes": "Causes & risk factors", "teratogens": "Teratogens & exposures", "meta": "Meta-analyses & systematic reviews", "review": "Reviews & guidelines", "genetics": "Genetics", "living": "Living with a limb difference", "prosthetics": "Prosthetics & technology", "clinical": "Clinical care & surgery"}


def doi_html(doi):
    """A DOI link that survives the angle brackets of the old SICI form, such as
    10.1002/1097-0223(200010)20:10<811::aid-pd927>3.0.co;2-j: percent-encoded in the address,
    escaped in the text, so the link resolves and the markup stays closed."""
    import html as _h
    href = "https://doi.org/" + doi.replace("<", "%3C").replace(">", "%3E").replace('"', "%22")
    return f'<a href="{_h.escape(href, quote=True)}" target="_blank" rel="noopener external">doi:{_h.escape(doi)}</a>'


# The registers ship a first slice as HTML (crawlable, readable without JavaScript) and the full
# set as JSON. Inlining that JSON made the two pages 477 KB and 400 KB; written as files and fetched
# after first paint, the pages are 68 KB and 83 KB and the filters come alive a moment later.
PAYLOADS = {}


def bibliography_html():
    entries = BIB.get("entries", [])
    names = dict(REG_CODE_NAMES, thal="Thalidomide embryopathy")
    codes_present = sorted({c for e in entries for c in e["codes"]}, key=lambda c: names.get(c, c))
    topics = sorted({t for e in entries for t in e["topics"]}, key=lambda t: list(BIB_TOPIC_LABEL).index(t) if t in BIB_TOPIC_LABEL else 99)
    items, records = [], []
    for e in entries:
        authors = ", ".join(e["authors"])
        link = (doi_html(e["doi"]) if e["doi"]
                else f'<a href="https://pubmed.ncbi.nlm.nih.gov/{e["pmid"]}/" target="_blank" rel="noopener external">PubMed {e["pmid"]}</a>')
        tags = "".join(f'<span class="bib-tag">{names.get(c, c)}</span>' for c in e["codes"]) + "".join(f'<span class="bib-tag bib-topic">{BIB_TOPIC_LABEL.get(t, t)}</span>' for t in e["topics"])
        via = [v for v in e.get("via", []) if v not in ("Orphanet", "DysNet", "PubMed search")]
        if via: tags += f'<span class="bib-tag bib-via">found on {", ".join(v.split(" (")[0] for v in via)}</span>'
        elif "PubMed search" in e.get("via", []): tags += '<span class="bib-tag bib-via">PubMed search</span>'
        why = e["notes"][0] if e["notes"] else ""
        text = (e["title"] + " " + authors + " " + e["journal"] + " " + str(e["year"]) + " " + why).lower().replace('"', "")
        items.append(f'<li class="bib-item" data-codes="{" ".join(e["codes"])}" data-topics="{" ".join(t.replace(" ", "_") for t in e["topics"])}" data-year="{e["year"]}" data-registries="{" ".join(e.get("rests_on", []))}" data-text="{text}">'
                     f'<p class="bib-title">{e["title"]}</p><p class="bib-meta">{authors} · <em>{e["journal"]}</em> · {e["year"]}{(" · " + e["volume"]) if e["volume"] else ""}{(":" + e["pages"]) if e["pages"] else ""} · {link}</p>'
                     f'<p class="bib-tags">{tags}</p></li>')
        records.append({"t": e["title"], "r": e.get("rests_on", []), "a": authors, "j": e["journal"], "y": e["year"], "v": e["volume"], "p": e["pages"], "d": e["doi"], "m": e["pmid"],
                        "c": e["codes"], "k": [t.replace(" ", "_") for t in e["topics"]], "w": ", ".join(v.split(" (")[0] for v in via) if via else ("PubMed search" if "PubMed search" in e.get("via", []) else ""), "n": why})
    code_opts = "".join(f'<option value="{c}">{names.get(c, c)}</option>' for c in codes_present)
    topic_chips = "".join(f'<button type="button" data-topic="{t.replace(" ", "_")}" aria-pressed="false">{BIB_TOPIC_LABEL.get(t, t)}</button>' for t in topics)
    years = sorted({e["year"] for e in entries if e["year"]})
    return f"""
    <div class="tick"></div>
    <p class="eyebrow">Bibliography · {len(entries)} references</p>
    <h2 class="h2">The literature, searchable.</h2>
    <p>Behind every condition described on this site lies a body of research: who is affected, how often, what is known and what is still missing. This bibliography gathers the peer-reviewed publications on those limb differences, and on thalidomide, the drug behind the largest cluster of them, so that families, associations and researchers can start from the same shelf. Each reference is checked against PubMed and links to its DOI. Filter by condition, theme or year, or search.</p>
    <div class="bib-controls" id="bib-controls">
      <input type="search" id="bib-q" autocomplete="off" placeholder="Search titles, authors, journals…" aria-label="Search the bibliography">
      <select id="bib-code" autocomplete="off" aria-label="Filter by condition"><option value="">All conditions</option>{code_opts}</select>
      <div class="finder-chips bib-focus" id="bib-focus"><button type="button" data-code="thal" aria-pressed="false">Thalidomide only</button><button type="button" data-exclude="thal" aria-pressed="false">Without thalidomide</button><span class="bib-focus-help">the drug, its embryopathy and its survivors: show only those papers, or leave them out</span></div>
      <div class="finder-chips" id="bib-topics">{topic_chips}</div>
      <div class="bib-years"><label for="bib-from">Published from</label> <input type="number" id="bib-from" min="{years[0]}" max="{years[-1]}" placeholder="{years[0]}" inputmode="numeric" autocomplete="off" aria-label="From year"> <label for="bib-to">to</label> <input type="number" id="bib-to" min="{years[0]}" max="{years[-1]}" placeholder="{years[-1]}" inputmode="numeric" autocomplete="off" aria-label="To year"> <span class="bib-focus-help">{years[0]}–{years[-1]}</span></div>
      <p class="bib-count" role="status"><strong id="bib-n">{len(entries)}</strong> of {len(entries)} references · <button type="button" id="bib-reset">Reset</button></p>
    </div>
    <ol class="bib-list" id="bib-list">{"".join(items[:60])}</ol>
    <script type="application/json" id="bib-data" data-src="/data/bibliography-index.json"></script>{PAYLOADS.__setitem__("bibliography-index.json", json.dumps({"codes": {c: names.get(c, c) for c in codes_present}, "topics": {t.replace(" ", "_"): BIB_TOPIC_LABEL.get(t, t) for t in topics}, "items": records}, ensure_ascii=False, separators=(",", ":"))) or ""}
    <p class="bib-more-row"><button type="button" class="btn btn-ghost" id="bib-more" hidden>Show all matching references</button></p>
    <p class="annex-note">Built {BIB.get("built", "")} from three trusted sources: the references Orphanet cites in its epidemiology data (Orphadata, CC BY 4.0), the sources of the prevalence annex, and the publications our member associations put forward on their own websites. Titles, authors and DOIs come from PubMed (NCBI E-utilities) or Crossref, never typed by hand. Every paper found on a member website was screened to keep only articles about the conditions described on this site. Three fixed PubMed queries, re-run at each build, add the thalidomide literature (title query: thalidomide with teratogenicity, embryopathy, birth defects, phocomelia, survivors, limb, malformation, Contergan, victims, disaster or tragedy), the systematic reviews and meta-analyses on our conditions (publication type or title, combined with the condition names), and the literature on causes and risk factors (title terms such as aetiology, risk factors, teratogen, maternal, exposure, environmental, pesticides, clusters or vascular disruption, combined with the condition names). The registries listed on Orphanet for our conditions were crawled the same way as member websites. Suggest a reference: <a href="mailto:info@dysnet.org?subject=Bibliography">info@dysnet.org</a>. <a href="/data/bibliography.json">Download the data (JSON, CC BY 4.0)</a>.</p>
"""

# Register 4 · care centres shown on the landing map. Centres named by a member association or visited by the board,
# and, where DysNet has no member association, centres whose own institutional page states congenital limb difference
# in its scope (those carry via_verb "verified from"),
# plus the children's hand clinics of the BSSH directory that Reach points families to; URLs checked; coordinates from OpenStreetMap Nominatim (see tools/care-centres.json for the audit trail).
CARE_PATH = pathlib.Path(__file__).parent / "tools" / "care-centres.json"
_CARE_RAW = json.loads(CARE_PATH.read_text(encoding="utf-8")) if CARE_PATH.exists() else {}
CARE_CENTRES = _CARE_RAW.get("centres", [])
CARE_CENTRES_BUILT = _CARE_RAW.get("built", "")


# A note printed under a centre's entry, where the register alone would leave a question open.
CENTRE_NOTES = {
    "EX-Center, national knowledge and rehabilitation centre for multiple limb deficiencies":
        ('EX-Center is the Swedish knowledge and rehabilitation centre for children and adults with multiple limb loss, whether '
         'congenital limb deficiency or amputation, in operation since 1993 and run as a cooperation between FfdN, the Swedish '
         'Thalidomide Society, and the Amputation and Dysmelia Center at Ottobock Care. '
         '<a href="/assets/ex-center-brochure-2025-en.pdf" download>Download the EX-Center brochure</a> (PDF, English, 1.7 MB).'),
}


def centres_html():
    out, last = [], None
    for c in sorted(CARE_CENTRES, key=lambda c: (c["country"], c["city"], c["name"])):
        if c["country"] != last:
            n = sum(1 for x in CARE_CENTRES if x["country"] == c["country"])
            out.append(f'<h2 class="h3" style="margin-top:var(--space-4)">{c["country"]} <span class="badge live">{n}</span></h2>')
            last = c["country"]
        host = c["url"].split("//")[-1].split("/")[0].removeprefix("www.") if c.get("url") else ""
        link = f'<a href="{c["url"]}" target="_blank" rel="noopener external">{host}</a>' if c.get("url") else "no public website"
        via = f'<a href="{c["via_url"]}" target="_blank" rel="noopener external">{c["via"]}</a>' if c.get("via_url") else c.get("via", "")
        verb = c.get("via_verb") or "named by"
        local = f'<p class="src">{c["name_local"]}</p>' if c.get("name_local") else ""
        note = f'<p class="entry-note">{CENTRE_NOTES[c["name"]]}</p>' if c["name"] in CENTRE_NOTES else ""
        # a status an authority has given the centre (or refused it), stated with the decision it rests on
        des = c.get("designation")
        if des:
            note += (f'<p class="entry-note">{des["text"]} <a href="{des["url"]}" target="_blank" rel="noopener external">'
                     f'{des.get("source", "Source")} ↗</a></p>')
        out.append(f'<article class="entry"><h3>{c["name"]} <span class="badge">{c["type"]}</span></h3>{local}'
                   f'<p>{c["specialism"]}</p>{note}<p class="src">{c["city"]}, {c["country"]} · {link} · {verb} {via}</p></article>')
    return "".join(out)


# Register 3 · research teams derived from the bibliography (tools/build-researchers.py; PubMed affiliations of first and last authors).
RES_PATH = pathlib.Path(__file__).parent / "tools" / "researchers.json"
RESEARCHERS = json.loads(RES_PATH.read_text(encoding="utf-8")) if RES_PATH.exists() else {"teams": []}
REG_PATH = pathlib.Path(__file__).parent / "tools" / "orphanet-registries.json"
ORPHA_REGS = json.loads(REG_PATH.read_text(encoding="utf-8")) if REG_PATH.exists() else {"registries": []}
# Which codes' registry lists have actually been read from Orphanet. A code outside this set has not
# been checked, and saying "no registry records it" of it would be a claim we have not earned.
REG_CHECKED = set(ORPHA_REGS.get("codes_checked") or [])
REG_COUNTS = ORPHA_REGS.get("orphanet_registry_counts") or {}
# How the registries relate to our conditions, counted here so the demands page and the register
# page quote the same split whenever the Orphanet records are refreshed.
REG_SPLIT = {"total": len(ORPHA_REGS.get("registries", [])),
             "direct": sum(1 for r in ORPHA_REGS.get("registries", []) if r.get("direct"))}
REG_SPLIT["other"] = REG_SPLIT["total"] - REG_SPLIT["direct"]


def researchers_html():
    teams = RESEARCHERS.get("teams", [])
    names = dict(REG_CODE_NAMES, thal="Thalidomide embryopathy")
    out, last = [], None
    for t in sorted(teams, key=lambda t: (t["country"] or "zz", -t["papers"], t["institution"])):
        c = t["country"] or "Country not stated"
        if c != last:
            n = sum(1 for x in teams if (x["country"] or "Country not stated") == c)
            out.append(f'<h2 class="h3" style="margin-top:var(--space-4)">{c} <span class="badge live">{n}</span></h2>'); last = c
        rep = t["representative"]
        link = doi_html(rep["doi"]) if rep.get("doi") else f'<a href="https://pubmed.ncbi.nlm.nih.gov/{rep["pmid"]}/" target="_blank" rel="noopener external">PubMed {rep["pmid"]}</a>'
        tags = "".join(f'<span class="bib-tag">{names.get(c2, c2)}</span>' for c2 in t["codes"] if c2 in names)
        yrs = f'{t["years"][0]}–{t["years"][1]}' if t["years"][0] != t["years"][1] else str(t["years"][0])
        where = []
        if t.get("address"): where.append(t["address"])
        if t.get("contact"): where.append(f'<a href="mailto:{t["contact"]}">{t["contact"]}</a>')
        where = f'<p class="src">{" · ".join(where)}</p>' if where else ""
        out.append(f'<article class="entry"><h3>{t["institution"]} <span class="badge">{t["papers"]} publications · {yrs}</span></h3>'
                   f'<p>Authors on our bibliography: {", ".join(t["authors"])}. Most recent: <em>{rep["title"]}</em> ({rep["year"]}), {link}.</p>'
                   f'{where}<p class="bib-tags">{tags}</p></article>')
    return "".join(out)


# Register 5 · substances and products with effects on the unborn child (tools/build-teratogens.py → tools/teratogens.json)
TERA_PATH = pathlib.Path(__file__).parent / "tools" / "teratogens.json"
TERA = json.loads(TERA_PATH.read_text(encoding="utf-8")) if TERA_PATH.exists() else {"entries": [], "sources": {}, "counts": {}}
TERA_LEVEL = {"known": "Known", "presumed": "Presumed", "suspected": "Suspected"}
TERA_KIND = {"chemical": "Chemical", "medicine": "Medicine", "product": "Consumer product"}
TERA_USE = {"food": "Food and drink", "construction": "Building and construction", "goods": "Manufactured goods",
            "cosmetics": "Cosmetics and personal care", "cleaning": "Cleaning and household",
            "agriculture": "Agriculture and pest control", "fuel": "Fuel and vehicles"}


# Square brackets do real work in chemical names (benzo[a]pyrene) and sometimes carry a
# meaningful qualifier (lead powder; [particle diameter < 1 mm]), so only the administrative
# notes the source lists append to a name are removed: OEHHA's listing history, and the
# footnote markers an Annex VI row uses when it covers several forms.
TERA_NAME_NOISE = re.compile(r"\s*\[(?:Basis for listing[^\]]*|This substance is identified[^\]]*|\d)\]"
                             r"|\s*\(\s*NOTE:.*$", re.I | re.S)


def tera_display_name(e):
    n = TERA_NAME_NOISE.sub("", e["name"]).strip(" ;,")
    return n if len(n) <= 90 else n.split(";")[0].strip()


def tera_status_chips(e):
    chips = []
    clp = next((x for x in e["sources"] if x["code"] == "clp"), None)
    if clp:
        cat = clp["category"].replace("Repr. ", "")
        chips.append(("EU: hazard label required", "st-label"))
        if cat in ("1A", "1B"):
            chips += [("EU: not supplied to the public above limits", "st-ban"), ("EU: prohibited in cosmetics", "st-ban"),
                      ("EU: not approvable as a pesticide", "st-ban"), ("EU: workplace controls", "st-work")]
        else:
            chips += [("EU: sale to the public allowed", "st-ok"), ("EU: cosmetics case by case", "st-warn")]
    if any(x["code"] == "p65" for x in e["sources"]):
        chips.append((f"California: delisted {e['delisted']}, no warning required", "st-ok") if e.get("delisted")
                     else ("California: warning required", "st-warn"))
    if clp and cat in ("1A", "1B"): chips.append(("ChemFORWARD: band F by list screening", "st-ban"))
    if e.get("efsa"): chips.append((f"EFSA: {e['efsa']['value'].split(';')[0].lower()}", "st-label"))
    codes = {x["code"] for x in e["sources"]}
    for place, val in e["jurisdictions"].items():
        if (place == "California (USA)" and "p65" in codes) or (place == "EU / EEA" and "clp" in codes): continue
        text = " ".join(val.values()) if isinstance(val, dict) else val
        short = ("authorised with a pregnancy prevention programme" if "programme" in text else "contraindicated in pregnancy" if "ontraindicated" in text else "REMS programme" if "REMS" in text else "boxed warning" if "boxed warning" in text else "pregnancy warning mandatory" if "mandatory" in text else "legal, no pregnancy warning" if "no EU-wide" in text else "legal, pack warnings" if "pack" in text else text.split(";")[0][:50])
        cls = "st-ban" if "contraindicated" in short else "st-warn" if ("warning" in short or "REMS" in short or "programme" in short) else "st-ok"
        chips.append((f"{place.replace(' / EEA', '').replace(' (USA)', '')}: {short}", cls))
    return chips


TERA_DEC_CLS = {"approved": "st-warn", "pending": "st-warn", "refused": "st-ban", "public_supply_banned": "st-ban",
                "cosmetics_banned": "st-ban", "cosmetics_restricted": "st-warn",
                "authorisation_required": "st-ban", "eliminated": "st-ban", "restricted": "st-ban",
                "unintentional": "st-label", "banned_somewhere": "st-ban"}


def tera_paper_chip(e):
    """A classification is an administrative act; a DOI is a study anyone can go and read."""
    n = e.get("paper_count") or 0
    if not n:
        return ""
    label = f'Peer-reviewed: {n} paper' + ("s" if n != 1 else "")
    if e.get("paper_cochrane_n"):
        label += f', incl. {e["paper_cochrane_n"]} Cochrane'
    return f'<span class="st dec st-doi">{label}</span>'


def tera_paper_lines(e):
    if not e.get("papers"):
        return []
    out = []
    for x in sorted(e["papers"], key=lambda x: -int(bool(x.get("cochrane"))))[:3]:
        cite = f'{x["title"]}' + (f' <span class="fine">{x["journal"]}, {x["year"]}</span>' if x.get("journal") else "")
        link = (f' <a href="https://doi.org/{x["doi"]}" target="_blank" rel="noopener external">doi:{x["doi"]} ↗</a>'
                if x.get("doi") else
                (f' <a href="https://pubmed.ncbi.nlm.nih.gov/{x["pmid"]}/" target="_blank" rel="noopener external">PubMed ↗</a>' if x.get("pmid") else ""))
        out.append(f'<li>{"<strong>Cochrane review:</strong> " if x.get("cochrane") else ""}{cite}{link}</li>')
    more = (e.get("paper_count") or 0) - min(3, len(e["papers"]))
    if more > 0 and e.get("paper_query"):
        out.append(f'<li><a href="{e["paper_query"]}" target="_blank" rel="noopener external">'
                   f'all {e["paper_count"]} on PubMed ↗</a></li>')
    return out


def tera_dec_chips(e):
    return "".join(f'<span class="st dec {TERA_DEC_CLS.get(d["verdict"], "st-label")}">{d["where"]}: {d["tag"]}</span>'
                   for d in e.get("decisions", []))


def tera_dec_lines(e):
    out = []
    for d in e.get("decisions", []):
        line = f'<strong>{d["tag"]}</strong> &mdash; {d["authority"]}' + (f', {d["detail"]}' if d.get("detail") else "")
        if d.get("url"):
            line += f' <a href="{d["url"]}" target="_blank" rel="noopener external">source ↗</a>'
        out.append(f"<li>{line}</li>")
    return out


def tera_item_html(e):
    srcs = []
    for src in e["sources"]:
        if src["code"] == "clp": lab, det = "EU CLP", f'{src["category"]} · {", ".join(src["statements"])}'
        elif src["code"] == "p65": lab, det = "California Prop 65", src.get("toxicity", "") + (f' · listed {src["listed"][:4]}' if src.get("listed") else "")
        elif src["code"] == "ema": lab, det = "EMA", "pregnancy prevention programme or contraindication"
        elif src["code"] == "who": lab, det = "WHO", "fact sheet on congenital disorders"
        elif src["code"] == "efsa": lab, det = "EFSA", "health-based guidance value"
        elif src["code"] == "nite": lab, det = "Japan NITE", ", ".join(src["statements"]) + (f' · classified {src["classified"]}' if src.get("classified") else "")
        else: lab, det = "DysNet bibliography", "peer-reviewed evidence"
        srcs.append(f'<span class="tera-src src-{src["code"]}">{lab}<small> · {det}</small></span>')
    reg = e.get("registry")
    reg_html = (f'<p class="tera-registry">A pregnancy registry is recruiting for {reg["medicine"]}: '
                f'<a href="{reg["url"]}" target="_blank" rel="noopener external">{reg["name"]}</a>'
                + (f' &middot; {reg["phone"]}' if reg.get("phone") else "")
                + ' <span class="fine">listed by the FDA, which does not endorse it</span></p>') if reg else ""
    chips = tera_dec_chips(e) + tera_paper_chip(e) + "".join(f'<span class="st {cls}">{txt}</span>' for txt, cls in tera_status_chips(e))
    uses = "".join(f'<span class="use use-{u}">{TERA_USE.get(u, u)}</span>' for u in e.get("uses", []))
    details = tera_dec_lines(e) + tera_paper_lines(e)
    if e.get("source_note"):
        details.append(f'<li><strong>California&rsquo;s note:</strong> {e["source_note"]}</li>')
    for src in e["sources"]:
        line = src["label"] + ": " + (f'{src["category"]}, {", ".join(src["statements"])}' + (f', applies from {src["applies_from"]}' if src.get("applies_from") else "") if src["code"] == "clp" else
                                    f'{src.get("toxicity", "")}' + (f', listed {src["listed"]}' if src.get("listed") else "") + (f', via {src["mechanism"]}' if src.get("mechanism") else "") if src["code"] == "p65" else
                                    ", ".join(src["statements"]) + (f', classified in the {src["classified"]} fiscal year' if src.get("classified") else "") if src["code"] == "nite" else src.get("note", ""))
        if src.get("url"): line += f' <a href="{src["url"]}"{" target=_blank rel=\"noopener external\"" if src["url"].startswith("http") else ""}>source ↗</a>'
        details.append(f"<li>{line}</li>")
    for place, val in e["jurisdictions"].items():
        txt = " ".join(val.values()) if isinstance(val, dict) else val
        if place == "California (USA)" and e.get("delisted"):
            txt = f"Listed as a developmental toxicant and delisted on {e['delisted']}; no warning is required today. " + txt
        details.append(f"<li><strong>{place}:</strong> {txt}</li>")
    clp = next((x for x in e["sources"] if x["code"] == "clp"), None)
    if clp and clp["category"].replace("Repr. ", "") in ("1A", "1B"):
        details.append('<li><strong>ChemFORWARD:</strong> meets the list-screening criterion for the F hazard band (Annex VI Repr. 1), per Chemical Hazard Rating Guidance v2.2, May 2024.</li>')
    if e.get("medicinal") and e.get("atc"):
        details.append(f'<li><strong>Medicine:</strong> {("“" + e["medicine_evidence"] + "” ") if e.get("medicine_evidence") else ""}ATC {", ".join(e["atc"])}, the WHO classification of medicines.</li>')
    for u, sent in sorted((e.get("use_evidence") or {}).items()):
        details.append(f'<li><strong>{TERA_USE.get(u, u)}:</strong> “{sent}” <a href="{e["wiki"]}" target="_blank" rel="noopener external">Wikipedia ↗</a></li>')
    if e.get("cas"):
        details.append(f'<li><strong>GreenScreen:</strong> check the <a href="https://registry.greenscreenchemicals.org/" target="_blank" rel="noopener external">assessment registry</a> for CAS {e["cas"]}.</li>')
    ids = " · ".join(x for x in (f"CAS {e['cas']}" if e.get("cas") else "", f"EC {e['ec']}" if re.fullmatch(r"\d{3}-\d{3}-\d", (e.get("ec") or "").strip()) else "",
                                 ("ATC " + ", ".join(e["atc"][:3])) if e.get("atc") else "") if x)
    return (f'<li class="tera-item"><div class="tera-head"><span class="tera-level tera-{e["level"]}">{TERA_LEVEL[e["level"]]}</span><h3 class="tera-name">{f'<a href="{e["wiki"]}" target="_blank" rel="noopener external" title="Wikipedia">{tera_display_name(e)}</a>' if e.get("wiki") else tera_display_name(e)}</h3><span class="badge">{TERA_KIND.get(e["kind"], e["kind"])}</span>{'<span class="badge badge-med">Medicine</span>' if e.get("medicinal") and e["kind"] != "medicine" else ""}{f"<span class=tera-ids>{ids}</span>" if ids else ""}</div>'
            f'<div class="tera-srcs">{"".join(srcs)}</div>{f"<div class=tera-uses>{uses}</div>" if uses else ""}<div class="tera-status">{chips}</div>{reg_html}'
            f'<details class="tera-details"><summary>Details and legal basis</summary><ul>{"".join(details)}</ul></details></li>')


def teratogens_html():
    E = sorted(TERA.get("entries", []), key=lambda e: ({"known": 0, "presumed": 1, "suspected": 2}[e["level"]], re.sub(r"^[^a-z]+", "", tera_display_name(e).lower())))
    def compact(e):
        srcs = []
        for src in e["sources"]:
            if src["code"] == "clp": srcs.append({"c": "clp", "cat": src["category"].replace("Repr. ", ""), "st": src["statements"], "from": src.get("applies_from", ""), "u": src.get("url", "")})
            elif src["code"] == "p65": srcs.append({"c": "p65", "tox": src.get("toxicity", ""), "on": src.get("listed", ""), "via": src.get("mechanism", "")})
            elif src["code"] == "nite": srcs.append({"c": "nite", "st": src["statements"], "fy": src.get("classified", ""), "u": src.get("url", "")})
            else: srcs.append({"c": src["code"], "note": src.get("note", ""), "u": src.get("url", "")})
        # jurisdiction texts for CLP and Proposition 65 are templated in site.js; others travel with the record
        codes = set(e["source_codes"])
        jur = {k: (" ".join(v.values()) if isinstance(v, dict) else v) for k, v in e["jurisdictions"].items() if not ((k == "California (USA)" and "p65" in codes) or (k == "EU / EEA" and "clp" in codes))}
        return {"n": tera_display_name(e), "f": e["name"], "cas": e.get("cas", ""), "ec": e.get("ec", ""), "k": e["kind"], "del": e.get("delisted", ""), "efsa": e.get("efsa", {}), "med": 1 if e.get("medicinal") else 0, "atc": e.get("atc", [])[:3], "mev": e.get("medicine_evidence", ""), "l": e["level"], "u": e.get("uses", []), "ue": e.get("use_evidence", {}), "s": e["source_codes"], "src": srcs, "jur": jur, "w": e.get("wiki") or "",
                "pc": e.get("paper_count") or 0, "pcn": e.get("paper_cochrane_n") or 0, "pcoch": 1 if e.get("paper_cochrane") else 0, "pq": e.get("paper_query", ""),
                "pp": [{"t": x["title"], "j": x.get("journal", ""), "y": x.get("year", ""), "d": x.get("doi", ""), "m": x.get("pmid", ""), "c": 1 if x.get("cochrane") else 0}
                       for x in sorted(e.get("papers") or [], key=lambda x: -int(bool(x.get("cochrane"))))[:3]],
                "reg": ({"m": e["registry"]["medicine"], "n": e["registry"]["name"], "u": e["registry"]["url"], "p": e["registry"].get("phone", "")} if e.get("registry") else 0),
                "dec": [{"c": d["code"], "v": d["verdict"], "w": d["where"], "t": d["tag"], "d": d.get("detail", "")}
                        | ({"u": d.get("url", "")} if d["code"] == "eu-ppp" else {}) for d in e.get("decisions", [])]}
    records = [compact(e) for e in E]
    html_first = [tera_item_html(e) for e in E[:40]]
    c = TERA.get("counts", {})
    use_chips = "".join(f'<button type="button" class="use use-{k}" data-use="{k}" aria-pressed="false">{lab} <small>{sum(1 for e in E if k in (e.get("uses") or []))}</small></button>' for k, lab in TERA_USE.items())
    DEC_CHIPS = [("approved", "Approved as a pesticide in the EU"), ("refused", "Refused as a pesticide in the EU"),
                 ("public_supply_banned", "Not to be sold to the public in the EU"), ("cosmetics_banned", "Banned in cosmetics in the EU"),
                 ("cosmetics_restricted", "Restricted in cosmetics in the EU"), ("authorisation_required", "Needs an EU authorisation"),
                 ("banned_somewhere", "Banned by a country"), ("eliminated", "Eliminated worldwide by treaty"), ("restricted", "Restricted worldwide by treaty")]
    PAPER_CHIPS = [("paper", "Has a peer-reviewed paper here"), ("cochrane", "Has a Cochrane review")]
    dec_n = {}
    for x in E:
        for d in x.get("decisions", []):
            dec_n[d["verdict"]] = dec_n.get(d["verdict"], 0) + 1
    dec_chips = "".join(f'<button type="button" data-dec="{code}" aria-pressed="false">{lab} <small>{dec_n.get(code, 0)}</small></button>'
                        for code, lab in DEC_CHIPS if dec_n.get(code))
    paper_n = {"paper": sum(1 for x in E if x.get("paper_count")), "cochrane": sum(1 for x in E if x.get("paper_cochrane"))}
    dec_chips += "".join(f'<button type="button" data-paper="{code}" aria-pressed="false">{lab} <small>{paper_n[code]}</small></button>'
                         for code, lab in PAPER_CHIPS if paper_n[code])
    src_chips = "".join(f'<button type="button" data-source="{code}" aria-pressed="false">{ {"clp": "EU harmonised classification", "nite": "Japan, government classification", "p65": "California Proposition 65", "ema": "EMA medicines", "efsa": "EFSA food values", "who": "WHO", "bib": "DysNet bibliography"}.get(code, code) }</button>' for code in ("clp", "nite", "p65", "ema", "efsa", "who", "bib"))
    return f"""
    <div class="bib-controls" id="tera-controls">
      <input type="search" id="tera-q" autocomplete="off" placeholder="Search a substance, CAS number or medicine…" aria-label="Search the register">
      <p class="bib-focus-help" style="margin:0.2rem 0 0.4rem">Listed by</p>
      <div class="finder-chips" id="tera-sources">{src_chips}</div>
      <p class="bib-focus-help" style="margin:0.4rem 0 0.4rem">What an authority decided</p>
      <div class="finder-chips" id="tera-decisions">{dec_chips}</div>
      <p class="bib-focus-help" style="margin:0.4rem 0 0.4rem">Level of evidence · Type</p>
      <div class="finder-chips" id="tera-levels"><button type="button" data-level="known" aria-pressed="false">Known</button><button type="button" data-level="presumed" aria-pressed="false">Presumed</button><button type="button" data-level="suspected" aria-pressed="false">Suspected</button>
        <span style="width:0.6rem"></span><button type="button" data-kind="chemical" aria-pressed="false">Chemicals</button><button type="button" data-kind="medicine" aria-pressed="false">Medicines</button><button type="button" data-kind="product" aria-pressed="false">Consumer products</button></div>
            <p class="bib-focus-help" style="margin:0.4rem 0 0.4rem">Where the substance is used, according to its Wikipedia article</p>
      <div class="finder-chips tera-use-chips" id="tera-uses">{use_chips}</div>
      <p class="bib-count" role="status"><strong id="tera-n">{len(E)}</strong> of {len(E)} entries · <button type="button" id="tera-reset">Reset</button></p>
    </div>
    <p class="tera-legend">Names link to Wikipedia where an article exists ({sum(1 for e in E if e.get("wiki"))} of {len(E)}). <span class="badge badge-med">Medicine</span> marks a substance used as a medicine, checked against the WHO ATC classification and the substance’s own article ({sum(1 for e in E if e.get("medicinal"))} of {len(E)}). Coloured tags say where the substance is used in everyday products, read from its Wikipedia article ({sum(1 for e in E if e.get("uses"))} of {len(E)}); open <em>Details</em> for the sentence each tag comes from. <span class="st st-label">hazard label required</span> <span class="st st-ban">banned or restricted</span> <span class="st st-warn">warning, programme or conditions</span> <span class="st st-ok">allowed without pregnancy-specific rule</span> <span class="st st-work">workplace exposure limits</span> · Open <em>Details and legal basis</em> on any entry for the exact rule and the source record.</p>
    <ol class="bib-list tera-list" id="tera-list">{"".join(html_first)}</ol>
    <p class="bib-more-row"><button type="button" class="btn btn-ghost" id="tera-more" hidden>Show all matching entries</button></p>
    <script type="application/json" id="tera-data" data-src="/data/teratogens-index.json"></script>{PAYLOADS.__setitem__("teratogens-index.json", json.dumps(records, ensure_ascii=False, separators=(",", ":"))) or ""}
    <p class="annex-note">Built {TERA.get("built", "")}. Sources: {c.get("clp", 0)} EU harmonised entries with a hazard statement for the unborn child (CLP Annex VI, ATP23), {c.get("p65", 0)} developmental toxicants on California's Proposition 65 list, {c.get("ema", 0)} medicines under EMA pregnancy prevention programmes or contraindications, plus alcohol (WHO) and tobacco smoking (peer-reviewed literature). {c.get("both_clp_and_p65", 0)} substances appear on both the EU and the Californian lists. Decisions come from four more public registers, read {c.get("legal_read", "")}: the EU Pesticides Database of DG SANTE, REACH Annex XIV and Annex XVII entry 30 as consolidated in Regulation 1907/2006, Annexes II and III of the cosmetics Regulation 1223/2009, the Stockholm Convention&rsquo;s annexes, and the national bans and severe restrictions notified to the Rotterdam Convention. The two conventions publish names rather than identifiers, so those two are matched on name; the EU sources are matched on CAS number. The Rotterdam and Stockholm listings are assembled in the browser rather than served as data, so they are captured rather than fetched, and the capture is dated in <a href="/data/teratogens.json">the data file</a>. {c.get("nite", 0)} entries also carry the Japanese government&rsquo;s own GHS classification, made by the National Institute of Technology and Evaluation for the ministries, {c.get("nite_not_in_clp", 0)} of them with no EU harmonised entry; ECHA&rsquo;s site refuses automated requests, so those are read through <a href="https://pubchem.ncbi.nlm.nih.gov/" target="_blank" rel="noopener external">PubChem</a>, which republishes them, and matched on CAS number alone. Read {c.get("nite_read", "")}. The register takes assessments made by public authorities: the self-classifications companies notify for their own products are deliberately not used. <a href="/data/teratogens.json">Download the data (JSON, CC BY 4.0)</a>. Report an error or a missing substance: <a href="mailto:info@dysnet.org?subject=Teratogens%20register">info@dysnet.org</a>.</p>
"""

BOARD = [
    ("Claudio Pirola", "Chair · Italy", "Joined Raggiungere in 1999; at DysNet since its 2012 foundation. Carries representation, external voice and member relations.", "CP", "claudio.pirola@dysnet.org", "Mission 3 · Voice"),
    ("Dr Loïc Rigal", "Deputy Chair · France", "Doctor in pharmaceutical law and patient advocate. Elected board member of the French association Assedea. Deputy Chair since the general assembly of 26 August 2026, carrying the registry mission.", "LR", "", "Mission 2 · Registry"),
    ("Michaela Moik", "Thalidomide patient expert · Austria", "Thalidomide survivor, co-founder of the Austrian thalidomide self-help group, former youth social worker in Vienna.", "MM", "michi.moik@dysnet.org", "Member relations"),
    ("Monika Eisenberg-Geginat", "Secretary · Germany", "Thalidomide survivor, former head teacher, family therapist specialised in the protection of disabled children.", "ME", "moni.eisenberg@dysnet.org", "Statutes · AGM"),
    ("Salvatore Giambruno", "Treasurer · Italy", "Past president of Raggiungere and of LEDHA; a career in sales management; parent of a daughter with dysmelia.", "SG", "sal.giambruno@dysnet.org", "Accounts"),
    ("Tobias Arndt", "Chief Operating Officer · Belgium", "IT expert and researcher, author on electronic commerce; supporting thalidomide projects across Europe since 2007.", "TA", "tobias.arndt@dysnet.org", "Operations"),
]


def person_card(name, role, bio, init, email, chip):
    _person = {"@type": "Person", "name": name, "jobTitle": role, "memberOf": {"@type": "NGO", "name": BRAND, "url": SITE + "/"}}
    if email: _person["email"] = email          # omitted rather than null when a member publishes no address
    PEOPLE_LD.append(_person)
    return f"""<div class="card person person-flip" tabindex="0">
      <div class="faces">
        <div class="face front">
          <div class="avatar">{init}</div>
          <h3 class="h4">{name}</h3>
          <p class="role">{role}</p>
          <p><span class="chip">{chip}</span></p>
        </div>
        <div class="face back">
          <h3 class="h4">{name}</h3>
          <p>{bio}</p>
          {f'<p><a href="mailto:{email}">{email}</a></p>' if email else '<p><a href="/contact/">Write via the contact page</a></p>'}
        </div>
      </div>
    </div>"""

PAGES = {}

# ────────────────────────────── HOME ──────────────────────────────
PAGES["/"] = {
    "title": "DysNet · The dysmelia network — knowledge, registry and voice for congenital limb differences",
    "desc": DESC_DEFAULT,
    "is_home": True,
    "body": f"""
__MAP_HERO__

<section class="aud-section">
  <div class="container">
    <div class="grid cols-4 aud-grid">
      <div class="card acc-library"><h2 class="h4">For families</h2><p>Understand the diagnosis and find the association near you.</p><p class="go">Start here →</p><a class="cover" href="/knowledge/understanding-dysmelia/" aria-label="For families: understanding dysmelia"></a></div>
      <div class="card acc-research"><h2 class="h4">For clinicians</h2><p>Reference centres, expert registers and the bibliography.</p><p class="go">Care centres →</p><a class="cover" href="/knowledge/care-centres/" aria-label="For clinicians: care centres"></a></div>
      <div class="card acc-studies"><h2 class="h4">For researchers</h2><p>Studies, registries and how to be listed as a researcher.</p><p class="go">The registry →</p><a class="cover" href="/registry/" aria-label="For researchers: the registry"></a></div>
      <div class="card acc-centres"><h2 class="h4">For associations</h2><p>Join the network, feed the registers, share your studies.</p><p class="go">Membership →</p><a class="cover" href="/about/members/" aria-label="For associations: membership"></a></div>
    </div>
  </div>
</section>

<section>
  <div class="container">
    {opener("01", "Five registers", "What is known, being studied, and where expertise lives.")}
    <p>Five living registers, each maintained by a named volunteer and dated, so families and clinicians always know how current the information is.</p>
    <div class="grid cols-4" style="margin-top:var(--space-4)">
      <div class="card acc-library">
        <h3 class="h4"><a href="/knowledge/bibliography/">Bibliography</a></h3>
        <p>Peer-reviewed publications on our conditions, searchable by condition, theme and year.</p>
        <p class="meta">Updated August 2026</p>
      </div>
      <div class="card acc-studies">
        <h3 class="h4"><a href="/knowledge/registries/">Registries</a></h3>
        <p>The registries that already record our conditions, from EUROCAT to the French population registries.</p>
        <p class="meta">Updated August 2026</p>
      </div>
      <div class="card acc-research">
        <h3 class="h4"><a href="/knowledge/researchers/">Researchers</a></h3>
        <p>Who works on limb difference, where, and how to reach them.</p>
        <p class="meta">Updated August 2026</p>
      </div>
      <div class="card acc-centres">
        <h3 class="h4"><a href="/knowledge/care-centres/">Care centres</a></h3>
        <p>Reference and competence centres, in Europe and beyond.</p>
        <p class="meta">Updated August 2026</p>
      </div>
      <div class="card acc-centres">
        <h3 class="h4"><a href="/knowledge/teratogens/">Teratogens register</a></h3>
        <p>Substances of concern for the unborn child, by source and by jurisdiction.</p>
        <p class="meta">New</p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="sheet sheet-cta">
    <div class="tick" style="background:#4cc42c"></div>
    <p class="eyebrow">02 · Flagship</p>
    <h2 class="h2-lg">The first international registry of limb malformations, owned by patients themselves.</h2>
    <p>Research on limb agenesis is starved of data. DysNet carries the first international, interoperable registry developed with member associations and replicable for other rare conditions. This is what membership returns to families.</p>
    <p style="margin-top:var(--space-3)"><a class="btn btn-light" href="/registry/">Discover the registry</a></p>
  </div>
</section>

<section>
  <div class="container">
    {opener("03", "One voice", "Where European decisions are made, families are in the room.")}
    <p>DysNet holds chosen seats at EURORDIS, the European Disability Forum and ERN BOND, each with a named delegate and a written report to members after every meeting.</p>
    <p>In every one of those rooms we carry the same <a href="/voice/">five demands</a>: recognise dysmelia as a public health priority; cover prosthetics and make equipment affordable; fund registries that cover whole populations and give each person their own record; look for the causes, not only the numbers; and act on the substances that harm the unborn child before the harm is done. Each demand says what we ask of public authorities, and what would count as progress.</p>
    <p style="margin-top:var(--space-3)"><a class="btn btn-ghost" href="/voice/">Read the five demands</a></p>
    <div class="grid cols-3" style="margin-top:var(--space-4)">
      <article class="card">
        <h3 class="h4"><a href="/voice/reports/">Advocacy skills webinar · Cerebral Palsy EU</a></h3>
        <p>Practical advocacy training shared with all member associations.</p>
        <p class="meta">22 June 2026</p>
      </article>
      <article class="card">
        <h3 class="h4"><a href="/voice/reports/">VOICE4ALL kicks off</a></h3>
        <p>DysNet joins the EU project on autonomous voting rights for persons with disabilities.</p>
        <p class="meta">May 2026</p>
      </article>
      <article class="card">
        <h3 class="h4"><a href="/voice/reports/">Biorobotics at Regione Lombardia</a></h3>
        <p>DysNet co-organised a biorobotics conference at Palazzo Pirelli, Milan.</p>
        <p class="meta">26 March 2026</p>
      </article>
    </div>
    <p style="margin-top:var(--space-3)"><a href="/voice/reports/">All reports →</a></p>
  </div>
</section>

<section>
  <div class="container">
    {opener("04", "The network", "Our members are the associations families actually belong to.")}
    <p>From Reach in the UK and Raggiungere in Italy to Aussiehands in Australia and AVITE in Spain: {MEMBER_SENTENCE}.</p>
    <p style="margin-top:var(--space-3)"><a class="btn btn-ghost" href="/about/members/">Meet the member associations</a></p>
  </div>
</section>
""",
}

# ─────────────────────────── KNOWLEDGE HUB ────────────────────────
PAGES["/knowledge/"] = {
    "title": "Knowledge",
    "desc": "Five maintained registers on limb difference: bibliography, registries, researchers, care centres and teratogens, plus studies you can join.",
    "crumbs": [("/knowledge/", "Knowledge")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Mission 1 · The international reference point</p>
    <h1 class="display">Knowledge on limb difference, kept current.</h1>
    <p>Families and clinicians come to DysNet to find what is known, what is being studied, and where expertise lives. Each register below is maintained by a named volunteer and shows its last update. Current beats polished.</p>
    <div class="start-here">
      <div>
        <p class="eyebrow" style="color:var(--dys-green-text)">Start here</p>
        <h2 class="h2"><a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a></h2>
        <p>New to limb difference? What dysmelia is, and a plain-language guide to the conditions behind the word, each linked to its Orphanet page. Four simple questions help you find the condition, and the ORPHAcode, that concerns you or your child.</p>
      </div>
      <div class="start-here-cta">
        <a class="btn btn-primary" href="/knowledge/understanding-dysmelia/#cond-finder">Which ORPHAcode concerns me? →</a>
        <p>The ORPHAcode is the reference number clinicians and registries use for a condition. Knowing yours makes every consultation easier.</p>
      </div>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">The five registers</p>
    <h2 class="h2">What is known, being studied, and where expertise lives.</h2>
    <div class="grid cols-2" style="margin-top:var(--space-3)">
      <div class="card acc-library">
        <h3 class="h3"><a href="/knowledge/bibliography/">Bibliography</a></h3>
        <p>Peer-reviewed publications on our conditions, searchable by condition, theme and year.</p>
        <p class="meta">Register 1 · {updated_text(BIB.get("built"))}</p>
      </div>
      <div class="card acc-studies">
        <h3 class="h3"><a href="/knowledge/registries/">Registries</a></h3>
        <p>The registries that already record our conditions: EUROCAT members, national rare-disease registries and the French population registries.</p>
        <p class="meta">Register 2 · {updated_text(ORPHA_REGS.get("fetched"))}</p>
      </div>
      <div class="card acc-research">
        <h3 class="h3"><a href="/knowledge/researchers/">Researchers</a></h3>
        <p>Research teams working on limb difference around the world.</p>
        <p class="meta">Register 3 · {updated_text(RESEARCHERS.get("built"))}</p>
      </div>
      <div class="card acc-centres">
        <h3 class="h3"><a href="/knowledge/care-centres/">Care centres</a></h3>
        <p>Reference and competence centres, in Europe and beyond, on a map.</p>
        <p class="meta">Register 4 · {updated_text(CARE_CENTRES_BUILT)}</p>
      </div>
      <div class="card acc-centres">
        <h3 class="h3"><a href="/knowledge/teratogens/">Teratogens register</a></h3>
        <p>Substances and products with known, presumed or suspected effects on the unborn child, with their source and their legal status.</p>
        <p class="meta">Register 5 · {updated_text(TERA.get("built"))}</p>
      </div>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">Also in Knowledge</p>
    <h2 class="h2">Studies to join, resources to read, and what the research shows.</h2>
    <div class="grid cols-2" style="margin-top:var(--space-3)">
      <div class="card acc-studies">
        <h3 class="h3"><a href="/knowledge/ongoing-studies/">Studies</a></h3>
        <p>Studies our community can join or follow, with who runs them, their status and whom to contact.</p>
      </div>
      <div class="card acc-library">
        <h3 class="h3"><a href="/knowledge/resources/">Resources</a></h3>
        <p>Guides, surveys and reports that are not research papers: Orphanet, the Rare Barometer, the European registry recommendations, our conference proceedings.</p>
      </div>
      <div class="card acc-research">
        <h3 class="h3"><a href="/knowledge/causes-of-dysmelia/">Causes of dysmelia</a></h3>
        <p>What causes a limb to form differently: genes, medicines and chemicals, maternal health, vascular disruption and mechanical forces, and how often a cause is actually found.</p>
      </div>
      <div class="card acc-research">
        <h3 class="h3"><a href="/knowledge/epidemiology/">Epidemiology</a></h3>
        <p>How common each condition is at birth, with the source and confidence interval behind each figure, and how many affected births a year that means in every country: registry rates beside World Bank births, filterable.</p>
      </div>
    </div>
  </div>
</section>
""",
}

REGISTER_FOOT = ('<div class="register-note">'
                 '<span>See something missing? <a href="mailto:info@dysnet.org?subject=Register%20suggestion">'
                 'Suggest an addition</a>.</span></div>')

PAGES["/knowledge/bibliography/"] = {
    "title": "Bibliography",
    "desc": "The DysNet bibliography: peer-reviewed publications on congenital limb difference, thalidomide and their causes, searchable by condition, theme and year.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/bibliography/", "Bibliography")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-library);--acc-text:var(--acc-library-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 1 · Bibliography {updated_badge(BIB.get("built"))}</p>
    <h1 class="display">Bibliography on limb difference.</h1>
    <p style="margin-top:var(--space-3)">Looking for guides, surveys and reports rather than papers? They have moved to <a href="/knowledge/resources/">Resources</a>.</p>
    <div id="bibliography">
    {bibliography_html()}
    </div>
    {REGISTER_FOOT}
  </div>
</section>
""",
}


# ─────────── Registries listed on Orphanet for our ORPHAcodes (harvested 2026-09-11) ───────────
COUNTRY_LABEL = {"SERBIEN": "Serbia"}




def _code_names():
    return REG_CODE_NAMES


# Each registry's own website, harvested from the "Link" field of its Orphanet record and
# checked on 19 September 2026. Orphanet tells a reader a registry exists; only the registry's
# own page tells them what it collects and whom to write to. Entries whose host no longer
# answers keep the note and lose the link, rather than sending a reader to nothing.
REG_SITES_PATH = pathlib.Path(__file__).parent / "tools" / "registry-sites.json"
REG_EUROCAT = "https://eu-rd-platform.jrc.ec.europa.eu/eurocat/"
REG_SITES, REG_NETWORK = {}, {}
if REG_SITES_PATH.exists():
    for _e in json.loads(REG_SITES_PATH.read_text(encoding="utf-8")):
        if "unreachable" in (_e.get("url_status") or ""):
            continue  # the host stopped answering; a reader is better served by no link
        for _i in _e.get("registry_ids", []):
            # The harvest groups several registries under one link, which is right for the
            # EUROCAT platform and wrong for everything else: it would have sent a reader
            # looking for Belgium's Central Registry to the bleeding-disorders registry. So a
            # link counts as a registry's own only when the harvested name is that registry.
            if _e["name"].strip() == next((_r["name"].strip() for _r in ORPHA_REGS.get("registries", []) if _r["id"] == _i), None):
                REG_SITES.setdefault(_i, _e["url"])
            elif _e["url"] == REG_EUROCAT:
                REG_NETWORK.setdefault(_i, _e["url"])


# ── The registries this site curates by hand ─────────────────────────────────
# One file feeds three things: the outlines on the map, the table on the registries page, and
# the count of papers in our own bibliography that rest on each registry. Before this, the map
# and the page were built from different places and could disagree.
REG_AREAS = json.loads((pathlib.Path(__file__).parent / "tools" / "registry-areas.json").read_text(encoding="utf-8"))["areas"]


def drawn_zones():
    """What the registry-coverage layer holds, counted from the two files that define it: the
    French registries by département, everything else by the area it records. The register page
    used to state these as words, and one of them had already drifted by one."""
    drawn = [a for a in REG_AREAS if a.get("map", True)]
    french = json.loads((pathlib.Path(__file__).parent / "tools" / "registry-zones.json").read_text(encoding="utf-8"))["zones"]
    return {"registries": len({a["registry"] for a in drawn} | {z["registry"] for z in french}),
            # By outline, not by name: CULA North is one registry drawn over each of its five countries.
            "clinical": sum(1 for a in drawn if a["status"] == "clinical"),
            "hospital": sum(1 for a in drawn if a["status"] == "hospital")}


ZONES = drawn_zones()
ZONE_SENTENCE = (
    f"{spell(ZONES['registries']).capitalize()} registries are drawn. Most are population registries, which cover a "
    f"territory and count the births in it. {spell(ZONES['clinical'] + ZONES['hospital']).capitalize()} outlines mark "
    f"something different: {spell(ZONES['clinical'])} a clinical registry that recruits through participating hospitals, "
    f"{spell(ZONES['hospital'])} a national system that samples births through reporting hospitals rather than covering "
    "a territory. The section below says why neither can be added to the rest."
)


def _reg_hit(title, phrase):
    """The phrase as a substring, exactly as the bibliography's own search matches it. An acronym
    is matched case-sensitively, or "CoULD" would catch every title containing the word "could"."""
    if phrase.upper() == phrase or sum(c.isupper() for c in phrase) > len(phrase) / 2:
        return phrase in title
    return phrase.lower() in title.lower()


def registry_evidence():
    """Per registry, the papers in our bibliography that rest on it, in two distinct senses.

    `names` — the paper rests on the registry: its title or abstract names it, which
               tools/enrich-bibliography-registries.py records in the entry's "rests_on" field.
               Titles alone missed most of them; a registry is named in the methods.
    `found`  — we discovered the paper through that registry's own publication list, which the
               bibliography records in its "via" field.

    They are different relations and the page says which is which. Counting them here rather
    than storing them keeps the figures from drifting away from the bibliography.
    """
    out, seen = {}, set()
    entries = BIB.get("entries", [])
    for a in REG_AREAS:
        key = a["registry"]
        if key in seen:
            continue
        seen.add(key)
        names = [e for e in entries if key in (e.get("rests_on") or [])]
        label0 = a["label"].split(":")[0].strip().lower()
        found = [e for e in entries
                 if any(key.lower() in v.lower() or (len(label0) > 6 and label0 in v.lower()) for v in e.get("via", []))]
        # Listed even with nothing on either side: the note under the table says a dash is worth
        # seeing, and a row that is dropped cannot be seen.
        out[key] = {"names": names, "found": found, "area": a}
    return out


# ── Which registries cover which condition ───────────────────────────────────
# The register said, of the 72 registries, how many name a condition and how many hold it
# inside a broader group. Turned the other way round the same data says something harder: for
# each condition, whether any registry in Europe can count it at all. Three can be counted
# directly. Two cannot be reached even by classification, and one of those is the commonest
# form of limb difference.
def condition_coverage():
    """Per ORPHAcode: the registries that code it directly, as a child form, or by classification."""
    out = {}
    regs = ORPHA_REGS.get("registries", [])
    # the registries this register lists beyond Orphanet, through the papers that rest on them:
    # a registry whose paper in our bibliography carries a condition's code has published on it
    published = {}
    for key, v in registry_evidence().items():
        for e in v["names"]:
            for c in e.get("codes", []):
                published.setdefault(c, set()).add(key)
    for code in _code_names():
        out[code] = {
            "direct": [r for r in regs if code in r["direct"]],
            "child": [r for r in regs if code in r["children"]],
            "parent": [r for r in regs if code in r["parent"]],
            "published": sorted(published.get(code, set())),
        }
    return out


COVERAGE = None  # filled on first use, because _code_names() needs CONDITIONS


def coverage_for(code):
    global COVERAGE
    if COVERAGE is None:
        COVERAGE = condition_coverage()
    return COVERAGE.get(str(code)) or {"direct": [], "child": [], "parent": [], "published": []}


def condition_registries_html(code):
    """The coverage line for a condition card."""
    if not code:
        return ""
    c = coverage_for(code)
    d, ch, pa = len(c["direct"]), len(c["child"]), len(c["parent"])
    if d:
        txt = f'<strong>{d} registries</strong> record it by name'
        if pa:
            txt += f', {pa} more only inside a broader group'
    elif ch:
        txt = f'<strong>{ch} registries</strong> record its specific forms'
        if pa:
            txt += f', {pa} only inside a broader group'
    elif pa:
        txt = f'No registry records it by name; <strong>{pa}</strong> reach it only inside a broader group'
    elif str(code) not in REG_CHECKED:
        n = REG_COUNTS.get(str(code))
        txt = (f'Orphanet lists <strong>{n} registries</strong> for this code, not yet read one by one'
               if n else 'Registry coverage <strong>not yet checked</strong> for this code')
    else:
        txt = '<strong>No registry records it</strong>, by name or by classification'
    pub = len(c.get("published") or [])
    if pub:
        txt += f'; {spell(pub)} registr{"ies" if pub > 1 else "y"} beyond Orphanet ha{"ve" if pub > 1 else "s"} published on it'
    return f'<p class="cond-regs"><a href="/knowledge/registries/">{txt}</a></p>'


def condition_coverage_html():
    """The table that turns the register of registries round to face the conditions."""
    names = _code_names()
    rows, direct_n, none_n, forms_n = [], 0, 0, 0
    by_name, nothing, unchecked = [], [], []
    for code, name in sorted(names.items(), key=lambda kv: (-len(coverage_for(kv[0])["direct"]),
                                                            -len(coverage_for(kv[0])["child"]), kv[1])):
        c = coverage_for(code)
        d, ch, pa, pub = len(c["direct"]), len(c["child"]), len(c["parent"]), len(c.get("published") or [])
        if d:
            direct_n += 1
            by_name.append(name)
        elif ch:
            forms_n += 1
        if not (d or ch or pa):
            if str(code) in REG_CHECKED:
                none_n += 1
                nothing.append(name)
            else:
                unchecked.append(name)
        cls = ' class="reg-direct"' if d or ch else ""
        pub_cell = (f'<a href="/knowledge/bibliography/?condition={code}" title="{"; ".join(c["published"])}">{pub}</a>' if pub else "&mdash;")
        if not (d or ch or pa) and str(code) not in REG_CHECKED:
            n = REG_COUNTS.get(str(code))
            cells = (f'<td colspan="3" class="reg-unchecked">{"Orphanet lists " + str(n) + ", not yet read one by one" if n else "not checked yet"}</td>')
        else:
            cells = (f'<td style="text-align:center">{d or "&mdash;"}</td>'
                     f'<td style="text-align:center">{ch or "&mdash;"}</td>'
                     f'<td style="text-align:center">{pa or "&mdash;"}</td>')
        rows.append(f'<tr{cls}><th scope="row">{name}</th>{cells}'
                    f'<td style="text-align:center">{pub_cell}</td></tr>')
    if nothing:
        unreachable = (", and " + (" and ".join(nothing)) + " cannot be reached at all, by name or by classification"
                       if len(nothing) > 1 else f", and {nothing[0]} cannot be reached at all, by name or by classification")
    else:
        unreachable = ""
    return f"""
    <div class="tick"></div>
    <p class="eyebrow">Coverage, condition by condition</p>
    <h2 class="h2">Which of our conditions a registry can actually count.</h2>
    <p>The table above reads from the registries. This one reads from the conditions, out of the same Orphanet data, and it
    is the harder view. <strong>By name</strong> means a registry is coded for that condition itself. <strong>Specific
    forms</strong> means it is coded for forms of it rather than the condition as a whole. <strong>Broader group only</strong>
    means the condition is somewhere inside a wider category the registry records, so a case exists in the data and cannot be
    pulled out of it. <strong>Published on it</strong> counts the registries this register lists beyond Orphanet, Hungary&rsquo;s
    or Texas&rsquo;s for instance, whose papers in our bibliography carry the condition&rsquo;s code: the join runs through the
    literature rather than through a coding table, and the number links to those papers.</p>
    <div class="annex-wrap">
      <table class="annex priv-table">
        <thead><tr><th scope="col">Condition</th><th scope="col">By name</th><th scope="col">Specific forms</th><th scope="col">Broader group only</th><th scope="col">Published on it</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    <p class="annex-note">The table holds the {len(names)} ORPHAcodes this site uses; brachydactyly and symbrachydactyly are
    described without one, so they cannot appear. Of the {len(names) - len(unchecked)} whose registry lists we have read from
    Orphanet code by code, <strong>{direct_n} can be counted by name</strong>: {", ".join(by_name)}. {forms_n} more are
    reached through their specific forms, which is what Orphanet does with a group of disorders rather than a single disease.
    Every other one of those exists only inside a wider category, so the case is in the data and cannot be pulled back out of
    it{unreachable}. The remaining {len(unchecked)} are the forms added to this page on 21 September 2026, and their lists
    have not been read yet: the table says so rather than reporting a zero it has not earned. This is what
    <a href="/voice/#demand-3">demand 3</a> is about, in one table.</p>
"""


def registry_evidence_html():
    """The table that joins this register to the bibliography."""
    ev = registry_evidence()
    if not ev:
        return ""
    rows = []
    for key, v in sorted(ev.items(), key=lambda kv: (-len(kv[1]["names"]) - len(kv[1]["found"]), kv[0])):
        a = v["area"]
        label = a["label"].split(":")[0] if ":" in a["label"] else a["label"]
        site = f'<a href="{a["website"]}" target="_blank" rel="noopener external">{key}</a>' if a.get("website") else key
        names = (f'<a href="/knowledge/bibliography/?registry={urllib.parse.quote(key)}">{len(v["names"])}</a>'
                 if v["names"] else "&mdash;")
        found = str(len(v["found"])) if v["found"] else "&mdash;"
        rows.append(f'<tr><th scope="row">{site}</th><td>{label}<br><span class="reg-local">{a["country"]}</span></td>'
                    f'<td style="text-align:center">{names}</td><td style="text-align:center">{found}</td></tr>')
    return f"""
    <div class="tick"></div>
    <p class="eyebrow">Registries and the bibliography</p>
    <h2 class="h2">Which registries our own evidence rests on.</h2>
    <p>A register of registries is worth little if it sits apart from the literature on the same shelf. These figures are
    counted from <a href="/knowledge/bibliography/">our bibliography</a> at every build, so they cannot drift away from it.
    Two different relations, and the difference matters. <strong>Rests on it</strong> means the paper&rsquo;s title or
    abstract names the registry, so the study was built on its data; the number links to those papers in the bibliography.
    <strong>Found through it</strong> means we discovered the paper on that registry&rsquo;s own list of publications, which
    is how a registry earns its place here rather than being taken on trust. A registry named in the literature and absent
    from this register is a gap in the register, not in the literature: that is how Hungary&rsquo;s national registry, Texas,
    Atlanta, New York State, Liaoning and Mexico&rsquo;s RYVEMCE came to be added in September 2026.</p>
    <div class="annex-wrap">
      <table class="annex priv-table">
        <thead><tr><th scope="col">Registry</th><th scope="col">What it is</th><th scope="col">Rests on it</th><th scope="col">Found through it</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    <p class="annex-note">A dash means none, which is itself worth seeing: several registries we list have never appeared in
    the limb-difference literature we collect, and several that shaped it are not registries at all.</p>
"""


def _code_label(code):
    """A code's name for the registry pages: the card or form it belongs to, else Orphanet's own term,
    so that a group the site has no card for (93458, the polydactyly, syndactyly and hyperphalangy
    group the old harvest recorded) is named rather than printed as a number."""
    code = str(code)
    return REG_CODE_NAMES.get(code) or (HIER["nodes"].get(code) or {}).get("term") or code


def _is_eurocat(r):
    """EUROCAT membership as Orphanet's registry record states it, in the registry's own name."""
    return "EUROCAT" in r["name"].upper()


def reg_filters_html(regs):
    """Country, condition and EUROCAT filters for the table of registries on Orphanet. Every option and
    count is read from the rows themselves, so a registry added to the register appears in them."""
    by_country = {}
    for r in regs:
        lab = COUNTRY_LABEL.get(r["country"], r["country"].title())
        by_country[lab] = by_country.get(lab, 0) + 1
    countries = "".join(f'<option value="{c}">{c} ({n})</option>' for c, n in sorted(by_country.items()))
    codes = sorted({c for r in regs for k in ("direct", "children", "parent") for c in r[k]}, key=lambda c: _code_label(c).lower())
    conditions = "".join(f'<option value="{c}">{_code_label(c)}</option>' for c in codes)
    ec = sum(1 for r in regs if _is_eurocat(r))
    unread = [c[0] for c in CONDITIONS if c[2] and str(c[2]) not in REG_CHECKED]
    unread_txt = (", ".join(unread[:-1]) + " and " + unread[-1]) if len(unread) > 1 else "".join(unread)
    note = (f'<p class="annex-note reg-filter-note">The condition list offers every code a registry on Orphanet is linked to. '
            f'{"The registry search has not yet been read for " + unread_txt + ", so " + ("they are" if len(unread) > 1 else "it is") + " not in it." if unread else ""}</p>')
    return f"""<div class="inc-controls reg-controls" id="reg-controls">
      <label for="reg-country">Country</label>
      <select id="reg-country"><option value="">Every country</option>{countries}</select>
      <label for="reg-condition">Condition</label>
      <select id="reg-condition"><option value="">Every condition</option>{conditions}</select>
      <label class="reg-check" for="reg-classif"><input type="checkbox" id="reg-classif" disabled> include registries that list it only through a broader group</label>
      <label for="reg-eurocat">EUROCAT</label>
      <select id="reg-eurocat"><option value="">All registries</option><option value="1">EUROCAT members ({ec})</option><option value="0">Not in EUROCAT ({len(regs) - ec})</option></select>
      <button type="button" id="reg-reset">Reset</button>
      <p class="inc-count" aria-live="polite"><strong id="reg-n">{len(regs)}</strong> of {len(regs)} registries<span id="reg-hint"></span></p>
    </div>
    {note}"""


def registries_html():
    names = _code_names()
    regs = ORPHA_REGS.get("registries", [])
    by_country = {}
    for r in regs:
        by_country.setdefault(r["country"], []).append(r)
    total = len(regs); direct = sum(1 for r in regs if r["direct"])
    eurocat = sum(1 for r in regs if _is_eurocat(r))
    rows = []
    for country in sorted(by_country):
        label = COUNTRY_LABEL.get(country, country.title())
        for r in sorted(by_country[country], key=lambda x: (not x["direct"], x["name"])):
            url = f"https://www.orpha.net/en/research-trials/registry/{r['id']}"
            if r["direct"]:
                cov = "<strong>Coded for:</strong> " + ", ".join(_code_label(c) for c in r["direct"])
                if r["children"]:
                    cov += "; specific forms of " + ", ".join(_code_label(c) for c in r["children"])
                cls = ' class="reg-direct"'
            else:
                n = len(r["parent"])
                cov = f"By classification: {n} of our {len(names)} ORPHAcodes" if n < len(names) else f"By classification: all {len(names)} ORPHAcodes"
                cls = ""
            local = f'<br><span class="reg-local">{r["local"]}</span>' if r["local"] and r["local"] != r["name"] else ""
            site = next((f["website"] for f in ORPHA_REGS.get("france_population_registries", {}).get("registries", []) if f.get("orphanet_id") == r["id"]), None)
            if r["id"] == "589005": site = "https://www.chu-rennes.fr/remabreizh.html"
            site = site or REG_SITES.get(r["id"])
            net = None if site else REG_NETWORK.get(r["id"])
            if site:
                web = f' · <a href="{site}" target="_blank" rel="noopener external">website ↗</a>'
            elif net:
                web = f' · <a href="{net}" target="_blank" rel="noopener external">EUROCAT ↗</a>'
            else:
                web = ""
            data = (f' data-country="{label}" data-eurocat="{1 if _is_eurocat(r) else 0}" data-direct="{" ".join(r["direct"])}"'
                    f' data-forms="{" ".join(r["children"])}" data-classif="{" ".join(r["parent"])}"')
            rows.append(f'<tr{cls}{data}><th scope="row">{label}</th><td><a href="{url}" target="_blank" rel="noopener external">{r["name"]}</a>{web}{local}</td><td>{cov}</td></tr>')
    fr = ORPHA_REGS.get("france_population_registries", {})
    fr_rows = "".join(f'<tr{" class=reg-direct" if not f.get("orphanet_id") else ""}><th scope="row">{f["region"]}</th><td><a href="{f["website"]}" target="_blank" rel="noopener external">{f["name"]}</a> · {f["host"]}{" · <strong>not yet on Orphanet</strong>" if not f.get("orphanet_id") else ""}</td><td>{f["created"]}</td><td>{f["births"]:,}{"*" if f.get("note") else ""}</td></tr>' for f in fr.get("registries", []))
    fr_block = f"""
    <h3 class="h3" style="margin-top:var(--space-4)">The French population registries, checked against Santé publique France</h3>
    <p>Santé publique France’s surveillance report for 2019-2021 (published July 2026) lists seven population-based registries of congenital anomalies. Together they covered {fr.get("coverage", "")}. Six are on Orphanet; the seventh, ATENA in Nouvelle-Aquitaine, is not yet listed there and is added here from the report. The same report describes the European network these registries feed: {fr.get("eurocat", "")}.</p>
    <div class="annex-wrap">
      <table class="annex reg-table">
        <thead><tr><th scope="col">Region</th><th scope="col">Registry</th><th scope="col">Created</th><th scope="col">Births covered per year (2019-2021)</th></tr></thead>
        <tbody>{fr_rows}</tbody>
      </table>
    </div>
    <p>Three of the seven publish a declaration form for families as well as for clinicians: REMERA in Rhône-Alpes, REMACOR in La Réunion and ReMaBreizh in Brittany each open their reporting page with the words “parent or practitioner”. Families are not only counted by these registries, they can address them directly.</p>
    <p>REMERA is also the only one that publishes figures for limbs. It puts the prevalence of limb reduction anomalies in the départements it watches at 8.7 per 10,000 births in 2020, and isolated unilateral transverse agenesis of the upper limb at 0.53 per 10,000 in 2017. Its own analysis of the Ain cluster, published in 2021, found 8 such cases among the 8,204 births between 2009 and 2014 inside a circle of 16.24 km, where 0.82 were expected.</p>
    <p class="annex-note">Sources: <a href="{fr.get("source_url", "")}" target="_blank" rel="noopener external">{fr.get("source", "")}</a>; the registries&rsquo; own websites, read 13 September 2026; Gnansia E, Michon L, Amar E, et al. <em>Birth Defects Res</em> 2021;113(13):1015-1025, <a href="https://doi.org/10.1002/bdr2.1876" target="_blank" rel="noopener external">doi:10.1002/bdr2.1876</a>. * Estimate of the births the registry would have covered had it been operating in 2019-2021. Live births and stillbirths. Download the data (JSON, CC BY 4.0): <a href="/data/registries.json">the {REG_SPLIT["total"]} Orphanet registry records</a>, <a href="/data/registry-areas.json">the registries and surveillance systems drawn beyond them</a>, and <a href="/data/registry-zones.json">the French registries by d&eacute;partement</a>.</p>
""" if fr else ""
    return f"""
    <div class="tick"></div>
    <p class="eyebrow">Registries on Orphanet</p>
    <h2 class="h2">{total} registries already record our conditions.</h2>
    <p>Orphanet’s directory of patient registries, queried for each of the {len(names)} ORPHAcodes on this site (harvested {ORPHA_REGS.get("fetched", "")[:10]}). Two kinds of match: registries <strong>coded for</strong> one of our conditions, which are the {eurocat} congenital-anomaly registries of the <strong>EUROCAT</strong> network and their national equivalents, and registries that reach our conditions only <strong>by classification</strong>, as national rare-disease or rare-bone registries. None of them is dedicated to limb differences; this is the landscape the DysNet initiative sets out to complement, not to duplicate.</p>
    {reg_filters_html(regs)}
    <div class="annex-wrap">
      <table class="annex reg-table" id="reg-table">
        <thead><tr><th scope="col">Country</th><th scope="col">Registry (link to its Orphanet record)</th><th scope="col">How it relates to our conditions</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    <p class="annex-note">Source: Orphanet, Research and trials, Patient registries, per ORPHAcode. “Coded for” = the registry declares the condition itself ({direct} registries); “by classification” = Orphanet lists the registry under a broader group that includes the condition. Registry names as published by Orphanet, with the local name where given.</p>
{fr_block}
"""

PAGES["/knowledge/ongoing-studies/"] = {
    "title": "Studies",
    "desc": "Limb-difference studies recruiting or under way: the ERN BOND Patient Journey, the Rare Barometer, prosthesis reimbursement, and who to contact.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/ongoing-studies/", "Studies")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-studies);--acc-text:var(--acc-studies-text)">
    <div class="tick"></div>
    <p class="eyebrow">Knowledge · Studies</p>
    <h1 class="display">Studies on limb difference you can join or follow.</h1>
    <p>Studies our community can join or follow. Each entry shows who runs it, its status, and whom to contact. Associations: tell us about studies in your country.</p>

    <h2 class="h3" style="margin-top:var(--space-4)">Clinical trials</h2>
    <p>A trial tests an intervention on people and carries a registration number, so anyone can check what it set out to measure before it began.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>How the brain adapts to congenital upper-limb loss · University of Zurich <span class="badge live">recruiting</span></h3>
        <p>An observational study combining MRI and behavioural measures to understand how the central nervous system reorganises in people born with upper-limb amelia, compared with controls. About 70 participants; adults with congenital upper-limb loss can take part in Zurich.</p>
        <p class="src">University of Zurich, Switzerland · recruiting until 2027 · <a href="https://clinicaltrials.gov/study/NCT06043518" target="_blank" rel="noopener external">ClinicalTrials.gov · NCT06043518 ↗</a></p>
      </article>
    </div>

    <h2 class="h3" style="margin-top:var(--space-4)">Surveys and interview studies</h2>
    <p>These ask about experience rather than testing a treatment. Most take minutes, and several shape the trials that follow.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>Bioethics of bionic and robotic prostheses · Texas Christian University <span class="badge live">recruiting</span></h3>
        <p>Interviews on the ethical questions that bionic and robotic prostheses raise, gathered from three groups: people with
        limb loss or limb difference, the clinicians who treat them, and the policymakers who decide what is funded. Adults who
        have lived mostly in the United States can take part, whether or not they use a prosthesis, and whatever the level or the
        cause of the limb difference. An intake survey of about fifteen minutes is followed by one interview of up to an hour over
        video, and participants receive a 50-dollar voucher.</p>
        <p class="src">Texas Christian University · recruiting until 29 January 2027 · contact Kristin Perrin,
        <a href="mailto:k.perrin@tcu.edu">k.perrin@tcu.edu</a> ·
        <a href="https://build.redcapcloud.com/survey.jsp?code=HYNOe9im72d7tz4X" target="_blank" rel="noopener external">intake survey ↗</a></p>
      </article>
      <article class="entry">
        <h3>Preventing chronic pain after amputation surgery · UTHealth Houston <span class="badge live">trial in preparation</span></h3>
        <p>The patient-engagement stage of a trial on how best to prevent chronic pain after an amputation. Before designing it,
        the researchers are asking the people it would treat: the survey takes ten to fifteen minutes, is open to adults who have
        had amputation surgery, and asks about their experience of pain afterwards so that the trial answers a question patients
        actually have. It concerns acquired limb loss rather than a limb difference present at birth, which matters for members
        who have had an amputation, whatever the cause. No registration number exists yet, as the trial itself has not started.</p>
        <p class="src">University of Texas Health Science Center at Houston · recruiting until 30 May 2026 · contact Philipp Lirk ·
        <a href="https://uthtmc.az1.qualtrics.com/jfe/form/SV_blxQKdj5j0J8QJg" target="_blank" rel="noopener external">the survey ↗</a></p>
      </article>
      <article class="entry">
        <h3>Rare Barometer surveys <span class="badge live">recurring</span></h3>
        <p>EURORDIS’s survey programme on living with a rare disease. DysNet contributes content and translations and relays each wave to members.</p>
        <p class="src">EURORDIS · <a href="https://www.eurordis.org/rare-barometer/english/" target="_blank" rel="noopener external">register to take part</a></p>
      </article>
      <article class="entry">
        <h3>“What if” phase 2: a European survey on dysmelia <span class="badge example">planned</span></h3>
        <p>A workgroup prepares a European-level survey across cultural, medical, scientific and technological dimensions, drawing on university and research centres, hospitals and orthopaedic units in the countries DysNet represents.</p>
        <p class="src">DysNet workgroup · in preparation</p>
      </article>
    </div>

    <h2 class="h3" style="margin-top:var(--space-4)">Projects and directories</h2>
    <p>Work under way in the network, and the catalogues where other studies are listed.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry" id="pregnancy-registries">
        <h3>Pregnancy exposure registries · US Food and Drug Administration <span class="badge live">{TERA.get("counts", {}).get("registries_listed", 0)} recruiting</span></h3>
        <p>A pregnancy exposure registry follows people who took a particular medicine while pregnant and records what happened. It is how the effect of a medicine on a pregnancy becomes known at all, and it is one of the few things a family can still do about an exposure that has already happened. The FDA keeps the public list, and {TERA.get("counts", {}).get("registries", 0)} of the medicines on our <a href="/knowledge/teratogens/">teratogens register</a> have one open, among them carbamazepine and topiramate; those entries carry the registry and its contact. Registries are listed at their sponsor&rsquo;s request and the FDA does not endorse them.</p>
        <p class="src">FDA · <a href="https://www.fda.gov/consumers/pregnancy-exposure-registries/list-pregnancy-exposure-registries" target="_blank" rel="noopener external">List of pregnancy exposure registries ↗</a> · read {TERA.get("counts", {}).get("registries_fetched", "")}</p>
      </article>
      <article class="entry" id="patient-journey">
        <h3>Patient Journey · ERN BOND / EURORDIS <span class="badge live">in progress</span></h3>
        <p>A five-step research project promoted by DysNet on behalf of Raggiungere, tracking the experiences of patients, families, doctors and researchers through a shared questionnaire, to give families updated medical and scientific knowledge.</p>
        <p class="src">ERN BOND ePAG · approved, in progress · contact via <a href="mailto:info@dysnet.org">info@dysnet.org</a></p>
      </article>
      <article class="entry">
        <h3>Prosthesis reimbursement across the EU <span class="badge live">workgroup</span></h3>
        <p>A DysNet workgroup compares the subsidies each EU country grants for prostheses: amounts due, and which prosthesis technologies qualify. A regional initiative at Regione Lombardia (2026) is the working example other countries can replicate.</p>
        <p class="src">DysNet workgroup · data collection open to all member associations</p>
      </article>
      <article class="entry">
        <h3>Orphanet research directories <span class="badge live">source</span></h3>
        <p>Orphanet catalogues ongoing clinical trials, research projects, registries and biobanks per rare disease. The maintainer screens it for limb-difference studies each quarter.</p>
        <p class="src">Orphanet · <a href="https://www.orpha.net/en/research-trials/clinical-trials" target="_blank" rel="noopener external">clinical trials</a> · <a href="https://www.orpha.net/en/research-trials/research-projects" target="_blank" rel="noopener external">research projects</a></p>
      </article>
    </div>
    <p style="margin-top:var(--space-4)">The registries that already record our conditions have their own register: <a href="/knowledge/registries/">Registries</a>.</p>
    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/registries/"] = {
    "title": "Registries",
    "desc": "Every registry that records congenital limb differences: those listed on Orphanet, the EUROCAT network and the seven French population registries.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/registries/", "Registries")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-studies);--acc-text:var(--acc-studies-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 2 · Registries {updated_badge(ORPHA_REGS.get("fetched"))}</p>
    <h1 class="display">Registries recording limb difference: what already exists.</h1>
    <p>Before building a registry owned by families, DysNet mapped the registries that already record our conditions. This register lists them, says how each one relates to the ORPHAcodes on this site, and checks the French population registries against the surveillance report of Santé publique France. The area each registry covers is drawn on the <a href="/#map">landing-page map</a>, under “Registry coverage”: the French registries département by département, the others by the region, canton, province or country they record. {ZONE_SENTENCE} The DysNet initiative itself is described on the <a href="/registry/">registry page</a>.</p>
    {registries_html()}

    <div class="tick"></div>
    <p class="eyebrow">The umbrella</p>
    <h2 class="h2">The body that connects most of the registries above.</h2>
    <p>The <strong>International Clearinghouse for Birth Defects Surveillance and Research</strong> has since 1974 brought
    national and regional surveillance programmes together so that their figures can be pooled. Its recent work on
    gastroschisis drew on 27 surveillance programmes across 24 countries. It holds no territory of its own, so it appears on
    no map, and it belongs at the head of this register rather than inside it.</p>
    <p>Two of the few worldwide studies of our own conditions came out of it, on <strong>amelia</strong> and on
    <strong>phocomelia</strong>, and <a href="/knowledge/epidemiology/">our epidemiology tables</a> and
    <a href="/knowledge/causes-of-dysmelia/">the causes review</a> already rest on its data. It was missing from this
    register until September 2026, which is the kind of gap a register of registries should be embarrassed by: we were
    quoting the figures of a body we had not listed.</p>
    <p class="src">International Clearinghouse for Birth Defects Surveillance and Research &middot;
    <a href="https://www.icbdsr.org/" target="_blank" rel="noopener external">icbdsr.org</a> &middot; read 21 September 2026</p>

    <div class="tick"></div>
    <p class="eyebrow">Clinical and patient-led registries</p>
    <h2 class="h2">Hand surgeons and families already run registries of their own.</h2>
    <p>Beside the population registries that count births, a second family of registries follows the children themselves. Four of them record congenital upper limb differences, and two more are run by DysNet member associations for one condition. They are smaller than EUROCAT, and they hold exactly what a population registry does not: diagnosis by a standard classification, treatment, and outcomes over years.</p>

    <h3 class="h4" style="margin-top:var(--space-3)">They do not speak the language of this site</h3>
    <p>Every register here is keyed to <strong>ORPHAcodes</strong>, Orphanet's identifier for a named rare disease, and the population registries above are indexed the same way. The four clinical registries classify instead by the <strong>Oberg-Manske-Tonkin</strong> system, which sorts a malformation by how the limb failed to form rather than by the name of a syndrome; CULA North records ICD-10 alongside it. The two answer different questions and neither maps cleanly onto the other. A child with a radial longitudinal deficiency appears under an ORPHAcode in a population registry and under an OMT category in a clinical one, so the two counts describe overlapping children and cannot be added. Agreeing that mapping is one of the things <a href="/voice/#demand-3">we ask for</a>.</p>
    <div class="annex-wrap">
      <table class="annex priv-table">
        <thead><tr><th scope="col">Registry</th><th scope="col">Where</th><th scope="col">Since</th><th scope="col">Run by</th><th scope="col">Classification</th></tr></thead>
        <tbody>
          <tr><th scope="row">CoULD</th><td>United States, participating centres. <a href="https://www.jhandsurg.org/article/S0363-5023(20)30674-2/fulltext" target="_blank" rel="noopener external">Described here</a>; it publishes no site of its own and enrolment runs through the treating surgeon.</td><td>2014</td><td>Washington University in St Louis, with St Louis Children's Hospital and Shriners Children's</td><td>Oberg-Manske-Tonkin</td></tr>
          <tr><th scope="row"><a href="https://www.mcri.edu.au/research/projects/ahdr" target="_blank" rel="noopener external">AHDR</a></th><td>Australia, national</td><td>2017</td><td><a href="https://www.mcri.edu.au/research/projects/ahdr" target="_blank" rel="noopener external">Murdoch Children's Research Institute</a> at the Royal Children's Hospital, Melbourne, with our member <a href="https://aussiehands.org/research/" target="_blank" rel="noopener external">Aussie Hands</a></td><td>Oberg-Manske-Tonkin</td></tr>
          <tr><th scope="row">CULA North</th><td>Denmark, Finland, Germany, Norway, Sweden</td><td>2018</td><td>Five registries with separate databases and one shared prospective protocol</td><td>Oberg-Manske-Tonkin and ICD-10</td></tr>
          <tr><th scope="row"><a href="https://www.bssh.ac.uk/professionals/audit_database.aspx" target="_blank" rel="noopener external">BSSH registry</a></th><td>United Kingdom</td><td>2019</td><td>The <a href="https://www.bssh.ac.uk/" target="_blank" rel="noopener external">British Society for Surgery of the Hand</a>, within the wider UK Hand Registry</td><td>Oberg-Manske-Tonkin</td></tr>
          <tr><th scope="row"><a href="https://www.llpr.org/" target="_blank" rel="noopener external">LLPR</a></th><td>United States</td><td>2022</td><td>Built by Mayo Clinic under NIH and Department of Defense funding, and since September 2024 run by a non-profit with the Amputee Coalition</td><td>Limb loss and limb difference, acquired and congenital</td></tr>
        </tbody>
      </table>
    </div>
    <p class="annex-note">Where a registry publishes a page of its own, its name links to it. CoULD and CULA North publish none, so the table points at what they do publish. Years and classifications for the first four come from the comparison below; the LLPR figures from its own publication and site. Four of these are outlined on the <a href="/#map">map</a> as countries where a clinical registry recruits, which is not the same as a territory a registry covers.</p>

    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>Four clinical registries, built to talk to each other <span class="badge live">2026</span></h3>
        <p>A comparison of the registries for congenital upper limb difference names the Congenital Upper Limb Difference registry in the United States, Congenital Upper Limb Anomalies North in northern Europe, the Australian Hand Difference Register, and the British Society for Surgery of the Hand registry in the United Kingdom. The authors find that these registries collect similar data, which allows effective interoperability while each keeps its own features, and they set out recommendations for the registries that follow.</p>
        <p class="src">McCombe D, Wall L, Goldfarb C, Hülsemann W. <em>J Hand Surg Eur Vol</em> 2026;51(1):111-118 · <a href="https://doi.org/10.1177/17531934251348360" target="_blank" rel="noopener external">doi:10.1177/17531934251348360</a></p>
      </article>
      <article class="entry">
        <h3>What it takes to keep one alive <span class="badge live">2026</span></h3>
        <p>Eight hand surgeons, two from each of those four registries, were interviewed about founding and sustaining them. They describe the early experience, the logistical obstacles, the research each registry produced, and whether an international congenital hand registry is feasible. That last question is the one DysNet asks from the families’ side.</p>
        <p class="src">Mosa A, Romans S, Goldfarb CA, Wall LB. <em>J Hand Surg Am</em> 2026;51(9):883.e1-883.e8 · <a href="https://doi.org/10.1016/j.jhsa.2026.02.017" target="_blank" rel="noopener external">doi:10.1016/j.jhsa.2026.02.017</a></p>
      </article>
      <article class="entry">
        <h3>CoULD, and what a registry sees that a survey does not <span class="badge live">United States</span></h3>
        <p>The multicentre Congenital Upper Limb Differences registry analysed its first four years at the two founding centres, a cohort of 1,381 patients. Compared with a one-year cross-sectional cohort from the American Midwest and with a Swedish birth registry, about a third of the diagnosis categories differed in frequency. The registry picked up more conditions that present late and more that rarely lead to surgery, which is precisely what a registry built on hospital episodes tends to miss.</p>
        <p class="src">Vuillermin C, Canizares MF, Bauer AS, Miller PE. <em>J Hand Surg Am</em> 2021;46(6):515.e1-515.e11 · <a href="https://doi.org/10.1016/j.jhsa.2020.11.006" target="_blank" rel="noopener external">doi:10.1016/j.jhsa.2020.11.006</a></p>
      </article>
      <article class="entry">
        <h3>The Italian Poland syndrome register, and its biobank <span class="badge live">Italy</span></h3>
        <p>AISP, our member association in Genoa, runs the Registro Sindrome di Poland, overseen by a scientific committee of clinicians and patient representatives, and records the personal and clinical data of people with the syndrome. The register is interoperable with the association’s biobank, held at the Istituto Giannina Gaslini under an agreement signed in December 2014 with the Telethon Network of Genetic Biobanks. The biobank keeps blood samples and skin fibroblasts, releases them coded for research and diagnosis anywhere in the world once the committee approves, and the association pays the costs.</p>
        <p class="src">AISP · <a href="https://www.sindromedipoland.org/registro/" target="_blank" rel="noopener external">sindromedipoland.org · the register</a> · <a href="https://www.sindromedipoland.org/biobanking/" target="_blank" rel="noopener external">the biobank</a> · read 13 September 2026</p>
      </article>
      <article class="entry">
        <h3>A register run by a member association <span class="badge live">Poland syndrome</span></h3>
        <p>PIP UK, our member association for Poland syndrome, runs the Poland Syndrome Community Register, open worldwide to anyone with a diagnosis confirmed by a physician, or to their parents and carers. The association states that it was ten years in the making and follows a model used by the Italian Poland syndrome association. Participants answer a medical survey, a demographic survey and a contact survey once, then a quality-of-life survey every six months. It is the closest thing in our network to what DysNet is building, one condition at a time.</p>
        <p class="src">PIP UK · <a href="https://www.pip-uk.org/poland-syndrome-community-register" target="_blank" rel="noopener external">pip-uk.org · the community register</a> · read 13 September 2026</p>
      </article>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">Outside Europe</p>
    <h2 class="h2">North America is building registries of its own.</h2>
    <p>Orphanet lists the registries that declare themselves to it, which leaves out initiatives that are being designed or that sit outside the rare-disease framing. Three of them concern our conditions directly, and two are led by the amputee community itself.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>Canada: a national strategy, and no registry yet <span class="badge live">2026</span></h3>
        <p>Canada has no national data source on limb loss and limb difference, so incidence, prevalence, risk factors and care outcomes remain unknown, and services vary from province to province. A survey of 96 invited representatives, answered by 53, was followed by a virtual workshop on 14 February 2024 attended by 64 people. Participants agreed on five domains for a future registry: representation, standardization, practice-based evidence, research and innovation, and policy and funding. Amputee advocacy organisations took part alongside clinicians, researchers and decision-makers, and the workshop looked to them to champion the registry. The authors also describe patient-powered registries, which patients and advocacy groups manage themselves, which is the model DysNet is building.</p>
        <p>A survey of the rehabilitation centres that treat people with limb loss found the same gap on the clinical side. Of 36 centres approached across the country, 31 answered, and the authors describe a landscape without shared rehabilitation guidelines and without a shared clinical database.</p>
        <p class="src">Mayo AL, Hitzig SL, Zidarov D, et al. <em>Can Prosthet Orthot J</em> 2026;9(1):46909 · <a href="https://doi.org/10.33137/cpoj.v9i1.46909" target="_blank" rel="noopener external">doi:10.33137/cpoj.v9i1.46909</a> · Hitzig SL, Zidarov D, MacKay C, et al. <em>Prosthet Orthot Int</em> 2025;49(2):248-255 · <a href="https://doi.org/10.1097/PXR.0000000000000405" target="_blank" rel="noopener external">doi:10.1097/PXR.0000000000000405</a></p>
      </article>
      <article class="entry">
        <h3>United States: the Limb Loss and Preservation Registry <span class="badge live">running</span></h3>
        <p>The registry standardises outcome data on limb loss and limb difference across all 50 states. More than 1,100 trigger codes identify a patient, and every later episode of care is then collected for that person’s lifetime. It has gathered data on more than 435,000 patients and more than 11.5 million episodes of care.</p>
        <p class="src">Kaufman KR, Bernhardt K, Murphy S, et al. <em>Arch Rehabil Res Clin Transl</em> 2024;6(4):100356 · <a href="https://doi.org/10.1016/j.arrct.2024.100356" target="_blank" rel="noopener external">doi:10.1016/j.arrct.2024.100356</a></p>
      </article>
      <article class="entry">
        <h3>Alberta: 33 years of congenital limb deficiencies <span class="badge live">population-based</span></h3>
        <p>The Alberta Congenital Anomalies Surveillance System records live births, stillbirths and terminations. Between 1980 and 2012 it ascertained 795 cases of congenital limb deficiency among 1,411,652 births, a prevalence of 5.6 per 10,000. It is the kind of population registry that Europe knows through EUROCAT, and it shows what continuity over three decades makes visible.</p>
        <p class="src">Bedard T, Lowry RB, Sibbald B, et al. <em>Am J Med Genet A</em> 2015;167A(11):2599-2609 · <a href="https://doi.org/10.1002/ajmg.a.37240" target="_blank" rel="noopener external">doi:10.1002/ajmg.a.37240</a></p>
      </article>
    </div>

    {registry_evidence_html()}
    {condition_coverage_html()}

    <div class="tick"></div>
    <p class="eyebrow">India</p>
    <h2 class="h2">India counts births by the million, and limb differences hardly at all.</h2>
    <p>About 600,000 children a year are born in India with a birth anomaly. There is no national birth-defects surveillance system and no registry dedicated to limb difference. What exists is a hospital-based reporting network, a sentinel surveillance scheme, a national child-screening programme that does not look for limb reduction defects, and, since March 2026, a national registry being designed. None of them is governed by the families concerned. DysNet has no member association in India, so each entry below is verified from the source named with it, the same rule the <a href="/knowledge/care-centres/">care centres</a> register follows.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>What India records today <span class="badge live">2025 review</span></h3>
        <p>A narrative review of birth-defect reporting in India finds three systems and no national surveillance. The WHO South-East Asia Region newborn and birth-defects surveillance, running since 2014, is passive and hospital-based: 70 non-randomly selected hospitals in 2020, 1,545,258 births reported and 18,006 birth defects detected, a prevalence of 1.16 per cent. Limb reduction defects are among the conditions it records. The national child-screening programme, Rashtriya Bal Swasthya Karyakram, has screened 157.36 million children since 2013 through mobile health teams, and the nine birth defects it looks for at birth include talipes and developmental dysplasia of the hip, but not limb reduction defects. A child born without a hand is not sought by the programme built to find children who need care.</p>
        <p class="src">Kar A. Birth defects reporting and surveillance in India: a narrative review. <em>J Community Genet</em> 2025;16(1):5-14 &middot; <a href="https://doi.org/10.1007/s12687-024-00760-5" target="_blank" rel="noopener external">doi:10.1007/s12687-024-00760-5</a></p>
      </article>
      <article class="entry">
        <h3>The Birth Defects Registry of India <span class="badge live">since 2001</span></h3>
        <p>Set up in 2001 by the Fetal Care Research Foundation in Chennai, the BDRI is passive and hospital-based: member hospitals report the anomalies they see, nodal hospitals coordinating the participating ones in each region. It reached 750 reporting hospitals in 2016, the widest birth-defects network the country has had. The 2025 review notes that no updated record of the surveillance could be found. That is the fragility any registry has to reckon with, ours included: a registry without sustained funding stops being a registry.</p>
        <p class="src">Fetal Care Research Foundation &middot; <a href="https://fcrf.org.in/bdri_acvs.asp" target="_blank" rel="noopener external">fcrf.org.in &middot; the registry&rsquo;s activities</a> &middot; read 13 September 2026, with Kar 2025 above for the figures</p>
      </article>
      <article class="entry">
        <h3>A national registry is being designed right now <span class="badge live">March 2026</span></h3>
        <p>On 2 March 2026, at the India Habitat Centre in New Delhi, Smile Train India and the Birth Defects Research Foundation launched the Birth Anomalies Network of India. A proposed National Birth Anomalies Registry is at its centre, meant to produce prevalence data, identify preventable risk factors and guide where resources go, and a whitepaper setting out a roadmap for a national task force was released the same day. The network states that it brings clinicians, researchers, caregivers, policymakers and civil society onto one platform. That is the moment at which families can still shape how a country decides to count them, and the reason India appears on this register before it appears in our network.</p>
        <p class="src">Smile Train India and the Birth Defects Research Foundation, Pune (Dr Anita Kar, founder-director) &middot; <a href="https://www.tribuneindia.com/news/business/smile-train-india-and-birth-defects-research-foundation-launch-birth-anomalies-network-of-india-2-2/" target="_blank" rel="noopener external">announcement, 5 March 2026</a> &middot; <a href="https://www.birthdefectsindia.com/" target="_blank" rel="noopener external">birthdefectsindia.com</a> &middot; read 13 September 2026</p>
      </article>
      <article class="entry">
        <h3>Rare diseases: the ICMR registry <span class="badge live">since 2019</span></h3>
        <p>The ICMR National Registry for Rare and other Inherited Disorders, begun in November 2019 with AIIMS New Delhi, collects demography, phenotype, natural history and outcomes across six groups of conditions, skeletal dysplasias among them. Nineteen centres contribute and more than 4,000 cases have been recorded. A limb malformation reaches it only when it belongs to a syndrome one of those groups covers, the same &ldquo;by classification&rdquo; route as the European rare-disease registries in the table above.</p>
        <p class="src">Indian Council of Medical Research &middot; <a href="https://rdrdb.icmr.org.in/registry/" target="_blank" rel="noopener external">rdrdb.icmr.org.in</a> &middot; read 13 September 2026</p>
      </article>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">China</p>
    <h2 class="h2">China counts our conditions in the millions.</h2>
    <p>The <strong>Chinese Birth Defects Monitoring Network</strong> has run since the Ministry of Health started it, and is held by the National Center for Birth Defects Monitoring at West China Second University Hospital, Sichuan University, in Chengdu. It is the largest source of data on our conditions that this register has found anywhere, and it does record them: syndactyly and polydactyly are counted by the million-birth cohort, year by year. It is not population-based. Births are reported by a sample of hospitals, so it describes the country without covering it, and the section below gives the numbers that sample reaches. DysNet has no member association in China, so each entry is verified from the source named with it.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>What the network is, and what it misses <span class="badge live">since the 1990s</span></h3>
        <p>By the 2009 data the national hospital-based system monitored over 1.3 million births, more than 8 per cent of all births in China, and 30 provincial hospital-based programmes covered a further 3.6 million, about 22 per cent. Its own authors set out the limits plainly: a short ascertainment period misses internal anomalies, inherited metabolic disease, and any malformed fetus aborted before the 28th week, and the absence of baseline data limits what the surveillance can say about causes. Those are the same limits that make a family-declared registry worth building beside it rather than instead of it.</p>
        <p class="src">Dai L, Zhu J, Liang J, Wang YP, Wang H, Mao M. Birth defects surveillance in China. <em>World J Pediatr</em> 2011;7(4):302-310 &middot; <a href="https://doi.org/10.1007/s12519-011-0326-0" target="_blank" rel="noopener external">doi:10.1007/s12519-011-0326-0</a></p>
      </article>
      <article class="entry">
        <h3>Syndactyly across 24 million births <span class="badge live">2007-2019</span></h3>
        <p>13,611 cases of syndactyly were identified among <strong>24,157,719 births</strong>, a prevalence of 5.63 per 10,000 overall, 4.66 isolated and 0.97 associated with another anomaly. The rate rose across the period for every type. The authors report it as notably higher than in other Asian and European countries, and call for the cause to be investigated. Among the cases affected on one side only, the hand was involved slightly more often than the foot. No cohort on this scale exists for any of our conditions in Europe.</p>
        <p class="src">Chen ZY, Li WY, Xu WL, et al. The changing epidemiology of syndactyly in Chinese newborns: a nationwide surveillance-based study. <em>BMC Pregnancy Childbirth</em> 2023;23(1):334 &middot; <a href="https://doi.org/10.1186/s12884-023-05660-z" target="_blank" rel="noopener external">doi:10.1186/s12884-023-05660-z</a></p>
      </article>
      <article class="entry">
        <h3>A province that publishes its own figures <span class="badge live">Hunan, 2016-2020</span></h3>
        <p>The Birth Defects Surveillance System of Hunan Province recorded 847,755 births and 14,459 birth defects, among them 1,888 cases of polydactyly and 626 of syndactyly, which is 13.06 and 4.33 per cent of all defects found. Prevalence was 2.23 per 1,000 for polydactyly and 0.74 per 1,000 for syndactyly, both rising year on year. Nearly all were diagnosed after birth rather than before it, 96.77 per cent of polydactyly and 95.69 per cent of syndactyly within seven days, which is what a limb difference usually does: it arrives unannounced.</p>
        <p class="src">Zhou X, Li T, Kuang H, et al. Epidemiology of congenital polydactyly and syndactyly in Hunan Province, China. <em>BMC Pregnancy Childbirth</em> 2024;24(1):216 &middot; <a href="https://doi.org/10.1186/s12884-024-06417-y" target="_blank" rel="noopener external">doi:10.1186/s12884-024-06417-y</a></p>
      </article>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">Brazil</p>
    <h2 class="h2">Brazil counts every birth, and still births children with thalidomide embryopathy.</h2>
    <p>Brazil records congenital anomalies on the birth certificate itself. <strong>SINASC</strong>, the national live-birth
    information system of the Ministry of Health, carries them in field 41 of the live-birth declaration, coded to chapter
    XVII of the ICD-10, and publishes through DATASUS. That makes it population-based in the strict sense: the denominator
    is every live birth in the country. Beside it runs <strong>ECLAMC</strong>, a network of maternity hospitals across South
    America coordinated from Porto Alegre since 1967. DysNet has no member association in Brazil, so each entry is verified
    from the source named with it.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>What SINASC shows about our conditions <span class="badge live">2010-2019</span></h3>
        <p>Across the decade the most frequent congenital anomaly of the upper limb in Brazil was supernumerary fingers,
        coded Q69.0, in <strong>11,708 children</strong>, a prevalence of 4.02 per 10,000 live births. Reporting of upper-limb
        anomalies rose over the ten years, which the authors read as an alert to health agencies rather than as a rise in
        occurrence. Mothers over 40 had a 36 per cent higher prevalence than mothers under 40. In 2021 the Ministry of Health,
        with the Brazilian Medical Genetics and Genomics Society, set a priority list of anomalies to improve that recording,
        chosen for being diagnosable at birth and having some intervention available.</p>
        <p class="src">Moura SRB, Nakachima LR, Santos JBGD, et al. Prevalence of Congenital Anomalies of the Upper Limbs in
        Brazil. <em>Sao Paulo Med J</em> 2024;142(6):e2023349 &middot;
        <a href="https://doi.org/10.1590/1516-3180.2023.0349.R1.08042024" target="_blank" rel="noopener external">doi:10.1590/1516-3180.2023.0349.R1.08042024</a>
        &middot; <a href="https://datasus.saude.gov.br/nascidos-vivos" target="_blank" rel="noopener external">datasus.saude.gov.br</a></p>
      </article>
      <article class="entry">
        <h3>Thalidomide has not finished in Brazil <span class="badge live">surveillance since 2007</span></h3>
        <p>Thalidomide is still dispensed in Brazil for erythema nodosum leprosum, because leprosy is endemic there, and
        children are still being born with thalidomide embryopathy. A phenotype was defined so that it could be watched
        prospectively across the ECLAMC hospitals. Its frequency reached <strong>3.10 per 10,000 births</strong>
        (95% CI 2.50-3.70) against a 1982-1999 baseline of 1.92 per 10,000 (95% CI 1.60-2.20), significantly higher and not
        evenly spread across the country. In the proactive period of 2007 and 2008 two suspected cases were found, and in
        both the mother denied having taken the drug.</p>
        <p>This is the founding subject of our own network, sixty years on, in a country where the drug is lawfully in use.
        It is also the clearest argument we have for <a href="/knowledge/teratogens/">the teratogens register</a> and for
        <a href="/voice/#demand-5">demand 5</a>: a substance whose harm is beyond dispute still reaches pregnancies, and only
        surveillance finds it.</p>
        <p class="src">Vianna FS, Lopez-Camelo JS, Leite JC, et al. Epidemiological surveillance of birth defects compatible
        with thalidomide embryopathy in Brazil. <em>PLoS One</em> 2011;6(7):e21735 &middot;
        <a href="https://doi.org/10.1371/journal.pone.0021735" target="_blank" rel="noopener external">doi:10.1371/journal.pone.0021735</a>
        &middot; with Sales Luiz Vianna F, et al. <em>Eur J Med Genet</em> 2017;60(1):12-15,
        <a href="https://doi.org/10.1016/j.ejmg.2016.09.015" target="_blank" rel="noopener external">doi:10.1016/j.ejmg.2016.09.015</a></p>
      </article>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">Japan</p>
    <h2 class="h2">Japan has published rates for our conditions since 1974.</h2>
    <p>This register was built from the Orphanet records of patient registries, and those records describe Europe. That is
    why Japan, Pakistan and T&uuml;rkiye were missing from it until September 2026, and why their absence said nothing
    about those countries. Japan has a national programme. The <strong>JAOG Birth Defects Monitoring Program</strong>, run
    by the Japan Association of Obstetricians and Gynecologists, started in 1972 and became a full member of the
    International Clearinghouse in 1988. As the Clearinghouse described it in 2014, the programme collected from 270
    hospitals throughout the country, about 100,000 births a year, some 9 per cent of the national total, and it included
    stillbirths from 22 weeks. Like the Chinese network it
    samples the country rather than covering it, so its outline on the map claims no coverage of the births in Japan.
    DysNet has no member association in Japan, so each entry below is verified from the source named with it.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>It publishes limb reduction defects by subtype <span class="badge live">2012</span></h3>
        <p>In 2012 the programme reported 108,087 births, 107,481 of them live. It counted 21 limb reduction defects among
        the live births and 7 among the stillbirths, a total rate of <strong>2.59 per 10,000</strong>, and it published the
        split: transverse 0.19, preaxial 0.46, postaxial 0.37, intercalary 0.56, mixed 0.93 and unspecified 0.09 per
        10,000. Preaxial polydactyly reached 6.85 per 10,000.</p>
        <p>That split is the point. An ICD-10 code gives Q71 or Q72 and stops there, while this programme separates the
        axis along which the limb failed to form, which is the distinction the Oberg-Manske-Tonkin groups on
        <a href="/knowledge/understanding-dysmelia/">our conditions page</a> are built on. A national surveillance system
        has been recording our conditions in that vocabulary for decades, outside every network we belong to.</p>
        <p class="src">International Clearinghouse for Birth Defects Surveillance and Research, <em>Annual Report 2014</em>,
        programme description and data tables for Japan: JAOG &middot;
        <a href="https://www.icbdsr.org/wp-content/annual_report/Report2014.pdf" target="_blank" rel="noopener external">icbdsr.org</a>
        &middot; read 21 September 2026</p>
      </article>
      <article class="entry">
        <h3>Four decades of rates, and no entry in the current international report <span class="badge live">1974-2011</span></h3>
        <p>The same report carries the programme&rsquo;s own series in five-year blocks, across <strong>4,052,935
        births</strong> between 1974 and 2011. Limb reduction defects ran at 3.22 per 10,000 in 1997-2001, 3.58 in
        2002-2006 and 3.81 in 2007-2011. Transverse defects held close to 0.3 throughout, while intercalary defects moved
        between 0.73 and 1.04. The only series of comparable length in this register is the Medical Birth Registry of
        Norway, which published limb reduction defects from 1970 to 2016.</p>
        <p>The programme does not appear among the 31 in the Clearinghouse&rsquo;s 2024 report. It has not stopped: a 2022
        study used its data up to 2019 and described it as the only national survey of congenital anomalies in Japan. A
        programme can keep running and still leave the international series, and once it does, its figures stop being
        comparable with anyone else&rsquo;s. The Indian network above shows the same fragility arriving by a different
        route.</p>
        <p class="src">ICBDSR, <em>Annual Report 2014</em> and <em>Annual Report 2024</em> &middot;
        <a href="https://www.icbdsr.org/resources/annual-report/" target="_blank" rel="noopener external">icbdsr.org/resources/annual-report</a>
        &middot; with Sugo Y, Kurasawa K, Saigusa Y, Hamanoue H, Hirahara F, Miyagi E. Changes in the number of babies born
        with Down syndrome in Japan. <em>J Obstet Gynaecol Res</em> 2022;48(9):2385-2391,
        <a href="https://doi.org/10.1111/jog.15342" target="_blank" rel="noopener external">doi:10.1111/jog.15342</a></p>
      </article>
      <article class="entry">
        <h3>The country surveyed limb deficiency once <span class="badge live">2014-2015</span></h3>
        <p>A two-stage postal survey went to 2,283 of the 7,825 orthopaedic, paediatric and plastic surgery departments in
        Japan, and 1,767 replied. Of those, 161 had seen at least one new patient with congenital limb deficiency, and 96
        answered the detailed second round. The survey estimated <strong>417 first visits a year</strong> (95% CI 339-495)
        and a birth prevalence of <strong>4.15 per 10,000 live births</strong> (95% CI 3.37-4.93), with a sex ratio of 1.40
        and the upper limbs affected more often than the lower.</p>
        <p>That figure is worth holding beside our own. The dots on the <a href="/#map">landing-page map</a> rest on the
        EUROCAT rate of about 45 per 100,000 births for all limb reduction defects, which is 4.5 per 10,000, and Japan
        reports 4.15 per 10,000 from a different method on a different continent. The two definitions are not identical,
        since this survey counts absence proximal to the finger joints while EUROCAT counts its own list of reduction
        defects, so the agreement is an indication rather than a validation. It is still the first figure from outside
        Europe that this register can set against the number our estimates are built on.</p>
        <p>Its authors call it the first nationwide epidemiological survey of congenital limb deficiency in Japan. A survey
        answers a question once, and this one ran for two years. A registry keeps answering, and that difference is the
        reason this register exists.</p>
        <p class="src">Mano H, Fujiwara S, Takamura K, et al. Congenital limb deficiency in Japan: a cross-sectional
        nationwide survey on its epidemiology. <em>BMC Musculoskelet Disord</em> 2018;19(1):262 &middot;
        <a href="https://doi.org/10.1186/s12891-018-2195-3" target="_blank" rel="noopener external">doi:10.1186/s12891-018-2195-3</a></p>
      </article>
      <article class="entry">
        <h3>A national birth cohort, and 369 limb differences in it <span class="badge live">JECS</span></h3>
        <p>The Japan Environment and Children&rsquo;s Study is a national birth cohort that records congenital anomalies
        from the medical record at delivery and at one month. Among its children, <strong>369 had a congenital limb
        abnormality</strong> and 89,794 had none; of the 369, 185 were polydactyly and 142 syndactyly. The study was
        examining whether cadmium, lead, mercury, selenium and manganese in maternal blood are associated with those
        anomalies, and found no significant association.</p>
        <p>This is the nearest existing design to the one DysNet argues for, families followed from pregnancy rather than
        from the first appointment, and it shows both what that design can answer and what it cannot. A cohort closes
        to new entrants, its consent belongs to the study rather than to the family, and when it ends the children are no
        longer counted anywhere.</p>
        <p class="src">Ikeda A, Marsela M, Miyashita C, et al. Heavy metals and trace elements in maternal blood and
        prevalence of congenital limb abnormalities among newborns: the Japan Environment and Children&rsquo;s Study.
        <em>Environ Health Prev Med</em> 2024;29:36 &middot;
        <a href="https://doi.org/10.1265/ehpm.23-00366" target="_blank" rel="noopener external">doi:10.1265/ehpm.23-00366</a></p>
      </article>
      <article class="entry">
        <h3>Registration was already an aim in 1976 <span class="badge live">JSSH</span></h3>
        <p>The Japanese Society for Surgery of the Hand set up a congenital hand anomaly committee in 1976, whose stated
        aims were a Japanese nomenclature, the registration of cases of congenital hand anomaly, and the teaching of young
        doctors. The society went on to modify the IFSSH classification for its own use. The review that records all this
        reports no registry operating from that aim, fifty years later.</p>
        <p>Two lessons sit in that sentence. A classification and a registry are not the same undertaking, and a
        professional society can carry the first for half a century without the second. It is also a reason to ask the
        society directly rather than to conclude from silence, the same approach the <a href="/registry/">registry
        page</a> sets out for the northern European hand registries.</p>
        <p class="src">Minamikawa Y, Horii E, Hamada Y. Hand Surgery in Japan. <em>J Hand Microsurg</em> 2021;13(1):42-48
        &middot; <a href="https://doi.org/10.1055/s-0041-1725210" target="_blank" rel="noopener external">doi:10.1055/s-0041-1725210</a></p>
      </article>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">Pakistan</p>
    <h2 class="h2">Pakistan has no registry, and the researchers who counted said so themselves.</h2>
    <p>Pakistan has no national birth-defects registry, no registry for limb difference, and no programme in either the
    2014 or the 2024 report of the International Clearinghouse. What exists is a research cohort in the northwest of the
    country, a twelve-month newborn screening programme in Karachi, and a published call for a registry from the people
    best placed to make it. No outline is drawn for Pakistan on the map, because drawing one would claim a coverage that
    nobody has. DysNet has no member association in Pakistan.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>141 people, 166 limbs, and a call for a national registry <span class="badge live">2017-2021</span></h3>
        <p>A prospective cross-sectional study at the Armed Forces Institute of Rehabilitation Medicine in Rawalpindi and
        Quaid-i-Azam University in Islamabad recruited <strong>141 individuals with 166 affected limbs</strong>. It found 77
        transverse defects (55 per cent), 61 longitudinal (43 per cent) and 3 intercalary (2 per cent). Among the transverse
        defects, 52 were terminal and 25 were symbrachydactyly. Among the longitudinal, thumb aplasia or hypoplasia led with
        20 cases, then oligodactyly and radial hemimelia with 18 each. Upper limbs were involved in 86 per cent, one side
        only in 83 per cent, and 92 per cent of cases were sporadic. Parental consanguinity appeared in 33 per cent.</p>
        <p>Three of those diagnoses are conditions this site describes and codes, terminal transverse limb defect,
        symbrachydactyly and radial aplasia, so the data is already compatible with our own coding. The authors end by
        stating the need to establish a national registry for congenital limb deficiency. That is a call from a clinical
        rehabilitation service and a genetics department together, which is exactly the pairing a registry needs.</p>
        <p class="src">Bibi A, Uddin S, Naeem M, Syed A, Ud-Din Qazi W, Rathore FA, Malik S. Prevalence pattern, phenotypic
        manifestation, and descriptive genetics of congenital limb deficiencies in Pakistan. <em>Prosthet Orthot Int</em>
        2023;47(5):479-485 &middot;
        <a href="https://doi.org/10.1097/PXR.0000000000000204" target="_blank" rel="noopener external">doi:10.1097/PXR.0000000000000204</a></p>
      </article>
      <article class="entry">
        <h3>A year of newborn screening in three Karachi hospitals <span class="badge live">2023-2024</span></h3>
        <p>Between 10 July 2023 and 30 June 2024, health workers screened <strong>18,728 of the 25,414 births</strong> at
        three public hospitals in Karachi, Sindh Government Qatar Hospital, Civil Hospital Karachi and Jinnah Postgraduate
        Medical Centre, a coverage of 73.7 per cent. Among the major anomalies found in live births, clubfoot was the most
        common with 78 cases, and <strong>23 were limb deficiencies</strong>.</p>
        <p>The programme describes itself as cross-sectional, so it has an end date. It also puts the real question in view.
        Reaching nearly three quarters of the births at three hospitals took health workers examining newborns one by one,
        and that is the recurring cost any Pakistani registry would have to carry rather than a one-off effort.</p>
        <p class="src">Samad L, Junejo S, Ali Muhammad A, et al. Newborn screening for external congenital anomalies at
        three public hospitals in Karachi, Pakistan. <em>BMJ Paediatr Open</em> 2026;10(1):e004015 &middot;
        <a href="https://doi.org/10.1136/bmjpo-2025-004015" target="_blank" rel="noopener external">doi:10.1136/bmjpo-2025-004015</a></p>
      </article>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">T&uuml;rkiye</p>
    <h2 class="h2">T&uuml;rkiye could count our conditions tomorrow, from codes we have already published.</h2>
    <p>T&uuml;rkiye (Turkey) has no congenital anomaly registry that this register can find. None appears in the Orphanet
    records it is built from, none in the EUROCAT list of member and associate registries, and none among the Clearinghouse
    programmes in either the 2014 or the 2024 report. What the country has instead is a national electronic health record,
    <strong>e-Nab&#305;z</strong>, with a health record reporting system behind it, and both are coded to ICD-10. DysNet has
    no member association in T&uuml;rkiye.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>A rare disease counted nationally, without a registry <span class="badge live">2016-2023</span></h3>
        <p>A study of congenital myasthenic syndromes queried the national reporting system for patients carrying the
        ICD-10 code G70.2 at least three times between 1 January 2015 and 22 May 2024, and analysed the years 2016 to 2023.
        It identified <strong>406 patients</strong> across the country. The state insurance covers most of the population,
        so the denominator is close to national.</p>
        <p>{ICD_COUNTED} of the {len(CONDITIONS)} conditions on our <a href="/knowledge/understanding-dysmelia/">conditions
        page</a> carry an ICD-10 code, the rest being Orphanet groups that ICD-10 has no single code for, which means the
        same query could be run for most of limb difference in T&uuml;rkiye the day somebody asks for it. The limits deserve saying in the same breath. A count of codes holds no phenotype, no
        laterality, no consent and no follow-up, a family cannot see or correct its own entry, and a coding error is
        invisible. It answers how many, and almost nothing else.</p>
        <p class="src">Inan B, et al. Epidemiological study of congenital myasthenic syndromes based on national electronic
        health database of Turkiye. <em>North Clin Istanb</em> 2025;12(4):468-474 &middot;
        <a href="https://doi.org/10.14744/nci.2025.08455" target="_blank" rel="noopener external">doi:10.14744/nci.2025.08455</a></p>
      </article>
      <article class="entry">
        <h3>What one hospital sees in ten years <span class="badge live">2014-2023</span></h3>
        <p>At Pamukkale University Hospital there were 16,030 births over ten years, and <strong>941 newborns</strong>, 5.87
        per cent, were diagnosed with a congenital anomaly. Cardiovascular anomalies accounted for 42 per cent of them,
        central nervous system anomalies 7 per cent and musculoskeletal anomalies 4 per cent, and 229 children, 24 per
        cent, had more than one anomaly. The authors conclude that national registries and epidemiological studies are
        needed for reliable figures.</p>
        <p>A single hospital series is what a country without a registry has to argue from, and it cannot say whether the
        rate it reports is the country&rsquo;s rate. The same authors reporting the same numbers from a national register
        would change what a health ministry could be asked for.</p>
        <p class="src">&Ccedil;etin H, Sorkun S, Lafc&#305; &#304;, et al. Congenital Anomaly Prevalence: A 10-Year
        Retrospective Study in a Tertiary Hospital in Turkey. <em>Birth Defects Res</em> 2026;118(9):e70113 &middot;
        <a href="https://doi.org/10.1002/bdr2.70113" target="_blank" rel="noopener external">doi:10.1002/bdr2.70113</a></p>
      </article>
    </div>

    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/resources/"] = {
    "title": "Resources",
    "desc": "Guides, surveys and reports on dysmelia that are not research papers: Orphanet sheets, the Rare Barometer, European registry recommendations.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/resources/", "Resources")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-library);--acc-text:var(--acc-library-text)">
    <div class="tick"></div>
    <p class="eyebrow">Knowledge · Resources</p>
    <h1 class="display">Resources on limb difference: guides, surveys and reports.</h1>
    <p>Reference works, surveys and reports that families, clinicians and associations return to, each with a short description and a link to its source. They are grouped by who tends to need them; nothing here is behind a paywall unless the entry says so.</p>
    {opener("01", "For families", "What can a family read first?")}
    <p>Written for people living with a limb difference and for those around them, free to download, and published by associations that answer the phone when a question follows.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>Language guide and family booklet, Reach <span class="badge live">free</span></h3>
        <p>Reach publishes a guide to the words used about upper limb difference, a booklet for families and new parents, and topic guides on appointments, surgery decisions, school and driving. Its page for professionals also points to the directory of dedicated children’s hand clinics that our <a href="/knowledge/care-centres/">care centres</a> map now lists.</p>
        <p class="src">Reach · <a href="https://www.reach.org.uk/resources/language-guide" target="_blank" rel="noopener external">reach.org.uk · language guide</a> · <a href="https://www.reach.org.uk/professionals" target="_blank" rel="noopener external">for professionals</a> · topic: upper limb, daily life</p>
      </article>
      <article class="entry">
        <h3>Condition factsheets for families, Steps <span class="badge live">free</span></h3>
        <p>Our member association for lower-limb conditions publishes free factsheets and booklets, several of them on the conditions this site describes: proximal femoral focal deficiency, tibial hemimelia, fibular hemimelia, leg length difference, planned amputation, and a leaflet for a diagnosis received during pregnancy.</p>
        <p class="src">Steps Charity Worldwide · <a href="https://steps-charity.org.uk/resources/" target="_blank" rel="noopener external">steps-charity.org.uk · resources</a> · topic: lower limb, daily life</p>
      </article>
      <article class="entry">
        <h3>Orphanet condition sheets on limb reduction defects <span class="badge live">source</span></h3>
        <p>The European reference database for rare diseases documents the conditions grouped under dysmelia, from amelia to ulnar hemimelia. Our <a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a> guide is built on it.</p>
        <p class="src">Orphanet · <a href="https://www.orpha.net/en/disease/encyclopedia" target="_blank" rel="noopener external">orpha.net · encyclopedia for patients</a> · topic: conditions</p>
      </article>
      <article class="entry" id="rare-barometer">
        <h3>Rare Barometer: take part in the surveys <span class="badge live">open to patients and families</span></h3>
        <p>EURORDIS runs the survey programme that turns what patients live into evidence, and it is patients who fill it in. Anyone living with a rare condition, anywhere in the world, can register, as can their family members and carers; responses are anonymous, invitations arrive by email, and participants receive the results of the surveys they answered. DysNet contributes content and translations, and relays each wave to its member associations.</p>
        <p class="src">EURORDIS · <a href="https://www.eurordis.org/rare-barometer/english/" target="_blank" rel="noopener external">register to take part</a> · what the surveys found is published for everyone, below · see also our <a href="/knowledge/ongoing-studies/">studies to join</a> · topic: lived experience, participation</p>
      </article>
      <article class="entry">
        <h3>Emergency card and factsheet for thalidomide survivors, Stichting NESOS <span class="badge live">free</span></h3>
        <p>A card for the wallet and a two-page factsheet, written so that an unknown doctor, an out-of-hours service or an emergency department knows in seconds what to take into account. Our Dutch member association developed them with the emergency department of the Radboud university hospital in Nijmegen, and publishes an English version of the folder as well. The medical pages carry the reasoning behind them: intubation complicated by airway and cervical anomalies, blood pressure that cannot be relied on at arm or leg, pulses that may not be palpable, and the instruction never to pull on arms or legs when moving an unconscious patient.</p>
        <p class="src">Stichting NESOS · <a href="https://softenon.nl/medische-informatie/emergency-card/" target="_blank" rel="noopener external">softenon.nl · emergency card</a> · <a href="https://softenon.nl/medische-informatie/factsheet/" target="_blank" rel="noopener external">the factsheet</a> · topic: emergency care</p>
      </article>
    </div>

    {opener("02", "For clinicians and researchers", "What do clinicians and researchers turn to?")}
    <p>Reference lists, survey programmes and the European standard for running a registry well. Peer-reviewed papers on our conditions live in the <a href="/knowledge/bibliography/">bibliography</a>.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>Rare Barometer results: what the surveys found <span class="badge live">source</span></h3>
        <p>The published results of the programme, free to read and to cite. They are written for the people who answered as much as for professionals: each survey is reported in plain language and in a form policymakers can use, which is how the experience of living with a rare condition reaches European decisions. Bone and limb diseases are among the conditions covered.</p>
        <p class="src">EURORDIS · <a href="https://www.eurordis.org/resources-search/?filterPostType=publications&amp;filterPublicationsTag=rare-barometer-survey-results" target="_blank" rel="noopener external">eurordis.org · survey results</a> · topic: lived experience, evidence</p>
      </article>
      <article class="entry">
        <h3>Recommendations for improving the quality of rare disease registries <span class="badge live">peer-reviewed</span></h3>
        <p>The European reference on what a rare-disease registry is and how to run one well: definition, governance, data quality, patient involvement and sustainability. The yardstick DysNet uses for its own initiative.</p>
        <p class="src">Kodra Y, Weinbach J, Posada-de-la-Paz M, et al. Int J Environ Res Public Health 2018;15(8):1644 · <a href="https://doi.org/10.3390/ijerph15081644" target="_blank" rel="noopener external">doi:10.3390/ijerph15081644</a> · topic: registries, research methods</p>
      </article>
      <article class="entry">
        <h3>Thalidomide research bibliography, The Thalidomide Trust <span class="badge live">source</span></h3>
        <p>The Trust keeps its own list of published thalidomide research from around the world, sorted into anomalies, physical health, mental health and quality of life, as a single point of access. The Trust states that the list does not claim to be exhaustive. Our own <a href="/knowledge/bibliography/">bibliography</a> covers the same literature with verified citations.</p>
        <p class="src">The Thalidomide Trust · <a href="https://thalidomidetrust.org/professional-resources-research/thalidomide-research-bibliography/" target="_blank" rel="noopener external">thalidomidetrust.org · research bibliography</a> · topic: thalidomide</p>
      </article>
    </div>

    {opener("03", "From the network", "What has DysNet published or taken part in?")}
    <p>Our own proceedings, and the accounts that record where this network came from.</p>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>Biorobotics for limb difference: conference proceedings, Milan 2026 <span class="badge live">DysNet event</span></h3>
        <p>Findings from the conference DysNet co-organised at Regione Lombardia (Palazzo Pirelli, 26 March 2026) with university researchers, prosthetics producers and patient associations.</p>
        <p class="src">DysNet &amp; Regione Lombardia · report available to members · topic: prosthetics, biorobotics</p>
      </article>
      <article class="entry">
        <h3>EDRIC explained: the slides from Nijmegen <span class="badge live">October 2017</span></h3>
        <p>Twenty-five slides that state what this network was built to do, presented by Michi Moik in Nijmegen on 13 October 2017.
        They record the founding: an NGO registered in Sweden in January 2009 by
        FfdN and the Thalidomide Trust, with three aims, to preserve the knowledge of the thalidomide survivors, to build an
        international European community, and to launch and maintain an information website. They then show the federation as it
        stood, 32 member organisations across 18 countries, and what dysnet.org then carried: articles, a catalogue of
        professionals, a forum, a resource database and the Dysmelia Knowledge Base, whose thalidomide section alone held 274
        entries.</p>
        <p>Two findings are worth the detour. The survey run with the University of Leeds, <em>What if your baby has a limb
        difference</em>, found that 39.1% of parents learned of the difference at an ultrasound scan and 60.4% only at birth. And
        the Dysmelia Experts&rsquo; Forum in Stockholm, 8 to 11 October 2015, brought 90 participants and 15 presenters into one
        room, which is the format our conferences still use. The closing slides explain the European Reference Networks launched
        that year, the structure in which DysNet now holds a seat.</p>
        <p class="src">Michi Moik, EDRIC · presented at Nijmegen, 13 October 2017 ·
        <a href="/assets/edric-nijmegen-2017.pdf" download>Download the slides</a> (PDF, 25 slides, 1.6 MB) ·
        see also <a href="/about/">how the network is organised today</a> · topic: our history</p>
      </article>
      <article class="entry">
        <h3>Portrait of a European militant: Björn Håkansson, EURORDIS <span class="badge live">August 2009</span></h3>
        <p>The story of the network, told the year it was registered. Björn Håkansson, then president of the Swedish Thalidomide
        Society (FfdN), was born in 1960 with dysmelia after his mother was prescribed thalidomide to help her sleep. EURORDIS
        records what that community built: the EX-Center, set up in 1993 at the Red Cross Hospital in Stockholm and, in his words,
        one of the first centres of expertise a disability organisation ran on the same platform as a hospital; and the
        compensation the Swedish government agreed in 2001, 55,000 euros per person, on top of the payments the distributor has
        made twice a year since 1970. It also gives the Swedish count: 170 children born with thalidomide damage between 1957 and
        1963, of whom 118 survived.</p>
        <p>The last project he describes is the one he had just started with the British Thalidomide
        Trust, because the people who knew thalidomide were growing old and a newborn with dysmelia might never meet a doctor who
        had seen it before: the European Dysmelia Reference Information Centre, EDRIC, which became DysNet.</p>
        <p class="src">EURORDIS, Living with a Rare Disease, August 2009 · <a href="https://www.eurordis.org/stories/dysmelia-swedish-thalidomide-victim/" target="_blank" rel="noopener external">eurordis.org · Dysmelia: Swedish thalidomide victim</a> · topic: thalidomide, our history</p>
      </article>
    </div>

    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/researchers/"] = {
    "title": "Researchers",
    "desc": "The DysNet register of researchers and teams working on congenital limb difference: who works on what, where, and how to reach them.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/researchers/", "Researchers")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-research);--acc-text:var(--acc-research-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 3 · Researchers {updated_badge(RESEARCHERS.get("built"))}</p>
    <h1 class="display">Who works on limb difference.</h1>
    <p>A factual register: teams that publish or run studies on congenital limb difference. Listing is by activity, not endorsement, so no one is preferred and no one is left out. Two partners DysNet has met in person open the list; the teams that publish on our conditions follow, drawn from the bibliography.</p>

    <h2 class="h3" style="margin-top:var(--space-4)">Partners DysNet has met in person</h2>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>The BioRobotics Institute · Scuola Superiore Sant’Anna, Pisa <span class="badge live">active</span></h3>
        <p>Research on advanced upper-limb prosthetics, including the bionic hand presented to DysNet associations by Prensilia’s managing director, engineer Francesco Clemente.</p>
        <p class="src">Pisa, Italy · biorobotics, prosthetics · <a href="https://www.santannapisa.it">santannapisa.it</a></p>
      </article>
      <article class="entry">
        <h3>INAIL Centro Protesi research unit <span class="badge live">active</span></h3>
        <p>Italy’s national prosthetics centre pairs clinical fitting with applied research on prosthetic technology and rehabilitation. The DysNet board visited in August 2024.</p>
        <p class="src">Vigorso di Budrio, Italy · prosthetics, rehabilitation · <a href="https://www.inail.it">inail.it</a></p>
      </article>
    </div>

    <div class="tick" style="margin-top:var(--space-5)"></div>
    <p class="eyebrow">Teams that publish · {len(RESEARCHERS.get("teams", []))} institutions</p>
    <h2 class="h2">Who publishes on our conditions.</h2>
    <p>Orphanet’s directory of research projects lists nothing specific to our ORPHAcodes, so this register is built from the evidence itself: the institutions of the first and senior authors of every publication in our <a href="/knowledge/bibliography/#bibliography">bibliography</a>, read from PubMed’s own affiliation records. An institution appears once it signs at least two of those publications. The count and the years say how active a team has been; the tags say on which conditions. Teams that want to be listed or corrected: <a href="mailto:info@dysnet.org?subject=Researchers%20register">info@dysnet.org</a>.</p>
    {researchers_html()}
    <p class="annex-note">Built {RESEARCHERS.get("built", "")} from {RESEARCHERS.get("bibliography_size", "")} PubMed records; {RESEARCHERS.get("records_without_affiliation", "")} older records carry no affiliation in PubMed and could not be attributed. <a href="/data/researchers.json">Download the data (JSON, CC BY 4.0)</a>.</p>
    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/care-centres/"] = {
    "title": "Care centres",
    "desc": "Reference centres, prosthetics units and expert clinics for congenital limb difference in Europe and beyond, so a family can find the nearest one.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/care-centres/", "Care centres")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-centres);--acc-text:var(--acc-centres-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 4 · Care centres {updated_badge(CARE_CENTRES_BUILT)}</p>
    <h1 class="display">Care centres for limb difference: where expertise lives.</h1>
    <p>The map of reference and competence centres for limb difference, in Europe and beyond, validated with our member associations so a family anywhere knows where the nearest expertise is. Every centre listed here was named by one of our member associations on its own website or visited by the board, and appears as an orange marker on the <a href="/">world map</a> on our home page. Where DysNet has no member association yet, a centre earns its place differently: its own institutional page must state congenital limb difference, limb reconstruction or prosthetic fitting in its scope, and those entries say <em>verified from</em> rather than <em>named by</em>, so you can see at a glance which are community-validated and which are not. The dedicated children’s hand clinics of the United Kingdom and Ireland come from the directory that the British Society for Surgery of the Hand publishes for families, which our member association Reach points parents to when they ask for a referral. {len(CARE_CENTRES)} centres in {len({c["country"] for c in CARE_CENTRES})} countries so far; associations add theirs by writing to <a href="mailto:info@dysnet.org?subject=Care%20centre">info@dysnet.org</a>. <a href="/data/care-centres.json">Download the data (JSON, CC BY 4.0)</a>.</p>

    <h2 class="h3" style="margin-top:var(--space-4)">Where the list comes from</h2>
    <div style="margin-top:var(--space-2)">
      <article class="entry">
        <h3>ERN BOND network centres <span class="badge live">source</span></h3>
        <p>The European Reference Network for rare bone diseases connects expert hospitals across the EU. DysNet’s seat in its patient advocacy group is the channel for validating limb-difference centres.</p>
        <p class="src">EU-wide · <a href="https://ernbond.eu">ernbond.eu</a></p>
      </article>
      <article class="entry">
        <h3>Orphanet directory of expert centres <span class="badge live">source</span></h3>
        <p>Orphanet maintains the European directory of expert centres for rare diseases, searchable by condition and country. Our register cross-references it: each DysNet-validated centre links to its Orphanet record.</p>
        <p class="src">Orphanet · <a href="https://www.orpha.net/en/expert-centres" target="_blank" rel="noopener external">orpha.net/en/expert-centres</a></p>
      </article>
      {centres_html()}
    </div>

    <figure class="photo" style="margin-top:var(--space-4)">
      <picture><source srcset="/assets/img/inail-lab-tour.webp" type="image/webp"><img src="/assets/img/inail-lab-tour.jpg" alt="The DysNet board touring a prosthetics workshop at the INAIL centre, with casts and tools on the benches" width="1400" height="787" loading="lazy" decoding="async"></picture>
      <figcaption>The DysNet board visiting the INAIL prosthetics workshops, Vigorso di Budrio, August 2024. Photo: DysNet.</figcaption>
    </figure>
    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/teratogens/"] = {
    "title": "Teratogens register",
    "desc": "Substances with known, presumed or suspected effects on the unborn child, each with its source, its level of evidence and its status where you live.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/teratogens/", "Teratogens register")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-centres);--acc-text:var(--acc-centres-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 5 · Substances of concern {updated_badge(TERA.get("built"))}</p>
    <h1 class="display">Teratogens register: which products can harm the unborn child, and who says so.</h1>
    <p>Families ask a simple question after a diagnosis: could something have caused this? No public authority answers it with one list. The World Health Organization keeps none. What exists is scattered across chemical law, medicines regulation and one American state. This register brings those lists together, names the source for every entry, states how strong the evidence is, and says where each substance is banned, restricted, labelled or simply allowed.</p>
    <p>It is not medical advice. For a question about a medicine or an exposure during a pregnancy, ask a teratology information service: <a href="https://www.lecrat.fr/" target="_blank" rel="noopener external">CRAT</a> in France, <a href="https://www.medicinesinpregnancy.org/" target="_blank" rel="noopener external">bumps</a> in the United Kingdom, <a href="https://mothertobaby.org/" target="_blank" rel="noopener external">MotherToBaby</a> in North America, or the <a href="https://www.entis-org.eu/centers" target="_blank" rel="noopener external">ENTIS member</a> in your country.</p>

    {opener("01", "How to read it", "Three levels of evidence, seven sources, one status per jurisdiction.")}
    <ul>
      <li><strong>Known</strong>: human evidence. In the EU this is category 1A of the harmonised classification; for medicines, a documented human teratogen; in California, a substance the State lists after its own experts review it, or because another law already requires the warning.</li>
      <li><strong>Presumed</strong>: strong animal evidence. Category 1B in the EU, a medicine contraindicated in pregnancy on animal data, or a substance California lists on an authoritative body&rsquo;s review, which is usually a review of animal studies. California&rsquo;s own wording is &ldquo;known to the State&rdquo;, a legal status rather than a statement about human evidence, so we read the basis of each listing rather than the phrase.</li>
      <li><strong>Suspected</strong>: limited evidence, category 2 in the EU, or an association shown in epidemiological studies.</li>
      <li><strong>A second authority</strong>: {TERA.get("counts", {}).get("nite", 0)} entries also carry a classification made by the Japanese government, through the GHS classification projects of the National Institute of Technology and Evaluation, to implement the labelling and safety-data-sheet duties of the Industrial Safety and Health Act and the PRTR Law. {TERA.get("counts", {}).get("nite_not_in_clp", 0)} of them have no EU harmonised entry. Each classification names the ministry that made it and the fiscal year, and links to its own page with the studies it rests on. It corroborates an entry and adds a jurisdiction; it does not set the level, because a GHS hazard code does not separate category 1A from category 1B.</li>
      <li><strong>What was decided, and by whom</strong>: the paragraphs below describe what the law provides. A tag on a card describes what an authority actually decided about that substance, and names it. {TERA.get("counts", {}).get("legal_any", 0)} entries carry at least one. The European Commission has refused {TERA.get("counts", {}).get("legal_eu-ppp", 0) - TERA.get("counts", {}).get("legal_eu-ppp-approved", 0)} of them as pesticide active substances and <strong>approved {TERA.get("counts", {}).get("legal_eu-ppp-approved", 0)}</strong>; {TERA.get("counts", {}).get("legal_reach-xvii", 0)} may not be sold to the general public at all; {TERA.get("counts", {}).get("legal_cosmetics", 0)} may not go into a cosmetic product; {TERA.get("counts", {}).get("legal_reach-xiv", 0)} need a Commission authorisation for any use; {TERA.get("counts", {}).get("legal_stockholm", 0)} are eliminated worldwide by treaty; and {TERA.get("counts", {}).get("legal_rotterdam", 0)} have been banned or severely restricted by at least one country, which the card names. An approval is not a contradiction: the EU excludes a category 1A or 1B reproductive toxicant from pesticide approval unless exposure is negligible, and category 2 is not excluded at all. It is, though, a decision worth seeing next to the evidence.</li>
      <li><strong>How much is tolerable</strong>: for substances in the food chain, the European Food Safety Authority derives the intake it considers tolerable and names the effect that figure rests on. {TERA.get("counts", {}).get("efsa", 0)} entries carry such a value, read from EFSA&rsquo;s pages and from its chemical hazards database, OpenFoodTox 3.0 (CC BY-ND 4.0). EFSA does not classify teratogens and its remit stops at food and feed, so its values sit beside the evidence level, never instead of it.</li>
    </ul>
    <p><strong>Independent hazard frameworks.</strong> Manufacturers and certifiers increasingly rate chemicals with two non-profit frameworks that score developmental and reproductive toxicity among their endpoints. <a href="https://www.greenscreenchemicals.org/learn/full-greenscreen-method" target="_blank" rel="noopener external">GreenScreen for Safer Chemicals</a> (Clean Production Action) assigns Benchmarks 1 to 4, Benchmark 1 being a chemical of high concern, through assessments by licensed profilers such as ToxServices; its free List Translator flags as LT-1 any chemical that an authoritative list already classes as a high-hazard reproductive or developmental toxicant, and its <a href="https://registry.greenscreenchemicals.org/" target="_blank" rel="noopener external">public registry</a> tells you, by CAS number, whether a full assessment exists. <a href="https://www.chemforward.org/" target="_blank" rel="noopener external">ChemFORWARD</a> rates chemicals used in consumer products and building materials in hazard bands A to F across 24 endpoints; its published <a href="https://static1.squarespace.com/static/60611efa464a766c6a812834/t/6657f7d9c7241a2e6ba86b55/1717041115329/Chemical+Rating+Guidance+v2.2_Abbreviated.pdf" target="_blank" rel="noopener external">rating guidance</a> places in band F, by list screening alone, every substance with an EU harmonised Repr. 1 classification or on the REACH candidate and authorisation lists as a reproductive toxicant. The two organisations <a href="https://www.chemforward.org/news/chemforward-and-greenscreen-offer-aligned-outputs-for-hazard-data-toxservices" target="_blank" rel="noopener external">reported in 2021</a> that their outputs are aligned. Full assessments sit behind subscriptions, so this register cannot import their scores; where an entry meets ChemFORWARD's published F-band criterion, it says so.</p>
    <p>The <strong>EU harmonised classification</strong> is binding law: once a substance carries a hazard statement for the unborn child (H360D, H361d and their variants), every container of it, and of mixtures containing it, must be labelled across the EU and EEA; categories 1A and 1B may not be sold to the general public, cannot be approved as pesticides and are banned from cosmetics. It says nothing about finished articles, food or medicines, which are outside its scope. <strong>Proposition 65</strong> is binding in California only and requires a warning before exposure, not a ban; it is enforced through litigation. <strong>EMA</strong> decisions bind marketing authorisations across the EU: the medicine stays available, under a pregnancy prevention programme. <strong>WHO</strong> guidance binds no one. Our <strong>bibliography</strong> reports evidence, not law.</p>

    {opener("02", "The register", f"{len(TERA.get('entries', []))} substances and products.")}
    {teratogens_html()}
    {REGISTER_FOOT}
  </div>
</section>
""",
}



def conditions_ld():
    items = []
    for name, desc, code, orpha_name, *_ in CONDITIONS:
        item = {"@type": "MedicalCondition", "name": name, "description": desc[0].upper() + desc[1:]}
        if code:
            item["alternateName"] = orpha_name
            item["code"] = {"@type": "MedicalCode", "code": f"ORPHA:{code}", "codingSystem": "Orphanet"}
            item["sameAs"] = ORPHA_URL.format(code)
        items.append(item)
    return {"@context": "https://schema.org", "@graph": items}


def dataset_ld(name, desc, path, file, keywords, size):
    return {"@context": "https://schema.org", "@type": "Dataset", "name": name, "description": desc, "url": SITE + path,
            "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True, "inLanguage": "en", "keywords": keywords,
            # Google's Dataset guidelines accept only Person or Organization here, and flag a subtype
            # such as NGO as an invalid object type (Search Console, September 2026)
            "creator": {"@type": "Organization", "name": BRAND, "url": SITE + "/"}, "variableMeasured": size,
            "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": SITE + "/data/" + file}]}




def condition_omt_html(name):
    """The OMT line for a condition card."""
    row = OMT.get(name) or {}
    group = row.get("group")
    if not group:
        if row.get("confidence"):
            return f'<p class="cond-omt">OMT <span class="omt-na">upper limb only, so not classified here</span></p>'
        return ""
    bits = [group]
    if row.get("part"):
        bits.append(row["part"])
    if row.get("axis"):
        bits.append(row["axis"] + " axis")
    title = row.get("diagnosis") or ""
    if row.get("note"):
        title = (title + ". " + row["note"]).strip(". ")
    label = " · ".join(bits)
    return (f'<p class="cond-omt">OMT <span title="{title}">{label}</span>'
            f'<span class="omt-prov" title="{row.get("confidence", "")}">provisional</span></p>')


def condition_icd_html(name):
    """The ICD-10 line for a condition card, with one marker for where the codes come from.

    No marker means Orphanet maps the condition to that code exactly. "broader" means Orphanet
    maps it as narrower than the code (NTBT), so the code covers more than this condition: Q87.2
    alone covers four of the conditions here. "narrower" is the opposite relation (BTNT), where the
    condition covers more than the code does, as for the numbered syndactyly types, each of which
    spans two ICD-10 codes. "classification" means Orphanet maps nothing and the code is read from
    the classification itself, or from the CDC surveillance manual.
    """
    row = ICD.get(name) or {}
    codes = row.get("icd10") or []
    if not codes:
        note = row.get("icd10_note")
        return f'<p class="cond-icd">{note}</p>' if note else ""
    rels = [str(e.get("relation", "")) for e in codes]
    if any(r.startswith("classification") for r in rels):
        src = next((e.get("source", "") for e in codes if e.get("source")), "")
        mark = f'<span class="icd-rel" title="{src}">classification</span>'
    elif all(r.startswith("E ") for r in rels):
        mark = ""
    elif all(r.startswith(("BTNT", "E ")) for r in rels):
        mark = ('<span class="icd-rel" title="Orphanet maps this condition as broader than the ICD-10 code, '
                'so the condition covers more than the code does">narrower</span>')
    else:
        mark = ('<span class="icd-rel" title="Orphanet maps this condition as narrower than the ICD-10 '
                'code, so the code covers more than this condition alone">broader</span>')
    shown = " ".join(f'<code>{e["code"]}</code>' for e in codes)
    line = f'ICD-10 {shown}{mark}'
    i11 = row.get("icd11") or []
    if i11 and mark and all(str(e.get("relation", "")).startswith("E ") for e in i11):
        c11 = " ".join(f'<code>{e["code"]}</code>' for e in i11)
        line += (f'<span class="icd-11"> · ICD-11 {c11}'
                 f'<span class="icd-rel" title="ICD-11 names this condition exactly, where ICD-10 has only a broader code">exact</span></span>')
    return f'<p class="cond-icd">{line}</p>'


def _orpha_link(code, text=None):
    n = HIER["nodes"].get(str(code)) or {}
    return (f'<a href="{ORPHA_URL.format(code)}" target="_blank" rel="noopener external">'
            f'{text or n.get("term") or "ORPHA:" + str(code)}</a>')


def _icd_codes_html(node):
    """A node's ICD-10 codes; one Orphanet attributes rather than maps exactly is marked."""
    out = []
    for e in node.get("icd10") or []:
        exact = str(e.get("relation", "")).startswith("E")
        out.append(f'<code{"" if exact else " class=icd-approx title=\"Orphanet attributes this code to the entity rather than mapping the two exactly\""}>{e["code"]}</code>')
    return " ".join(out)


def _slug_name(name):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def _key_word(term):
    """The first six letters of a term, ignoring case and punctuation: enough to tell a spelling
    variant of the same name from a genuinely different one."""
    return re.sub(r"[^a-z]", "", term.lower())[:6]


def condition_hierarchy_html(code):
    """Where the code sits in Orphanet's tree, from tools/orphanet-hierarchy.json.

    A group code lists every entity it covers, in Orphanet's order, with each one's ICD-10 code and
    a link to its own card when this page describes it. A disorder names the group Orphanet files it
    under, and the card on this page that group sits within, if any. A code Orphanet has withdrawn
    says so, because the alternative is a card quietly pointing at a concept that no longer exists.
    """
    if not code:
        return ""
    code = str(code); nodes = HIER["nodes"]; rel = HIER["conditions"].get(code) or {}
    n = nodes.get(code) or {}
    ours = {str(c[2]): c[0] for c in CONDITIONS if c[2]}
    if n.get("status") != "ok":
        # Orphanet keeps a page for an excluded entity but files it in no classification.
        return (f'<p class="cond-orpha cond-orpha-warn">Orphanet has withdrawn {_orpha_link(code, "ORPHA:" + code)} '
                f'from its classifications; its page names the entity that replaced it.</p>')
    if not n:
        return ""
    if n.get("level") == "Group of disorders":
        desc = rel.get("descendants") or []
        leaves = [d for d in desc if (nodes.get(d) or {}).get("level") != "Group of disorders"]
        here = [d for d in desc if d in ours]
        def item(c):
            m = nodes.get(c) or {}
            txt = _orpha_link(c)
            # Orphanet's term is not always the name a family or a surgeon uses, and this list is now
            # the only place the form appears, so one familiar name travels with it. A spelling
            # variant of the same term teaches nobody anything, and nor does a bare acronym, so a
            # synonym is shown only when it reads as a different name.
            syn = next((x for x in (m.get("synonyms") or [])
                        if _key_word(x) != _key_word(m.get("term") or "")
                        and not x.isupper() and len(x) > 5), None)
            if syn:
                txt += f' <span class="orpha-syn">{syn.lower()}</span>'
            txt += f' <span class="orpha-code">ORPHA:{c}</span>'
            if m.get("icd10"): txt += " " + _icd_codes_html(m)
            if c in ours: txt += f' <a class="on-page" href="#cond-{c}">on this page</a>'
            kids = [k for k in m.get("children") or [] if k in nodes]
            if kids and m.get("level") == "Group of disorders":
                txt += "<ul>" + "".join(f"<li>{item(k)}</li>" for k in kids) + "</ul>"
            return txt
        top = [c for c in n.get("children") or [] if c in nodes]
        summary = (f'An Orphanet group rather than one disease. It covers <strong>{len(leaves)} disorders</strong>'
                   + (f', and {spell(len(here))} card{"s" if len(here) > 1 else ""} on this page fall{"" if len(here) > 1 else "s"} within it' if here else '') + '.')
        return (f'<details class="cond-tree"><summary class="cond-orpha">{summary}</summary>'
                f'<ul>{"".join(f"<li>{item(c)}</li>" for c in top)}</ul>'
                f'<p class="fine">Orphanet\'s classification, read {HIER.get("fetched", "")}. A greyed ICD-10 code is one Orphanet attributes rather than maps exactly.</p></details>')
    parents = [p for p in rel.get("parents") or [] if p in nodes]
    if not parents:
        return ""
    def limbish(p):
        t = (nodes[p].get("term") or "").lower()
        return any(w in t for w in ("limb", "melia", "reduction", "dactyly", "hyperphalangy"))
    order = {p: i for i, p in enumerate(parents)}   # a limb-related group first, Orphanet's order otherwise
    parents.sort(key=lambda p: (not limbish(p), order[p]))
    first, rest = parents[0], parents[1:]
    txt = f'Orphanet files it under {_orpha_link(first)}'
    # the card on this page that the group itself sits within, when there is one
    up = [g for g in (nodes[first].get("parents") or []) if g in ours and g != code]
    if first in ours and first != code:
        txt += f' (<a class="on-page" href="#cond-{first}">on this page</a>)'
    elif up:
        txt += f', within {ours[up[0]]} (<a class="on-page" href="#cond-{up[0]}">on this page</a>)'
    if rest:
        others = "; ".join(nodes[p].get("term") or p for p in rest)
        txt += f' <span class="orpha-more" title="{others}">and {spell(len(rest))} other group{"s" if len(rest) > 1 else ""}</span>'
    return f'<p class="cond-orpha">{txt}.</p>'


def _icd_rows(name):
    """One row per ICD edition for the card's code block: the codes, and what Orphanet says the
    mapping is. The relation is the load-bearing part, so it is stated on every row rather than
    only on the ones that need a caveat: an epidemiologist reading the card should see at a glance
    which of these codes are identities and which are approximations."""
    row = ICD.get(name) or {}
    out = []
    for edition, key in (("ICD-10", "icd10"), ("ICD-11", "icd11")):
        codes = row.get(key) or []
        if not codes:
            continue
        rels = [str(e.get("relation", "")) for e in codes]
        if any(r.startswith("classification") for r in rels):
            rel = "from the classification"
            why = next((e.get("source", "") for e in codes if e.get("source")), "Orphanet maps no code; this one is read from the classification itself")
        elif all(r.startswith("E ") for r in rels):
            rel, why = "exact", "Orphanet maps this condition and this code to each other exactly"
        elif all(r.startswith(("BTNT", "E ")) for r in rels):
            rel, why = "narrower", "Orphanet maps this condition as broader than the code, so the condition covers more than the code does"
        else:
            rel, why = "broader", "Orphanet maps this condition as narrower than the code, so the code covers more than this condition alone"
        out.append((edition, " ".join(f'<code>{e["code"]}</code>' for e in codes), rel, why))
    if not out and row.get("icd10_note"):
        out.append(("ICD-10", f'<span class="cc-none">{row["icd10_note"]}</span>', "", ""))
    return out


def _omt_row(name):
    """The Oberg-Manske-Tonkin position, or the reason there is none."""
    row = OMT.get(name) or {}
    if not row.get("group"):
        return (("OMT", '<span class="cc-none">upper limb only, so not classified here</span>', "", row["confidence"])
                if row.get("confidence") else None)
    bits = [row["group"]] + ([row["part"]] if row.get("part") else []) + ([row["axis"] + " axis"] if row.get("axis") else [])
    why = row.get("diagnosis") or ""
    if row.get("note"):
        why = (why + ". " + row["note"]).strip(". ")
    return ("OMT", f'<span title="{why}">{" &middot; ".join(bits)}</span>', "provisional", row.get("confidence", ""))


def condition_codes_html(name, code, orpha_name):
    """The card's code block: Orphanet, ICD-10, ICD-11 and OMT side by side, each with its relation.

    A condition card has two readers. A family needs the name and the sentence above this block and
    nothing else. Someone building a registry needs exactly this: the four vocabularies that have to
    be reconciled before two countries can add their figures together, and how good each mapping is.
    Putting them in one labelled table rather than four grey sentences serves both, because the one
    reader can skip a block and the other can scan it.
    """
    rows = []
    if code:
        node = HIER["nodes"].get(str(code)) or {}
        level = "group" if node.get("level") == "Group of disorders" else "disorder"
        val = (f'<a href="{ORPHA_URL.format(code)}" target="_blank" rel="noopener external" '
               f'title="{orpha_name} &mdash; Orphanet">ORPHA:{code} &#8599;</a>')
        rows.append(("Orphanet", val, level, f"Orphanet holds this as a {node.get('level', 'disorder').lower()}"))
    elif name == "Symbrachydactyly":
        rows.append(("Orphanet", f'<a href="{ORPHA_URL.format(1570)}" target="_blank" rel="noopener external">ORPHA:1570 &#8599;</a>',
                     "hands and feet only", "Orphanet has no entity for symbrachydactyly as such: 1570 is the rarer form affecting hands and feet together"))
    else:
        rows.append(("Orphanet", '<span class="cc-none">no code: an umbrella term</span>', "", ""))
    rows += _icd_rows(name)
    omt = _omt_row(name)
    if omt:
        rows.append(omt)
    cells = ""
    for label, value, rel, why in rows:
        badge = f'<span class="cc-rel" title="{html.escape(why, quote=True)}">{rel}</span>' if rel else ""
        cells += f"<dt>{label}</dt><dd>{value}{badge}</dd>"
    return f'<dl class="cond-codes">{cells}</dl>'


def condition_search_text(name, desc, ref_code, orpha_name):
    # What the search box at the top of the page matches on. A reader arrives with a name, a
    # synonym, an ORPHAcode or an ICD code from a letter, and any of them should find the card.
    # One function, because the registry matches on the same text through /data/conditions.json.
    _icd = ICD.get(name) or {}
    _node = HIER["nodes"].get(str(ref_code)) or {}
    # The forms Orphanet files under this code no longer have cards of their own, so their names,
    # synonyms and codes are matched here: a reader who types "acheiria" or "Haas" must still land
    # on the card that documents it rather than on nothing.
    _kids = SUBCONDITION_WORDS.get(str(ref_code), "")
    return " ".join(filter(None, [
        name, desc, orpha_name or "", _node.get("term") or "",
        " ".join(_node.get("synonyms") or []), _kids,
        f"ORPHA:{ref_code} {ref_code}" if ref_code else "",
        " ".join(e["code"] for e in (_icd.get("icd10") or [])),
        " ".join(e["code"] for e in (_icd.get("icd11") or [])),
        (OMT.get(name) or {}).get("diagnosis") or "",
    ])).lower().replace('"', "")


def condition_card(name, desc, code, orpha_name, limbs, ctype, other, genetic):
    # the register's filters now travel in the address, so a card can point at its own slice of it
    # Deliberately broad. A code is assigned from a paper's title and its abstract, so this
    # counts the literature that touches a condition rather than the studies devoted to it:
    # one paper on symbrachydactyly carries five codes, and ORPHA:498461 carries 50 references
    # of which about a dozen name it in the title. Loïc chose the broad reading on 21 September
    # 2026, having been shown both figures. Do not narrow it to title matches as a bug fix.
    # A card with no code of its own still has literature and coverage under the code the name table
    # gives its name: symbrachydactyly, under ORPHA:1570. Without this the thirteen papers tagged
    # 1570 were reachable from the bibliography's filter and from nowhere else.
    ref_code = code or next((int(k) for k, v in REG_CODE_NAMES.items() if v == name), None)
    n_refs = sum(1 for e in BIB.get("entries", []) if str(ref_code) in e.get("codes", []))
    refs = (f'<a class="cond-refs" href="/knowledge/bibliography/?condition={ref_code}">{n_refs} references &rarr;</a>'
            if ref_code and n_refs >= 3 else "")
    anchor = f"cond-{ref_code}" if ref_code else "cond-" + _slug_name(name)
    # Three layers, in the order the two readers need them: what it is, how it is coded, what we hold
    # on it. The plain sentence stays at the top and in the page's own voice; the codes sit in a block
    # of their own that a family can skip in one glance; the footer is the reach of our own registers.
    chips = "".join(f'<span class="cond-chip">{FACET_SHORT[v]}</span>'
                    for v in limbs.split() + ctype.split() if v in FACET_SHORT)
    haystack = condition_search_text(name, desc, ref_code, orpha_name)
    foot = condition_registries_html(ref_code) + refs
    return (f'<div class="card cond" id="{anchor}" data-limbs="{limbs}" data-type="{ctype}" data-other="{other}" data-genetic="{genetic}" data-search="{haystack}">'
            f'<h3 class="h4">{name}</h3>'
            f'<p class="cond-desc">{desc}</p>'
            f'<p class="cond-chips">{chips}</p>'
            f'{condition_rate_html(name)}'
            f'{condition_codes_html(name, code, orpha_name)}'
            f'{condition_hierarchy_html(ref_code)}'
            f'<div class="cond-foot">{foot}</div></div>')


# ───────────── Annex: prevalence of the listed conditions (Orphanet + literature) ─────────────
# Orphanet rows come from tools/condition-prevalence.json (Orphadata API, CC BY 4.0), the same file
# the card order rests on, so the table and the cards cannot disagree. Every row Orphanet publishes
# is shown, with the study it cites, because the spread between territories is itself a finding.
# Literature rows were each verified against the primary abstract (authors + figures) on 2026-09-04;
# the two polydactyly studies (Castilla 1997, Ortiz-Cruz 2019) on 2026-09-22.
PREV_FILE = json.loads(PREV_PATH.read_text(encoding="utf-8")) if PREV_PATH.exists() else {}
PREV_SOURCES = PREV_FILE.get("sources", {})


def poisson_ci(cases, births, per=10000):
    """A 95% confidence interval for a count of cases in a number of births, per 10,000 or 100,000.

    Byar's approximation to the exact Poisson limits, which is what registries use for prevalence
    (EUROCAT Guide 1.5, chapter 4.1, cites the Poisson distribution). It is arithmetic on figures
    already verified in the sentence that carries it, not a new source."""
    z = 1.96
    lo = cases * (1 - 1 / (9 * cases) - z / (3 * cases ** 0.5)) ** 3
    hi = (cases + 1) * (1 - 1 / (9 * (cases + 1)) + z / (3 * (cases + 1) ** 0.5)) ** 3
    f = lambda v: f"{v * per / births:.2f}".rstrip("0").rstrip(".")
    return f"{f(cases)} per {per:,} (95% CI {f(lo)}\u2013{f(hi)})"


def orphanet_source(src):
    """The study behind an Orphanet row, from the identifiers Orphanet publishes with it."""
    if not src:
        return ""
    parts = []
    for tok in src.split("_"):
        m = re.match(r"(\d{5,9})\[PMID\]", tok)
        if m and m.group(1) in PREV_SOURCES:
            x = PREV_SOURCES[m.group(1)]
            parts.append(f'<a href="https://pubmed.ncbi.nlm.nih.gov/{m.group(1)}/" target="_blank" rel="noopener external">'
                         f'{x["first_author"].split()[0]} {x["year"]}</a>')
        elif tok.startswith("ISBN:"):
            parts.append("a book, ISBN " + tok[5:].split("[")[0])
        elif tok.upper().startswith("EUROCAT"):
            parts.append("EUROCAT")
        elif tok.upper().startswith("ORPHANET"):
            parts.append("Orphanet\u2019s own estimate")
        elif tok.upper().startswith("[EXPERT]"):
            parts.append("expert opinion")
    return ", ".join(dict.fromkeys(parts))

SOURCES = [
    ("Bermejo-Sánchez E, Cuevas L, Amar E, et al. Amelia: a multi-center descriptive epidemiologic study in a large dataset from the International Clearinghouse for Birth Defects Surveillance and Research, and overview of the literature. <em>Am J Med Genet C Semin Med Genet</em>. 2011;157C(4):288-304.", "https://doi.org/10.1002/ajmg.c.30319"),
    ("Pakkasjärvi N, Syvänen J, Wiro M, Koskimies-Virta E. Amelia and phocomelia in Finland: characteristics and prevalences in a nationwide population-based study. <em>Birth Defects Res</em>. 2022;114(20):1427-1433.", "https://doi.org/10.1002/bdr2.2123"),
    ("Vasluian E, van der Sluis CK, van Essen AJ, et al. Birth prevalence for congenital limb defects in the northern Netherlands: a 30-year population-based study. <em>BMC Musculoskelet Disord</em>. 2013;14:323.", "https://doi.org/10.1186/1471-2474-14-323"),
    ("Chen ZY, Li WY, Xu WL, et al. The changing epidemiology of syndactyly in Chinese newborns: a nationwide surveillance-based study. <em>BMC Pregnancy Childbirth</em>. 2023;23:334.", "https://doi.org/10.1186/s12884-023-05660-z"),
    ("Temtamy SA, Aglan MS. Brachydactyly. <em>Orphanet J Rare Dis</em>. 2008;3:15.", "https://doi.org/10.1186/1750-1172-3-15"),
    ("Koskimies E, Lindfors N, Gissler M, Peltonen J, Nietosvaara Y. Congenital upper limb deficiencies and associated malformations in Finland: a population-based study. <em>J Hand Surg Am</em>. 2011;36(6):1058-1065.", "https://doi.org/10.1016/j.jhsa.2011.03.015"),
    ("Pakkasjärvi N, Koskimies E, Ritvanen A, Nietosvaara Y, Mäkitie O. Characteristics and associated anomalies in radial ray deficiencies in Finland: a population-based study. <em>Am J Med Genet A</em>. 2013;161A(2):261-267.", "https://doi.org/10.1002/ajmg.a.35707"),
    ("Syvänen J, Nietosvaara Y, Ritvanen A, Koskimies E, Kauko T, Helenius I. High risk for major nonlimb anomalies associated with lower-limb deficiency: a population-based study. <em>J Bone Joint Surg Am</em>. 2014;96(22):1898-1904.", "https://doi.org/10.2106/JBJS.N.00155"),
    ("Klungsøyr K, Nordtveit TI, Kaastad TS, et al. Epidemiology of limb reduction defects as registered in the Medical Birth Registry of Norway, 1970-2016: population based study. <em>PLoS One</em>. 2019;14(7):e0219930. Cites the EUROCAT figure for Europe 2003-2012 (Morris et al., 2018).", "https://doi.org/10.1371/journal.pone.0219930"),
    ("Shin YH, Baek GH, Kim YJ, Kim MJ, Kim JK. Epidemiology of congenital upper limb anomalies in Korea: a nationwide population-based study. <em>PLoS One</em>. 2021;16(3):e0248105.", "https://doi.org/10.1371/journal.pone.0248105"),
    ("Orphanet. Orphadata, epidemiological data (product 9), release of 23 June 2026. Licence CC BY 4.0.", "https://www.orphadata.com/epidemiology/"),
    ("Gordillo M, Vega H, Jabs EW. ESCO2 Spectrum Disorder. In: GeneReviews. University of Washington, Seattle.", "https://www.ncbi.nlm.nih.gov/books/NBK1153/"),
    ("Gnansia E, Michon L, Amar E, Estève J. Evidence for a cluster of rare birth defects in the Ain department (France). <em>Birth Defects Res</em>. 2021;113(13):1015-1025. States the general prevalence of unilateral isolated transverse upper-limb reduction as one case in 10,000 births.", "https://doi.org/10.1002/bdr2.1876"),
    ("EUROCAT. <em>EUROCAT Guide 1.5: Instruction for the registration of congenital anomalies</em>. European Commission, Joint Research Centre. Chapter 3.2 (minor anomalies for exclusion), chapter 3.3 (subgroups: limb reduction Q71-Q73, polydactyly Q69, syndactyly Q70) and chapter 4.1 (calculation of prevalence and confidence intervals).", "https://eu-rd-platform.jrc.ec.europa.eu/system/files/public/eurocat/EUROCAT_Guide_1.5.pdf"),
    ("Castilla EE, da Graça Dutra M, Lugarinho da Fonseca R, Paz JE. Hand and foot postaxial polydactyly: two different traits. <em>Am J Med Genet</em>. 1997;73(1):48-54.", "https://pubmed.ncbi.nlm.nih.gov/9375922/"),
    ("Ortiz-Cruz G, Luna-Muñoz L, Arteaga-Vázquez J, Mutchinick OM. Isolated postaxial polydactyly: epidemiologic characteristics from a multicenter birth defects study. <em>Am J Med Genet A</em>. 2019;179(7):1240-1247.", "https://doi.org/10.1002/ajmg.a.61193"),
]

def cite(*nums):
    return " ".join(f'<sup><a href="#src-{n}">{n}</a></sup>' for n in nums)

# Literature column, keyed by the card name used in CONDITIONS
LITERATURE = {
    "Amelia": f"326 cases in 23.1 million births, 20 registries, 1968-2006: {poisson_ci(326, 23.1e6, 100000)}" + cite(1) + "; Finland: 2.43 per 100,000 births, 0.63 per 100,000 live births (1993-2008)" + cite(2),
    "Amelia of the upper limb": "Upper limbs in 54% of single-limb amelia cases" + cite(1) + "; 26% of amelia cases in Finland" + cite(2),
    "Amelia of the lower limb": "Lower limbs in 70% of amelia cases in Finland" + cite(2),
    "Terminal transverse limb defect": "About one case in 10,000 births for the unilateral isolated upper-limb form" + cite(13) + "; this is the commonest form of limb reduction and the defect behind the three French clusters",
    "Amniotic band syndrome": f"Upper-limb defects from constriction bands: 51 in 753,342 births, {poisson_ci(51, 753342)} (Finland)" + cite(6),
    "Brachydactyly": "No population figure; Temtamy and Aglan describe types A3 and D as the common isolated forms and the others as infrequent" + cite(5),
    "Ectrodactyly (SHFM)": f"Central ray deficiency: 41 in 753,342 births, {poisson_ci(41, 753342)} (Finland), consistent with the European and North American rows Orphanet lists and a third of the Chinese one" + cite(6),
    "Fibular hemimelia": "All lower-limb deficiencies: 2.8 per 10,000 births (Finland, 266 cases)" + cite(8),
    "Phocomelia": "All forms of phocomelia: 0.74 per 100,000 births (Finland, 7 cases, 1993-2008)" + cite(2),
    "Polydactyly": "8.4 per 10,000 births (northern Netherlands, 1981-2010)" + cite(3) + "; the most common upper-limb anomaly in Korea, where all upper-limb anomalies total 23.5 per 10,000 live births" + cite(10),
    "Radial aplasia": "Radial ray deficiency, all forms: 1.83 per 10,000 births, 13% of them isolated (Finland)" + cite(7) + "; the isolated share matches Orphanet's figure",
    "Roberts syndrome": "Prevalence unknown; part of the ESCO2 spectrum" + cite(12),
    "Symbrachydactyly": f"Undergrowth category, mainly symbrachydactyly: 91 in 753,342 births, {poisson_ci(91, 753342)} (Finland)" + cite(6),
    "Syndactyly": "4.7 per 10,000 births (northern Netherlands, 1981-2010; non-syndromic cases fell from 5.2 to 1.1 between 1992 and 2010)" + cite(3) + "; 5.63 per 10,000 (China, 2007-2019, 13,611 cases)" + cite(4),
    "Tibial hemimelia": "All lower-limb deficiencies: 2.8 per 10,000 births (Finland)" + cite(8),
    "Ulnar hemimelia": f"Ulnar ray deficiency: 33 in 753,342 births, {poisson_ci(33, 753342, 100000)} (Finland)" + cite(6) + ", above Orphanet's not-yet-validated class",
    "Postaxial polydactyly": f"Isolated, hand or foot: 2,271 cases in 1,582,289 births in the ECLAMC registries of South America, 1967-1993, {poisson_ci(2271, 1582289)}; hand 11.0, foot 2.2, both 1.2 per 10,000, with hand polydactyly associated with African ancestry and foot polydactyly with Amerindian ancestry" + cite(15) + f"; Mexico: 697 in 1,178,993 live births, {poisson_ci(697, 1178993)}, and a worldwide range quoted from 6.08 per 10,000 in Argentina to 225 in Nigeria" + cite(16),
    "Postaxial polydactyly type A": "25.5% of isolated postaxial polydactyly in Mexico, the share Orphanet's figure of 15.7 per 100,000 rests on; the reverse proportion, 75% type A, in the Mayan population" + cite(16),
    "Postaxial polydactyly type B": "74.5% of isolated postaxial polydactyly in Mexico, the share Orphanet's figure of 43.5 per 100,000 rests on; a decreasing time trend over the study period" + cite(16),
}
TOTAL_ROW = ("All limb reduction defects", "Not an Orphanet entity",
             "4.5 per 10,000 births in Europe, 2003-2012 (EUROCAT)" + cite(9) + "; Norway 4.4 (1970-2016)" + cite(9) +
             "; northern Netherlands 6.9 (1981-2010)" + cite(3) + "; upper-limb deficiencies 5.6 per 10,000 births in Finland" + cite(6))

def orphanet_cell(code, name=None):
    """Every birth prevalence Orphanet publishes for the code, each with its territory and the study
    Orphanet cites; then a point prevalence or a case count where that is all Orphanet has."""
    if name == "Symbrachydactyly":
        return (f'Not an Orphanet entity as such; <a href="{ORPHA_URL.format(1570)}" target="_blank" rel="noopener external">ORPHA:1570</a> '
                'covers only the rare form affecting hands and feet (2 cases described)')
    if code is None:
        return "No ORPHAcode (umbrella term)"
    c = ORPHA_PREV.get(name) or {}
    births = [r for r in c.get("birth_rows", []) if r.get("class") and r["class"] != "Unknown"]
    if births:
        parts = []
        for r in births:
            src = orphanet_source(r.get("source"))
            val = f"<strong>{r['per_100000']:g}</strong>" if r.get("per_100000") else f"class {html.escape(r['class'])}"
            flag = "" if r.get("status") == "Validated" else ", not yet validated"
            parts.append(f"{val} ({r.get('geo', '')}{'; ' + src if src else ''}{flag})")
        unit = "per 100,000 births" if any(r.get("per_100000") for r in births) else ""
        return f"{unit}: " + "; ".join(parts) if unit else "; ".join(parts)
    points = [r for r in c.get("point_rows", []) if r.get("class") and r["class"] != "Unknown"]
    if points:
        r = points[0]
        src = orphanet_source(r.get("source"))
        val = f"{r['per_100000']:g} per 100,000" if r.get("per_100000") else f"class {html.escape(r['class'])}"
        tail = f"; about {c['cases']} {c['cases_unit']} described" if c.get("cases") else ""
        flag = "" if r.get("status") == "Validated" else ", not yet validated"
        return f"Point prevalence only, not a birth prevalence: {val} ({r.get('geo', '')}{'; ' + src if src else ''}{flag}){tail}"
    if c.get("cases"):
        return f"No prevalence; about {c['cases']} {c['cases_unit']} described"
    if (ICD.get(name) or {}).get("group") == "Group of disorders":
        return ('Orphanet holds this as a <strong>group of disorders</strong> rather than a single disease, and '
                'publishes no prevalence against a group')
    return "No prevalence published"


BASIS_LABEL = {"measured": "Measured", "pooled": "Pooled from several registries",
               "reported": "Reported, without a population study behind it",
               "derived": "Derived, not measured", "none": "Not measured"}
DOT_BASIS = {DOT_ALIAS.get(lab, lab): (basis, note) for lab, r, src, basis, note in DOT_RATES}


def site_figure_cell(name):
    """The one figure the rest of the site uses for the condition: the card order, the map's dots and
    the expected-births table all read CONDITION_RATE, and this column shows the reader which row of
    the two columns to its right that figure is, and how firm it is."""
    hit = CONDITION_RATE.get(name)
    if not hit:
        return '<span class="cc-none">No figure exists, so no expected number can be computed</span>'
    rate, src = hit
    basis, note = DOT_BASIS.get(name, ("orphanet", ""))
    label = BASIS_LABEL.get(basis, "Orphanet\u2019s headline row")
    if basis == "orphanet":
        src = src.replace("Orphanet, ", "", 1)
    return (f"<strong>{_rate_txt(rate)}</strong>, about 1 in {_one_in(rate)}<br>"
            f'<span class="cc-rel" title="{html.escape(note) if note else label}">{label}</span> <small>{src}</small>')


def prevalence_html():
    rows = [f'<tr><th scope="row">{TOTAL_ROW[0]}</th><td><strong>{_rate_txt(DOT_RATES[0][1])}</strong>, about 1 in {_one_in(DOT_RATES[0][1])}<br>'
            f'<span class="cc-rel">{BASIS_LABEL["pooled"]}</span> <small>{DOT_RATES[0][2]}</small></td><td>{TOTAL_ROW[1]}</td><td>{TOTAL_ROW[2]}</td></tr>']
    unrated = [c for c in CONDITIONS_BY_RATE if c[0] not in CONDITION_RATE]
    for i, (name, desc, code, orpha_name, *_) in enumerate(CONDITIONS_BY_RATE):
        if unrated and name == unrated[0][0]:
            rows.append(f'<tr class="annex-sep"><th scope="row" colspan="4">The {spell(len(unrated))} conditions below have no '
                        f'published birth prevalence from any source; they run in alphabetical order, and each blank row marks a gap in what has been counted.</th></tr>')
        o = orphanet_cell(code, name)
        if code:
            o += f' <a href="{ORPHA_URL.format(code)}" target="_blank" rel="noopener external" title="{orpha_name} on Orphanet">ORPHA:{code}</a>' + cite(11)
        lit = LITERATURE.get(name, "No population figure found")
        rows.append(f'<tr><th scope="row">{name}</th><td>{site_figure_cell(name)}</td><td>{o}</td><td>{lit}</td></tr>')
    sources = "".join(f'<li id="src-{i}">{t} <a href="{u}" target="_blank" rel="noopener external">{u.replace("https://", "")}</a></li>' for i, (t, u) in enumerate(SOURCES, 1))
    # how far the same condition differs from one territory to another, read off Orphanet's rows
    spreads = []
    for name, *_ in CONDITIONS:
        vals = [r["per_100000"] for r in (ORPHA_PREV.get(name) or {}).get("birth_rows", []) if r.get("per_100000")]
        if len(vals) > 1 and min(vals) > 0:
            spreads.append((max(vals) / min(vals), name, min(vals), max(vals)))
    spreads.sort(reverse=True)
    spread_txt = "; ".join(f"{n}, {lo:g} to {hi:g} per 100,000" for _, n, lo, hi in spreads)
    orphanet_n = sum(1 for c in CONDITIONS if (ORPHA_PREV.get(c[0]) or {}).get("birth_prevalence"))
    return f"""
    <div class="tick"></div>
    <p class="eyebrow">Part 1 · Birth prevalence</p>
    <h2 class="h2">How common is each condition at birth?</h2>
    <p>Three columns, three kinds of figure. The first is the <strong>one figure this site uses</strong> for the condition,
    the same on the map, in the order of the condition cards and in the expected numbers below, with a label saying how firm it
    is: measured in a defined population, pooled from several registries, reported in the literature without a population
    study behind it, or derived by arithmetic from another figure. The second reproduces <strong>every birth prevalence Orphanet
    publishes</strong> for the ORPHAcode, one entry per territory, each with the study Orphanet cites, as published and without our
    re-reading those studies. The third gives the <strong>population studies</strong> we have read ourselves, with the case count, the
    number of births and a 95% confidence interval wherever the paper states both, so that a rate resting on seven cases can be told
    from one resting on two thousand. Every figure in that column was checked against its original publication in September 2026.</p>
    <p>The rows run in the order of the condition cards, from the commonest to the rarest of the {RATED_N} conditions with a figure,
    then the {len(CONDITIONS) - RATED_N} without one. Orphanet publishes a birth prevalence for {orphanet_n} of the {len(CONDITIONS)};
    our own table covers {sum(1 for c in CONDITIONS if c[0] in DOT_BASIS and DOT_BASIS[c[0]][0] != "none")}. <a href="/data/condition-prevalence.json">Download Orphanet&rsquo;s
    rows with their sources (JSON, CC BY 4.0)</a>.</p>
    <div class="annex-wrap">
      <table class="annex prev">
        <colgroup><col style="width:17%"><col style="width:21%"><col style="width:30%"><col style="width:32%"></colgroup>
        <thead><tr><th scope="col">Condition</th><th scope="col">Figure used on this site</th><th scope="col">Orphanet, per territory</th><th scope="col">Population studies</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    <h3 class="h4" style="margin-top:var(--space-4)">How to read these figures</h3>
    <p class="annex-note"><strong>They are birth prevalences, not incidences.</strong> A registry counts the affected births in a
    defined population over a defined period and divides by all births there. EUROCAT, whose convention the European figures
    follow, counts live births, fetal deaths and terminations of pregnancy after a prenatal diagnosis in the numerator, and live
    and still births in the denominator, always per 10,000 births{cite(14)}. Orphanet states its figures per 100,000. An incidence
    would count every affected conception, and the pregnancies lost before any registry can see them are never counted, so no
    registry measures one; a prevalence at birth is the measure that exists. None of these figures says how many people live with a
    condition today.</p>
    <p class="annex-note"><strong>The named conditions do not add up</strong> to the total for limb reduction defects. EUROCAT
    counts a child once in each subgroup they fall in, so subgroups cannot be summed{cite(14)}; most limb differences are isolated
    deficiencies without a syndrome name; and the two commonest conditions here, polydactyly and syndactyly, are separate EUROCAT
    subgroups (Q69 and Q70) outside limb reduction (Q71 to Q73), so the 4.5 per 10,000 does not contain them{cite(14)}.</p>
    <p class="annex-note"><strong>Rates differ between populations, and between registries counting the same population.</strong>
    Where Orphanet lists more than one territory for the same condition, the figures differ by up to
    {spreads[0][0]:.0f}-fold: {spread_txt}. Postaxial polydactyly of the hand is associated with African ancestry and of the foot
    with Amerindian ancestry in the South American registries{cite(15)}, and the figures quoted for it worldwide run from 6 to
    225 per 10,000 births{cite(16)}. Part of the spread is real and part is method: which anomalies a registry treats as minor and
    leaves out when they occur alone (EUROCAT excludes cutaneous syndactyly of the second and third toes, for instance{cite(14)}),
    whether terminations are counted, how far prenatal diagnosis reaches, and whether a syndromic case is counted under the limb
    defect as well. A figure travels badly from one of these settings to another, which is why the third column names the
    population each one comes from.</p>
    <p class="annex-note"><strong>Not every affected birth is a live birth.</strong> In Finland, amelia stood at 2.43 per 100,000
    births when fetal deaths and terminations were counted and at 0.63 per 100,000 live births{cite(2)}, so about
    {0.63 / 2.43:.0%} of the affected pregnancies ended in a live birth. The ratio is specific to a condition, a period and a
    country&rsquo;s prenatal screening, and it is the first thing to ask of any figure before turning it into children to plan for.
    None of this is medical advice.</p>
    <h3 class="h4" style="margin-top:var(--space-4)">Sources of the prevalence figures</h3>
    <ol class="sources">{sources}</ol>
"""

# The condition list as data, for the DysNet registry's condition question, which reads it live
# (owner, 2026-09-24). Built from exactly what the cards are built from, so the page and the
# registry cannot disagree: the same names, codes, forms and search text. Orphanet's names, codes
# and ICD relations are Orphadata's (CC BY 4.0); the OMT placements are ours and provisional.
def _conditions_payload():
    def node_codes(n, key):
        return [{"code": e["code"], "relation": e.get("relation", "")} for e in (n.get(key) or [])]
    out = []
    for name, desc, code, orpha_name, limbs, ctype, other, genetic in CONDITIONS:
        ref_code = code or next((int(k) for k, v in REG_CODE_NAMES.items() if v == name), None)
        node = HIER["nodes"].get(str(code)) or {} if code else {}
        icd = ICD.get(name) or {}
        omt = OMT.get(name) or {}
        subs = []
        for sub_code, term in SUBCONDITIONS.get(str(code), []) if code else []:
            m = HIER["nodes"].get(sub_code) or {}
            subs.append({"orphaCode": int(sub_code), "term": term, "level": m.get("level"),
                         "synonyms": m.get("synonyms") or [], "icd10": node_codes(m, "icd10"), "icd11": node_codes(m, "icd11")})
        out.append({
            "name": name, "description": desc, "orphaCode": code, "orphaLabel": orpha_name,
            "orphaLevel": node.get("level"), "limbs": limbs.split(), "type": ctype.split(),
            "other": other.split(), "genetic": genetic.split(),
            "synonyms": node.get("synonyms") or [],
            "icd10": [{"code": e["code"], "relation": e.get("relation", "")} for e in (icd.get("icd10") or [])],
            "icd11": [{"code": e["code"], "relation": e.get("relation", "")} for e in (icd.get("icd11") or [])],
            "omt": {k: omt.get(k) for k in ("group", "part", "axis", "diagnosis")} if omt.get("group") else None,
            "search": condition_search_text(name, desc, ref_code, orpha_name),
            "subconditions": subs,
        })
    return json.dumps({"version": 1, "page": "https://www.dysnet.org/knowledge/understanding-dysmelia/",
                       "licence": "Orphanet names, codes and ICD relations: Orphadata, CC BY 4.0. OMT placements: DysNet, provisional.",
                       "conditions": out}, ensure_ascii=False, separators=(",", ":"))


PAGES["/knowledge/understanding-dysmelia/"] = {
    "title": "Understanding dysmelia",
    "desc": "What dysmelia means, in plain language: the conditions behind the term with their ORPHAcodes, for families and clinicians who need a clear start.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/understanding-dysmelia/", "Understanding dysmelia")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Start here · For families and clinicians</p>
    <h1 class="display">Understanding dysmelia.</h1>
    <p class="lede">Dysmelia is a congenital limb difference: an arm or a leg that formed differently, incompletely or not at all
    before birth. It differs from an amputation, which comes later through injury, illness or surgery, yet the care is often much
    the same: a prosthesis where it helps, and the psychological support a child and a family need.</p>
    <details class="def-more">
    <summary>Read the two senses and their sources</summary>
    <p>The word is used in two senses, and each has an authoritative source. <strong>In the narrow sense</strong>, dysmelia is a reduction: a limb, or a part of one, is missing. Sweden&rsquo;s National Board
    of Health and Welfare, which has concentrated the specialised care of dysmelia in four university hospitals and refers every
    patient, whatever their age, to one of them for a multidisciplinary assessment, defines it as a &ldquo;<span lang="sv">medfödd
    reduktionsmissbildning av hela eller delar av övre och/eller nedre extremitet</span>&rdquo;, a congenital reduction malformation of
    all or part of an arm or a leg, and leaves out the malformations that involve no reduction.<sup><a href="#def-src-1">1</a></sup>
    It leaves out amputations after sepsis, trauma, cancer or burns too, while recognising that those patients have similar care
    needs and that the same units can be consulted for them, and it names what the care requires, from the hand surgeon and the
    orthopaedic engineer who fits a prosthesis to psychosocial support.<sup><a href="#def-src-1">1</a></sup>
    <strong>In the broad sense</strong>, it is any congenital anomaly of the limbs: the Human Phenotype Ontology, the international
    vocabulary clinicians and geneticists use to describe the features of a disease, lists dysmelia as a synonym of
    &ldquo;abnormality of limbs&rdquo;.<sup><a href="#def-src-2">2</a></sup></p>
    <p>DysNet uses the broad sense, which is why this guide also covers extra and joined fingers and toes;
    {sum(1 for c in CONDITIONS if "reduction" in c[5].split())} of the {len(CONDITIONS)} conditions below are reductions, the ones the
    narrow definition names. European registries count limb reduction defects in about {DOT_RATES[0][1] / 10:g} of every 10,000
    births, and polydactyly and syndactyly, which they count separately, in {CONDITION_RATE["Polydactyly"][0] / 10:g} and
    {CONDITION_RATE["Syndactyly"][0] / 10:g}. The guide introduces each condition in plain language, with links to Orphanet, the
    European reference database for rare diseases.</p>
    <p class="annex-note">The definition rests on two sources. <span id="def-src-1">1.</span> Socialstyrelsen,
    <a href="https://www.socialstyrelsen.se/globalassets/sharepoint-dokument/dokument-webb/ovrigt/nationell-hogspecialiserad-vard-definitionsbeslut-dysmeli.pdf" target="_blank" rel="noopener external" lang="sv">Beslut om nationell högspecialiserad vård: viss vård vid dysmeli</a>,
    9 January 2024, Dnr 17800/2022; the four units hold the permit from 1 September 2025
    (<a href="https://www.socialstyrelsen.se/kunskapsstod-och-regler/regler-och-riktlinjer/nationell-hogspecialiserad-vard/oversikt/dysmeli/" target="_blank" rel="noopener external">overview</a>); translation ours.
    <span id="def-src-2">2.</span> Human Phenotype Ontology,
    <a href="https://hpo.jax.org/browse/term/HP:0040064" target="_blank" rel="noopener external">HP:0040064, Abnormality of limbs</a>, synonym &ldquo;Dysmelia&rdquo;.</p>
    </details>

    {opener("01", "The conditions", "Which conditions does it cover?")}

    <div class="finder" id="cond-finder">
      <p class="finder-title">Find the pages that concern you</p>
      <p class="finder-sub">Search a name or a code, or answer the three questions below. This helper does not diagnose anything: only a clinician or geneticist can. It simply helps you find the right Orphanet pages to read and to bring to your consultation.</p>
      <div class="finder-search">
        <label for="cond-q">Name, synonym, ORPHAcode or ICD code</label>
        <input type="search" id="cond-q" placeholder="acheiria, Q71.3, ORPHA:498461, LB99.6&hellip;" autocomplete="off" spellcheck="false">
      </div>
      <fieldset>
        <legend>Which limbs are concerned?</legend>
        <div class="finder-chips" data-q="limbs">{facet_chips("limbs")}</div>
      </fieldset>
      <fieldset>
        <legend>What best describes the difference?</legend>
        <div class="finder-chips" data-q="type">{facet_chips("type")}</div>
      </fieldset>
      <fieldset>
        <legend>Are other parts of the body also concerned (heart, skull, organs, blood)?</legend>
        <div class="finder-chips" data-q="other">
          <button type="button" data-v="" aria-pressed="true">Not sure</button>
          <button type="button" data-v="other" aria-pressed="false">Yes, other signs too</button>
          <button type="button" data-v="limbsonly" aria-pressed="false">No, limbs only</button>
        </div>
      </fieldset>
      <fieldset>
        <legend>Is the condition of genetic origin (inherited, or caused by a gene change)?</legend>
        <div class="finder-chips" data-q="genetic">
          <button type="button" data-v="" aria-pressed="true">I don’t know</button>
          <button type="button" data-v="genetic" aria-pressed="false">Yes</button>
          <button type="button" data-v="nongenetic" aria-pressed="false">No</button>
        </div>
      </fieldset>
      <p class="finder-count" aria-live="polite"><strong id="finder-n">{len(CONDITIONS)}</strong> of {len(CONDITIONS)} conditions match · <button type="button" id="finder-reset">Reset</button></p>
    </div>

    <p class="cond-order">Ordered from the commonest to the rarest, by birth prevalence: {RATED_N} of the
    {len(CONDITIONS)} have a published figure, ours where the map draws a dot for it and Orphanet&rsquo;s for the rest.
    The last {len(CONDITIONS) - RATED_N} have none at all, and they are placed together at the end in alphabetical order.
    That is a gap in what has been counted rather than a statement that they are the rarest things here, and closing it is
    what <a href="/registry/">the registry</a> is for.</p>
    <div class="grid cols-3" id="cond-grid">
      {"".join(condition_card(*c) for c in CONDITIONS_BY_RATE)}
    </div>
    <p style="margin-top:var(--space-3)">Each card links to the condition’s page on Orphanet, the European reference database for rare diseases, through its permanent ORPHAcode; the codes were carried over from the previous DysNet site and re-verified in August 2026. Know one we have not covered, or have information to add? <a href="mailto:info@dysnet.org">Tell us</a>.</p>
    <p class="annex-note">Every card carries a block of codes, and it is there for a different reader than the sentence above it. Four vocabularies have to be reconciled before two countries can add their figures together: the <strong>ORPHAcode</strong> a rare-disease registry uses, the <strong>ICD-10</strong> code a hospital, a national registry and an insurer use, <strong>ICD-11</strong> where it exists, and <strong>Oberg-Manske-Tonkin</strong>, which is what the hand surgeons&rsquo; registries use. Each row says how good the mapping is, because a code quoted without its relation invites a reader to treat an approximation as an identity. Of the {ICD_STATS["icd10"]["rows"]} conditions Orphanet gives an ICD-10 code, only {ICD_STATS["icd10"].get("exact", 0)} are exact. The words matter. <strong>Broader</strong> means Orphanet maps the condition as narrower than the code, so the code covers more than this condition alone: {ICD10_WIDEST[0]} stands for {spell(ICD10_WIDEST[1])} of the cards on this page at once. <strong>Narrower</strong> is the reverse, where the condition covers more than the code does, {"as for " + ICD10_NARROWER[0].lower() if ICD10_NARROWER else "which happens among the forms listed inside the cards rather than among the cards themselves"}. <strong>From the classification</strong> means Orphanet maps no code, and the one shown is read from the ICD-10 classification itself, or for terminal transverse defects from the surveillance manual of the United States Centers for Disease Control. Where ICD-10 has no code at all, the card says so rather than offering an approximation.</p>
    <p class="annex-note"><strong>Oberg-Manske-Tonkin</strong> is the last row of each card&rsquo;s code block, and the vocabulary the four clinical registries of congenital upper limb difference all use, in place of the Swanson classification the IFSSH retired. It sorts a condition by the mechanism rather than the name: which axis of limb development was disturbed, and whether the whole limb or the hand alone is affected, with syndromes held in a group of their own. This mapping is <strong>ours and provisional</strong>, offered to start the interoperability work rather than to end it, and it wants a hand surgeon&rsquo;s review before anyone relies on it. It also stops where the classification stops: OMT covers the upper limb, so {spell(sum(1 for c in CONDITIONS if not (OMT.get(c[0]) or {}).get("group")))} of the cards here, all of the leg, have no place in it. That is a limit of the classification and not a gap in the mapping.</p>
    <p class="annex-note"><strong>ICD-11</strong> now sits beside ICD-10 on every card that has one, {ICD_STATS["icd11"]["rows"]} of them, because the point of the block is to show what a registry would have to reconcile rather than to flatter either edition. ICD-11 resolves real things: amniotic band syndrome and Poland syndrome share the single ICD-10 code Q79.8 and ICD-11 names each exactly, and polydactyly has no Orphanet mapping to ICD-10 at all while ICD-11 names it exactly. It is not a general improvement. The share of exact mappings rises only from {ICD_STATS["icd10"].get("exact", 0)} of {ICD_STATS["icd10"]["rows"]} under ICD-10 to {ICD_STATS["icd11"].get("exact", 0)} of {ICD_STATS["icd11"]["rows"]} under ICD-11, and in one respect ICD-11 is the coarser: its code {ICD11_WIDEST[0]} stands for {spell(ICD11_WIDEST[1])} of the conditions on this page at once.</p>

    <div id="toc-here"></div>
    {opener("02", "Not alone", "Which association knows my condition?")}
    <p>Whatever the diagnosis, a member association near you has walked this road: Reach and Steps in the United Kingdom for upper and lower limb differences, Aussiehands in Australia for children born with a hand difference, AISP in Italy and PIP UK for Poland syndrome, Svensk Dysmeliförening in Sweden for dysmelia in all its forms, Assedea in France for limb agenesis. <a href="/about/members/">Find yours</a>.</p>

    {opener("03", "Going further", "How common is it, and why did it happen?")}
    <p>Two pages carry those questions further. Each is sourced and dated, and each says where the evidence stops.</p>
    <div class="grid cols-2" style="margin-top:var(--space-3)">
      <div class="card acc-research">
        <h3 class="h3"><a href="/knowledge/epidemiology/">How common is each condition?</a></h3>
        <p>European registries recorded limb reduction defects in about 4.5 of every 10,000 births between 2003 and 2012; Norway recorded 4.4 over 1970 to 2016 and the northern Netherlands 6.9 over 1981 to 2010. The figures differ widely from one condition to the next: amelia appears at 1.41 per 100,000 births across 20 registries, while polydactyly reaches 8.4 and syndactyly 4.7 per 10,000. The page sets out Orphanet&rsquo;s prevalence class and the population studies condition by condition, with the publication each figure was checked against.</p>
        <p><a href="/knowledge/epidemiology/">See how common each condition is &rarr;</a></p>
      </div>
      <div class="card acc-research">
        <h3 class="h3"><a href="/knowledge/causes-of-dysmelia/">Why did it happen?</a></h3>
        <p>A cause is named in roughly one case in five: the China Birth Cohort Study identified one in 22.4% of 2,123 birth defect cases, and in 13.4% of those born alive. For limb differences the pattern is sharper still. In a population series of 391 fetuses and children with limb reduction defects in the northern Netherlands, a diagnosis naming the cause was reached nearly three times as often when several limbs were affected as when only one was, and no genetic disorder at all was found among isolated defects of a single limb. The review works through genes, medicines and chemicals, maternal health, vascular disruption and mechanical forces.</p>
        <p><a href="/knowledge/causes-of-dysmelia/">Read what is known about the causes &rarr;</a></p>
      </div>
    </div>
  </div>
</section>
""",
}



# ── Expected affected births: what a birth prevalence means in births a year, country by country ──
# Births come from the World Bank (tools/build-births.py); the rates are those of the prevalence
# table above, per 100,000 births. Multiplying one by the other gives an expectation, not a count:
# it assumes the rate a European or Finnish registry measured holds in every country, which no one
# has shown. It is not an incidence either, and the page says why. The registry exists to replace
# these expectations with consented, counted cases.
BIRTHS = json.loads((pathlib.Path(__file__).parent / "tools" / "births.json").read_text(encoding="utf-8"))
WORLD_BIRTHS = sum(c["births"] for c in BIRTHS["countries"])


def _slug(label):  # the address of a filtered view: ?condition=all-limb-reduction-defects
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", label.lower())).strip("-")


def _rate_txt(rate):  # the unit that reads best: per 10,000 births, or per 100,000 for the rare ones
    return f"{rate / 10:g} per 10,000 births" if rate >= 10 else f"{rate:g} per 100,000 births"


def _cases(births, rate):  # rate per 100,000 births
    n = births * rate / 100000
    return f"{n:,.0f}" if n >= 10 else (f"{n:.1f}" if n >= 0.1 else "&lt;0.1")


def incidence_html():
    rates = DOT_RATES
    rows = "".join(
        f'<tr data-name="{c["name"].lower()}" data-region="{c["region"]}" data-births="{c["births"]}">'
        f'<th scope="row">{c["name"]}</th><td>{c["region"]}</td><td class="num">{c["births"]:,}</td>'
        f'<td class="num cases">{_cases(c["births"], rates[0][1])}</td></tr>'
        for c in BIRTHS["countries"])
    options = "".join(
        f'<option value="{i}" data-slug="{_slug(lab)}">{lab} · {_rate_txt(r) if r else "no published rate"}</option>'
        for i, (lab, r, _src, _basis, _note) in enumerate(rates))
    regions = "".join(f'<option value="{r}">{r}</option>' for r in sorted({c["region"] for c in BIRTHS["countries"]}))
    world = {lab: (_cases(WORLD_BIRTHS, r) if r else "") for lab, r, _s, _b, _n in rates}
    data = json.dumps({"rates": [[lab, r, src, _slug(lab), basis, note] for lab, r, src, basis, note in rates],
                       "basisLabels": BASIS_LABEL,
                       "births": [[c["name"], c["region"], c["births"]] for c in BIRTHS["countries"]]},
                      ensure_ascii=False, separators=(",", ":"))
    return f"""
    <div class="tick"></div>
    <p class="eyebrow">Part 2 · Expected affected births, year by year</p>
    <h2 class="h2">How many affected births a year does that mean?</h2>
    <p>A prevalence is a proportion; families and health services need a number. The world records about
    {WORLD_BIRTHS / 1e6:.0f} million births a year across the {len(BIRTHS["countries"])} countries the World Bank counts, so the
    {rates[0][1] / 10:g} per 10,000 births that European registries measure for limb reduction defects works out at roughly
    <strong>{world[rates[0][0]]} affected births a year</strong> worldwide. On the same arithmetic, polydactyly reaches about
    {world["Polydactyly"]} a year and syndactyly {world["Syndactyly"]}, while amelia, the absence of a whole limb, comes to about
    {world["Amelia, all forms"]}. In a country the size of France, with {next(c["births"] for c in BIRTHS["countries"] if c["name"] == "France"):,} births a year,
    the same rates give {_cases(next(c["births"] for c in BIRTHS["countries"] if c["name"] == "France"), rates[0][1])} limb reduction defects
    and {_cases(next(c["births"] for c in BIRTHS["countries"] if c["name"] == "France"), 1.41)} births with amelia.</p>
    <p>Three cautions go with every number below, and they are the epidemiologist&rsquo;s rather than the statistician&rsquo;s.
    <strong>They are expectations, not counts.</strong> The rates in the selector were measured or pooled in
    {" · ".join(sorted({src for _l, r, src, _b, _n in rates if r and src}))}, and applying one of them to births in Nigeria, India
    or Brazil assumes the rate is the same there, which no one has shown; where other registries have measured, the figures differ,
    as the previous section shows. <strong>They are not incidences.</strong> An incidence would count affected conceptions, and
    the losses before registration are invisible; what is multiplied here is a prevalence at birth, so the result is the number of
    affected births a registry of that kind would expect to record. <strong>They are not all live births.</strong> The registry
    numerators include fetal deaths and terminations after a prenatal diagnosis, and for the severest conditions those are the
    majority: in Finland about {0.63 / 2.43:.0%} of amelia births were live births. The World Bank counts live births, so the
    denominator differs slightly too. Read the numbers as the order of magnitude a health service should plan for, and as the
    reason a patient-owned registry is worth building: it turns an expectation into a consented, counted child who can be
    offered care.</p>

    <div class="inc-controls" id="inc-controls">
      <label for="inc-condition">Condition</label>
      <select id="inc-condition">{options}</select>
      <label for="inc-region">Region</label>
      <select id="inc-region"><option value="">Every region</option>{regions}</select>
      <label for="inc-q">Country</label>
      <input type="search" id="inc-q" placeholder="Search a country…" autocomplete="off">
      <button type="button" id="inc-reset">Reset</button>
      <p class="inc-count" aria-live="polite"><strong id="inc-n">{len(BIRTHS["countries"])}</strong> countries ·
        <strong id="inc-total">{world[rates[0][0]]}</strong> affected births a year expected, for
<span id="inc-label">{rates[0][0].lower()} ({_rate_txt(rates[0][1])}, {rates[0][2]})</span></p>
      <p class="inc-basis" id="inc-basis" aria-live="polite"><strong>Pooled from several registries.</strong> Source: {rates[0][2]}.</p>
    </div>
    <div class="annex-wrap">
      <table class="annex inc-table" id="inc-table">
        <thead><tr><th scope="col">Country</th><th scope="col">Region</th><th scope="col">Births a year</th>
          <th scope="col" id="inc-head">Expected a year: {rates[0][0]}</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <button type="button" class="inc-more" id="inc-more" hidden>Show all {len(BIRTHS["countries"])} countries</button>
    <script type="application/json" id="inc-data">{data.replace("</", "<\\/")}</script>
    <p class="annex-note">Births: {BIRTHS["source"]} Read {BIRTHS["built"]}, covering {min(c["year"] for c in BIRTHS["countries"])}.
    <a href="{BIRTHS["source_url"]}" target="_blank" rel="noopener external">data.worldbank.org</a> ·
    <a href="/data/births.json">Download the births data (JSON)</a>. Rates: the prevalence table above, with its sources; each is
    stated per 10,000 births in the selector. Expected affected births = births &times; birth prevalence. A country whose expectation
    falls below one a year is shown to one decimal: it means the condition is expected there less often than once a year, not never.</p>
    <p style="margin-top:var(--space-4)">These figures say how often each condition occurs at birth and how many affected births that means.
    What is known about why it occurs is set out in <a href="/knowledge/causes-of-dysmelia/">Causes of dysmelia</a>, and what each
    condition is in <a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a>.</p>
"""


PAGES["/knowledge/epidemiology/"] = {
    "title": "Epidemiology",
    "desc": "How common limb differences are at birth, with every figure's source and confidence interval, and how many affected births a year that means in each country.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/epidemiology/", "Epidemiology")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Knowledge · Epidemiology</p>
    <h1 class="display">How common is dysmelia, and how many affected births a year?</h1>
    <p>Two questions, two kinds of answer. <strong>Birth prevalence</strong> is what the registries measure: how many births in
    10,000 are affected by a condition, counting live births, fetal deaths and terminations after a prenatal diagnosis, in a
    defined population over a defined period. It is a proportion, and it is not an incidence, for reasons the first part explains.
    The <strong>expected number of affected births</strong> is what that proportion becomes when it meets a country&rsquo;s births:
    how many a year a health service should plan for. The first part gives the prevalences, condition by condition, with the source,
    the population and the confidence interval behind each; the second turns them into numbers for every country, which you can filter.</p>

    {prevalence_html()}
    {incidence_html()}
  </div>
</section>
""",
}

# ───────────────── Causes of dysmelia · referenced review ─────────────────
# Every reference is an entry of the bibliography register (tools/bibliography.json), resolved by DOI
# or by "pmid:NNNN" for the few entries PubMed carries without one, so a citation here cannot drift
# from the register and the build fails if one goes missing. A paper the standing PubMed queries do
# not reach belongs in REVIEW_SEED in tools/build-bibliography.py, not in a list on this page.
# Numbering follows first appearance: cref() runs while the body f-string is evaluated, left to right.

BIB_BY_DOI = {(e.get("doi") or "").lower(): e for e in BIB.get("entries", []) if e.get("doi")}
BIB_BY_PMID = {str(e.get("pmid")): e for e in BIB.get("entries", []) if e.get("pmid")}


# ── How unevenly the causes of dysmelia have been studied (quoted in Voice, demand 4) ──
# Counted from the register at every build, so the figures in the prose cannot go stale.
# Thalidomide and epidemiology come from the register's own tags; the three remaining
# buckets are read off the title, because the register has no field for "names a gene".
# NOT_A_GENE lists the all-caps tokens that look like gene symbols but are not: study
# acronyms, classifications, and the chemicals that appear in titles in the same shape.
NOT_A_GENE = {
    "DNA", "RNA", "USA", "UK", "EU", "US", "WHO", "MRI", "CT", "PCR", "QF", "CNV", "IVF", "ART", "COVID", "SARS",
    "ICBDSR", "EUROCAT", "OMT", "IFSSH", "TAR", "EEC", "VACTERL", "VATER", "ADAM", "LBWC", "ABS", "ICD", "NBDPS",
    "CHD", "CDS", "FADS", "AMC", "BMI", "CVS", "TTTS", "GWAS", "NGS", "WES", "WGS", "SNP", "OMIM", "HIV", "AND",
    "THE", "FOR", "WITH", "NOT", "NEW", "III", "CARE", "CASE", "RARE", "TYPE", "PART", "ONE", "TWO", "PRELLIM",
    "NSQIP", "GOAL", "PRCM", "SVA", "IMI2", "TBN", "ACASS", "CDG", "IFT", "GPT",
    "CAR", "DHA", "B12", "ENU", "DEHP", "SAG",  # compounds and vitamins, not genes
}
GENE_SYMBOL = re.compile(r"\b([A-Z][A-Z0-9]{2,8})\b")
MEDICINE_RX = re.compile(
    r"\b(drugs?|medications?|medicines?|prescription|pharmaceutical|analgesics?|misoprostol|mifepristone|valproat\w*"
    r"|phenytoin|phenobarbital|carbamazepin\w*|oxcarbazepine|topiramate|lamotrigine|levetiracetam|antiepileptic"
    r"|antiseizure|anticonvulsant|retinoic|retinoid|isotretinoin|methotrexate|mycophenolate|warfarin|leflunomide"
    r"|cabergoline|macrolides?|amoxicillin|antibiotics?|antidepressants?|SSRIs?|antipsychotics?|opioids?|fentanyl"
    r"|cytarabine|cyclophosphamide|ondansetron|fluconazole|paracetamol|acetaminophen|ibuprofen|NSAIDs?|progestogens?"
    r"|progesterone|beta-blockers?|antihypertensives?|corticosteroids?|vaccin\w*|CAR T-cell)\b", re.I)
ENVIRONMENT_RX = re.compile(
    r"\b(pollut\w*|pesticid\w*|herbicid\w*|solvents?|occupational|heavy metals?|trace elements?|cadmium|mercury"
    r"|arsenic|dioxins?|PFAS|phthalates?|endocrine disrupt\w*|drinking water|air quality|radiation|hyperthermia"
    r"|environmental (exposure|factor|pollut|contamina|chemical|risk|mixture|toxic)\w*)\b"
    r"|(?<!familial )(?<!family )\bcluster\w*", re.I)
def bib_causes_stats():
    entries = BIB.get("entries", [])
    thal = [e for e in entries if "thal" in (e.get("codes") or [])]
    rest = [e for e in entries if "thal" not in (e.get("codes") or [])]
    named_gene = [e for e in rest
                  if any(s not in NOT_A_GENE and not s.isdigit() for s in GENE_SYMBOL.findall(e["title"]))]
    env = [e for e in rest if ENVIRONMENT_RX.search(e["title"])]
    years = sorted(int(e["year"]) for e in env if str(e.get("year", "")).isdigit())
    span = (years[-1] - years[0] + 1) if years else 0
    return {
        "total": len(entries), "thalidomide": len(thal),
        "epidemiology": sum(1 for e in entries if "epidemiology" in e["topics"]),
        "gene": len(named_gene), "medicine": sum(1 for e in rest if MEDICINE_RX.search(e["title"])),
        "environment": len(env), "env_span": span, "env_first": years[0] if years else 0,
        "env_years_per_paper": (span / len(env)) if env else 0,
        "teratogens": sum(1 for e in entries if "teratogens" in e["topics"]),
    }


BIBSTAT = bib_causes_stats()

CAUSES_REF_ORDER = []

# ── Glossary: plain-language definitions shown on hover, tap or keyboard focus ──
# key -> (regex fragment matched in the prose, definition, source label, source URL).
# Definitions are written for families by the DysNet documentation team; the link points to the
# reliable reference page where the reader can go further. Every URL was fetched and its page
# title checked in September 2026; a term with no suitable public lay page carries no link.
NCI_G = "https://www.cancer.gov/publications/dictionaries/genetics-dictionary/def/"
NCI_C = "https://www.cancer.gov/publications/dictionaries/cancer-terms/def/"
MPG = "https://medlineplus.gov/genetics/"
ORPHA_D = "https://www.orpha.net/en/disease/detail/"

GLOSSARY = [
    # (pattern, definition, source label, url)
    (r"mesenchyme", "The soft, unspecialised tissue of the early embryo. It is the raw material from which bone, cartilage, muscle and blood vessels are later built.", "", ""),
    (r"apical ectodermal ridge", "A thin ridge of skin-forming tissue running along the tip of the growing limb bud. It tells the limb how far to grow, from shoulder to fingertip. Remove it in an animal embryo and the limb stops short.", "", ""),
    (r"zone of polarising activity", "A small patch of cells at the back edge of the limb bud that tells the hand which side is the thumb and which the little finger.", "", ""),
    (r"fibroblast growth factors", "A family of signalling proteins that tell cells to divide and keep growing. The ridge at the tip of the limb bud uses them to drive the limb outwards.", "", ""),
    (r"sonic hedgehog", "A signalling protein, named after the video-game character, produced at the back edge of the limb bud. The amount of it a cell receives decides which finger that cell will help build.", "MedlinePlus Genetics", MPG + "gene/shh/"),
    (r"dorsal ectoderm", "The outer layer of cells covering the back of the developing limb. It is what makes the back of the hand different from the palm.", "", ""),
    (r"enhancer", "A stretch of DNA that works as a switch: it does not describe a protein, it decides where and when a nearby gene is switched on. An enhancer can sit a long way from the gene it controls.", "NCI Dictionary of Genetics Terms", NCI_G + "enhancer"),
    (r"homeodomain", "The part of a HOX protein that grips DNA. A change here alters which genes the protein can switch on.", "NCI Dictionary of Genetics Terms", NCI_G + "homeobox"),
    (r"HOX genes", "A set of master genes that tell each part of the embryo what it should become, in the right order from head to tail and from shoulder to fingertip.", "NCI Dictionary of Genetics Terms", NCI_G + "homeobox"),
    (r"transcription factors", "Proteins whose job is to switch other genes on or off.", "NCI Dictionary of Genetics Terms", NCI_G + "transcription-factor"),
    (r"transduces", "Passes a signal on: a message arriving at the cell is relayed inwards and changes what the cell does.", "NCI Dictionary of Genetics Terms", NCI_G + "signal-transduction"),
    (r"phenotype", "What can actually be observed in a person: the shape of the hand, the height, the results of a scan. The visible outcome, as opposed to the underlying genetic instructions.", "NCI Dictionary of Genetics Terms", NCI_G + "phenotype"),
    (r"genotype", "The genetic instructions a person carries, whether or not they show.", "NCI Dictionary of Genetics Terms", NCI_G + "genotype"),
    (r"homozygous", "Carrying the same version of a gene on both copies, one inherited from each parent. Some conditions only appear when both copies are affected.", "NCI Dictionary of Genetics Terms", NCI_G + "homozygous"),
    (r"[Hh]eterozygous", "Carrying two different versions of a gene, one from each parent. For many conditions one affected copy is enough to cause them.", "NCI Dictionary of Genetics Terms", NCI_G + "heterozygous"),
    (r"de novo", "New in the child: a genetic change that neither parent carries. It happened in the egg, the sperm or the earliest cell divisions, and it is nobody's fault.", "NCI Dictionary of Genetics Terms", NCI_G + "de-novo-mutation"),
    (r"monogenic", "Caused by a change in a single gene.", "", ""),
    (r"trisomy 13", "Also called Patau syndrome: three copies of chromosome 13 instead of two, causing severe malformations of the brain, heart, face and limbs.", "MedlinePlus Genetics", MPG + "condition/trisomy-13/"),
    (r"[Tt]risomy 18", "Also called Edwards syndrome: three copies of chromosome 18 instead of two, causing severe malformations including clenched hands with overlapping fingers.", "MedlinePlus Genetics", MPG + "condition/trisomy-18/"),
    (r"[Tt]risomy", "Having three copies of a chromosome instead of the usual two.", "NCI Dictionary of Genetics Terms", NCI_G + "trisomy"),
    (r"[Cc]hromosomal breakpoints", "The points at which a chromosome has broken and been rejoined in the wrong place. Genes near the break can end up cut off from the switches that control them.", "MedlinePlus Genetics", MPG + "understanding/mutationsanddisorders/structuralchanges/"),
    (r"[Cc]hromosomes", "The packages in which our DNA is stored. Humans normally have 46, in 23 pairs.", "MedlinePlus", "https://medlineplus.gov/ency/article/002327.htm"),
    (r"[Cc]opy-number variants", "Stretches of DNA that are present in too many or too few copies. They can affect several genes at once, and are found by a different test from ordinary gene sequencing.", "NCI Dictionary of Genetics Terms", NCI_G + "copy-number-variation"),
    (r"[Ee]xome sequencing", "Reading all the parts of a person's DNA that describe proteins, about 1-2% of the genome, in one test. It finds many causes, but not changes in switches outside those parts.", "NCI Dictionary of Genetics Terms", NCI_G + "exome-sequencing"),
    (r"coding genome", "The parts of DNA that describe proteins. The rest, once called junk, contains the switches that control when and where genes work.", "MedlinePlus Genetics", MPG + "understanding/basics/noncodingdna/"),
    (r"simple loss of one working copy", "Called haploinsufficiency: the person has one normal copy of the gene and one that does not work, and the half dose is not enough.", "NCI Dictionary of Genetics Terms", NCI_G + "haploinsufficiency"),
    (r"consanguineous", "Describing parents who are blood relatives, most often first cousins. Their children are more likely to inherit the same rare gene change from both sides.", "NCI Dictionary of Genetics Terms", NCI_G + "consanguineous"),
    (r"[Mm]onozygotic twins", "Identical twins, formed when one fertilised egg splits. They share the same DNA, so a difference between them points to something other than inherited genes.", "NCI Dictionary of Genetics Terms", NCI_G + "monozygotic-twins"),
    (r"apoptosis", "Programmed cell death: the orderly self-destruction a cell undergoes when it is damaged or no longer needed. Too much of it in a limb bud removes tissue that should have been built.", "NCI Dictionary of Genetics Terms", NCI_G + "apoptosis"),
    (r"[Aa]ntiangiogenic", "Blocking the growth of new blood vessels.", "NCI Dictionary of Genetics Terms", NCI_G + "angiogenesis"),
    (r"blood-vessel formation", "The growth of new blood vessels, called angiogenesis. A limb bud grows so fast that it needs new vessels continuously; losing them starves it.", "NCI Dictionary of Genetics Terms", NCI_G + "angiogenesis"),
    (r"hypoxia", "A shortage of oxygen in a tissue.", "NCI Dictionary of Genetics Terms", NCI_G + "hypoxia"),
    (r"ubiquitin ligase", "A cellular machine that tags unwanted proteins for destruction. Which proteins it tags depends on a receptor part that thalidomide is able to hijack.", "NCI Dictionary of Cancer Terms", NCI_C + "ubiquitin-ligase"),
    (r"cereblon", "A protein inside our cells that selects which other proteins should be destroyed. Thalidomide sticks to it and changes that selection, which is how the drug is now thought to act on the embryo.", "", ""),
    (r"p53-dependent", "Depending on p53, a protein that halts or destroys damaged cells. It protects us from cancer, but in an embryo it can also remove cells a limb still needed.", "NCI Dictionary of Genetics Terms", NCI_G + "p53-gene"),
    (r"cohesion gene", "A gene involved in holding the two copies of each chromosome together while a cell divides. When it fails, cells divide badly and die.", "", ""),
    (r"teratogen", "Any substance, infection or physical agent that can disturb the development of an unborn child.", "NCI Dictionary of Cancer Terms", NCI_C + "teratogen"),
    (r"embryopathy", "The pattern of damage caused to an embryo by a particular agent. Thalidomide embryopathy is the pattern left by that drug.", "", ""),
    (r"aetiological diagnosis", "A diagnosis that names the cause, not just the condition. Saying a hand is affected describes it; saying which gene change produced it explains it.", "", ""),
    (r"prevalence", "How common something is in a population at a given time, here usually expressed as cases per 10,000 births.", "NCI Dictionary of Cancer Terms", NCI_C + "prevalence"),
    (r"odds ratio", "A way of comparing two groups. An odds ratio of 1 means no difference; 1.3 means roughly 30% higher odds in the exposed group; 12 means twelve times the odds. It is a comparison, not a personal risk.", "NCI Dictionary of Cancer Terms", NCI_C + "odds-ratio"),
    (r"[Rr]elative risk", "How many times more likely an outcome is in one group than another. A relative risk of 1.14 means 14% more likely, which on a very rare condition still means very few extra cases.", "NCI Dictionary of Cancer Terms", NCI_C + "relative-risk"),
    (r"95% CI", "The confidence interval: the range within which the true figure most probably lies. A wide range, or one that includes 1, means the study cannot tell us much.", "NCI Dictionary of Cancer Terms", NCI_C + "confidence-interval"),
    (r"meta-analysis", "A study of studies: results from several separate studies are pooled statistically to get a single, more reliable figure.", "NCI Dictionary of Cancer Terms", NCI_C + "meta-analysis"),
    (r"case-control stud", "A study that starts from children who have the condition and compares their history with that of similar children who do not. Quick for rare conditions, but it relies on remembering past exposures correctly.", "NCI Dictionary of Cancer Terms", NCI_C + "case-control-study"),
    (r"cohort", "A group followed forward in time, recording what happens to them. Slower and costlier than a case-control study, but less prone to error.", "NCI Dictionary of Cancer Terms", NCI_C + "cohort-study"),
    (r"[Pp]ericonceptional", "In the weeks just before and just after conception, the period when the limbs are formed.", "", ""),
    (r"gestation", "The length of the pregnancy so far, counted in days or weeks.", "NCI Dictionary of Cancer Terms", NCI_C + "gestation"),
    (r"[Hh]ypoplastic", "Underdeveloped: present, but smaller or less complete than it should be.", "NCI Dictionary of Cancer Terms", NCI_C + "hypoplasia"),
    (r"synpolydactyly", "A hand or foot with both extra digits and digits joined together.", "", ""),
    (r"polydactyly", "Being born with one or more extra fingers or toes. Preaxial means on the thumb or big-toe side, postaxial on the little-finger or little-toe side.", "Orphanet", ORPHA_D + "2913"),
    (r"syndactyly", "Fingers or toes joined together, by skin alone or by bone.", "Orphanet", ORPHA_D + "93458"),
    (r"phocomelia", "A limb in which the hand or foot is attached close to the body because the segments in between are absent or very short.", "Orphanet", ORPHA_D + "2879"),
    (r"tetra-amelia", "The absence of all four limbs. Amelia means the complete absence of a limb.", "Orphanet", ORPHA_D + "1027"),
    (r"limb reduction defects", "The general term registries use for a limb in which part is missing. Transverse means the limb stops at a level, as an amputation would; longitudinal means a bone is missing along one side while the rest is present.", "", ""),
    (r"amniotic band", "A strand of the inner membrane of the amniotic sac, floating free after the membrane tears, which can wrap around a limb or a finger and constrict it.", "Orphanet", ORPHA_D + "295000"),
    (r"limb body wall complex", "A severe pattern of malformation involving the limbs together with the wall of the abdomen or chest. Whether it shares a cause with amniotic bands is disputed.", "", ""),
    (r"[Rr]educed amniotic fluid", "Too little of the fluid surrounding the baby, called oligohydramnios. The baby has less room to move, and pressure on the limbs can deform them.", "MedlinePlus", "https://medlineplus.gov/ency/article/002220.htm"),
    (r"[Aa]rthrogryposis", "Being born with several joints fixed in one position. It is a description, not a cause: many different problems can produce it.", "", ""),
    (r"fetal akinesia", "The unborn baby moving too little. Movement is what shapes joints, so when it is reduced the joints stiffen, whatever the underlying reason.", "", ""),
    (r"[Dd]eformations", "A limb that formed normally and was then bent or squashed by outside forces. Distinct from a malformation, where the limb was built differently from the start.", "", ""),
    (r"[Cc]horionic villus sampling", "A prenatal test in which a sample of the developing placenta is taken for genetic analysis. It is now performed after 11 weeks, which is why the limb risk seen in early studies has receded.", "NHS", "https://www.nhs.uk/conditions/chorionic-villus-sampling-cvs/"),
    (r"[Ff]etoscopic laser", "Keyhole surgery inside the womb, using a camera and a laser to seal the shared blood vessels when identical twins share a placenta unequally.", "", ""),
    (r"twin-twin transfusion syndrome", "A complication of identical twins sharing one placenta, in which blood passes unevenly from one twin to the other.", "", ""),
    (r"Möbius sequence", "A condition in which the nerves controlling the face and the eyes did not develop, so the face cannot show expression. It is often accompanied by limb differences.", "MedlinePlus Genetics", MPG + "condition/moebius-syndrome/"),
    (r"VATER/VACTERL", "A combination of malformations that occur together more often than chance allows: vertebrae, anus, heart, windpipe, oesophagus, kidneys and limbs.", "MedlinePlus Genetics", MPG + "condition/vacterl-association/"),
    (r"Holt-Oram syndrome", "An inherited condition combining a difference of the thumb or forearm with a heart defect.", "MedlinePlus Genetics", MPG + "condition/holt-oram-syndrome/"),
    (r"Roberts syndrome", "A rare inherited condition with severely shortened limbs and facial clefts.", "MedlinePlus Genetics", MPG + "condition/roberts-syndrome/"),
    (r"Poland syndrome", "The absence or underdevelopment of the chest muscle on one side, usually with a smaller hand and shorter fingers on the same side.", "MedlinePlus Genetics", MPG + "condition/poland-syndrome/"),
    (r"[Cc]audal regression", "A failure of the lower end of the spine and the pelvis to form properly, strongly associated with diabetes in the mother.", "", ""),
    (r"corpus callosum", "The thick bundle of fibres joining the two halves of the brain.", "", ""),
    (r"dermatomal", "Following the strip of skin served by a single nerve root, which is why the scarring of congenital varicella appears in bands.", "", ""),
    (r"endothelial", "Belonging to the single layer of cells lining the inside of every blood vessel.", "", ""),
    (r"[Ee]mbryo", "The developing child during the first eight weeks after conception, the period in which the limbs are built.", "NCI Dictionary of Cancer Terms", NCI_C + "embryo"),
]
_GLOSS_N = [0]


def glossify(html):
    """Wrap the first occurrence of each glossary term in a hoverable, focusable definition.
    Only text nodes are touched, and never inside links, headings or citation markers."""
    parts = re.split(r"(<[^>]+>)", html)
    skip, remaining = 0, list(GLOSSARY)
    out = []
    for tok in parts:
        if tok.startswith("<"):
            tag = re.match(r"</?\s*([a-zA-Z0-9]+)", tok)
            name = tag.group(1).lower() if tag else ""
            if name in ("a", "h1", "h2", "h3", "h4", "sup", "button", "script", "style"):
                skip += 1 if not tok.startswith("</") else -1
            out.append(tok)
            continue
        if skip > 0 or not tok.strip():
            out.append(tok)
            continue
        # Collect non-overlapping first matches against the ORIGINAL text, then splice once,
        # so a definition inserted here can never be scanned for further terms.
        hits = []
        for item in list(remaining):
            pat, definition, label, url = item
            # the prose is hard-wrapped, so a term may be split across a line break
            for m in re.finditer(r"\b" + pat.replace(" ", r"\s+"), tok):
                if any(m.start() < e and s < m.end() for s, e, *_ in hits):
                    continue
                hits.append((m.start(), m.end(), m.group(0), definition, label, url))
                remaining.remove(item)
                break
        if hits:
            hits.sort()
            buf, cursor = [], 0
            for s, e, word, definition, label, url in hits:
                _GLOSS_N[0] += 1
                gid = f"gloss-{_GLOSS_N[0]}"
                more = (f' <a href="{url}" target="_blank" rel="noopener external">{label} &rarr;</a>' if url else "")
                buf.append(tok[cursor:s])
                buf.append(f'<span class="gloss"><button type="button" class="gloss-t" aria-describedby="{gid}">'
                           f'{word}</button><span class="gloss-pop" role="tooltip" id="{gid}">'
                           f'<strong>{" ".join(word.split())}</strong>{definition}{more}</span></span>')
                cursor = e
            buf.append(tok[cursor:])
            tok = "".join(buf)
        out.append(tok)
    missed = [p for p, *_ in remaining]
    if missed:
        print(f"  ! glossary terms never matched in the prose: {', '.join(missed)}")
    return "".join(out)


def _causes_ref(key):
    """Resolve a citation key to (authors, title, journal, year, volume, pages, link)."""
    e = BIB_BY_PMID.get(key[5:]) if key.startswith("pmid:") else BIB_BY_DOI.get(key.lower())
    if not e:
        raise SystemExit(f"causes-of-dysmelia: citation {key!r} is not in the bibliography register. Add it to "
                         "REVIEW_SEED in tools/build-bibliography.py and rebuild the register.")
    link = (f'https://doi.org/{e["doi"]}' if e.get("doi") else f'https://pubmed.ncbi.nlm.nih.gov/{e["pmid"]}/')
    return (", ".join(e["authors"]), e["title"], e["journal"], str(e["year"]), e.get("volume") or "", e.get("pages") or "", link)


def cref(*keys):
    ns = []
    for key in keys:
        _causes_ref(key)  # fail the build on an unresolvable citation
        if key not in CAUSES_REF_ORDER:
            CAUSES_REF_ORDER.append(key)
        ns.append(CAUSES_REF_ORDER.index(key) + 1)
    return '<sup class="ref">' + ",".join(f'<a href="#ref-{n}">{n}</a>' for n in ns) + "</sup>"


def causes_sources_html():
    rows = []
    for i, key in enumerate(CAUSES_REF_ORDER, 1):
        a, t, j, y, v, p, link = _causes_ref(key)
        vol = f" {v}" if v else ""
        pag = f":{p}" if p else ""
        shown = link.replace("https://doi.org/", "doi:").replace("https://", "")
        rows.append(f'<li id="ref-{i}">{a.rstrip(".")}. {t.rstrip(".")}. <em>{j}</em>. {y};{vol.strip()}{pag}. '
                    f'<a href="{link}" target="_blank" rel="noopener external">{shown}</a></li>')
    return f"""
    <h2 class="h4" style="margin-top:var(--space-4)" id="sources">Sources</h2>
    <ol class="sources">{"".join(rows)}</ol>
"""


_CAUSES_BODY = f"""
<section>
  <div class="container" style="--acc:var(--acc-library);--acc-text:var(--acc-library-text)">
    <div class="tick"></div>
    <p class="eyebrow">Review · September 2026</p>
    <h1 class="display">What causes dysmelia?</h1>
    <p class="byline"><strong>Loïc Rigal, PhD, JD</strong>, for the DysNet documentation team · first published September 2026 ·
    <a href="#method">how this article was written</a> · <a href="#sources">sources</a></p>
    <p class="gloss-hint">Underlined words carry a plain-language definition: hover over one, tap it, or reach it with the
    keyboard.</p>
    <p>It is the first question families ask, and the one research still cannot answer for most of them. A limb that formed
    differently is the visible end of a process that ran for about four weeks, early in pregnancy, and left almost no other trace.
    This review sets out what is established, what is probable and what is still only a hypothesis, in the order the evidence
    supports rather than the order the ideas are usually told in. It is written for families who want more than a leaflet and for
    clinicians who want the references. Nothing here is medical advice, and nothing here can diagnose a particular child.</p>

    <blockquote class="definition">
      <p>Across large birth-defect cohorts, a cause is identified in roughly one case in five; for an isolated limb difference
      affecting a single limb, it is usually none.</p>
      <footer>China Birth Cohort Study, 2,123 reviewed cases{cref("10.1136/bmjpo-2025-003451")}; EUROCAT Northern Netherlands,
      391 limb reduction defects{cref("10.1002/ajmg.a.61875")}.</footer>
    </blockquote>

    {opener("01", "The window", "When does a limb form? Four weeks in which a limb is decided.")}
    <p>Human limbs are built between roughly the fourth and the eighth week after conception. A bud of undifferentiated
    mesenchyme grows out of the body wall under the control of three signalling centres, each governing one axis. The apical
    ectodermal ridge, a thickened rim of ectoderm at the tip, drives outgrowth from shoulder to fingertip through fibroblast
    growth factors. The zone of polarising activity, at the posterior margin, sets the thumb-to-little-finger axis through
    sonic hedgehog. The dorsal ectoderm, through WNT7A, separates the back of the hand from the palm. The three are locked in
    feedback loops: remove one and the others fail in turn{cref("10.1631/jzus.b2000285")}.</p>
    <p>Two consequences follow, and they shape everything below. First, <strong>timing decides the shape of the defect more than
    the cause does</strong>: the same insult a few days earlier or later produces a different limb, and very different insults
    striking at the same hour produce limbs that look alike{cref("10.1111/j.1440-169X.2007.00939.x", "10.1007/s00204-024-03930-z")}.
    Second, by the time a pregnancy is confirmed, most of this window has already passed. A limb difference is therefore almost
    never the result of anything that happened after the mother knew she was pregnant.</p>

    {opener("02", "How often a cause is found", "How often is a cause found? Most of the time, honestly, we do not know.")}
    <p>The China Birth Cohort Study reviewed 2,123 birth defect cases and found an identifiable cause in 22.4% of them: 415
    chromosomal anomalies, 31 monogenic disorders, 23 environmental exposures and 6 attributable to twinning. Among live births
    the proportion fell to 13.4%{cref("10.1136/bmjpo-2025-003451")}. This is not a Chinese peculiarity; it is what every
    well-run cohort finds.</p>
    <p>For limb differences specifically, the most useful study is a population-based series of 391 fetuses and children with
    limb reduction defects registered in the northern Netherlands between 1981 and 2017. An aetiological diagnosis was made
    almost three times as often when several limbs were affected as when one was (relative risk 2.9, 95% CI 2.2 to 3.8). No
    genetic disorder at all was identified among isolated defects of a single limb, whereas a genetic disorder was found in 16%
    of cases that had one affected limb alongside other anomalies{cref("10.1002/ajmg.a.61875")}. The practical reading is
    consistent with what geneticists advise: an isolated one-limb difference is usually sporadic, with a low recurrence risk;
    several limbs, or other organs involved, make genetic testing worthwhile.</p>
    <p>Counting also depends on classification. Under the Oberg-Manske-Tonkin system, the 577 congenital upper-limb anomalies
    recorded in Stockholm over eleven years split into 429 malformations, 124 deformations, 10 dysplasias and 14
    syndromes{cref("10.1016/j.jhsa.2013.11.014")}. Malformations and deformations have entirely different causes, and mixing
    them is the commonest way to get the aetiology wrong.</p>

    {opener("03", "Genes", "Which genes are involved? From a single letter to a whole chromosome.")}
    <p><strong>Patterning genes.</strong> The HOX genes encode transcription factors and act as the selectors of the body plan;
    <em>HOXD13</em> is the one most
    often implicated in the hand. Changes inside and outside its homeodomain produce synpolydactyly, in which digits are both
    extra and fused{cref("10.1242/dev.00396", "10.1002/ajmg.a.37464", "10.1038/s41419-023-05681-8")}. Chromosomal breakpoints
    around the HOXD cluster, which do not touch the coding sequence at all, produce a whole range of limb
    malformations{cref("10.1136/jmg.2005.033555")}, and the same is true of rearrangements affecting the distant control
    region of the HOXA cluster{cref("10.1007/s10577-009-9059-5")}.</p>
    <p><strong>GLI3</strong>, which transduces hedgehog signalling, illustrates how precisely genotype can predict phenotype. In
    297 patients carrying 127 different variants, two distinct groups emerged: variants causing simple loss of one working copy
    give anterior anomalies, while truncating variants inside the activator domain give posterior ones (postaxial polydactyly of
    the hand, odds ratio 12.7; of the foot, 33.9) together with a raised risk of corpus callosum anomalies (odds ratio
    8.8){cref("10.1136/jmedgenet-2020-106948")}.</p>
    <p><strong>The switches, not the genes.</strong> Some of the clearest lessons of the last two decades concern DNA that codes
    for nothing. The ZRS is an enhancer sitting about a megabase away from <em>SHH</em>, inside an intron of a neighbouring gene;
    single-letter changes and small insertions in it switch <em>SHH</em> on at the front of the limb bud, where it does not
    belong, creating a second polarising zone and a duplicated thumb or great toe{cref("10.1002/humu.22097", "10.1038/s41436-019-0626-7", "10.1002/ajmg.a.36367")}.
    The number of enhancer copies can matter as much as their sequence{cref("10.1038/ng.3939")}. A family can therefore carry a
    limb malformation with a completely normal coding genome, which is why standard gene panels miss some of them.</p>
    <p><strong>Signalling ligands and the severe end.</strong> Homozygous loss of <em>WNT3</em> causes tetra-amelia, the absence
    of all four limbs{cref("10.1086/382196")}; homozygous <em>WNT7A</em> variants do the same{cref("10.1002/ajmg.a.33717")}.
    Heterozygous <em>FGF8</em> variants are found in patients with VATER/VACTERL features{cref("10.1002/bdra.23278")}.</p>
    <p><strong>Where the genetic and the vascular meet.</strong> Roberts syndrome is caused by variants in <em>ESCO2</em>, a
    cohesion gene with no obvious link to limb patterning. In a mouse model, the limb reduction turns out to be produced by
    p53-dependent apoptosis together with disrupted blood-vessel formation{cref("10.1038/s41467-024-51328-3")}. A genetic cause
    and a vascular mechanism are not alternatives; here they are the same story told at two levels.</p>
    <p><strong>Syndromes.</strong> <em>TBX5</em> causes Holt-Oram syndrome, the heart-hand condition, described across European
    registries{cref("10.1186/s13023-014-0156-y")} and reviewed systematically for its cardiac
    spectrum{cref("10.1016/j.ejmg.2024.104920")}. <em>SALL4</em> causes Duane-radial ray, IVIC and acro-renal-ocular syndromes,
    a group whose limb findings overlap closely with thalidomide embryopathy{cref("10.1136/jmg.40.7.473", "10.1159/000531452")};
    that overlap turns out not to be a coincidence, as section 04 explains.</p>
    <p><strong>Chromosomes.</strong> Trisomy 18 and trisomy 13 have birth prevalences of 4.8 and 1.9 per 10,000 in Europe. Among
    live-born babies with trisomy 13, 44% had polydactyly{cref("10.1002/ajmg.a.37355")}; limb deficiencies also occur, though
    less often{cref("10.1002/1096-8628(20000814)93:4<339::aid-ajmg15>3.0.co;2-r")}. Smaller copy-number changes are found in a
    minority of patients with conditions usually called non-genetic, such as Poland
    syndrome{cref("10.1186/s12881-016-0351-x")}. In consanguineous families, exome sequencing is the reasonable first
    test{cref("10.3390/genes12070962")}, and recessive variants in genes such as <em>BHLHA9</em> account for syndactyly forms
    that would otherwise look sporadic{cref("10.1038/hgv.2017.54")}.</p>

    {opener("04", "Medicines and chemicals", "Which medicines and chemicals are proven? One certainty, several strong signals, and a long tail of weak ones.")}
    <p>A teratogen is any agent that can disturb the development of an unborn child. The list of those actually proved to cause
    limb differences in humans is far shorter than the internet suggests, and the strength of the evidence varies enormously from
    one entry to the next; the substances below are ordered accordingly, and those with a regulatory status are tracked in the
    <a href="/knowledge/teratogens/">teratogens register</a>.</p>
    <p><strong>Thalidomide</strong> remains the reference case, and its mechanism has changed since most textbooks were written.
    The drug binds cereblon, the substrate receptor of a CRL4 ubiquitin ligase, and reprograms what that ligase destroys. The
    proteins degraded include SALL4{cref("10.1038/s41589-018-0129-x")}, PLZF/ZBTB16, degraded by thalidomide and by its
    metabolite 5-hydroxythalidomide{cref("10.15252/embj.2020105375")}, and p63{cref("10.1038/s41589-019-0366-7")}. The SALL4
    result is the most persuasive, because people with inherited <em>SALL4</em> mutations are born with limbs that resemble
    thalidomide embryopathy{cref("10.1136/jmg.40.7.473")}.</p>
    <p>It is not the whole account. Antiangiogenic metabolites of thalidomide destroy the immature blood vessels of the early
    limb bud, upstream of any change in patterning gene expression{cref("10.1073/pnas.0901505106")}, and current reviews treat
    loss of vasculature, targeted protein degradation and oxidative stress as mechanisms that act
    together{cref("10.1002/bdrc.21096", "10.3390/ph13050095", "10.1016/j.biopha.2020.110114", "10.1177/17531934231177425")}. A
    2025 re-evaluation goes further and argues that the usual human phenotype is a longitudinal, preaxial defect that becomes
    transverse only in its most severe form, with the arms affected before the legs and the left side before the
    right{cref("10.1007/s00204-024-03930-z")}. Saying simply that thalidomide "causes phocomelia by stopping blood vessels
    growing" is the short version of a question that is still open.</p>
    <p>Why some exposed pregnancies produced an affected child and others did not is equally unresolved. Variation in
    <em>CRBN</em>{cref("10.1016/j.reprotox.2016.10.003")}, in <em>ESCO2</em>, <em>SALL4</em> and
    <em>TBX5</em>{cref("10.1038/s41598-019-47739-8")} and in angiogenesis genes{cref("10.1016/j.reprotox.2017.01.012")} has been
    examined in survivors, and screens continue in differentiating stem cells{cref("10.3390/cells14030215")}, without a
    settled answer.</p>
    <p><strong>Misoprostol</strong> is the strongest post-thalidomide signal. First reported from Brazil, where it was used in
    unsuccessful attempts to end a pregnancy{cref("10.1056/nejm199806253382604")}, it was confirmed by a meta-analysis of four
    case-control studies covering 4,899 cases: odds ratio 25.31 (95% CI 11.11 to 57.66) for Möbius sequence and 11.86 (4.86 to
    28.90) for terminal transverse limb defects{cref("10.1016/j.reprotox.2006.03.015")}. The presumed mechanism is uterine
    contraction and a fall in blood flow to the embryo, which is why the defects are transverse rather than
    patterned{cref("10.1016/j.ejogrb.2016.11.007", "10.1002/bdr2.1160")}.</p>
    <p><strong>Retinoids.</strong> Prenatal isotretinoin exposure has been associated with limb reduction
    defects{cref("10.1002/tera.1420440602")}, and retinoic acid produces limb malformations experimentally in a strictly
    stage-dependent way{cref("10.1002/tera.1420230106", "10.1002/bdra.20232", "10.1002/bdra.20385")}.</p>
    <p><strong>Antiseizure medicines</strong> need to be stated carefully, because the risk is real but is mostly not a limb
    risk. In EURAP, 10,121 prospectively followed monotherapy pregnancies gave major malformation rates of 9.9% for valproate,
    6.3% for phenytoin, 6.2% for phenobarbital, 5.4% for carbamazepine, 4.9% for topiramate, 3.1% for lamotrigine, 2.9% for
    oxcarbazepine and 2.5% for levetiracetam, dose-dependent for the first three; as prescribing shifted away from valproate and
    carbamazepine, the overall malformation rate fell by 39%{cref("10.1001/jamaneurol.2024.0258")}, a ranking the Cochrane
    review reproduces{cref("10.1002/14651858.cd010224.pub3")}. The limb findings in this group are typically hypoplastic distal
    phalanges and nails rather than dysmelia; postaxial defects after valproate{cref("10.1097/00019605-200009020-00015")} and a
    hypoxic-ischaemic pattern after phenytoin{cref("10.1002/bdra.10100")} are described at the level of case reports. Nobody
    should stop an antiseizure medicine on the strength of this page; uncontrolled seizures carry their own risks.</p>
    <p><strong>Methotrexate</strong> produces a recognised embryopathy including limb anomalies when given in the sensitive
    window at sufficient dose{cref("10.1002/bdra.23003", "10.1016/j.reprotox.2019.05.066")}.</p>
    <p><strong>Tobacco, alcohol and opioids.</strong> A meta-analysis of 37 studies puts maternal smoking at a pooled odds ratio
    of 1.27 (95% CI 1.18 to 1.38) for limb reduction defects; the same analysis found an association for polydactyly, syndactyly
    and adactyly taken as one group (1.32) that disappeared when polydactyly (1.06) and syndactyly (0.91) were analysed
    separately{cref("10.3390/jcm12134181")}, which is a useful reminder of how fragile these signals
    are{cref("10.1111/ppe.12075")}. Periconceptional alcohol has been examined in the National Birth Defects Prevention Study
    without a consistent association{cref("10.1002/bdra.23292")}. For prescription opioids, a population cohort found no excess
    of major malformations after first-trimester exposure (adjusted relative risk 1.40, 95% CI 0.84 to
    2.34){cref("10.1001/jamanetworkopen.2021.5708")}. Recent surveillance of antipsychotics{cref("10.1136/bmjment-2025-302270")}
    and macrolides{cref("10.1371/journal.pmed.1004576")} has likewise not produced a limb signal.</p>
    <p><strong>Air and workplace.</strong> The environmental literature is the weakest part of the field. In the National Birth
    Defects Prevention Study, adjusted odds ratios for limb deficiencies were near-null for particulates and ozone, and modestly
    raised for carbon monoxide (1.02 to 1.30){cref("10.1016/j.envres.2019.108716")}. A 2026 cohort in Wuhan found a small
    association for sulphur dioxide in the first three months (1.033 to 1.043) and none for PM2.5, PM10, nitrogen dioxide,
    carbon monoxide or ozone{cref("10.1038/s41598-026-36527-w")}. Occupational exposures in textile
    manufacturing{cref("10.1080/14767058.2019.1593358")} and parental pesticide exposure{cref("10.5271/sjweh.1412")} have been
    reported, on small numbers. All of this rests on self-reported or modelled exposure, and the misclassification that follows
    can move an odds ratio in either direction{cref("10.1111/ppe.13161")}.</p>

    {opener("05", "The mother’s health", "Which maternal conditions matter? Diabetes is the one that matters most.")}
    <p>A meta-analysis covering more than 80 million births found that pre-gestational diabetes raises the risk of congenital
    anomaly overall (relative risk 1.99) far more than gestational diabetes does (1.18); for limb reduction defects specifically,
    gestational diabetes carried a relative risk of 1.14 (95% CI 1.06 to 1.23){cref("10.1371/journal.pmed.1003900")}. Caudal
    regression and femoral hypoplasia remain the signature patterns of diabetic embryopathy{cref("10.1002/ajmg.a.32071")}, and
    raised glucose alone is enough to produce limb defects in experimental
    embryos{cref("10.1016/j.bbadis.2020.165955")}. Because the damage is done before most pregnancies are confirmed, glycaemic
    control before conception is where it is prevented, which is one of the few genuinely actionable findings in this whole
    article.</p>
    <p>Maternal fever and hyperthermia have long been suspected, on an evidence base that is old and
    thin{cref("10.1002/ajmg.1320210319")}. Periconceptional supplements show a clearer effect for clubfoot than for limb
    deficiencies: in 63,969 singleton deliveries in Beijing, folic acid or multiple micronutrients were associated with a
    relative risk of 0.40 for clubfoot, while the reduction for limb defects overall did not reach significance (0.80, 95% CI
    0.56 to 1.12){cref("10.1111/ppe.12775")}. Younger maternal age is associated with vascular disruption anomalies as a
    group{cref("10.1002/bdr2.2122")}, and maternal age also tracks with defects of unknown
    cause{cref("10.1002/bdra.23049")}.</p>
    <p><strong>Infection</strong> deserves a proportionate statement. Congenital varicella syndrome, whose features include limb
    hypoplasia and scarring in a dermatomal pattern, is genuinely rare: in a prospective cohort of 347 pregnancies complicated by
    varicella, one definite case was identified (0.4%), and no case of limb hypoplasia was
    observed{cref("10.1016/s0029-7844(02)02059-8")}. The damage is attributed to viral injury to developing nerves rather than
    to the limb bud itself. Newer claims should be read cautiously: the report of Adams-Oliver syndrome after maternal COVID-19
    is a single case, which is a hypothesis and not evidence of causation{cref("10.1080/15513815.2022.2064018")}.</p>

    {opener("06", "Vascular disruption", "Can a limb be lost after it has formed? A limb that formed, then was lost.")}
    <p>Vascular disruption is a different kind of cause. The limb is built correctly, and blood flow to it then fails, producing
    hypoxia, endothelial damage, haemorrhage, tissue loss and repair. Of 7,020 infants with malformations at one American
    hospital over forty years, 105 had defects attributed to this process, including terminal transverse limb defects at three
    consistent levels{cref("10.1002/bdr2.1160")}; abnormal arterial anatomy is documented in limb deficiencies both clinically
    and experimentally{cref("10.1016/j.reprotox.2016.10.005")}. Across 26 EUROCAT registries, 5,220 vascular disruption
    anomalies were recorded, with a prevalence of 8.85 per 10,000 births in the United Kingdom against 5.44
    elsewhere, though transverse limb reduction defects were equally common in both (2.16 and 2.14), which suggests they may not
    share the aetiology of the rest of the group{cref("10.1002/bdr2.2122")}.</p>
    <p><strong>Poland syndrome</strong> is where this reasoning is most often applied and least often proved. The subclavian
    artery supply disruption sequence has been the leading hypothesis for decades and is supported by case-level
    evidence{cref("10.1136/bcr-2020-238392")}, but the published consensus recommendations describe the condition as a sequence
    of uncertain origin rather than a settled vascular diagnosis{cref("10.1186/s13023-020-01481-x")}. Copy-number variants are
    found in a minority{cref("10.1186/s12881-016-0351-x")}, a pair of affected monozygotic twins was found to share a de novo
    chromosomal deletion{cref("10.1186/1471-2350-15-63")}, and classification remains under
    discussion{cref("10.1053/j.sempedsurg.2018.05.007")}. Honest practice is to present the vascular hypothesis as a hypothesis.</p>

    {opener("07", "The amnion and mechanical forces", "Do amniotic bands and crowding explain it? Bands, crowding, and a widespread misconception.")}
    <p><strong>Amniotic band syndrome.</strong> Across 30 EUROCAT registries over forty years, 866 cases of amniotic band
    syndrome and 451 of limb body wall complex were recorded, a mean prevalence of 0.53 and 0.34 per 10,000 births, with twinning
    confirmed as a risk factor{cref("10.1002/ajmg.a.63107")}. A Finnish case-control study of 106 limb deficiencies associated
    with bands found primiparity (adjusted odds ratio 2.42) and young maternal age (1.72) to raise the risk, together with
    first-trimester use of progestogens (3.79) and of beta-blockers, the latter on a very wide confidence interval that should
    be read with caution (24.2, 95% CI 2.57 to 228){cref("10.1097/BPO.0000000000001686")}. Maternal vasoactive exposures have
    been linked to bands and terminal transverse defects together{cref("10.1002/bdra.20524")}, and whether limb body wall
    complex and amniotic bands are one entity or two is still
    argued{cref("10.1002/bdr2.1442")}.</p>
    <p><strong>Crowding, and what it does not explain.</strong> Reduced amniotic fluid, uterine anomalies and twin pregnancies do
    restrict fetal movement and can deform a normally formed limb{cref("pmid:3533366")}. But the common assumption that
    clubfoot and joint contractures are therefore mechanical is, in most cases, wrong. Arthrogryposis and the fetal akinesia
    deformation sequence are usually intrinsic: more than 320 genes have been implicated, and neuromuscular or connective-tissue
    disease is a far more frequent explanation than crowding{cref("10.1002/pd.5505")}. The lack of movement produces the
    contractures; something else produces the lack of movement. This is exactly why the malformation-deformation distinction in
    the OMT classification matters{cref("10.1016/j.jhsa.2013.11.014")}.</p>

    {opener("08", "Procedures", "Has medicine itself caused limb differences? Two causes that medicine created and then reduced.")}
    <p>Chorionic villus sampling performed before 70 days of gestation was shown, in a registry-based case-control study, to
    raise the risk of transverse limb defects and oromandibular-limb hypogenesis{cref("10.1002/ajmg.1320440639")}; maternal age
    was excluded as a confounder{cref("10.1002/ajmg.1320530212")} and a distinctive effect on the fingers was
    described{cref("10.1002/bdra.10078")}. Practice changed, and the procedure is now performed later. Fetoscopic laser
    treatment for twin-twin transfusion syndrome can produce a pseudoamniotic band
    sequence{cref("10.1002/jum.14295")}, with prevalence, risk factors and outcomes now quantified in dedicated
    series{cref("10.1016/j.ajog.2020.04.016", "10.1159/000550538")}. Both are worth knowing precisely because they show what
    identifying a cause makes possible.</p>

    {opener("09", "Genes and environment together", "Why has fifty years of research found so little? The wrong question, asked for fifty years.")}
    <p>The division of this article into genetic and environmental sections is a convenience, not a claim about nature. Mice
    carrying one working copy of <em>Shh</em> or <em>Gli2</em> develop limb defects after prenatal alcohol exposure that
    wild-type littermates do not{cref("10.1002/bdr2.1026")}, and a hedgehog pathway agonist given at the right hour produces
    preaxial polydactyly{cref("10.1002/bdra.23571")}. Human candidate-gene studies have looked for the same interactions across
    limb development, angiogenesis and coagulation genes{cref("10.1002/ajmg.a.35565", "10.1002/ajmg.a.31402")}. For most
    children, the honest formulation is that susceptibility and exposure met, and that neither alone would have been enough.</p>

    {opener("10", "Clusters", "What happens when a cluster is investigated properly?")}
    <p>In the Ain department of France, a regional registry reported an excess of isolated transverse upper-limb reduction
    defects and argued the cluster was real{cref("10.1002/bdr2.1876")}. A national, multidisciplinary investigation of three
    suspected clusters followed, examining exposures systematically, and concluded that no common cause could be
    identified{cref("10.1007/s10654-024-01125-5")}. The episode is worth recording without taking a side: with defects this
    rare, small numbers make clusters both easy to see and hard to prove, and a registry designed for counting is not
    automatically a registry designed for causal investigation.</p>

    {opener("11", "What is missing", "Why is DysNet building a registry?")}
    <p>Three things keep this field where it is. Cases are few in any one place and scattered across countries, so no single centre accumulates
    enough of them. Coding differs between registries, so the same limb is counted differently on either side of a border.
    And the phenotype is recorded far more often than the exposures, the family history and the genome that would make a cause
    findable. The result is the 22.4% with which this article opened.</p>
    <p>That is the argument for an interoperable, consent-based registry owned by the community it describes, which families
    contribute to once and researchers can query across borders. It is what DysNet is building; see
    <a href="/registry/">the registry</a> and the plain-language <a href="/knowledge/guides/patient-owned-registry/">two-minute
    guide</a>. The evidence assembled here comes from the <a href="/knowledge/bibliography/">bibliography</a>, and the substances
    named in section 04 are tracked, with their regulatory status, in the <a href="/knowledge/teratogens/">teratogens
    register</a>. For what the individual conditions are called and how frequent they are, start with
    <a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a>.</p>

    <div class="tick" id="method"></div>
    <p class="eyebrow">Method</p>
    <h2 class="h2">How was this article written?</h2>
    <p><strong>Author.</strong> Loïc Rigal, PhD, JD, for the DysNet documentation team, September 2026.</p>
    <p><strong>Sources.</strong> The starting point was the DysNet <a href="/knowledge/bibliography/">bibliography</a>, the
    register of peer-reviewed publications on our conditions, searched by theme for causes, genetics and epidemiology. Where the
    register had no coverage of a question that families ask (maternal diabetes, varicella, antiseizure medicines, misoprostol,
    fetal akinesia), the missing papers were found on PubMed and added to the register itself, so that every reference below is
    an entry of it. Every figure quoted is the figure the study itself reports, with its confidence interval where it gives one,
    checked against the published abstract or article rather than against a secondary source.</p>
    <p><strong>Drafting.</strong> The article was researched, drafted and fact-checked with the assistance of Claude Opus 5
    (Anthropic), working directly against the bibliography register and the PubMed record. Every reference was resolved
    programmatically at build time, so that a citation on this page cannot drift from its entry in the register; the build fails
    if a citation cannot be resolved. Every glossary link was fetched and its page title verified. The judgements about what the
    evidence supports, and the responsibility for any error, are the author's.</p>
    <p><strong>Editorial stance.</strong> Where the evidence is a single case report, an animal model or a hypothesis, the text
    says so rather than rounding it up to a cause. Where a widely repeated claim is weaker than its reputation, such as the
    mechanism of thalidomide or the mechanical explanation of clubfoot, the text says that too.</p>

    <div class="tick" style="background:var(--dys-green)"></div>
    <p class="eyebrow" style="color:var(--dys-green-text)">Call for corrections</p>
    <h2 class="h2">Researchers: tell us where we are wrong.</h2>
    <p>This page is a living document, and it is written by a patient network rather than by a specialist department of
    teratology or clinical genetics. If you work in this field and you find a statement that overstates the evidence, a figure
    that has been superseded, a reference that should be here and is not, or a mechanism described in terms the literature has
    moved beyond, we want to hear it and we will correct the page and credit the correction. Write to
    <a href="mailto:info@dysnet.org?subject=Causes%20of%20dysmelia%20-%20correction">info@dysnet.org</a>. Researchers are also
    welcome to add their team to the <a href="/knowledge/researchers/">researchers register</a> and their work to the
    <a href="/knowledge/bibliography/">bibliography</a>. Families who spot something that reads as jargon, or a definition that
    does not help, should tell us as well: that is a correction too.</p>
"""

PAGES["/knowledge/causes-of-dysmelia/"] = {
    "title": "Causes of dysmelia",
    "desc": "What causes congenital limb differences: genes, medicines and chemicals, maternal health, vascular disruption and bands, and how often a cause is found.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/causes-of-dysmelia/", "Causes of dysmelia")],
    "body": glossify(_CAUSES_BODY) + causes_sources_html() + """
  </div>
</section>
""",
}

# ───────────────────────────── REGISTRY ───────────────────────────
HDS_ORG = {
    "@type": "Organization", "name": "Health Data Safe", "url": "https://www.healthdatasafe.org/en/",
    "sameAs": ["https://www.healthdatasafe.org", "https://www.wikidata.org/wiki/Q141112222"],
    "address": {"@type": "PostalAddress", "addressCountry": "CH"},
}
REGISTRY_LD = {
    "@context": "https://schema.org", "@type": "Project",
    "name": "DysNet international associative registry of limb malformations",
    "url": SITE + "/registry/",
    "description": "The first international, interoperable registry of congenital limb malformations owned by the patient community, developed with DysNet's member associations and Health Data Safe.",
    "foundingDate": "2026-08-26",
    "parentOrganization": {"@type": "NGO", "name": "DysNet", "url": SITE,
                          "sameAs": ["https://www.wikidata.org/wiki/Q131894541"]},
    "member": [
        {"@type": "OrganizationRole", "roleName": "Technical and operational partner", "startDate": "2026-08-26", "member": HDS_ORG},
        {"@type": "OrganizationRole", "roleName": "Pilot association", "member": {"@type": "Organization", "name": "Assedea", "url": "https://www.assedea.fr"}},
        {"@type": "OrganizationRole", "roleName": "Pilot association", "member": {"@type": "Organization", "name": "Raggiungere", "url": "https://www.raggiungere.it"}},
    ],
    "areaServed": "Worldwide",
}

# ── Who is reading the registry page ─────────────────────────────────────────
# The page opened on perinatal mortality and a DOI, which is the right evidence and the
# wrong first sentence for a family whose child was born last week. Four people arrive here
# with four different questions, so each gets a short answer in their own terms before the
# argument proper. Every panel is rendered; the script hides all but the chosen one, so with
# no JavaScript the reader simply gets all four.
REGISTRY_AUDIENCES = [
    ("families", "A family, or a person concerned",
     "You are the reason this exists, and nothing in it happens without you.",
     [("What it is",
       "A place where what you or your child lives with is written down once, properly, and counted. "
       "Today those details sit in different hospitals in different countries, in systems that cannot "
       "talk to each other, so nobody can see the whole picture."),
      ("What you would do",
       "Nothing yet. The registry is being built. When it opens you enter your own information, through "
       "your national association, and you decide who may see it."),
      ("What stays yours",
       "The data stays yours. You give consent study by study and you can withdraw it. DysNet does not "
       "sell data, and it does not go to insurers or employers."),
      ("Why it is worth doing",
       'Across large birth-defect cohorts a cause is found in about one case in five, and usually none '
       'for a single limb. That number moves only when enough cases are described well enough to study. '
       '<a href="/knowledge/causes-of-dysmelia/">What the evidence shows today</a>.')],
     ("/about/members/", "Find your national association")),

    ("associations", "An association thinking of taking part",
     "Your families keep their data, and they keep their relationship with you.",
     [("What you would give",
       "A point of contact, help translating the questions into your language, and families you invite "
       "rather than enrol. Nobody is entered by their association."),
      ("What you would get",
       "The figures for your own country, which most associations have never had, and a seat in deciding "
       "which research may be put to your families at all."),
      ("What it costs",
       'No licence fee and no charge per family: Health Data Safe contributes the infrastructure in kind. The cost is '
       'volunteer time. The <a href="/assets/dysnet-registry-pilot.pdf">two-page brief</a> answers the questions a board '
       'asks, and you can forward it without writing to us first.'),
      ("Where it stands",
       "Pilots first, with a small number of associations. The general assembly of 26 August 2026 "
       "created the registry and mandated Health Data Safe as its technical partner.")],
     ("/assets/dysnet-registry-pilot.pdf", "Download the pilot brief (2 pages)")),

    ("registries", "A registry or public health agency in Europe",
     "We want what you already hold in the common registry, and we bring the means to move it.",
     [("Push what you hold",
       "Your cases belong in a European picture, and today they cannot reach one. We are asking you to "
       "contribute them, not to hand over your register: the route runs through the people themselves, "
       "each of whom has the right to a copy of what you hold about them."),
      ("We provide the means",
       "Interoperability support to map your fields onto a shared minimum set and onto ORPHAcodes, "
       "portability solutions so a record can move without being retyped, and a straightforward way to "
       "give people their data proactively rather than on written request. That work is ours to do, "
       "with Health Data Safe, not yours."),
      ("Align on what you collect",
       "Two national figures cannot be set side by side when each counts a different thing. We want a "
       "common definition of what is recorded, so that a comparison is a comparison. "
       f'Of the <a href="/knowledge/registries/">{REG_SPLIT["total"]} registries</a> that record our conditions, {REG_SPLIT["direct"]} name a '
       f"condition itself; the other {REG_SPLIT['other']} capture it only inside a broader group."),
      ("What you would get",
       "Figures that can honestly be compared with your neighbours', cases described from the patient's "
       "own side, including people who never reach your catchment area, and a proactive answer to the "
       "right of access you already owe.")],
     ("mailto:info@dysnet.org?subject=Registry%20interoperability", "Talk to us about interoperability")),

    ("researchers", "A researcher wanting access",
     "There is no data to request yet. There is a route to propose a study, and five registers you can use today.",
     [("How access will work",
       "You propose a study. The member associations and the board decide together whether it may be "
       "put to families. Each family then consents, or does not, one study at a time."),
      ("What will never be possible",
       "Buying the data, or receiving it in bulk without the consent of the people it describes. The "
       "point of a patient-owned registry is that this decision is not ours to sell."),
      ("What exists today",
       f'The bibliography ({len(BIB.get("entries", [])):,} references), the teratogens register '
       f'({TERA.get("counts", {}).get("total", 0)} substances), the care centres, the researcher register '
       'and the epidemiology tables. All free, all <a href="/knowledge/">documented and downloadable</a>.'),
      ("What you can do now",
       'Ask to be listed in the <a href="/knowledge/researchers/">researcher register</a>, or propose a '
       'study for the <a href="/knowledge/ongoing-studies/">studies page</a>.')],
     ("mailto:info@dysnet.org?subject=Research%20proposal", "Propose a study")),
]


def registry_audiences_html():
    pills = "".join(
        f'<button type="button" role="tab" data-aud="{key}" aria-selected="{"true" if i == 0 else "false"}" '
        f'aria-controls="aud-{key}" id="pill-{key}">{label}</button>'
        for i, (key, label, _l, _p, _c) in enumerate(REGISTRY_AUDIENCES))
    panels = ""
    for key, label, lede, points, (href, cta) in REGISTRY_AUDIENCES:
        items = "".join(f'<div class="aud-point"><h3>{h}</h3><p>{t}</p></div>' for h, t in points)
        panels += (f'<section class="aud-panel" id="aud-{key}" role="tabpanel" aria-labelledby="pill-{key}">'
                   f'<h2 class="h3 aud-h">{label}</h2><p class="aud-lede">{lede}</p>'
                   f'<div class="aud-points">{items}</div>'
                   f'<p class="aud-cta"><a class="btn btn-primary" href="{href}">{cta}</a></p></section>')
    return (f'<div class="aud" id="reg-aud"><p class="aud-q" id="aud-q">Who is reading?</p>'
            f'<div class="aud-pills" role="tablist" aria-labelledby="aud-q">{pills}</div>{panels}</div>')


PAGES["/registry/"] = {
    "jsonld": [REGISTRY_LD],
    "title": "The registry",
    "desc": "The first international registry of limb malformations owned by the patient community itself, built with member associations and Health Data Safe.",
    "crumbs": [("/registry/", "The registry")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick" style="background:var(--dys-green)"></div>
    <p class="eyebrow" style="color:var(--dys-green-text)">Mission 2 · Flagship project</p>
    <h1 class="display">The limb-malformation registry owned by the people it describes.</h1>
    <p class="lede">A registry is a list of cases described the same way, so they can be counted and studied. This one is being
    built by the associations that represent the families, and the data in it belongs to the people it describes, not to us.
    It does not exist yet: this page says what it will be, who is building it, and where it has got to.</p>
    <div id="toc-here"></div>
    {registry_audiences_html()}
    <p>Congenital anomalies remain a major cause of perinatal illness and death, accounting for up to 27% of infant deaths in developed countries, as <a href="https://www.santepubliquefrance.fr/sites/default/files/cadic_files/documents/spf00006640.pdf" target="_blank" rel="noopener external">Santé publique France</a> recalls in its 2026 surveillance report, citing Syngelaki et al. (<em>Prenat Diagn</em> 2011, <a href="https://doi.org/10.1002/pd.2642" target="_blank" rel="noopener external">doi:10.1002/pd.2642</a>). Yet we still do not understand what causes most of these anomalies, and understanding begins with counting and describing cases. Research on limb agenesis is starved of exactly that. Cases are not rare, but they are scattered across countries and recorded in incompatible systems, when they are recorded at all, so too few are described well enough to investigate the possible causes thoroughly. Families answer the same questions again and again, and science still cannot see the whole picture.</p>
    <p>Patient groups strongly suspect environmental causes and teratogenic effects, of the kind thalidomide made undeniable, behind agenesis and other forms of dysmelia. Far too little research is carried out to confirm or rule them out. Between 2007 and 2014, three clusters of transverse upper-limb agenesis came to light in France, in Loire-Atlantique, Ain and Morbihan. The investigations led by <a href="https://www.santepubliquefrance.fr/les-actualites/agenesies-transverses-des-membres-superieurs-sante-publique-france-revient-sur-les-principaux-faits" target="_blank" rel="noopener external">Santé publique France</a> with the regional registries found no common exposure. The episode did move surveillance forward: the regional registries were federated around a common database, a seventh registry followed in Nouvelle-Aquitaine, and Santé publique France plans to reach national coverage for some anomalies through the national health data system. Yet the French registries covered about one birth in six over 2019-2021 (<a href="https://www.santepubliquefrance.fr/sites/default/files/cadic_files/documents/spf00006640.pdf" target="_blank" rel="noopener external">16.4%</a>), with a stated aim of about 23.6% once the Nouvelle-Aquitaine registry is fully deployed, the ministry’s 2016 request for a national registry of malformations was answered in <a href="https://www.santepubliquefrance.fr/anomalies-et-malformations-congenitales/rapportsynthese/anomalies-congenitales-liees-aux-expositions-medicamenteuses-et-environnementales-proposition-de" target="_blank" rel="noopener external">2018</a> by building on the existing registries rather than creating one, and no registry at national or European level is dedicated to limb anomalies. Those investigations also met the limits of any case investigation: families were questioned years after the birth, from memory. Families who take part actively and from pregnancy onwards, recording circumstances and exposures as they happen, can correct that weakness and give the next investigation the data the last one lacked.</p>
    <p>Our registry therefore sets itself three objectives, in this order.</p>
    <ol class="objectives">
      <li><strong>Find the next clusters.</strong> Bring families’ declared cases together across countries so that further clusters like those in France can be spotted, documented and handed to researchers, and research on causes can start again.</li>
      <li><strong>Keep existing registries alive.</strong> Offer the population-based registries that already record our conditions a place to preserve their limb-difference data and continuity should their funding fail.</li>
      <li><strong>Make registries talk to each other.</strong> Create the conditions for interoperability and portability of data between existing registries, and complete them where needed, so that new lines of research open.</li>
    </ol>

    <p>Three of the seven French registries already accept a declaration from the family itself, alongside the clinician’s. That is the door DysNet wants to widen: a family that declares from pregnancy onwards, in its own words, corrects what a retrospective enquiry years later can no longer reconstruct.</p>

    <p>The same conclusion was reached on the other side of the Atlantic. A Canadian workshop held in February 2024 found that the country has no national data source on limb loss and limb difference, agreed on five domains for building one, and looked to the amputee organisations themselves to carry it. Its authors describe what they call patient-powered registries, managed by patients and advocacy groups themselves. Our <a href="/knowledge/registries/">registries register</a> summarises that work and the American registry already running.</p>

    {opener("01", "Words matter", "What a registry is, and what this is.", toc="What a registry is")}
    <blockquote class="definition">
      <p>“A patient registry is an organized system that uses observational study methods to collect uniform data (clinical and other) to evaluate specified outcomes for a population defined by a particular disease, condition, or exposure, and that serves one or more predetermined scientific, clinical, or policy purposes.”</p>
      <footer>Definition of the Agency for Healthcare Research and Quality, as adopted by the European recommendations on rare-disease registries: Kodra Y, Weinbach J, Posada-de-la-Paz M, et al. <em>Int J Environ Res Public Health</em> 2018;15(8):1644. <a href="https://doi.org/10.3390/ijerph15081644" target="_blank" rel="noopener external">doi:10.3390/ijerph15081644</a></footer>
    </blockquote>
    <p>Measured against that definition, what DysNet is building is not a registry yet, and we would rather say so than borrow the word’s authority. Three gaps are real:</p>
    <ul>
      <li><strong>It is not exhaustive.</strong> A registry aims to capture every case in a defined population. Ours gathers the families who choose to take part through their associations; it will describe a community, not count a population.</li>
      <li><strong>No medical board, for now.</strong> Writing a research protocol and deciding which data are worth collecting are scientific acts. An association without a scientific committee is not equipped to perform them, and will not pretend to.</li>
      <li><strong>Declared data.</strong> What families report about themselves is precious and is not the same as clinician-verified data; the two must never be confused.</li>
    </ul>
    <p><strong>What this initiative is</strong>: a lasting engagement between families, their associations and research initiatives, so that when a study needs the limb-difference community, the community is organised, consenting and reachable, and its data are held in a form research can use. That engagement is worth building only to the highest degree of scientific method and quality: predefined purposes, uniform data, documented quality controls and a long-term perspective, the very recommendations of the European experts cited above. Earning the word “registry” is the roadmap: a scientific committee, a written protocol, an agreed minimum data set, and a published quality plan.</p>

    {opener("02", "The answer", "An international, patient-owned data infrastructure: a registry in the making.", toc="Where it stands")}
    <p>DysNet builds a data infrastructure that is international and interoperable by design, owned by the patient community itself, developed with member associations, and replicable for other rare conditions. We call it a registry for short; the section above says exactly how far that word applies today. It is the concrete answer to what DysNet membership returns to families: their data, working for their care. Once live, the registry will be declared in <a href="https://www.orpha.net/en/research-trials/registries" target="_blank" rel="noopener external">Orphanet’s European directory of rare-disease registries</a>, where researchers already look for data sources.</p>

    {opener("03", "How it works", "Patients hold the data; associations and the board steer the research.", toc="Who decides what")}
    <div class="grid cols-3">
      <div class="card acc-studies"><h3 class="h4">Families contribute</h3><p>Through their national association, on explicit consent, in their own language.</p></div>
      <div class="card acc-studies"><h3 class="h4">Control stays with the patient</h3><p>Each person holds their own data and decides what enters the registry. Which research may be proposed to families is a shared responsibility of the member associations and the DysNet board.</p></div>
      <div class="card acc-studies"><h3 class="h4">Research gets fuel</h3><p>Interoperable, comparable data across countries, at last.</p></div>
    </div>

    <p style="margin-top:var(--space-3)"><a class="btn btn-ghost" href="/knowledge/guides/patient-owned-registry/">New to the idea? The two-minute guide</a></p>

    {opener("04", "The partner", "Built with Health Data Safe.", toc="The technical partner")}
    <div class="partner-card">
      <a class="partner-logo" href="https://www.healthdatasafe.org/en/" target="_blank" rel="noopener external"><img src="/assets/img/hds-logo.svg" alt="Health Data Safe" width="1024" height="400"></a>
      <div>
        <p><strong>By decision of the DysNet Annual General Meeting of 26 August 2026, the registry is created with <a href="https://www.healthdatasafe.org/en/our-projects/" target="_blank" rel="noopener external">Health Data Safe</a> as its technical and operational partner.</strong></p>
        <p>Health Data Safe is a Swiss non-profit foundation that builds open-source infrastructure for people to gather, read and share their own health data, for their care and for research. It contributes its infrastructure to the DysNet registry in kind.</p>
      </div>
    </div>

    <div class="grid cols-3" style="margin-top:var(--space-3)">
      <div class="card acc-research">
        <h3 class="h4">The technology</h3>
        <p>Every person holds their own data account; nothing is pooled without a granular, revocable consent. The data model is built for interoperability and portability, so French and Italian records become one comparable registry. The stack runs today: Health Data Safe’s patient and clinician apps are published on the Apple and Google stores.</p>
      </div>
      <div class="card acc-library">
        <h3 class="h4">The regulation</h3>
        <p>Designed for the GDPR and the Swiss Federal Act on Data Protection, with a documented compliance programme (HIPAA-aligned procedures, workforce training register). The foundation’s statutes bind it: health data can never be bought or sold, and its use is limited to care and research.</p>
      </div>
      <div class="card acc-studies">
        <h3 class="h4">The trust</h3>
        <p>A non-profit with no commercial exit, whose purpose is written into its statutes, and a partner already in DysNet’s circle. Control of the data stays in the patient’s hands, and which research may be proposed to families is decided jointly by the member associations and the DysNet board.</p>
      </div>
    </div>

    <div class="tick"></div>
    <p class="eyebrow">The first pilots</p>
    <h2 data-toc="Why these two associations" class="h2">Why Assedea and Raggiungere launch the registry with Health Data Safe.</h2>
    <p>The two pilot associations, in France and Italy, carry the same duty towards their families: never let their data become a product. Their reasons for choosing Health Data Safe as the partner to launch the registry:</p>
    <ul>
      <li><strong>Ownership that is legally binding.</strong> The foundation’s statutes rule out any sale of health data and limit its use to care and research; that promise does not depend on goodwill.</li>
      <li><strong>Consent the family controls.</strong> Each person decides what enters the registry and can withdraw at any time, in their own language, under the GDPR rules both associations already work with.</li>
      <li><strong>No servers to run.</strong> Volunteer associations cannot operate health-data infrastructure; the technical and regulatory burden sits with a partner whose sole purpose is exactly that.</li>
      <li><strong>One registry, not two.</strong> Interoperable by design, so the French and Italian pilots feed a single dataset that research can finally use, and other member associations can join with the same tools.</li>
      <li><strong>A partner who knows the network.</strong> Health Data Safe already works alongside DysNet on the strategy that the AGM adopted, and brings its infrastructure in kind rather than as a commercial service.</li>
    </ul>

    {opener("05", "Progress", "The log.", toc="The log")}
    <div class="report"><p class="seat">Registry</p><h3 class="h4">The AGM votes to create the registry with Health Data Safe</h3><time datetime="2026-08-26">26 August 2026</time><p>The Annual General Meeting adopts the refocused strategy and mandates Health Data Safe as the registry’s technical and operational partner.</p></div>
    <div class="report"><p class="seat">Funding</p><h3 class="h4">Call for funding</h3><time datetime="2026-09">September 2026</time><p>EU rare-disease calls are being screened. The registry now seeks its first funders: research foundations, rare-disease prizes, and partners able to contribute hosting, development or translation in kind. <a href="mailto:info@dysnet.org?subject=Registry%20funding">Write to the board</a> or <a href="/donate/">support the registry directly</a>.</p></div>
  </div>
</section>

<section>
  <div class="sheet sheet-cta">
    <div class="tick" style="background:#4cc42c"></div>
    <p class="eyebrow">Take part</p>
    <h2 data-toc="Become a pilot" class="h2">Your association can be a pilot.</h2>
    <p>The registry grows association by association. Write to <a href="mailto:info@dysnet.org">info@dysnet.org</a> to join the first wave.</p>
  </div>
</section>
""",
}

# ─────────────────────────────── VOICE ────────────────────────────
# The five demands are held as data, not as markup: the accordion on /voice/ and
# the one-page briefing PDF are rendered from this one list, so they cannot drift.
# "progress" is the criterion a policy maker should leave with; "brief" is the ask
# in one sentence, for the PDF.
BRIEF_PDF = "/assets/dysnet-five-demands.pdf"

# What each level of evidence actually attracts from an authority, counted from the register
# itself so the table on /voice/ cannot drift from the register it cites.
def tera_evidence_table():
    levels = [("known", "Known", "human"), ("presumed", "Presumed", "animal"),
              ("suspected", "Suspected", "limited")]
    cols = [("approved", "Approved"), ("refused", "Refused"), ("cosmetics_banned", "Cosmetics"),
            ("banned_somewhere", "National bans"), ("eliminated", "Treaty")]
    rows = []
    for key, label, gloss in levels:
        E = [e for e in TERA.get("entries", []) if e.get("level") == key]
        n = {}
        for e in E:
            for d in e.get("decisions", []):
                n[d["verdict"]] = n.get(d["verdict"], 0) + 1
        lit = sum(1 for e in E if e.get("paper_count"))
        cells = "".join(f"<td>{n.get(c, 0)}</td>" for c, _ in cols)
        rows.append(f'<tr><th scope="row">{label}<br><span class="ev-gloss">{gloss} evidence</span></th>'
                    f'<td>{len(E)}</td>{cells}<td>{lit}</td></tr>')
    head = "".join(f"<th>{lab}</th>" for _, lab in cols)
    return ('<div class="annex-wrap"><table class="annex evidence-table">'
            f'<thead><tr><th>Evidence</th><th>Total</th>{head}<th>Literature</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            # the key sits outside the scrolling wrapper, or it slides sideways with the table
            '<p class="ev-key">Approved and refused: as an EU pesticide active substance. '
            'Cosmetics: banned from cosmetic products in the EU. National bans: banned or severely '
            'restricted by at least one country. Literature: substances with published research.</p>')


DEMANDS = [
    {
        "title": "Recognition of dysmelia as a public health priority, and access to quality healthcare for every family affected",
        "body": [
            "A child is born with a hand or an arm that stopped growing, and the parents ask one question first: where do we go now? The answer still depends on where they live — some families reach a team that has seen the condition before, others spend years moving between services that have not, explaining the condition to each new professional they meet.",
            'The World Health Organization counts congenital disorders among the leading causes of newborn death and lifelong disability, and the 2010 World Health Assembly resolution on birth defects asks every state to build registration and surveillance systems, to develop expertise in prevention and care, and to support affected families (<a href="https://www.who.int/news-room/fact-sheets/detail/birth-defects" target="_blank" rel="noopener external">WHO fact sheet on congenital disorders</a>). Limb differences are among the most visible of these disorders and among the least studied.',
            "We ask health authorities to name dysmelia in their rare-disease and disability plans, and to guarantee every child and adult a pathway to a competent team: diagnosis, surgery when useful, prosthetics, rehabilitation and psychological support, wherever the family lives.",
        ],
        "progress": "national pathways published, reference centres named, and waiting times measured.",
        "brief": "Name dysmelia in national rare-disease and disability plans, and guarantee every child and adult a pathway to a competent team: diagnosis, surgery when useful, prosthetics, rehabilitation and psychological support, wherever the family lives.",
        "cta": [],
    },
    {
        "title": "Universal coverage of prosthetics, research that reaches people with dysmelia, and an orphan medical devices framework that makes equipment affordable",
        "body": [
            "For many people with a limb difference, a prosthesis is what makes school, work, sport and everyday tasks possible. Coverage varies from full reimbursement to nothing at all, children outgrow devices that insurers replace too slowly, and the most advanced hands and arms are priced for a handful of users. Progress in robotics rarely reaches people with congenital differences, whose anatomy differs from that of amputees.",
            'Medicines for rare diseases enjoy orphan status: fee reductions, protocol assistance and market exclusivity that make small markets worth serving. Devices for small populations have no equivalent, so a prosthetic component designed for a few thousand people is often never built. Europe took a first step in June 2024: guidance <a href="https://health.ec.europa.eu/document/download/daa1fc59-9d2c-4e82-878e-d6fdf12ecd1a_en?filename=mdcg_2024-10_en.pdf" target="_blank" rel="noopener external">MDCG 2024-10</a> defines an orphan device as one intended for a condition affecting no more than 12,000 people a year in the EU and eases the clinical evidence expected. It is guidance, not law, and it brings no fee relief, no priority assessment and no exclusivity.',
            "We ask for coverage of a functional prosthesis for everyone who wants one, renewed at the pace of a growing child; for public research funding that names congenital limb difference; and for an orphan medical devices status in law, with fee relief and priority assessment, tied to transparent pricing and coverage of families’ out-of-pocket costs for the equipment they actually need, from a first passive hand to adapted bicycle or car controls.",
        ],
        "progress": "comparable reimbursement rules across countries, research calls that name our conditions, a legal definition and public register of orphan devices, and families’ remaining costs measured and falling.",
        "brief": "Cover a functional prosthesis for everyone who wants one, renewed at the pace of a growing child; fund research that names congenital limb difference; and write an orphan medical devices status into law, with fee relief and priority assessment.",
        "cta": [(BRIEF_PDF, "Take this to a regulator (PDF)"),
                ("mailto:info@dysnet.org?subject=Orphan%20medical%20devices", "Work with us on orphan devices")],
    },
    {
        "title": "Registries that cover whole populations, interoperability and portability of their data, and personal data returned to the people concerned",
        "body": [
            "Population registries of congenital anomalies cover a fraction of births, even in countries that run them well: in France about one birth in six. Clusters of limb agenesis have been found and then lost for want of comparable data across borders, and the causes, environmental or otherwise, remain unproven either way. Data held in one registry can only answer that region’s questions.",
            "We ask for registries that cover whole populations, that are funded to last, that are independent of any single interest, and that talk to each other across countries. We ask for interoperability: shared data models and common definitions, so that what one registry records can be read, compared and pooled by another, and so that aggregated data reach researchers without friction. We ask for portability: a registry must be able to move its data if its host disappears or its funding ends, and a family must be able to take its own record elsewhere. Any sharing of identifiable data must rest on the explicit, revocable consent of the person or family concerned.",
            'We ask, finally, that personal data be returned to the people it describes. Each person living with dysmelia, or their guardian, should hold a copy of their own record, see who has used it, and decide what happens to it next. Our own <a href="/registry/">associative registry</a> exists to add the families’ knowledge to this picture, not to replace it.',
        ],
        "progress": "coverage figures rising, cluster investigations that can compare notes internationally, common data models adopted, published access procedures, consent that families can see and change, and records that families can download and carry with them.",
        "brief": "Fund registries that cover whole populations, make them interoperable and portable across borders, and return to each person a copy of their own record, with consent they can see and change.",
        "cta": [],
    },
    {
        "title": "Research that looks for the causes of dysmelia, not only for how often it happens",
        "body": [
            "Counting tells us how many children are born with a limb difference. It does not tell us why, and families are asking why.",
            f'The evidence is neither complete nor conclusive. Our <a href="/knowledge/bibliography/">bibliography</a> holds {BIBSTAT["total"]:,} references, {BIBSTAT["teratogens"]} of them on a substance or an exposure in pregnancy, and thalidomide accounts for {BIBSTAT["thalidomide"]} on its own: the one cause that was identified, sixty years ago. Our <a href="/knowledge/teratogens/">teratogens register</a> can point a family to published research for {TERA.get("counts", {}).get("papers_substances", 0)} of its {TERA.get("counts", {}).get("total", 0)} substances and finds none for the other {TERA.get("counts", {}).get("total", 0) - TERA.get("counts", {}).get("papers_substances", 0)}, among them {sum(1 for e in TERA.get("entries", []) if e.get("level") == "known" and not e.get("paper_count"))} that an authority has already classified on human evidence. The table under demand 5 shows the same gap level by level.',
            'Where the research does exist, it does not close the question. Across large birth-defect cohorts a cause is identified in roughly one case in five, and for an isolated difference of a single limb it is usually none, as our review <a href="/knowledge/causes-of-dysmelia/">Causes of dysmelia</a> sets out. That figure is the demand, in one number.',
            "So there are two gaps, and they need different answers: substances no one has studied, and a literature that accumulates association and toxicology without closing a hypothesis. We ask for funded programmes whose object is causation: exposure histories collected from pregnancy onwards and linked to registry records, standing protocols for investigating clusters rather than committees improvised after each alert, toxicological work on the substances already suspected and on those nobody has examined, and the publication of negative results so that a hypothesis can be closed honestly. Epidemiology is necessary and we defend it. It is not sufficient.",
        ],
        "progress": "calls for proposals that name the causes of congenital limb anomalies as their subject, published research for every substance the register lists, and the share of cases with an identified cause rising above one in five.",
        "brief": "Fund research whose object is causation, not only frequency: exposure histories linked to registry records, standing protocols for investigating clusters, toxicology on the substances already suspected and on those nobody has examined, and the publication of negative results. The evidence today is neither complete nor conclusive: no published research for a third of the substances our register lists, and a cause identified in about one case in five.",
        "cta": [],
    },
    {
        "title": "Precaution first: science-based information and enforceable rules on products with suspected, potential or proven teratogenic effects",
        "body": [
            "Thalidomide taught the lesson once: a product reached pregnant women before its effect on the unborn child was known, and thousands of children were born with limb differences. Families still learn about suspected teratogens after the fact, from a news report or a cluster investigation, rather than from a label or from the authority in charge.",
            "We ask governments to apply the precautionary principle to substances with suspected, potential or proven teratogenic effects, on the basis of the science available and updated as it evolves: clear information to families and health professionals, and enforceable obligations for food suppliers, the construction and building sector and product manufacturers, so that exposure during pregnancy is prevented rather than discovered afterwards.",
            'No authority publishes such a list today; our <a href="/knowledge/teratogens/">teratogens register</a> gathers what the EU, California, Japan and the medicines agencies each list separately, with the legal status of every substance and the decisions authorities have taken about it.',
            "The list is needed at two levels, because neither works alone. The World Health Organization should keep one global reference list of substances of concern: that is what makes a substance recognisable in every country and keeps a family&rsquo;s answer the same wherever they live. The WHO binds no one, so each state should keep its own register with legal force, and publish, for every product it approves or forbids, the evidence and the reasoning behind the decision. A decision that cannot be read cannot be checked. Where an authority approves a substance its own classification calls harmful to the unborn child, families are entitled to read why, which interests were heard, and what would change the answer.",
            "Our register shows how unevenly this is done:",
            "__EVIDENCE_TABLE__",
            "No substance with human evidence is approved as a pesticide in the EU; 21 of the 26 approvals rest on the weakest evidence. That is lawful, since category 2 is not excluded from approval. It is also where the reasoning should be published rather than inferred.",
        ],
        "progress": "one WHO reference list of substances of concern, a national register in each state with legal force and published reasons, mandatory labelling and disclosure, and inspections with consequences.",
        "brief": "Apply the precautionary principle to substances with suspected, potential or proven teratogenic effects. The list is needed at two levels: one WHO reference list, so a substance is recognisable across borders, and a register in each state with legal force, publishing the evidence and the reasoning behind every approval and every prohibition. With it, clear information to families and professionals, and enforceable obligations on food suppliers, the construction sector and product manufacturers.",
        "cta": [("/knowledge/teratogens/", "Open the teratogens register"),
                (BRIEF_PDF, "Take this to a regulator (PDF)")],
    },
]


def demands_html():
    items = []
    for i, d in enumerate(DEMANDS, 1):
        paras = "".join(tera_evidence_table() if p == "__EVIDENCE_TABLE__" else f"<p>{p}</p>" for p in d["body"])
        cta = ("".join(f'<a class="btn btn-sm btn-ghost" href="{href}">{label}</a>' for href, label in d["cta"]))
        cta = f'<p class="demand-cta">{cta}</p>' if cta else ""
        items.append(
            f'<li id="demand-{i}"><details><summary><span class="demand-n">{i}</span><span>{d["title"]}</span></summary>\n'
            f'        <div class="demand-body">{paras}'
            f'<p class="progress"><span>Progress looks like</span>{d["progress"]}</p>{cta}'
            f"</div></details></li>")
    return '<ol class="demands">\n      ' + "\n      ".join(items) + "\n    </ol>"


# ── The one-page briefing, for delegates to hand over in a meeting ──
# Rendered from DEMANDS with ReportLab at build time, so the PDF and the page
# on /voice/ always carry the same five demands and the same progress criteria.
BRIEF_LEDE = ("Dysmelia is a congenital limb difference. DysNet is the network of the associations that "
              "represent the families concerned, and it carries these five demands into every body where "
              "it holds a seat: EURORDIS, the European Disability Forum, ERN BOND and the European "
              "Economic and Social Committee. Each demand states what we ask of public authorities, and "
              "what would count as progress.")


def build_brief_pdf():
    """Write docs/assets/dysnet-five-demands.pdf — the five demands as a one-page policy brief."""
    import hashlib
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether,
                                    PageTemplate, Paragraph, Spacer, Table, TableStyle)

    out = ROOT / "assets" / "dysnet-five-demands.pdf"
    logo = ROOT / "assets" / "img" / "dysnet-logo.png"
    digest = hashlib.sha1(repr([(d["title"], d["brief"], d["progress"]) for d in DEMANDS]
                               + [BRIEF_LEDE, SITE]).encode("utf-8")).hexdigest()
    # The digest rides in the PDF's own metadata, so no stamp file is published.
    if out.exists() and digest.encode() in out.read_bytes():
        return "briefing PDF unchanged"

    INK, MUTED = colors.HexColor("#241a33"), colors.HexColor("#5d5470")
    PURPLE, PTEXT, PDEEP, PSOFT = (colors.HexColor("#9333ea"), colors.HexColor("#7222c2"),
                                   colors.HexColor("#47156e"), colors.HexColor("#f3e8fd"))
    F, FB = "Helvetica", "Helvetica-Bold"

    def st(name, **kw):
        base = dict(fontName=F, fontSize=8.6, leading=11.6, textColor=INK, spaceAfter=0)
        base.update(kw)
        return ParagraphStyle(name, **base)

    s_kicker = st("kicker", fontName=FB, fontSize=7.4, leading=10, textColor=PTEXT)
    s_title = st("title", fontName=FB, fontSize=18.5, leading=20, textColor=PDEEP, spaceAfter=2)
    s_lede = st("lede", fontSize=8.4, leading=11.2, textColor=MUTED, alignment=TA_JUSTIFY)
    s_h2 = st("h2", fontName=FB, fontSize=9.8, leading=12, spaceAfter=2.4)
    s_body = st("body", alignment=TA_JUSTIFY)
    s_prog = st("prog", fontSize=8.4, leading=11.2)
    s_act = st("act", fontSize=8.4, leading=11.2, textColor=colors.white)
    s_foot = st("foot", fontSize=7.6, leading=9.8, textColor=MUTED)

    class Dot(Flowable):
        """The numbered purple disc, as on the web page."""
        def __init__(self, n, d=8.4 * mm):
            super().__init__()
            self.n, self.d = n, d
        def wrap(self, *_):
            return self.d, self.d
        def draw(self):
            c = self.canv
            c.setFillColor(PDEEP)
            c.circle(self.d / 2, self.d / 2, self.d / 2, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont(FB, 11)
            c.drawCentredString(self.d / 2, self.d / 2 - 3.9, str(self.n))

    doc = BaseDocTemplate(str(out), pagesize=A4,
                          leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=15 * mm,
                          title="DysNet — five demands for people with dysmelia",
                          author="DysNet", subject="Policy briefing", keywords=[digest])
    width = doc.width

    def furniture(canv, _doc):
        canv.saveState()
        y = 11 * mm
        canv.setStrokeColor(PDEEP)
        canv.setLineWidth(2.2)
        canv.line(doc.leftMargin, y, doc.leftMargin + width, y)
        canv.setFont(F, 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(doc.leftMargin, y - 4.6 * mm, "The full reasoning, with sources: " + SITE.split("//")[-1] + "/voice/")
        canv.drawRightString(doc.leftMargin + width, y - 4.6 * mm, "DysNet Ideell Förening · info@dysnet.org")
        canv.restoreState()

    doc.addPageTemplates([PageTemplate(id="brief", frames=[
        Frame(doc.leftMargin, doc.bottomMargin, width, doc.height, leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0)], onPage=furniture)])

    lede_cell = [Paragraph("Policy briefing · Mission 3 · The voice of families", s_kicker),
                 Spacer(1, 1.6 * mm),
                 Paragraph("Five demands for people with dysmelia", s_title),
                 Spacer(1, 1.2 * mm),
                 Paragraph(BRIEF_LEDE, s_lede)]
    logo_w = 29 * mm
    head_left = Image(str(logo), width=logo_w, height=logo_w * 176 / 269) if logo.exists() else Spacer(1, 1)
    story = [Spacer(1, 1 * mm), Table([[head_left, lede_cell]], colWidths=[logo_w + 8 * mm, width - logo_w - 8 * mm],
                   style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                     ("RIGHTPADDING", (0, 0), (0, 0), 8 * mm),
                                     ("RIGHTPADDING", (1, 0), (1, 0), 0),
                                     ("TOPPADDING", (0, 0), (-1, -1), 0),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
                                     ("LINEBELOW", (0, 0), (-1, -1), 2.2, PDEEP)])),
             Spacer(1, 4.2 * mm)]

    body_w = width - 12.6 * mm
    for i, d in enumerate(DEMANDS, 1):
        prog = Table([[Paragraph(f'<font name="{FB}" size="7.4" color="#7222c2">PROGRESS LOOKS LIKE</font>  '
                                 + d["progress"], s_prog)]], colWidths=[body_w],
                     style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PSOFT),
                                       ("LINEBEFORE", (0, 0), (0, -1), 2.4, PURPLE),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 2.6 * mm),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 2.6 * mm),
                                       ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm)]))
        row = Table([[Dot(i), [Paragraph(d["title"], s_h2), Paragraph(d["brief"], s_body),
                               Spacer(1, 1.9 * mm), prog]]],
                    colWidths=[12.6 * mm, body_w],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                      ("TOPPADDING", (0, 0), (-1, -1), 0),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        story.append(KeepTogether(row))
        if i < len(DEMANDS):
            story += [Spacer(1, 2.4 * mm),
                      Table([[""]], colWidths=[width], rowHeights=[0.4],
                            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e6dcf2"))])),
                      Spacer(1, 2.4 * mm)]

    act = [Paragraph('<font name="%s" size="9.6" color="#ffffff">What you can do</font>' % FB, s_act),
           Spacer(1, 1.4 * mm),
           Paragraph("Name one of these five demands in your next meeting, consultation response or "
                     "national plan, and tell us which: we will send the evidence behind it.", s_act),
           Spacer(1, 1 * mm),
           Paragraph("The registers that support these demands are public and free to cite — teratogens, "
                     "care centres, population registries and our bibliography, at "
                     + SITE.split("//")[-1] + "/knowledge/. Write to info@dysnet.org.", s_act)]
    story += [Spacer(1, 3.6 * mm),
              Table([[act]], colWidths=[width],
                    style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PDEEP),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                                      ("TOPPADDING", (0, 0), (-1, -1), 3.6 * mm),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3.8 * mm)]))]

    doc.build(story)
    pages = out.read_bytes().count(b"/Type /Page\n") or out.read_bytes().count(b"/Type /Page")
    return f"briefing PDF rebuilt ({out.stat().st_size // 1024} kB, {pages} page{'s' if pages != 1 else ''})"


# ── The pilot brief ──────────────────────────────────────────────────────────
# The registry page told an interested association to write and ask what a pilot involves,
# which cost every one of them a round trip and gave their board nothing to read. This is
# that answer, laid out as a board paper: what you give, what you get, what it costs, the
# questions a treasurer asks, and the things we are careful not to claim.
PILOT_GIVE = [
    ("A point of contact", "One person who answers our mail and carries the pilot inside your association. Not a project team."),
    ("Your language", "Help turning the questions into the words your families actually use, so an Italian record and a French one mean the same thing."),
    ("An invitation, not a list", "You invite your families. Nobody is entered by their association, and we never ask you for your membership file."),
    ("Patience with a first version", "A pilot exists to be corrected. We would rather you told us the questions are wrong than watched you answer them anyway."),
]
PILOT_GET = [
    ("The figures for your own country", "Most associations have never had them. You would be able to say how many, where, and with what care, and say it with a source."),
    ("A seat on the research question", "Which studies may be put to your families at all is decided by the member associations and the DysNet board together, not by whoever asks first."),
    ("Data your families own", "Each person holds their own account and decides what enters the registry. Your relationship with them is not mediated by us."),
    ("An infrastructure you do not run", "No servers, no hosting contract, no data protection officer to recruit. That burden sits with the technical partner."),
]
PILOT_QA = [
    ("Who owns the data?",
     "The person described by it. Not DysNet, not your association, and not the technical partner. Each person holds their own "
     "account, decides what enters the registry, and can withdraw."),
    ("What does it cost us?",
     "No licence fee and no charge per family. Health Data Safe contributes its infrastructure in kind rather than as a "
     "commercial service. The real cost is volunteer time: a contact, the translation, and the invitations."),
    ("Do we hand over our member list?",
     "No. We never ask for it. Families are invited by you and enter their own information themselves, which is also why the "
     "registry describes a community rather than counting a population."),
    ("What if a family changes its mind?",
     "Consent is given study by study and can be withdrawn at any time, in the family's own language, under the GDPR rules "
     "your association already works with."),
    ("What if Health Data Safe disappears?",
     "Its statutes provide that personal data is never treated as an asset of the foundation, and that on dissolution the data "
     "is destroyed or moved to a service offering similar guarantees. The data model is built for portability for the same reason."),
    ("Does this compete with our national registry?",
     "No. Population registries count a catchment area from the clinical side. This records what families declare, from "
     "pregnancy onwards, including the people who never reach a catchment area at all."),
]
PILOT_STEPS = [
    ("One call", "We show you the questions, and what a single record actually looks like. Nothing is signed."),
    ("The questions in your language", "You correct the wording until it matches how your families speak about themselves."),
    ("A handful of families, not a launch", "You invite a small group. A pilot is meant to find what is wrong while it is still cheap to change."),
    ("Each family opens its own account", "They decide what goes in, and they consent, or they do not. You are not asked to vouch for anyone."),
    ("Your country's figures come back to you", "The first thing a pilot produces is a picture of your own membership that you did not have before."),
    ("Then it becomes findable", "Once live, the registry is declared in Orphanet's European directory of rare-disease registries, where researchers already look."),
]
PILOT_CAREFUL = [
    "It is not exhaustive. A registry aims at every case in a defined population; ours gathers the families who choose to take part.",
    "There is no medical board yet. Writing a protocol and choosing what is worth collecting are scientific acts, and an association without a scientific committee will not pretend to perform them.",
    "Declared data is not clinician-verified data. What families report about themselves is precious, and the two must never be confused.",
]


def build_pilot_pdf():
    """Write docs/assets/dysnet-registry-pilot.pdf — the two-page brief an association can hand its board."""
    import hashlib
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate,
                                    Paragraph, Spacer, Table, TableStyle)

    out = ROOT / "assets" / "dysnet-registry-pilot.pdf"
    logo = ROOT / "assets" / "img" / "dysnet-logo.png"
    digest = hashlib.sha1(repr([PILOT_GIVE, PILOT_GET, PILOT_QA, PILOT_CAREFUL, PILOT_STEPS,
                                len(BIB.get("entries", [])), TERA.get("counts", {}).get("total", 0)]).encode("utf-8")).hexdigest()
    if out.exists() and digest.encode() in out.read_bytes():
        return "pilot brief unchanged"

    INK, MUTED = colors.HexColor("#241a33"), colors.HexColor("#5d5470")
    GREEN, GTEXT, GDEEP, GSOFT = (colors.HexColor("#16a34a"), colors.HexColor("#15803d"),
                                  colors.HexColor("#14532d"), colors.HexColor("#eafaf0"))
    F, FB = "Helvetica", "Helvetica-Bold"

    def st(name, **kw):
        base = dict(fontName=F, fontSize=8.5, leading=11.3, textColor=INK, spaceAfter=0)
        base.update(kw)
        return ParagraphStyle(name, **base)

    s_kick = st("kick", fontName=FB, fontSize=7.4, leading=10, textColor=GTEXT)
    s_title = st("title", fontName=FB, fontSize=17.5, leading=19.5, textColor=GDEEP, spaceAfter=2)
    s_lede = st("lede", fontSize=8.4, leading=11.2, textColor=MUTED, alignment=TA_JUSTIFY)
    s_sec = st("sec", fontName=FB, fontSize=10.4, leading=12.6, textColor=GDEEP, spaceAfter=2.6)
    s_h = st("h", fontName=FB, fontSize=8.6, leading=11)
    s_body = st("body", alignment=TA_JUSTIFY)
    s_small = st("small", fontSize=7.9, leading=10.4, textColor=MUTED)
    s_white = st("white", fontSize=8.5, leading=11.4, textColor=colors.white)

    doc = BaseDocTemplate(str(out), pagesize=A4,
                          leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=15 * mm,
                          title="DysNet — what a registry pilot involves for your association",
                          author="DysNet", subject="Registry pilot brief", keywords=[digest])
    width = doc.width

    def furniture(canv, docu):
        canv.saveState()
        y = 11 * mm
        canv.setStrokeColor(GDEEP)
        canv.setLineWidth(2.2)
        canv.line(docu.leftMargin, y, docu.leftMargin + width, y)
        canv.setFont(F, 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(docu.leftMargin, y - 4.6 * mm, "The full detail, with sources: " + SITE.split("//")[-1] + "/registry/")
        canv.drawRightString(docu.leftMargin + width, y - 4.6 * mm,
                             "DysNet Ideell Förening · info@dysnet.org · page %d of 2" % canv.getPageNumber())
        canv.restoreState()

    doc.addPageTemplates([PageTemplate(id="pilot", frames=[
        Frame(doc.leftMargin, doc.bottomMargin, width, doc.height, leftPadding=0, rightPadding=0,
              topPadding=0, bottomPadding=0)], onPage=furniture)])

    def pairs(items, cols=2):
        """Two columns of heading-and-text, as on the web page."""
        cw = (width - 5 * mm) / cols
        rows, row = [], []
        for h, t in items:
            row.append([Paragraph(h, s_h), Spacer(1, 0.8 * mm), Paragraph(t, s_body)])
            if len(row) == cols:
                rows.append(row); row = []
        if row:
            row += [""] * (cols - len(row)); rows.append(row)
        return Table(rows, colWidths=[cw] * cols,
                     style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                                       ("TOPPADDING", (0, 0), (-1, -1), 0),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4 * mm)]))

    head = [Paragraph("Registry pilot · Mission 2 · A paper for your board", s_kick),
            Spacer(1, 1.6 * mm),
            Paragraph("What a registry pilot involves for your association", s_title),
            Spacer(1, 1.2 * mm),
            Paragraph("DysNet is building the first international registry of limb malformations owned by the people it "
                      "describes. The Annual General Meeting of 26 August 2026 created it and mandated Health Data Safe, a Swiss "
                      "non-profit foundation, as its technical and operational partner. Assedea in France and Raggiungere in Italy "
                      "launch it. This paper answers, without a meeting, what taking part would ask of your association.", s_lede)]
    logo_w = 29 * mm
    head_left = Image(str(logo), width=logo_w, height=logo_w * 176 / 269) if logo.exists() else Spacer(1, 1)
    story = [Table([[head_left, head]], colWidths=[logo_w + 8 * mm, width - logo_w - 8 * mm],
                   style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                     ("RIGHTPADDING", (0, 0), (0, 0), 8 * mm),
                                     ("RIGHTPADDING", (1, 0), (1, 0), 0),
                                     ("TOPPADDING", (0, 0), (-1, -1), 0),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
                                     ("LINEBELOW", (0, 0), (-1, -1), 2.2, GDEEP)])),
             Spacer(1, 4 * mm)]

    why = Table([[[Paragraph('<font name="%s" size="8.6" color="#14532d">Why a registry, and why now</font>' % FB, s_body),
                   Spacer(1, 1.2 * mm),
                   Paragraph("Between 2007 and 2014 three clusters of transverse upper-limb agenesis came to light in France, in "
                             "Loire-Atlantique, Ain and Morbihan. The investigations found no common exposure, and they met the "
                             "limit of any retrospective enquiry: families were questioned years after the birth, from memory. "
                             "Families who record circumstances and exposures as they happen, from pregnancy onwards, give the "
                             "next investigation what the last one lacked. No registry at national or European level is dedicated "
                             "to limb anomalies.", s_body)]]],
                colWidths=[width],
                style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), GSOFT),
                                  ("LINEBEFORE", (0, 0), (0, -1), 2.4, GREEN),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 3.4 * mm),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 3.4 * mm),
                                  ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6 * mm)]))
    story += [why, Spacer(1, 4.4 * mm),
              Paragraph("What your association gives", s_sec), pairs(PILOT_GIVE), Spacer(1, 1.6 * mm),
              Paragraph("What your association gets", s_sec), pairs(PILOT_GET)]

    story += [Paragraph("The questions your board will ask", s_sec)]
    for q, a in PILOT_QA:
        story.append(KeepTogether([Paragraph(q, s_h), Spacer(1, 0.7 * mm), Paragraph(a, s_body), Spacer(1, 2.6 * mm)]))

    steps = [Paragraph("How a pilot runs", s_sec)]
    for i, (h, t) in enumerate(PILOT_STEPS, 1):
        steps.append(Table([[Paragraph('<font name="%s" color="#15803d">%d</font>' % (FB, i), s_h),
                             [Paragraph(h, s_h), Spacer(1, 0.6 * mm), Paragraph(t, s_body)]]],
                           colWidths=[6 * mm, width - 6 * mm],
                           style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                             ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                             ("TOPPADDING", (0, 0), (-1, -1), 0),
                                             ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm)])))
    story.append(KeepTogether(steps))

    stands = [[Paragraph('<font name="%s" size="8.6" color="#14532d">Where it stands today</font>' % FB, s_body),
               Spacer(1, 1.2 * mm),
               Paragraph("<b>26 August 2026.</b> The Annual General Meeting adopted the refocused strategy, created the registry "
                         "and mandated Health Data Safe as its technical and operational partner.", s_body),
               Spacer(1, 1 * mm),
               Paragraph("<b>September 2026.</b> European rare-disease calls are being screened, and the registry is seeking its "
                         "first funders. Assedea and Raggiungere carry the two launch pilots.", s_body)]]
    story += [Spacer(1, 1.6 * mm),
              Table([stands], colWidths=[width],
                    style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), GSOFT),
                                      ("LINEBEFORE", (0, 0), (0, -1), 2.4, GREEN),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 3.4 * mm),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 3.4 * mm),
                                      ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6 * mm)])),
              Spacer(1, 4 * mm)]

    careful = [Paragraph("What we are careful not to claim", s_sec),
               Paragraph("Measured against the definition of a patient registry adopted by the European recommendations on "
                         "rare-disease registries, what we are building is not yet a registry, and we would rather say so than "
                         "borrow the word's authority.", s_small), Spacer(1, 1.8 * mm)]
    for line in PILOT_CAREFUL:
        careful += [Paragraph("\u2022  " + line, s_small), Spacer(1, 1.2 * mm)]
    careful += [Spacer(1, 1.2 * mm),
                Paragraph("Earning the word is the roadmap: a scientific committee, a written protocol, an agreed minimum data "
                          "set and a published quality plan.", s_small)]
    story.append(KeepTogether(careful))

    act = [Paragraph('<font name="%s" size="9.6" color="#ffffff">What we are asking of you</font>' % FB, s_white),
           Spacer(1, 1.4 * mm),
           Paragraph("Tell us whether your board wants a conversation. A pilot starts with one call, a look at the questions in "
                     "your language, and a date. Write to info@dysnet.org with the word <b>pilot</b> in the subject line.", s_white),
           Spacer(1, 1.2 * mm),
           Paragraph("While you decide, everything else we maintain is already free to use: a bibliography of %s references, a "
                     "teratogens register of %s substances with the decisions authorities have taken on them, the care centres, "
                     "the researcher register and the epidemiology tables, at %s/knowledge/."
                     % (format(len(BIB.get("entries", [])), ","), TERA.get("counts", {}).get("total", 0),
                        SITE.split("//")[-1]), s_white)]
    story += [Spacer(1, 4 * mm),
              Table([[act]], colWidths=[width],
                    style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), GDEEP),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                                      ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                                      ("TOPPADDING", (0, 0), (-1, -1), 3.6 * mm),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3.8 * mm)]))]

    doc.build(story)
    raw = out.read_bytes()
    pages = raw.count(b"/Type /Page\n") or raw.count(b"/Type /Page")
    return f"pilot brief rebuilt ({out.stat().st_size // 1024} kB, {pages} pages)"


# ── Delegate reports ────────────────────────────────────────────────────────
# The feed lives here rather than inside the page, because /voice/ shows the three most
# recent entries and the only way to keep the two in step is to have one source. The
# teaser below reads this markup instead of a second list that would drift from it.
REPORTS_FEED = """    <div style="margin-top:var(--space-4)">
      <article class="report" id="edpd-2026">
        <p class="seat">European Disability Forum · European Day of Persons with Disabilities, Brussels</p>
        <h2 class="h3">DysNet is invited to Brussels to talk about living and working across borders</h2>
        <time datetime="2026-12-03">3 and 4 December 2026</time>
        <p>Places in the room at the European Day of Persons with Disabilities go by invitation, and DysNet, which
        <a href="#edpd-2024">took part in 2024</a>, has been invited again to the 2026 edition. Its theme is &ldquo;Travelling, living and working across borders: fair mobility and equal protection&rdquo;,
        and for two days it brings the European institutions together with disability organisations from across the Union to share
        knowledge, talks and ideas. The European Commission&rsquo;s Directorate-General for Justice and Consumers opens and closes it.</p>
        <p>The first day asks whether the assessment of a disability is a starting block or a hurdle, and how social protection and
        social security can follow a disabled person who moves from one member state to another. The second brings the Access City
        Award, for the cities doing most to make urban life accessible, and a panel on barrier-free transport and passengers&rsquo;
        rights. The theme meets two threads DysNet already follows: the European Disability Card, and the comparison of what each
        country actually provides. The sessions are streamed, and anyone can register for the livestream on the Forum&rsquo;s page.</p>
        <p class="src">European Disability Forum ·
        <a href="https://www.edf-feph.org/events-slug/european-day-of-persons-with-disabilities-2026/" target="_blank" rel="noopener external">European Day of Persons with Disabilities 2026 ↗</a></p>
      </article>
      <article class="report" id="ix-commissione-2026">
        <p class="seat">Regione Lombardia · IX Commission of the Regional Council</p>
        <h2 class="h3">The biorobotics conference goes before the Regional Council</h2>
        <time datetime="2026-10-08">8 October 2026 · Claudio Pirola</time>
        <p>After the <a href="#biorobotics-palazzo-pirelli">conference on biorobotics</a> that DysNet organised at Palazzo Pirelli
        on 26 March, DysNet asked the Regional Council of Lombardy to hear what it had produced. The Council&rsquo;s IX Commission,
        on social sustainability, housing and the family, has invited it to a hearing on Thursday 8 October at 16:00, at the
        Council&rsquo;s seat in Via Filzi, Milan, with a remote link for those who cannot come in person.</p>
        <p>A regional councillor carried the request to the Commission and opens the hearing. Claudio Pirola, DysNet&rsquo;s
        chairman, then sets out why DysNet promoted the March conference, and the conference&rsquo;s speakers follow with short
        contributions on assistive devices, on biorobotics and on the <em>Nomenclatore Tariffario</em>, the national list that sets
        which prostheses and assistive devices the Italian health service pays for. It is the step from a conference to the
        institution that can act on what it heard.</p>
      </article>
      <article class="report">
        <p class="seat">Cerebral Palsy EU</p>
        <h2 class="h3">Advocacy skills webinar</h2>
        <time datetime="2026-06-22">22 June 2026 · Claudio Pirola</time>
        <p>Practical training on advocacy techniques, shared onward to all member associations; directly useful for national reimbursement campaigns.</p>
      </article>
      <article class="report">
        <p class="seat">VOICE4ALL</p>
        <h2 class="h3">New EU project on autonomous voting starts</h2>
        <time datetime="2026-05">May 2026 · Claudio Pirola</time>
        <p>Following Vote4All (study visits to the Parliaments of The Hague and Lisbon, dialogue with the Dutch Ministry of the Interior, the Municipality of Milan, the Portuguese Parliament and the mayors of Lisbon and Porto), DysNet joins the successor project: webinars and in-person workshops across the EU.</p>
      </article>
      <article class="report" id="biorobotics-palazzo-pirelli">
        <p class="seat">DysNet event · Regione Lombardia</p>
        <h2 class="h3">Biorobotics conference at Palazzo Pirelli</h2>
        <time datetime="2026-03-26">26 March 2026 · Claudio Pirola</time>
        <p>DysNet organised a conference on biorobotics for persons with disability at the seat of Regione Lombardia in Milan: university professors and researchers, prosthetics producers and association representatives. The follow-up is <a href="#ix-commissione-2026">a hearing before the Regional Council&rsquo;s IX Commission</a> on 8 October 2026.</p>
        <p>Artificial intelligence was raised there too. DysNet is a member of the European Disability Forum and has followed
        <a href="https://www.edf-feph.org/artificial-intelligence/" target="_blank" rel="noopener external">its work on AI</a> over the
        last few years, where the Forum argues in Brussels that these systems must be designed and used inclusively, and follows the
        European Union’s AI Act on behalf of disabled people.</p>
        <p>That thread continues on 28 November 2026, at a meeting DysNet is organising with a foundation linked to Intesa Sanpaolo,
        which the Forum will join. The question it puts is a practical one: how far does artificial intelligence already help persons
        with disability do their daily work? Details follow before the date.</p>
      </article>
      <article class="report">
        <p class="seat">EURORDIS · <a href="https://www.eurordis.org/social-policy-action-group/" target="_blank" rel="noopener external">Social Policy Action Group</a></p>
        <h2 class="h3">Independent living: what one country already does, another can copy</h2>
        <time datetime="2026-02">February 2026 · Claudio Pirola</time>
        <p>DysNet is a member of the group, and contributed to its work on independent living by submitting the laws already in force in several
        countries, so that a provision that works in one place can be argued for in another. The comparison is long work, and it
        continues with the full support of EURORDIS.</p>
      </article>
      <article class="report">
        <p class="seat">ERN BOND · patient advocacy group</p>
        <h2 class="h3">Comparing what each country provides, and carrying the Patient Journey</h2>
        <time datetime="2026-02">February 2026 · Claudio Pirola</time>
        <p>In the European Reference Network for rare bone diseases, DysNet is comparing what different European countries
        actually provide, and takes that comparison to the next meeting in Leiden. DysNet promotes the Patient Journey inside the
        network: <a href="/knowledge/ongoing-studies/#patient-journey">a study in five steps</a> that follows patients, their
        families, their doctors and researchers through one shared questionnaire, so that a family receives updated medical and
        scientific knowledge rather than having to hunt for it.</p>
      </article>
      <article class="report">
        <p class="seat">European Disability Forum · General Assembly, Ljubljana</p>
        <h2 class="h3">What the assembly taught us, Milan asked us to come and say</h2>
        <time datetime="2026-02">February 2026 · Claudio Pirola</time>
        <p>At the Forum&rsquo;s general assembly in Ljubljana, as at Vilnius, DysNet followed the European Disability Card and its
        perspective to 2027, artificial intelligence, accessibility and transport, and above all assistive technology for
        employment. That knowledge makes the network an active partner in the same discussions at national level: the Municipality
        of Milan invited DysNet to lecture at Milan Civil Week, and has asked it to come back with a focus on jobs for disabled
        people.</p>
      </article>
      <article class="report">
        <p class="seat">European Economic and Social Committee</p>
        <h2 class="h3">Contacts opened with the EESC</h2>
        <time datetime="2026-02">February 2026 · Claudio Pirola</time>
        <p>Contacts with the Committee give the network a reading of where European policy is heading at a moment when much is
        changing worldwide, which is what a small organisation needs before it decides where to spend its voice.</p>
      </article>
      <article class="report">
        <p class="seat">EURORDIS · Rare Barometer</p>
        <h2 class="h3">Writing the questions, and translating them</h2>
        <time datetime="2026-02">February 2026 · Claudio Pirola</time>
        <p>DysNet took part in the Rare Barometer programme with contributions to the content of the surveys and with translations,
        so that families who do not read English can answer in their own language. You can
        <a href="/knowledge/resources/#rare-barometer">take part in the current surveys</a> from our resources page.</p>
      </article>
      <article class="report">
        <p class="seat">Sport · Milano-Cortina 2026</p>
        <h2 class="h3">Disability and sport around the Winter Games</h2>
        <time datetime="2026-02">February 2026 · Claudio Pirola</time>
        <p>Milan co-hosted the 2026 Olympic and Paralympic Winter Games with Cortina d&rsquo;Ampezzo. The Paralympic Winter Games
        opened in the Arena di Verona on 6 March 2026 and closed on 15 March in the Cortina curling stadium built for the Games of
        1956: around 665 athletes, 79 medal events and six sports, fifty years after the first Paralympic Winter Games and twenty
        after Torino 2006.<sup class="fn"><a href="#games-src">1</a></sup> In February the chairman reported a growing involvement
        in those Games and structured contacts with the Municipality of Milan on disability and sport, with an event on the subject
        among the plans. DysNet had already argued the case in the city a year earlier, at the first
        <a href="#vote4all-milan">Vote4All study visit</a>, where much of the programme turned on sport as a way into public life.</p>
        <p class="src" id="games-src">International Paralympic Committee ·
        <a href="https://www.paralympic.org/milano-cortina-2026/about" target="_blank" rel="noopener external">About the Milano Cortina 2026 Paralympic Winter Games ↗</a></p>
      </article>
      <article class="report">
        <p class="seat">EURORDIS</p>
        <h2 class="h3">European Regional Task Force on Rare Diseases</h2>
        <time datetime="2026">2026 · Claudio Pirola</time>
        <p>DysNet participates in the task force created by EURORDIS with Rare Diseases International, supporting the WHO European region’s implementation of the World Health Assembly resolution on rare diseases.</p>
      </article>
      <article class="report">
        <p class="seat">EDF</p>
        <h2 class="h3">General Assembly, Vilnius</h2>
        <time datetime="2025-06-28">28 June 2025 · Claudio Pirola</time>
        <p>EU Disability Card perspectives to 2027, AI and disability, assistive technology for employment, accessibility and transport.</p>
      </article>
      <article class="report" id="vote4all-milan">
        <p class="seat">Vote4All · study visit, Milan</p>
        <h2 class="h3">Three days in Milan on what makes a city usable</h2>
        <time datetime="2025-02-13">13 to 15 February 2025 · Claudio Pirola</time>
        <p>Milan hosted the first of the five study visits of Vote4All, the EU-funded project led by Cerebral Palsy Europe that
        works to let everyone vote autonomously, including people with cerebral palsy and complex disabilities. In a city about to
        co-host the 2026 Olympic and Paralympic Winter Games, much of the programme turned on sport as a driver of inclusion: the
        PlayMore centre, which opens its sports facilities to disabled people and to refugees, presented by Milan&rsquo;s sports
        councillor Martina Riva; the AC Milan Foundation at Casa Milan on its disability programmes in Italy and in Africa; a
        wheelchair-accessible walk through the Porta Nuova district. The rest tested the technology and the welcome: Microsoft
        House on digital accessibility, with Milan&rsquo;s council delegate for disabled people Haydee Longo, the Google
        Accessibility Discovery Centre, La Scala, and a lunch at a restaurant that employs people with Down syndrome, where
        CoorDown&rsquo;s president Martina Fuga made the economic case alongside the social one. The visits continue in Ljubljana,
        Lisbon, Porto, The Hague and Brussels.</p>
        <p class="src">Written for EURORDIS ·
        <a href="https://www.eurordis.org/breaking-barriers-advancing-accessibility-and-inclusion-for-cerebral-palsy-in-milan/" target="_blank" rel="noopener external">Breaking barriers: advancing accessibility and inclusion for cerebral palsy in Milan ↗</a></p>
      </article>
      <article class="report" id="edpd-2024">
        <p class="seat">European Disability Forum · European Day of Persons with Disabilities, Brussels</p>
        <h2 class="h3">DysNet joins the European Day of Persons with Disabilities in Brussels</h2>
        <time datetime="2024-11-28">28 and 29 November 2024</time>
        <p>The European Commission hosted the 2024 edition with the European Disability Forum, and DysNet was in the room. The
        conference came at a turning point, after the European elections and ahead of the new Commission&rsquo;s priorities, and it
        looked five years ahead, to the second phase of the European Strategy for the rights of persons with disabilities.
        Employment, independent living and transport were on the programme, with a special focus on accessible cities for the
        fifteenth anniversary of the Access City Award. The same themes, employment and transport above all, came back at the
        Forum&rsquo;s general assemblies in Vilnius and Ljubljana.</p>
        <div class="grid cols-2" style="margin-top:var(--space-3)">
          <figure class="photo"><picture><source srcset="/assets/img/edpd-2024-banner.webp" type="image/webp"><img src="/assets/img/edpd-2024-banner.jpg" alt="The conference banner: European Day of Persons with Disabilities, 28-29 November 2024, with the European Commission&rsquo;s logo" width="1000" height="750" loading="lazy" decoding="async"></picture>
            <figcaption>The conference banner stood in the lobby on the first morning. Photo: DysNet.</figcaption></figure>
          <figure class="photo"><picture><source srcset="/assets/img/edpd-2024-hall.webp" type="image/webp"><img src="/assets/img/edpd-2024-hall.jpg" alt="The conference hall seen from the delegates&rsquo; seats, with the speaker and a sign-language interpreter on the big screen" width="1000" height="750" loading="lazy" decoding="async"></picture>
            <figcaption>DysNet followed the first day from the hall, on 28 November. Photo: DysNet.</figcaption></figure>
          <figure class="photo"><picture><source srcset="/assets/img/edpd-2024-berlaymont.webp" type="image/webp"><img src="/assets/img/edpd-2024-berlaymont.jpg" alt="The Berlaymont building at night, with the European Commission&rsquo;s name on the wall" width="1000" height="750" loading="lazy" decoding="async"></picture>
            <figcaption>The Berlaymont, seat of the European Commission, stays lit after the first day. Photo: DysNet.</figcaption></figure>
          <figure class="photo"><picture><source srcset="/assets/img/edpd-2024-flags.webp" type="image/webp"><img src="/assets/img/edpd-2024-flags.jpg" alt="European Union flags in front of the curved glass fa&ccedil;ade of the Berlaymont" width="1000" height="750" loading="lazy" decoding="async"></picture>
            <figcaption>Flags line the front of the Berlaymont on the second morning. Photo: DysNet.</figcaption></figure>
        </div>
        <p class="src">European Disability Forum ·
        <a href="https://www.edf-feph.org/events-slug/european-day-of-persons-with-disabilities-2024/" target="_blank" rel="noopener external">European Day of Persons with Disabilities 2024 ↗</a></p>
      </article>
    </div>
"""


def reports_teaser(n=3):
    """The n most recent entries as cards, read from REPORTS_FEED itself."""
    out = []
    for art in re.findall(r'<article class="report"[^>]*>(.*?)</article>', REPORTS_FEED, re.S)[:n]:
        seat = re.search(r'<p class="seat">(.*?)</p>', art, re.S).group(1)
        seat = re.sub(r"<a [^>]*>(.*?)</a>", r"\1", seat, flags=re.S).strip()
        title = re.search(r'<h2[^>]*>(.*?)</h2>', art, re.S).group(1).strip()
        when = re.search(r"<time[^>]*>(.*?)</time>", art, re.S).group(1).split("·")[0].strip()
        out.append(f'<div class="card"><p class="seat">{seat}</p>'
                   f'<h3 class="h4"><a href="/voice/reports/">{title}</a></h3>'
                   f'<p class="fine">{when}</p></div>')
    return '<div class="grid cols-3">' + "".join(out) + "</div>"


PAGES["/voice/"] = {
    "title": "Where DysNet sits",
    "desc": "DysNet's seats at EURORDIS, the European Disability Forum and ERN BOND: a named delegate, a written mandate and a public report for each.",
    "crumbs": [("/voice/", "Voice")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Mission 3 · The voice of families</p>
    <h1 class="display">Our voice for people with dysmelia.</h1>
    <p>DysNet keeps its seats but chooses them: a restricted list of international bodies active alongside researchers. Each seat has a named delegate, a written mandate, and a short written report to members after every meeting.</p>
    <p class="brief-cta"><a class="btn btn-primary" href="/assets/dysnet-five-demands.pdf" download><span class="btn-ic" aria-hidden="true">↓</span> Download the five demands (one-page PDF)</a></p>

    {opener("01", "Our voice", "Five demands, carried into every room we sit in.", toc="The five demands")}
    <p>What DysNet asks for on behalf of families, in the order we argue them.</p>
    {demands_html()}

    {opener("02", "Where we sit", "The seats, with a mandate.", toc="Where we sit")}
    <div class="grid cols-2" style="margin-top:var(--space-4)">
      <div class="card">
        <h3 class="h4">EURORDIS · Rare Diseases Europe</h3>
        <p>Member, and part of the <a href="https://www.eurordis.org/social-policy-action-group/" target="_blank" rel="noopener external">Social Policy Action Group</a>, where DysNet contributes on independent living. Active in the Rare Barometer programme and the European Regional Task Force on Rare Diseases (with Rare Diseases International, supporting the WHO resolution on rare diseases).</p>
      </div>
      <div class="card">
        <h3 class="h4">EDF · European Disability Forum</h3>
        <p>Member. General assemblies and workstreams on the EU Disability Card, AI, assistive technology for employment, and accessibility.</p>
      </div>
      <div class="card">
        <h3 class="h4">ERN BOND · patient advocacy group</h3>
        <p>Patient representative seat in the European Reference Network for bone diseases; promoter of the Patient Journey project.</p>
      </div>
      <div class="card" style="--acc:var(--acc-centres);--acc-text:var(--acc-centres-text)">
        <h3 class="h4">EESC · European Economic and Social Committee</h3>
        <p>Standing contacts. The EU’s consultative body for organised civil society advises the Parliament, Council and Commission, and carries a permanent group on disability rights: opinions on the EU Disability Card and on the rights of persons with disabilities are shaped here.</p>
      </div>
    </div>

    {opener("03", "What came back", "Every seat reports, and the reports are public.", toc="The reports")}
    <p>A seat is worth what it brings home, so each delegate writes a short report after every meeting and we publish it. Here are the three most recent.</p>
    {reports_teaser(3)}
    <p style="margin-top:var(--space-3)"><a class="btn btn-primary" href="/voice/reports/">Read all delegate reports</a></p>

    {opener("04", "Also active in", "Projects we joined by invitation.", toc="Also active in")}
    <ul>
      <li><strong>VOTE4ALL / VOICE4ALL</strong> (Cerebral Palsy Europe, EU-supported): autonomous voting rights for persons with disabilities; study visits to The Hague and the Portuguese Parliament.</li>
      <li><strong>Local lectures</strong>: Milan Civil Week, and an event planned around the Milano-Cortina 2026 Winter Paralympics.</li>
    </ul>
  </div>
</section>
""",
}

PAGES["/voice/reports/"] = {
    "og": "/assets/img/limbloss-day-2012.jpg",
    "title": "Reports",
    "desc": "Short written reports from DysNet's delegates after every meeting in the bodies where DysNet represents families affected by limb difference.",
    "crumbs": [("/voice/", "Voice"), ("/voice/reports/", "Reports")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Mission 3 · Delegate reports</p>
    <h1 class="display">Reports from our seats.</h1>
    <p>What our delegates heard, said and brought home, in a few paragraphs each. This feed replaces the old blog. Entries dated
    February 2026 come from the chairman&rsquo;s activity report of that month.</p>

    {REPORTS_FEED}

    <figure class="photo" style="margin-top:var(--space-4)">
      <picture><source srcset="/assets/img/limbloss-day-2012.webp" type="image/webp"><img src="/assets/img/limbloss-day-2012.jpg" alt="A speaker presents DysNet and EDRIC at European LimbLoss Day 2012" width="1400" height="1050" loading="lazy" decoding="async"></picture>
      <figcaption>Representation is in DysNet’s DNA: European LimbLoss Day, 2012. Photo: DysNet.</figcaption>
    </figure>
  </div>
</section>
""",
}

# ─────────────────────────────── ABOUT ────────────────────────────
PAGES["/about/"] = {
    "og": "/assets/img/dysnet-banner-2012.jpg",
    "title": "About DysNet",
    "desc": "DysNet, formerly EDRIC: the network for people with congenital limb differences, founded by thalidomide families and registered in Sweden in 2009.",
    "crumbs": [("/about/", "About")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · Built by families</p>
    <h1 class="display">About DysNet: a network families built.</h1>
    <p>In 2009, the Swedish Thalidomide Society (FfdN), the EX-Center knowledge and rehabilitation centre and the UK Thalidomide Trust registered EDRIC, the European Dysmelia Reference Information Centre, in Sweden. The portal opened in 2012 and the network became DysNet: the only global network dedicated to congenital limb differences.</p>

    {opener("01", "Vision", "What we work towards.")}
    <p>A world where every family affected by a congenital limb difference can find the knowledge that concerns them, and where the community’s own data drives the research that shapes their care. DysNet pools what member associations know at national level into a shared international resource: documented research, a registry owned by patients themselves, and one voice in the institutions where decisions are made.</p>

    {opener("02", "Three missions", "Everything DysNet does fits one of three missions.")}
    <div class="grid cols-3">
      <div class="card acc-library"><h3 class="h4"><a href="/knowledge/">Knowledge</a></h3><p>The international reference point for limb-difference research: five maintained registers, published as data.</p></div>
      <div class="card acc-studies"><h3 class="h4"><a href="/registry/">Registry</a></h3><p>The international associative registry of limb malformations, our flagship.</p></div>
      <div class="card"><h3 class="h4"><a href="/voice/">Voice</a></h3><p>Families represented where European decisions are made, with mandates and reports.</p></div>
    </div>

    {opener("03", "History", "From Malmö 2012 to today.")}
    <div class="grid cols-2">
      <figure class="photo">
        <picture><source srcset="/assets/img/dysnet-banner-2012.webp" type="image/webp"><img src="/assets/img/dysnet-banner-2012.jpg" alt="The original DysNet launch banner: Let the conversation begin" width="750" height="1000" loading="lazy" decoding="async"></picture>
        <figcaption>The launch banner, 2012: “Let the conversation begin.” Photo: DysNet.</figcaption>
      </figure>
      <div>
        <p><strong>2008-2009</strong> · EDRIC founded and registered in Sweden (org. no. 802444-3015).</p>
        <p><strong>2012</strong> · The web portal opens; first network meeting in Malmö.</p>
        <p><strong>2015</strong> · Stockholm meeting; the network grows across Europe.</p>
        <p><strong>2025</strong> · Co-organiser of a biorobotics conference with Regione Lombardia.</p>
        <p><strong>2026</strong> · The refocused strategy: three missions, five registers, one registry.</p>
        <div class="yt-embed" data-yt="P8M2n7Gr3V0" data-title="The chair’s address to members">
          <picture><source srcset="/assets/img/chair-address-thumb.webp" type="image/webp"><img src="/assets/img/chair-address-thumb.jpg" alt="Video: Claudio Pirola, DysNet’s chair, addresses the members" width="640" height="480" loading="lazy" decoding="async"></picture>
          <button type="button" aria-label="Play: the chair’s address to members"><span></span></button>
        </div>
        <p style="font-size:var(--text-small);color:var(--dys-muted)">The chair’s address to members · <a href="https://www.youtube.com/watch?v=P8M2n7Gr3V0" target="_blank" rel="noopener external">open on YouTube ↗</a></p>
      </div>
    </div>

    <div id="board"></div>
    {opener("04", "The board", "Volunteers who carry a mission each.")}
    <p>Most of the board live with dysmelia or are parents of children with limb differences, as the statutes require. Under the 2026-2029 strategy every seat owns a mission: no seat without a mission. Hover or tap a card to read the bio and write to its holder.</p>
    <div class="grid cols-3" style="margin-top:var(--space-3)">
      {"".join(person_card(*p) for p in BOARD)}
    </div>
    <figure class="photo" style="margin-top:var(--space-4)">
      <picture><source srcset="/assets/img/board-inail-2024.webp" type="image/webp"><img src="/assets/img/board-inail-2024.jpg" alt="DysNet board members and guests at the INAIL prosthetics centre, August 2024" width="1800" height="1012" loading="lazy" decoding="async"></picture>
      <figcaption>The board and member-association guests at INAIL Centro Protesi, Vigorso di Budrio, August 2024. Photo: DysNet.</figcaption>
    </figure>

    {opener("05", "Documents", "The texts that govern us.")}
    <ul>
      <li><a href="/about/transparency/">Statutes, accounts and AGM documents</a></li>
      <li><a href="#board">The board</a> and <a href="/about/members/">the member associations</a></li>
    </ul>
  </div>
</section>
""",
}

# (name, role, bio, initials, email, mission chip)




# (country, [(name, url or None), ...]) — URLs from the previous dysnet.org
# member pages plus known member sites, each verified reachable on 2026-08-18.
# Unreachable sites (taionlus.org, vitachi.cl, ITSS on webs.com, aussiehands,
# neurosedyn.se, steps-charity) deliberately stay unlinked until confirmed.

# ─────────────── Landing map: registry participants by country ───────────────
# ISO 3166-1 numeric ids (as used by Natural Earth / world-atlas).
ISO_NUM = {"Australia": "036", "Austria": "040", "Belgium": "056", "Canada": "124", "Chile": "152",
           "France": "250", "Germany": "276", "Ireland": "372", "Italy": "380", "Netherlands": "528",
           "Norway": "578", "Spain": "724", "Sweden": "752", "United Kingdom": "826", "United States": "840"}
# Registry (Mission 2) participation status. Candidates are grounded in the
# strategy: a grant application in preparation on the French side; Raggiungere
# (Italy) promoter of the Patient Journey. Both remain to be confirmed at the AGM.
ISO_A3 = {"036": "AUS", "040": "AUT", "056": "BEL", "124": "CAN", "152": "CHL", "250": "FRA", "276": "DEU",
          "372": "IRL", "380": "ITA", "528": "NLD", "578": "NOR", "724": "ESP", "752": "SWE", "826": "GBR", "840": "USA"}
REGISTRY_STATUS = {"250": "candidate", "380": "candidate", "124": "contact"}
MAP_LABELS = {"member": "Member association", "candidate": f"Piloting the registry ({', '.join(PILOTS)}; AGM mandate, August 2026)",
              "contact": "Contact opened"}
MAP_COUNTRIES = {}
for _country, _orgs in MEMBERS:
    _id = ISO_NUM[_country]
    MAP_COUNTRIES[_id] = {"name": _country, "a3": ISO_A3[_id], "status": REGISTRY_STATUS.get(_id, "member"), "orgs": _orgs}
MAP_COUNTRIES["124"] = {"name": "Canada", "a3": "CAN", "status": "contact", "orgs": ["A national amputee organisation (contact opened, 2026)"]}
MAP_OFFICES = [{"name": "Solna", "lat": 59.36, "lon": 17.99}, {"name": "Brussels", "lat": 50.85, "lon": 4.35}]
# Papers in our bibliography that rest on each registry, keyed by the registry name the map
# carries in its zone properties, so the popup and the registries page quote one figure.
REG_BIB = {k: [len(v["names"]), len(v["found"])] for k, v in registry_evidence().items()}

# Countries where a clinical registry recruits, for the country tooltip. Read from the same
# declarative input the map outlines are drawn from, so the two cannot disagree.
CLINICAL_BY_COUNTRY = {}
for _a in REG_AREAS:
    if _a.get("status") == "clinical":
        CLINICAL_BY_COUNTRY.setdefault(_a["country"], [])
        if _a["registry"] not in CLINICAL_BY_COUNTRY[_a["country"]]:
            CLINICAL_BY_COUNTRY[_a["country"]].append(_a["registry"])

# ── The dot tiles' own ladder ──────────────────────────────────────────────────────────────
# Each dot in docs/assets/map/dots.pmtiles carries b, its rank on the ladder of thresholds the tiles
# were built with, and tools/build-pop-dots.py writes that ladder to dots-ladder.json beside them.
# The map must rank a condition on THAT ladder and not on today's DOT_RATES: between the tiles of
# 14 September and 21 September DOT_RATES gained four thresholds, and every condition was drawn at
# the wrong rank. A rate the tiles do not hold is drawn at the nearest lower step, and the legend
# says so, until the tiles are rebuilt.
DOT_LADDER = json.loads((pathlib.Path(__file__).parent / "docs" / "assets" / "map" / "dots-ladder.json").read_text(encoding="utf-8"))["thresholds"]
_off_ladder = sorted({round(r * 100) for _, r, *_ in DOT_RATES if r is not None} - set(DOT_LADDER))
if _off_ladder:
    print(f"WARNING: DOT_RATES holds thresholds the dot tiles were not built with: {_off_ladder}. Those conditions "
          "are drawn at the nearest lower step until the tiles are rebuilt: python3 tools/build-pop-dots.py "
          "tools/ghs/<GHS-POP GeoTIFF> && bash tools/build-pop-tiles.sh")

# One set of words for a registry zone's status, read by the legend, the WebGL map and the SVG
# fallback alike. A drawn status this table does not name stops the build.
ZONE_LABELS = {
    "covered": {"css": "l-zone", "legend": "Area covered by a registry that records our conditions",
                "tip": "Covered by a population-based registry of congenital anomalies"},
    "in_progress": {"css": "l-zone-progress", "legend": "Area a registry is starting to cover",
                    "tip": "Registry starting to cover this area"},
    "clinical": {"css": "l-zone-clinical", "legend": "Country where a clinical registry recruits",
                 "tip": "A clinical registry recruiting here, not population coverage"},
    "hospital": {"css": "l-zone-hospital", "legend": "Hospital-based surveillance of births",
                 "tip": "Hospital-based surveillance sampling births, not every birth"},
}
_drawn_statuses = ({a["status"] for a in REG_AREAS if a.get("map", True)}
                   | {z["status"] for z in json.loads((pathlib.Path(__file__).parent / "tools" / "registry-zones.json").read_text(encoding="utf-8"))["zones"]})
if _drawn_statuses - set(ZONE_LABELS):
    raise SystemExit(f"ZONE_LABELS has no words for the drawn status {_drawn_statuses - set(ZONE_LABELS)}")

MAP_DATA = json.dumps({"countries": MAP_COUNTRIES, "clinical": CLINICAL_BY_COUNTRY, "dotLadder": DOT_LADDER, "zoneLabels": ZONE_LABELS, "regBib": REG_BIB, "offices": MAP_OFFICES, "centres": [{k: c.get(k) for k in ("name", "name_local", "label", "city", "country", "type", "specialism", "url", "via", "via_verb", "lat", "lon")} for c in CARE_CENTRES], "teams": [{"name": t["institution"], "country": t["country"], "papers": t["papers"], "years": t["years"], "codes": [dict(REG_CODE_NAMES, thal="Thalidomide embryopathy").get(c, c) for c in t["codes"]], "authors": t["authors"], "rep": t["representative"], "address": t.get("address", ""), "contact": t.get("contact", ""), "lat": t["lat"], "lon": t["lon"]} for t in RESEARCHERS.get("teams", []) if t.get("lat")], "labels": MAP_LABELS, "rates": [[lab, r, src, _slug(lab), basis, note] for lab, r, src, basis, note in DOT_RATES], "zonesUrl": "/assets/map/registry-zones.geojson?v=" + __import__("hashlib").md5((pathlib.Path(__file__).parent / "docs/assets/map/registry-zones.geojson").read_bytes()).hexdigest()[:8]}, ensure_ascii=False)

# Injected into the home page at build time (placeholder __MAP_HERO__): it needs the map data
# assembled below, which the home page body is written before.
MAP_HERO = """
<section class="map-hero" id="map" aria-label="The DysNet network on the world map">
  <div id="worldmap"></div>
  <div id="glmap"></div>
  <div class="map-panel" id="map-panel">
    <button type="button" class="map-panel-close" aria-label="Close this card and explore the map">×</button>
    <p class="kicker">Mission 2 · The international associative registry</p>
    <h1>The registry of limb malformations, <em>owned by the families it describes.</em></h1>
    <p>Each highlighted country is an association ready to bring its families’ knowledge into one shared, patient-governed registry. Hover a country to see who.</p>
    <ul class="map-stats">
      <li><strong data-count="countries">__N_COUNTRIES__</strong>countries</li>
      <li><strong data-count="orgs">__N_ORGS__</strong>associations</li>
      <li><strong data-count="candidate">__N_PILOTS__</strong>associations piloting the registry</li>
    </ul>
    <div class="hero-actions">
      <a class="btn btn-primary" href="/registry/">The registry project</a>
      <a class="btn btn-ghost" href="/about/members/">Join the network</a>
    </div>
  </div>
  <button type="button" class="map-panel-reopen" id="map-panel-reopen" hidden>About this map</button>
  <div class="map-side" id="map-side">
  <button type="button" class="map-options-toggle" id="map-options-toggle" aria-expanded="false" aria-controls="map-side">Map options</button>
  <div class="map-layers" id="map-layers" role="group" aria-label="Show on the map">
    <span class="map-layers-label">Show</span>
    <button type="button" data-layer="members" aria-pressed="true">Member countries</button>
    <button type="button" data-layer="zones" aria-pressed="true">Registry coverage</button>
    <button type="button" data-layer="people" aria-pressed="true">Estimated people</button>
    <button type="button" data-layer="centres" aria-pressed="true">Care centres</button>
    <button type="button" data-layer="teams" aria-pressed="true">Research teams</button>
    <button type="button" data-layer="offices" aria-pressed="true">DysNet offices</button>
    <button type="button" data-layer="cities" aria-pressed="true">City names</button>
  </div>
  <div class="map-views" role="group" aria-label="Map view">
    <button type="button" data-view="world" aria-pressed="true">World</button>
    <button type="button" data-view="europe" aria-pressed="false">Europe</button>
    <button type="button" data-view="americas" aria-pressed="false">Americas</button>
    <button type="button" data-view="asiapacific" aria-pressed="false">Asia-Pacific</button>
    <button type="button" data-view="africa" aria-pressed="false">Africa &amp; Middle East</button>
  </div>
  <p class="map-guess" aria-live="polite"></p>
  <div class="map-dots" id="map-dots" hidden>
    <label for="dot-condition">Estimated people living with</label>
    <select id="dot-condition"></select>
    <p class="dot-legend" id="dot-legend" aria-live="polite"></p>
    <p class="dot-caption">Grey dots are <strong>estimates</strong> (prevalence × population, GHSL 2025 population grid, EU JRC). The registry’s purpose is to turn these estimates into known, consented cases.</p>
  </div>
  <div class="map-legend" id="map-legend" aria-label="Legend">
    <button type="button" class="map-legend-toggle" id="map-legend-toggle" aria-expanded="false" aria-controls="map-legend">Legend</button>
    <span class="l-member" data-layer="members">Member association</span>
    <span class="l-candidate" data-layer="members">Piloting the registry (__PILOTS__)</span>
    <span class="l-contact" data-layer="members">Contact opened</span>
    <span class="l-office" data-layer="offices">DysNet office</span>
    __ZONE_LEGEND__
    <span class="l-centre" data-layer="centres">Care centre named by a member association or verified from its own institutional page (click for details)</span>
    <span class="l-team" data-layer="teams">Research team publishing on our conditions (click for details)</span>
    <span class="l-dot" data-layer="people">Grey dot: one <strong>estimated</strong> person living with a limb difference (1 dot = 1 person at city zoom; 10, 100 or 1,000 people when zoomed out), computed from prevalence × population. This is the situation as statistics describe it; the registry exists to make it visible. Choose the condition above.</span>
    <span class="l-note">Every marker is also listed, in full, on the <a href="/knowledge/care-centres/">care centres</a>, <a href="/knowledge/researchers/">researchers</a> and <a href="/knowledge/registries/">registries</a> pages.</span>
    <span class="map-credit">Map data: Natural Earth (public domain), GeoNames (CC BY 4.0), GHSL population (EU JRC, CC BY 4.0), French départements from IGN Admin Express (Licence Ouverte) via france-geojson; registry coverage after Santé publique France 2026 · rendered with MapLibre, self-hosted</span>
  </div>
  </div>
  <div class="map-tip" role="tooltip"></div>
  <script>window.DYSNET_MAP = __MAP_DATA__;</script>
  <link rel="stylesheet" href="/assets/vendor/maplibre-gl.css">
  <script src="/assets/vendor/maplibre-gl.js"></script>
  <script src="/assets/vendor/pmtiles.js"></script>
  <script src="/assets/js/map-gl.js?v=__MAPGL_V__"></script>
</section>
""".replace("__MAP_DATA__", MAP_DATA).replace("__MAPGL_V__", __import__("hashlib").md5((pathlib.Path(__file__).parent / "docs/assets/js/map-gl.js").read_bytes()).hexdigest()[:8])
# the legend's zone rows come from ZONE_LABELS, the same words the two maps use for a zone's status
MAP_HERO = MAP_HERO.replace("__ZONE_LEGEND__", "\n    ".join(f'<span class="{v["css"]}" data-layer="zones">{v["legend"]}</span>' for v in ZONE_LABELS.values()))
# The card's counts and the pilots' names come from MEMBERS, the same source as every sentence that
# counts the members. The scripts used to total the map data instead, and counted Canada's
# "contact opened" placeholder as a thirtieth association.
MAP_HERO = (MAP_HERO.replace("__N_COUNTRIES__", str(MEMBER_STATS["countries"])).replace("__N_ORGS__", str(MEMBER_STATS["orgs"]))
            .replace("__N_PILOTS__", str(MEMBER_STATS["pilots"])).replace("__PILOTS__", ", ".join(PILOTS)))


# Notes printed under a country's list, where the list alone would mislead.
MEMBER_NOTES = {
    "Sweden": ('FfdN, Föreningen för de Neurosedynskadade, is the Swedish Thalidomide Society: a national association in Solna '
               '(<a href="https://www.thalidomide.org/" target="_blank" rel="noopener external">thalidomide.org</a>, also reachable at '
               '<a href="https://www.ffdn.se" target="_blank" rel="noopener external">ffdn.se</a>) with two regional associations, '
               'Stockholm and Väst/Skåne. EX-Center, which FfdN runs with Ottobock Care, is a rehabilitation centre rather than an '
               'association, and has its place in our <a href="/knowledge/care-centres/">care centres register</a>.'),
}


# Who leads each association and how to reach it. Every name and address below was read on the
# association's own website on 14 September 2026, except where "src" says otherwise; an association
# that publishes no name keeps only its contact address. "src" records where each entry came from,
# so a correction can be traced; it is not printed on the page.
MEMBER_INFO = {
    "Aussiehands": {"role": "President and chairperson", "person": "Elizabeth Borg", "email": "info@aussiehands.org",
                    "src": "the association's site, 2026 board"},
    "Thalidomide Australia": {"email": "lisa@thalidomidegroupaustralia.com", "src": "the association's contact page"},
    "Assedea": {"role": "President", "person": "Carine Faucher Lombardo", "deputy_role": "Vice-president", "deputy": "Alice Delmas",
                "email": "contact@assedea.fr", "src": "the association's team page"},
    "Contergan NRW": {"role": "Represented by", "person": "Udo Herterich", "email": "info@contergan-nrw.eu",
                      "phone": "+49 221 37985947", "src": "the association's Impressum"},
    "HICOHA Hamburg": {"role": "Chair", "person": "Gernot Stracke", "deputy_role": "Deputy chairs",
                       "deputy": "H.-Hinnerk Maass and Heike Erhardt-Maaß", "phone": "+49 40 41092110",
                       "src": "the association's Impressum"},
    "Interessenverband Contergangeschädigter, Köln": {"role": "Chair", "person": "Udo Herterich",
                                                      "deputy_role": "Second chair", "deputy": "Brigitte Gerards",
                                                      "person_email": "udo.herterich@conterganverband-koeln.de", "src": "the association's board page"},
    "Contergangeschädigte Hessen": {"role": "Chair", "person": "Alfonso J. Fernandez Garcia", "deputy_role": "Second chair",
                                    "deputy": "Jutta Sattler", "email": "info@contergan-hessen.de",
                                    "src": "the association's Impressum"},
    "Raggiungere": {"role": "President", "person": "Carlo Antonini", "deputy_role": "Vice-president", "deputy": "Giulia Sarpero",
                    "email": "info@raggiungere.it",
                    "src": "the association's site, board 2026-2028"},
    "Thalidomidici Italiani (TAI onlus)": {"role": "President", "person": "Vincenzo Tomasso", "email": "segreteria@taionlus.it",
                                           "src": "the association's about page"},
    "V.I.TA – Vittime Talidomide Italia": {"role": "President", "person": "Giovanni Del Mastro", "deputy_role": "Vice-president",
                                           "deputy": "Maria Angela Gilli", "email": "segreteria@vittimetalidomideitalia.it",
                                           "person_email": "presidente@vittimetalidomideitalia.it",
                                           "src": "the association's board page"},
    "AISP – Sindrome di Poland": {"role": "President", "person": "Ilaria Baldelli", "email": "segreteria@sindromedipoland.org",
                                  "src": "the association's site, board elected 7 November 2024"},
    "Stichting NESOS": {"email": "informatievraag@stichtingnesos.nl", "src": "the foundation's contact page"},
    "AVITE": {"role": "Founding president", "person": "José Riquelme López", "deputy_role": "Vice-president and treasurer",
              "deputy": "Rafael Basterrechea Estella", "email": "info@avite.org", "src": "the association's board page"},
    "FfdN, the Swedish Thalidomide Society (Föreningen för de Neurosedynskadade)":
        {"role": "President", "person": "Bengt-Lennart Widell", "deputy_role": "Vice chair", "deputy": "Christina Swanberg",
         "person_email": "bengt-lennart.w@ffdn.se", "email": "info@ffdn.se", "src": "the association's site, board 2026"},
    "FfdN Stockholm": {"role": "Chair", "person": "Carina Essberg", "deputy_role": "Vice chair", "deputy": "Peter Idar",
                       "email": "ffdn-stockholm@ffdn.se", "src": "the association's regional board page"},
    "FfdN Väst/Skåne": {"role": "Chair", "person": "Tina Henriksson", "deputy_role": "Vice chair", "deputy": "Birgitta Widell",
                        "person_email": "tina.h@ffdn.se", "src": "the association's regional board page"},
    "Svensk Dysmeliförening": {"role": "Chair", "person": "Jelena Blingros", "deputy_role": "Vice chair", "deputy": "Ulrik Nilsson",
                               "person_email": "jelena@dysmeli.se", "email": "info@dysmeli.se", "src": "the association's board page"},
    "Thalidomide Trust": {"role": "Chair of trustees", "person": "David Body", "deputy_role": "Vice-chair of trustees",
                          "deputy": "Professor Andrew Owens", "src": "the Trust's trustees page; it takes enquiries through its website"},
    "Reach": {"role": "Chairman", "person": "Chris Creamer", "deputy_role": "Vice chairman", "deputy": "Gary Phillips",
              "email": "reach@reach.org.uk", "src": "the DysNet board"},
    "Thalidomide Society": {"role": "Chair of trustees", "person": "Mandy De La Mare", "deputy_role": "Vice chair",
                            "deputy": "Ed Freeman", "email": "info@thalidomidesociety.org",
                            "src": "the association's board of trustees page"},
    "Steps Charity": {"role": "Chief executive", "person": "Amanda Goulding", "email": "info@steps-charity.org.uk",
                      "src": "the charity's team page"},
}


def member_li(entry):
    name, url = entry[0], entry[1]
    support = entry[2] if len(entry) > 2 else None
    i = MEMBER_INFO.get(name, {})
    rows = []
    if i.get("person"):
        rows.append(f'<p class="assoc-lead"><strong>{i.get("role", "President")}</strong>{i["person"]}</p>')
    if i.get("deputy"):
        rows.append(f'<p class="assoc-lead"><strong>{i.get("deputy_role", "Vice chair")}</strong>{i["deputy"]}</p>')
    contact = []
    if i.get("person_email"): contact.append(f'<a href="mailto:{i["person_email"]}">{i["person_email"]}</a>')
    if i.get("email"): contact.append(f'<a href="mailto:{i["email"]}">{i["email"]}</a>')
    if i.get("phone"): contact.append(i["phone"])
    if contact: rows.append(f'<p class="assoc-contact">Contact: {" · ".join(contact)}</p>')
    if url:
        host = url.split("//")[-1].split("/")[0].removeprefix("www.")
        rows.append(f'<p class="assoc-site"><a href="{url}" target="_blank" rel="noopener external">{host} ↗</a></p>')
    # the donation button stays outside the dropdown, visible without opening the card
    give = (f'<div class="assoc-foot"><a class="btn btn-donate btn-sm" href="{support}" target="_blank" '
            f'rel="noopener external" aria-label="Support {name}">♥ Support them</a></div>') if support else ""
    if not rows:
        return f'<li class="assoc-plain"><span>{name}</span>{give}</li>'
    return (f'<li><details class="assoc"><summary>{name}</summary>'
            f'<div class="assoc-body">{"".join(rows)}</div></details>{give}</li>')

PAGES["/about/members/"] = {
    "title": "Member associations",
    "desc": f"The national associations families belong to: {spell(MEMBER_STATS['orgs'])} limb-difference and thalidomide organisations across {spell(MEMBER_STATS['countries'])} countries, on {spell(MEMBER_STATS['continents'])} continents.",
    "crumbs": [("/about/", "About"), ("/about/members/", "Member associations")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · The network</p>
    <h1 class="display">Member associations: the groups families belong to.</h1>
    <p>DysNet is a federation: our members are national associations of people with limb differences and their families. Find yours below, or bring your association in.</p>

    <h2 class="h3" style="margin-top:var(--space-4)">Our members, country by country</h2>
    <div style="margin-top:var(--space-2)">
      {"".join(f'<div class="country"><h3>{c}</h3><ul>{"".join(member_li(m) for m in sorted(ms, key=lambda m: len(m) < 3))}</ul>{f"<p class=\'country-note\'>{MEMBER_NOTES[c]}</p>" if c in MEMBER_NOTES else ""}</div>' for c, ms in MEMBERS)}
    </div>

    {opener("01", "Join", "Two ways in.")}
    <div class="grid cols-2">
      <div class="card"><h3 class="h4">Full member</h3><p>For associations ready to take part in governance: voting rights, a voice at the AGM, and a duty to feed the registers. Write to the board for the terms of membership.</p></div>
      <div class="card" style="--acc:var(--dys-green);--acc-text:var(--dys-green-text)"><h3 class="h4">Associate (observer)</h3><p>For associations that want to support one mission, typically the registry, without governance duties, returning to full membership when capacity allows.</p></div>
    </div>
    <p style="margin-top:var(--space-3)"><a class="btn btn-primary" href="mailto:info@dysnet.org?subject=Membership">Write to us about membership</a></p>
    <p style="font-size:var(--text-small);color:var(--dys-muted)">Member associations are also encouraged to register in <a href="https://www.orpha.net/en/patient-organisations" target="_blank" rel="noopener external">Orphanet’s directory of patient organisations</a>, where families and clinicians across Europe and beyond search for support groups. DysNet is listed there as a federation: <a href="https://www.orpha.net/en/patient-organisations/federations-alliances/646248" target="_blank" rel="noopener external">see our entry</a>.</p>
  </div>
</section>
""",
}

PAGES["/about/transparency/"] = {
    "title": "Transparency",
    "desc": "DysNet's governing documents in one place: statutes, annual accounts, AGM documents and reports, published for members and the public.",
    "crumbs": [("/about/", "About"), ("/about/transparency/", "Transparency")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · Transparency</p>
    <h1 class="display">Transparency: our documents, in the open.</h1>
    <p>An organisation of volunteers runs on trust. The texts that govern DysNet and the accounts that trace its funds are published here.</p>
    <h2 class="h3" style="margin-top:var(--space-4)">The documents we publish</h2>
    <div style="margin-top:var(--space-2)">
      <article class="entry"><h3>Statutes of DysNet <span class="badge live">2011</span></h3><p>Adopted by the Extraordinary Meetings of 20 October 2011. Name, objectives, membership, decision-making bodies, board, accounts and audit.</p><p class="src"><a href="/about/statutes/">Read online</a> · PDF · English</p></article>
      <article class="entry"><h3>A Refocused Strategy 2026-2029 <span class="badge live">AGM 2026</span></h3><p>Three missions, one task each, a governance built to carry them, and funding tied to each. Adopted by the AGM of 26 August 2026.</p><p class="src">PDF · English</p></article>
      <article class="entry"><h3>Annual accounts <span class="badge example">to publish</span></h3><p>The previous year’s operating statement, accounts and auditor’s report, as considered by each AGM.</p><p class="src">Published after each AGM</p></article>
      <article class="entry"><h3>AGM minutes and reports <span class="badge example">to publish</span></h3><p>Minutes of the general meetings, and the mission reports the refocused strategy asks each mission to produce. The minutes of the AGM of 26 August 2026 are not drafted yet.</p><p class="src">Each set goes online once the meeting has adopted it</p></article>
    </div>
  </div>
</section>
""",
}

# ────────────────────────────── CONTACT ───────────────────────────
PAGES["/contact/"] = {
    "title": "Contact",
    "desc": "Contact DysNet: info@dysnet.org, offices in Solna (Sweden) and Brussels (Belgium). For families, clinicians, researchers and associations.",
    "crumbs": [("/contact/", "Contact")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Contact</p>
    <h1 class="display">Contact the dysmelia network: talk to us.</h1>
    <p>One address reaches the whole network: <a href="mailto:info@dysnet.org"><strong>info@dysnet.org</strong></a>.</p>
    <h2 class="h3" style="margin-top:var(--space-4)">Who is writing?</h2>
    <div class="grid cols-3" style="margin-top:var(--space-2)">
      <div class="card"><h3 class="h4">Families</h3><p>Looking for information or an association near you? Start with <a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a> and <a href="/about/members/">the member directory</a>.</p></div>
      <div class="card acc-research"><h3 class="h4">Researchers &amp; clinicians</h3><p>Ask to be listed in the <a href="/knowledge/researchers/">researcher register</a> or propose a study for <a href="/knowledge/ongoing-studies/">the studies page</a>.</p></div>
      <div class="card acc-studies"><h3 class="h4">Associations</h3><p>Join as a <a href="/about/members/">full or associate member</a>, or bring your national data into <a href="/registry/">the registry</a>.</p></div>
    </div>
    {opener("01", "Offices", "Solna and Brussels.")}
    <div class="grid cols-2">
      <div class="card"><h3 class="h4">Registered office</h3><p>DysNet Ideell Förening<br>Nybodagatan 1<br>171 42 Solna, Sweden</p></div>
      <div class="card"><h3 class="h4">Brussels office</h3><p>DysNet Ideell Förening<br>Rue du Chantier 2<br>B-1000 Brussels, Belgium</p></div>
    </div>
  </div>
</section>
""",
}



# ────────────────── Pages ported from HDS website ideas ──────────────
PAGES["/donate/"] = {
    "title": "Support DysNet",
    "desc": "A one-off or monthly gift, membership or help in kind carries the three missions families rely on: knowledge, the registry and our voice.",
    "crumbs": [("/donate/", "Support DysNet")],
    "body": """
<section>
  <div class="container don-grid">
    <div>
      <div class="tick" style="background:var(--dys-green)"></div>
      <p class="eyebrow" style="color:var(--dys-green-text)">Support · Every gift carries a mission</p>
      <h1 class="display">Support DysNet: power the network families rely on.</h1>
      <p>DysNet runs entirely on volunteers, so a small gift goes remarkably far: it keeps the registers current, the registry moving, and a delegate in the room when European decisions are made.</p>
      <ul class="don-carry">
        <li><a href="/knowledge/"><strong>Knowledge</strong> · hosting &amp; translation of the five registers</a></li>
        <li><a href="/registry/"><strong>Registry</strong> · the patient-owned data flagship</a></li>
        <li><a href="/voice/"><strong>Voice</strong> · delegates where decisions are made</a></li>
      </ul>
      <figure class="don-photo">
        <picture><source srcset="/assets/img/inail-lab-2.webp" type="image/webp"><img src="/assets/img/inail-lab-2.jpg" alt="Prosthetics being crafted in the INAIL workshop visited by the DysNet board" width="1400" height="787" loading="lazy" decoding="async"></picture>
      </figure>
      <p style="font-size:var(--text-small);color:var(--dys-muted);margin-top:var(--space-1)">The INAIL prosthetics workshop, Vigorso di Budrio. Photo: DysNet.</p>
    </div>

    <div class="donate-box" id="donate">
      <h2 class="h3">Make a gift</h2>
      <p class="sub">To DysNet Ideell Förening, non-profit, Sweden.</p>
      <div class="freq" role="group" aria-label="Frequency">
        <button type="button" aria-pressed="true">One-off</button>
        <button type="button" aria-pressed="false">Monthly</button>
      </div>
      <div class="amounts" role="group" aria-label="Amount">
        <button type="button" aria-pressed="false">€25<small>friend</small></button>
        <button type="button" aria-pressed="true">€50<small>regular</small></button>
        <button type="button" aria-pressed="false">€100<small>supporter</small></button>
        <button type="button" aria-pressed="false">€250<small>patron</small></button>
        <button type="button" aria-pressed="false">€500<small>benefactor</small></button>
        <button type="button" aria-pressed="false">Other<small>you choose</small></button>
      </div>
      <button type="button" class="btn-go" id="bank-toggle">Give by bank transfer</button>
      <div class="bank-reveal" id="bank-details">
        <p id="bank-chosen">Your gift: <strong>one-off, €50</strong>.</p>
        <dl class="bank-lines">
          <dt>Account name</dt><dd>DysNet - The Dysmelia Network</dd>
          <dt>Bank</dt><dd>Handelsbanken, Sweden</dd>
          <dt>IBAN</dt><dd><code>SE21 6000 0000 0000 4459 5719</code></dd>
          <dt>BIC</dt><dd><code>HANDSESS</code></dd>
          <dt>Account number</dt><dd>44 595 719 <span class="fine">(within Sweden)</span></dd>
          <dt>Reference</dt><dd>your name, and “donation”</dd>
        </dl>
        <a class="btn btn-primary" id="bank-ask" href="mailto:sal.giambruno@dysnet.org?cc=info@dysnet.org&amp;subject=Donation%20to%20DysNet&amp;body=Hello%2C%0A%0AI%20have%20made%20a%20one-off%20gift%20of%20EUR%2050%20by%20bank%20transfer.%0A%0AThank%20you%2C%0A">Tell the treasurer it is on its way</a>
        <span class="fine">A receipt, a question or a standing order: <a href="mailto:sal.giambruno@dysnet.org">sal.giambruno@dysnet.org</a> or <a href="mailto:info@dysnet.org">info@dysnet.org</a>.</span>
      </div>

      <div class="give-via">
        <h3 class="h4">Do you need a receipt for your tax return?</h3>
        <p>DysNet is registered in Sweden, and a Swedish receipt helps a Swedish taxpayer and nobody else. Your national member association is registered where <em>you</em> pay tax, and can usually give a receipt your own tax office accepts.</p>
        <p>So give through your association, write <strong>DysNet</strong> in the reference or message field, and ask them to pass the gift on. The money reaches the same work, and you keep the deduction. <a href="/about/members/">Find your national association</a>.</p>
        <p class="give-via-note">Each association decides for itself whether it can forward a gift marked this way and issue a receipt for it, so <strong>ask yours before you give</strong>.</p>
      </div>

    </div>
  </div>
</section>

<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">01 · Other ways to help</p>
    <h2 class="h2">Not all gifts are money.</h2>
    <div class="grid cols-3" style="margin-top:var(--space-4)">
      <div class="card"><h3 class="h4">Association membership</h3><p>Membership gives your association a vote and a voice, and your families the registers. An associate status exists for associations with limited capacity. Write to the board for the terms.</p><p class="meta"><a href="/about/members/">How to join</a></p></div>
      <div class="card" style="--acc:var(--dys-green);--acc-text:var(--dys-green-text)"><h3 class="h4">In-kind contributions</h3><p>Design, hosting, translation or research hours: the most valuable gifts for the registers come from partners of member associations.</p><p class="meta"><a href="mailto:info@dysnet.org?subject=In-kind%20contribution">Offer a skill</a></p></div>
      <div class="card acc-centres"><h3 class="h4">Give your time</h3><p>A few hours a month move the work forward: helping us raise funds, reading the evidence that feeds the registers, welcoming and supporting member associations, or carrying our position to national and European bodies.</p><p class="meta"><a href="mailto:info@dysnet.org?subject=Volunteering%20with%20DysNet">Volunteer with us</a></p></div>
    </div>
  </div>
</section>
""",
}

STATUTE_SECTIONS = [
    ("Identity and objective (§1–2)", [
        ("§1 · Name, registration and official language", "The organisation is named DYSNET, a not-for-profit NGO registered in Stockholm, Sweden. The official language is English."),
        ("§2 · Objective", "DYSNET safeguards the interests of persons with congenital limb-reduction deficiencies (dysmelia): an information service for patient groups; a network for sharing information across the EU and beyond; advocacy and support for research; a network of specialist practitioners and centres of best practice; promotion of assistive technologies; systems for managing clinical information; advice to national authorities; and research on social and economic inclusion."),
    ]),
    ("Membership (§3–7)", [
        ("§3 · Membership", "Open to patient groups and organisations representing people affected by dysmelia. Entities led by people affected by dysmelia that accept the objectives and statutes shall be accepted; others at the Board's discretion."),
        ("§4 · Members' rights", "All members may take part in DysNet's activities and must be kept informed of the organisation's work."),
        ("§5 · Members' duties", "Pay the membership fee, work for DysNet's development, abide by the statutes, promote DysNet, and stay loyal to its objectives."),
        ("§6 · Expulsion", "The Board may expel a member for false statements at admission, conduct bringing DysNet into disrepute, serious breaches, or unpaid fees; the member may appeal to a general meeting within 30 days."),
        ("§7 · Withdrawal", "Members may withdraw on written request; fees are not refunded."),
    ]),
    ("Governance (§8–15)", [
        ("§8–10 · General meetings", "The AGM is held before 30 April each year; notice 30–60 days ahead; motions at least 21 days ahead. The AGM approves accounts, elects the chair, deputy chair, Board, auditors and nominating committee, and sets fees."),
        ("§11 · Extraordinary meetings", "Convened by the Board when necessary or at the request of one third of members; shorter notice allowed when the situation requires."),
        ("§12 · Voting", "Members in good standing vote; decisions by simple majority unless stated otherwise; a member may carry up to five written proxies."),
        ("§13 · The Board", "Four to nine members, elected for two years; the majority of the Board shall be people with dysmelia. The Board appoints operating officers and may co-opt up to three members."),
        ("§14–15 · Remuneration and signature", "The AGM decides remuneration; DysNet is bound by the Board, by two Board members jointly, or by two appointed signatories jointly."),
    ]),
    ("Finances and audit (§16–18)", [
        ("§16 · Accounts", "Kept per accepted bookkeeping principles; closed each financial year and handed to the auditor by 15 February."),
        ("§17 · Audit", "At least one auditor with at least one deputy."),
        ("§18 · Confidentiality", "Personal data is handled as prescribed by law and DysNet's confidentiality rules."),
    ]),
    ("Amendments and validity (§19–21)", [
        ("§19 · Amendment and dissolution", "Amending the statutes requires two general meetings (annual or extraordinary) and a two-thirds majority of votes cast. Dissolution requires a written request of two thirds of voting members, confirmed by qualified majority."),
        ("§20–21 · Validity", "These statutes apply since their adoption by the two Extraordinary Meetings of 20 October 2011."),
    ]),
]


def statute_html():
    out = []
    for i, (heading, arts) in enumerate(STATUTE_SECTIONS, 1):
        out.append(f'<div class="tick"></div><p class="eyebrow">0{i} · Statutes</p><h2 class="h2">{heading}</h2>')
        for t, body in arts:
            out.append(f'<h3 class="h4" style="margin-top:var(--space-3)">{t}</h3><p>{body}</p>')
    return "\n".join(out)


PAGES["/about/statutes/"] = {
    "title": "Statutes",
    "desc": "The statutes of DYSNET (EDRIC), adopted 20 October 2011: objective, membership, meetings, board, accounts and amendment rules, readable online.",
    "crumbs": [("/about/", "About"), ("/about/statutes/", "Statutes")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · Governing text</p>
    <h1 class="display">The DysNet statutes, readable online.</h1>
    <p>Adopted by the two Extraordinary Meetings of 20 October 2011, replacing the founding regulations of 13 October 2008. This page is an abridged, plain-language rendering for orientation; the signed PDF remains the authoritative text and is available from the secretary.</p>
    {statute_html()}
  </div>
</section>
""",
}

PAGES["/knowledge/guides/patient-owned-registry/"] = {
    "title": "What is a patient-owned registry?",
    "desc": "A two-minute guide: what a patient-owned registry of limb malformations is, who owns the data, and what it changes for families and researchers.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/guides/patient-owned-registry/", "Guide: patient-owned registry")],
    "body": """
<section>
  <div class="container">
    <div class="tick" style="background:var(--dys-green)"></div>
    <p class="eyebrow" style="color:var(--dys-green-text)">Guide · Two-minute read</p>
    <h1 class="display">What is a patient-owned registry?</h1>
    <p>Plain language, no jargon. This is the first of a series of short guides that explain one idea at a time.</p>

    <div class="tick"></div><p class="eyebrow">01 · The idea</p>
    <h2 class="h2">A shared, well-kept list.</h2>
    <p>A registry is a structured list of people who share a condition: which condition, treated where, with what outcome. Kept well, it is the raw material of research; nobody can study what nobody can count.</p>

    <div class="tick"></div><p class="eyebrow">02 · What “patient-owned” changes</p>
    <h2 class="h2">The community holds the keys.</h2>
    <p>In most registries, a hospital or a company decides what is collected and who may use it. In a patient-owned registry, each person keeps control of their own data, and the member associations and the DysNet board share the responsibility for which research may be proposed to families. Families contribute on explicit consent, can withdraw at any time, and the data serves care and research only; it is never bought or sold.</p>

    <div class="tick"></div><p class="eyebrow">03 · For families</p>
    <h2 class="h2">Answer questions once, help every family after you.</h2>
    <p>Every entry makes the picture sharper: how frequent each condition is, which treatments help at which age, where expertise lives. The next family gets better answers because yours were recorded.</p>

    <div class="tick"></div><p class="eyebrow">04 · For researchers</p>
    <h2 class="h2">Comparable data across countries, at last.</h2>
    <p>Limb-difference research is starved of data because cases are scattered across countries and too few are described well enough to investigate their causes. An interoperable registry pools them across borders in one comparable format, large enough to study.</p>

    <div class="tick"></div><p class="eyebrow">05 · How DysNet builds it</p>
    <h2 class="h2">Association by association, with a technical partner.</h2>
    <p>Member associations bring their families in, country by country. <a href="https://www.healthdatasafe.org/en/">Health Data Safe</a>, a Swiss non-profit foundation, is the technical and operational partner, mandated by the AGM of 26 August 2026. Read more on <a href="/registry/">the registry page</a>.</p>
  </div>
</section>
""",
}

# ── Privacy ─────────────────────────────────────────────────────────────────
# The first version ran to twelve sections and 2,240 words, which is the notice of an
# organisation that collects things. This one collects almost nothing, so the page says that
# and spends its length only where a reader gains something: the registers name professionals
# (art. 14, the part such notices skip), and the registers are not behind a consent wall.
PAGES["/privacy/"] = {
    "title": "Privacy",
    "desc": "DysNet asks once whether it may count your visit, and collects nothing else through this site. What is processed, what the registers name, and your rights under the GDPR.",
    "crumbs": [("/privacy/", "Privacy")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Privacy · Articles 13 and 14 GDPR</p>
    <h1 class="display">We collect nothing unless you say yes.</h1>
    <p>No advertising, no tracker that follows you elsewhere, no account and no form. The one thing we ask is whether we may count your visit, and a banner asks you once. Say no and nothing changes: every page and every register stays open either way. This page says what is processed, what our registers name, and how to exercise your rights. Questions go to <a href="mailto:info@dysnet.org?subject=Data%20protection">info@dysnet.org</a>.</p>
    <p class="annex-note">Version of 22 September 2026; earlier versions stay in <a href="https://github.com/dysnet-org/website">the public history of this site</a>. The controller is DysNet Ideell Förening, organisation number 802444-3015, Nybodagatan 1, 171 42 Solna, Sweden, with an office at Rue du Chantier 2, B-1000 Brussels. We have appointed no data protection officer, and we will name one before the registry begins processing health data.</p>

    {opener("01", "The site", "What happens when you read a page.", toc="Reading a page")}
    <ul>
      <li><strong>Your request reaches our host, not us.</strong> GitHub Pages serves these files, so GitHub receives what every web request carries: your IP address, the time, the page and your browser. It uses that to deliver the page and to protect the service. We keep no visitor database and receive nothing visitor-level, so nobody here can look up who read what. Legal basis: our legitimate interest in a website that works, Article 6(1)(f). The site is static files with no database and no login, served over HTTPS.</li>
      <li><strong>We count visits only if you accept.</strong> A banner asks once. Accept, and Google Analytics records the page, the time, the country your address places you in, and your browser and device, and it gives your browser a random number so that a second page counts as the same visit rather than a new stranger. It tells us which registers people actually reach. It does not tell us who you are, and every advertising feature Google offers is switched off. Decline, and none of it loads and nothing is stored. Legal basis: your consent, Article 6(1)(a).</li>
      <li><strong>Your answer is remembered, and so is the map card.</strong> Your browser keeps your yes or no so the banner does not ask again, and on the pages with a map it keeps the word <em>open</em> or <em>closed</em> so the information card stays as you left it. Neither carries an identifier and neither reaches us. To change your answer, use the button in section 04.</li>
      <li><strong>Videos wait for you.</strong> Nothing loads from Google until you press play. Then Google receives your IP address and device information under its own policy.</li>
    </ul>

    {opener("02", "Email", "If you write to us.", toc="If you write to us")}
    <p>Our mail runs on Zoho's European service, with Zoho Corporation B.V. in Utrecht as our processor. We read your message and answer it, and we keep the thread. We do not delete correspondence on a timer, because a question from a family or an association often resumes years later and that record is part of what the network is for. You can ask us to erase your correspondence at any time, and we will. Membership and donation records that count as accounting information stay for the seven years after the end of the calendar year in which the financial year closed, which Swedish law requires (Bokföringslag 1999:1078, chapter 7).</p>
    <p>Legal bases: answering the people who write to us, Article 6(1)(f); membership, donations and agreements, Article 6(1)(b) and (c). If you describe your own or your child's condition, you are sending health data. We may hold it because we are a non-profit body with a health aim, acting for our members and the people in regular contact with us, and because we disclose it to nobody outside (Article 9(2)(d)). Write in general terms if you would rather. We ask for no medical detail we do not need.</p>

    {opener("03", "Registers", "The registers name professionals, not patients.", toc="What the registers name")}
    <p>Some of what we publish concerns named professionals we never asked, and Article 14 requires us to say so. The <a href="/knowledge/researchers/">researcher register</a> holds {len(RESEARCHERS.get("teams", []))} research teams with their institution, country, the surnames and initials of first and last authors and their publications on our conditions, taken from the affiliations recorded in PubMed. The <a href="/knowledge/bibliography/">bibliography</a> holds {len(BIB.get("entries", [])):,} references with their authors as published. The <a href="/knowledge/ongoing-studies/">studies</a> page carries the contact each study gives for itself, <a href="/about/members/">member associations</a> the addresses they publish for themselves, and <a href="/about/people/">People</a> our board and the volunteers who maintain the registers. Care centres and registries name institutions only.</p>
    <p>Legal basis: our legitimate interest, Article 6(1)(f), in publishing a free resource on conditions too few people study. We keep to professional information its holders have already published in a professional capacity, and we publish nothing about anyone's health. To be corrected or removed, write and name the entry: we act within 30 days and ask you for no reason. One limit we state openly, because the registers are open data under CC BY 4.0: a copy downloaded before a removal stays with whoever took it.</p>

    {opener("04", "No wall", "The registers stay open.", toc="The registers stay open")}
    <p>We considered putting the registers behind an analytics tracker you would have to accept. We had the question tested first, and it cannot be done lawfully. It would also be wrong: these pages describe a health condition, so a record that you read them would say something about your own or your child's health. A family looking up a diagnosis at two in the morning owes us nothing in exchange.</p>
    <p>This page used to promise that if we ever measured our traffic we would count pages rather than people, and say so here before we started. We are saying so. Since 22 September 2026 a banner asks whether we may count visits with Google Analytics, and it counts only for readers who accept. Refusing costs you nothing at all, which is the whole point: the registers are not the payment.</p>
    <p>You can change your mind whenever you like, in either direction.</p>
    <p><button type="button" class="btn btn-ghost btn-sm" data-consent-reset>Change your answer</button></p>
    <p class="annex-note">Why the wall is unlawful, for the reader who wants it: Swedish law allows an identifier to be stored on your device only with your consent, or where that is strictly necessary for the service you asked for (9 kap. 28 § lagen (2022:482) om elektronisk kommunikation). Consent extracted by withholding the content is not freely given (European Data Protection Board guidelines on consent of 4 May 2020, paragraphs 39 to 41). Our banner asks for that consent and takes no for an answer, leaving every page readable either way, which is the condition those guidelines set.</p>

    {opener("05", "The registry", "Nothing is collected yet.", toc="The registry")}
    <p>The limb-malformation registry does not exist, and no health data reaches us through this site. When it opens it will carry its own notice, published before the first family enters anything. Four things will hold.</p>
    <ul>
      <li>Each person holds their own account and decides what goes into it.</li>
      <li>Consent is explicit, given study by study, and withdrawable at any time (Article 9(2)(a)).</li>
      <li>No association enrols anybody. Families are invited, and they enter their own information.</li>
      <li>We do not sell the data, and we will not pass it to insurers or employers. Bulk access without the consent of the people described will not be possible.</li>
    </ul>
    <p>The technical partner is <a href="https://www.healthdatasafe.org/en/">Health Data Safe</a>. Its statutes rule out any sale of health data and limit its use to care and research, and they provide that personal data is never treated as an asset of the foundation.</p>

    {opener("06", "Your rights", "What you can ask, and whom to tell.", toc="Your rights")}
    <p>You may ask us to do any of this, and Article 15 to Article 21 GDPR give you the right:</p>
    <ul>
      <li>give you a copy of what we hold about you, or correct it;</li>
      <li>erase it, or stop using it while a question about it is open;</li>
      <li>hand it over in a form you can take elsewhere;</li>
      <li>stop processing that rests on our legitimate interest.</li>
    </ul>
    <p><strong>In the registry, you will not have to ask us.</strong> These rights are part of how the registry is built rather than a procedure wrapped around it. Each person holds their own account at Health Data Safe, and from it they review, correct, export and delete their own data, and withdraw a consent to share, without writing to anybody. Health Data Safe already publishes a <a href="https://www.healthdatasafe.org/users/data-portability/">self-service download of everything in an account</a> and a <a href="https://www.healthdatasafe.org/users/data-deletion/">route to delete it</a>. Until the registry opens, the rights above are exercised by writing to us, and we carry them out by hand.</p>
    <p>Consent, where we rely on it, can be withdrawn at any time. Write to <a href="mailto:info@dysnet.org?subject=Data%20protection%20request">info@dysnet.org</a>. We answer within one month, free of charge, and if a request is genuinely complex we say so inside that month (Article 12(3)). We take no automated decisions about anybody and we build no profiles.</p>
    <p>Three others ever touch anything: <strong>GitHub</strong> hosts the site from the United States, and states that it complies with the EU-US Data Privacy Framework; <strong>Zoho</strong> carries our mail on its European service; and <strong>Google</strong> counts the visits of readers who accept the banner, from the United States, and states that it complies with the same framework. Nobody else. We use no advertising network, no data broker and no mailing-list service, and we have never sold or rented personal data.</p>
    <p>If we get something wrong, tell us, because most of it we can simply fix. You may also complain to a supervisory authority, choosing the one where you live, where you work or where you think the problem happened (Article 77), and you may go to court (Article 79). Ours is <strong>Integritetsskyddsmyndigheten</strong>, the Swedish Authority for Privacy Protection: Box 8114, 104 20 Stockholm, <a href="mailto:imy@imy.se">imy@imy.se</a>, +46 8 657 61 00, which takes complaints through <a href="https://www.imy.se/en/individuals/forms-and-e-services/file-a-gdpr-complaint/">its own form</a>.</p>
  </div>
</section>
""",
}

# ── Accessibility ────────────────────────────────────────────────────────────
# A network for people with limb differences cannot publish a site its own members
# struggle to operate, so this page states what was measured rather than what we hope.
# Every figure below came from a run over the built pages on 17 September 2026, and the
# checks are cheap enough to repeat on any build.
PAGES["/accessibility/"] = {
    "title": "Accessibility",
    "desc": "How accessible this site is, measured rather than claimed: what we tested, what passed, where it still falls short, and how to tell us when something blocks you.",
    "crumbs": [("/accessibility/", "Accessibility")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Accessibility · Statement</p>
    <h1 class="display">What we measured, and where this site still falls short.</h1>
    <p>DysNet exists for people with a physical difference, so a site our own members struggle to operate would contradict the point of it. We hold www.dysnet.org to <strong>WCAG 2.2, level AA</strong>, whether or not the law requires that of an association our size. This page says what we tested, what passed, and what did not.</p>
    <p class="annex-note">Statement of 17 September 2026, written from a run over all 24 pages of the site on that date.</p>

    {opener("01", "The measurements", "What we tested, and what came back.", toc="What we measured")}
    <div class="annex-wrap">
      <table class="annex priv-table">
        <thead><tr><th scope="col">Check</th><th scope="col">Result</th></tr></thead>
        <tbody>
          <tr><th scope="row">Text alternatives</th><td>31 images, every one carrying alt text.</td></tr>
          <tr><th scope="row">Names of controls</th><td>2,224 links and 239 buttons, every one with a name a screen reader can announce.</td></tr>
          <tr><th scope="row">Headings</th><td>One h1 per page, and no level skipped anywhere.</td></tr>
          <tr><th scope="row">Landmarks</th><td>Every page carries a main landmark and a skip link before it.</td></tr>
          <tr><th scope="row">Tables</th><td>All 7 data tables use real header cells with a scope.</td></tr>
          <tr><th scope="row">Contrast</th><td>32 distinct colour, size and weight combinations on the most colour-heavy page, none below the AA threshold.</td></tr>
          <tr><th scope="row">Target size</th><td>397 controls on that same page, every one at least 24 by 24 pixels.</td></tr>
          <tr><th scope="row">Keyboard</th><td>Focus is always visible, as a 3-pixel outline. Nothing needs a drag, a double-click or a steady hand.</td></tr>
          <tr><th scope="row">Motion</th><td>Animation stops when your system asks for reduced motion.</td></tr>
          <tr><th scope="row">Changing figures</th><td>When a filter changes a count, the new figure is announced rather than silently repainted.</td></tr>
        </tbody>
      </table>
    </div>
    <p>Two of those results came from fixes made on the day of this statement: the target-size floor, and the announcement of filter counts. We publish the date so you can hold the claim to it.</p>

    {opener("02", "Shortfalls", "Where it does not reach the standard.", toc="Where it falls short")}
    <ul>
      <li><strong>The maps are drawn, not written.</strong> A screen reader cannot read the points plotted on the world map, and no alt text would carry a map honestly. Everything the maps show exists in text on the same pages, in the epidemiology tables, the care-centre list and the registry list, and in the data file that <a href="/knowledge/">each register page</a> offers for download.</li>
      <li><strong>Our PDFs are not tagged.</strong> The five demands, and the briefs we publish for boards, are laid out for print rather than marked up for a screen reader. The same content sits in HTML on <a href="/voice/">the Voice pages</a>. Ask us and we will send you any of it as plain text.</li>
      <li><strong>The site is in English only.</strong> For a network whose members are German, Italian, French, Spanish, Swedish, Dutch and Norwegian, that is an accessibility barrier as real as any technical one, and we know it.</li>
      <li><strong>No independent audit has been commissioned,</strong> and we have not tested with every assistive technology. What is above was measured by our own tools, which find what they are built to find and no more.</li>
      <li><strong>There is no easy-read version</strong> and no sign-language version of the main pages.</li>
    </ul>

    {opener("03", "Tell us", "If something here blocks you.", toc="If something blocks you")}
    <p>Write to <a href="mailto:info@dysnet.org?subject=Accessibility">info@dysnet.org</a> and say what you were trying to do and what stopped you. You do not need technical words for it, and telling us which page it was is enough to start. We answer within 10 working days, and where we cannot fix something quickly we will say so and send you the content another way.</p>
    <p>If an assistive technology of yours behaves differently from the ones we tested, that is worth telling us too. We would rather hear it from you than keep publishing a statement that is true only of our own machines.</p>
  </div>
</section>
""",
}

PAGES["/404/"] = {
    "title": "Page not found",
    "desc": "The page you are looking for does not exist or has moved. Find your way back to the DysNet knowledge base, registry and network pages.",
    "body": """
<section>
  <div class="container e404">
    <p class="code">404</p>
    <h1 class="h2-lg">Page not found.</h1>
    <p>The page you are looking for does not exist or has moved with the new site.</p>
    <nav class="links" aria-label="Return navigation">
      <a class="btn btn-primary" href="/">Go to the homepage</a>
      <a class="btn btn-ghost" href="/contact/">Contact us</a>
    </nav>
    <script>
      // Old Wix URLs not covered by a redirect stub: send them to the closest new section.
      (function () {
        var p = location.pathname.replace(/[/]+$/, "");
        var rules = [[/^[/]post[/]/, "/voice/reports/"], [/^[/]copy-.*(aussiehands|avbs|norske|limbs4life|contergan)/, "/about/members/"],
          [/^[/]copy-.*(pirola|moro)/, "/about/#board"], [/^[/]copy-.*(privacy|terms|meeting)/, "/about/transparency/"],
          [/^[/]copy-of-about-1$/, "/knowledge/researchers/"], [/^[/]copy-.*about/, "/knowledge/understanding-dysmelia/"],
          [/^[/]copy-.*bank/, "/donate/"], [/^[/](profile|forum|members|our-members)/, "/about/members/"], [/^[/]copy-/, "/"]];
        for (var i = 0; i < rules.length; i++) if (rules[i][0].test(p)) { location.replace(rules[i][1]); return; }
      })();
    </script>
    <p style="margin-top:var(--space-4);font-size:var(--text-small);color:var(--dys-muted)">Or jump to:
      <a href="/knowledge/">Knowledge</a> · <a href="/registry/">The registry</a> · <a href="/voice/reports/">Reports</a> · <a href="/about/members/">Member associations</a> · <a href="/donate/">Support DysNet</a></p>
  </div>
</section>
""",
}




# ─────────────── Redirects for the old Wix site's URLs ───────────────
# GitHub Pages has no server-side redirects, so each old path gets a stub page
# (meta refresh + canonical + script). Inventory from the Wix sitemap, Aug 2026.
_POSTS = ["a-week-full-of-opportunities", "artificial-intelligence-and-disability",
    "biorobotics-francesco-clemente-in-dialogue-with-claudio-pirola", "chez-assedea-in-paris",
    "claudio-pirola-will-be-at-civil-week-milano", "design-a-stunning-blog", "dysnets-agm-august-1st-at-3pm-cest",
    "edf-european-disability-forum-general-assembly",
    "ern-a-holistic-vision-of-disability-claudio-pirola-may-11th-at-3-00-pm-at-iit-istituto-italiano", "ern-presentation",
    "eurordis-european-rare-diseases-organisation", "eurordis-meeting-in-brussels-12-13-december",
    "follow-up-eurordis-membership-meeting", "franck-brouillard-handisport", "grow-your-blog-community",
    "how-high-technology-can-support-persons-with-disability-01", "in-paris-for-eurordis", "interview",
    "living-the-values-of-an-association", "manage-your-blog-from-your-live-site",
    "meeting-at-the-dutch-ministry-of-interior-and-parliament", "more-accessibility-for-persons-with-disability",
    "presentation-bionic-hand-thank-you-prensilia", "rare-barometer-survey-get-involed", "rare-disease-europe-agm",
    "stockholm-eurordis-membership-meeting-2023", "thalidomide-60-we-re-still-here",
    "webinar-by-cerebral-palsy-eu-on-advocacy-skills"]
REDIRECTS = {
    "/knowledge/prevalence-of-dysmelia": "/knowledge/epidemiology/",
    "/about/people": "/about/#board",
    "/knowledge/research-library": "/knowledge/bibliography/",
        "/people": "/about/#board", "/our-members": "/about/members/", "/members": "/about/members/",
    "/conditions": "/knowledge/understanding-dysmelia/", "/blog": "/voice/reports/", "/forum": "/about/members/",
    "/whatifyourbaby": "/knowledge/understanding-dysmelia/", "/aussiehands": "/about/members/", "/raggiungere": "/about/members/",
    "/copy-of-about": "/knowledge/understanding-dysmelia/", "/copy-of-about-1": "/knowledge/researchers/",
    "/copy-of-bank-account": "/donate/", "/copy-of-privacy": "/about/transparency/",
    "/copy-of-terms-of-use": "/about/transparency/", "/copy-of-terms-of-use-1": "/about/transparency/",
    "/copy-of-annual-general-meeting-2022": "/about/transparency/", "/copy-of-board-meeting-8-22": "/about/transparency/",
    "/copy-of-claudio-pirola": "/about/#board", "/copy-of-claudio-pirola-1": "/about/#board", "/copy-of-claudio-pirola-2": "/about/#board",
    "/copy-of-mirko-moro": "/about/#board", "/copy-of-dysnet": "/about/",
}
for _s in ["copy-of-about-2", "copy-2-of-about", "copy-3-of-about", "copy-4-of-about", "copy-5-of-about"]:
    REDIRECTS["/" + _s] = "/knowledge/understanding-dysmelia/"
for _s in ["copy-of-support-messages", "copy-of-support-messages-1", "copy-of-support-messages-2", "copy-of-support-messages-3"]:
    REDIRECTS["/" + _s] = "/about/"
for _s in (["copy-of-aussiehands", "copy-of-aussiehands-1", "copy-of-aussiehands-2", "copy-of-limbs4life", "copy-of-contergan-austria",
            "copy-of-den-norske-thalidomide-fore", "copy-2-of-den-norske-thalidomide-fo"] +
           [f"copy-of-den-norske-thalidomide-fore-{i}" for i in range(1, 6)] + ["copy-of-avbs"] + [f"copy-of-avbs-{i}" for i in range(1, 14)]):
    REDIRECTS["/" + _s] = "/about/members/"
for _s in _POSTS:
    REDIRECTS["/post/" + _s] = "/voice/reports/"


def redirect_html(new_path):
    url = SITE + new_path
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Page moved · DysNet</title>'
            f'<meta name="robots" content="noindex"><link rel="canonical" href="{url}">'
            f'<meta http-equiv="refresh" content="0; url={new_path}"><script>location.replace({json.dumps(new_path)});</script>'
            f'<style>body{{font-family:system-ui,sans-serif;margin:3rem;color:#241a33}}a{{color:#7222c2}}</style></head>'
            f'<body><p>This page has moved to <a href="{new_path}">{url}</a>.</p></body></html>\n')


def page_dates(path, new_html):
    """datePublished = first commit of the page; dateModified = last commit, or today when this build changes the page."""
    import subprocess, datetime
    rel = "docs" + path + "index.html"
    today = datetime.date.today().isoformat()
    def git(*args):
        try: return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT.parent, timeout=20).stdout.strip()
        except Exception: return ""
    # the cache-busting query changes on every asset build; a page that only carries a new hash
    # has not changed, and counting it as changed made all 22 pages claim the same date every day
    # and the draft this is compared against is built without dates, so its JSON-LD has no
    # datePublished/dateModified keys and no article:*_time tags at all: those go too, or no page
    # ever matches its committed copy and every build dates every page today
    strip = lambda t: re.sub(r', "date(?:Published|Modified)": "[^"]*"|<meta property="article:(?:published|modified)_time" content="[^"]*">|\?v=[0-9a-f]+|\d{4}-\d{2}-\d{2}|Page updated [^<]*|\d{1,2} [A-Z][a-z]+ \d{4}', "", t)
    committed = git("show", f"HEAD:{rel}")
    first = (git("log", "--diff-filter=A", "--format=%cs", "--", rel).splitlines() or [today])[-1]
    if not committed: return {"published": today, "modified": today}
    if strip(committed) != strip(new_html):
        return {"published": first, "modified": today}
    # Unchanged: keep the date the committed page already states. The file's last commit is not that
    # date, because every stylesheet or script change rewrites the cache-busting hash in every page and
    # so commits them all: a CSS fix would otherwise date all 24 pages to the day it was made.
    kept = re.search(r'"dateModified": "(\d{4}-\d{2}-\d{2})"', committed)
    return {"published": first, "modified": kept.group(1) if kept else (git("log", "-1", "--format=%cs", "--", rel) or today)}


EXTRA_LD = {
    "/knowledge/understanding-dysmelia/": lambda: [conditions_ld()],
    "/knowledge/bibliography/": lambda: [dataset_ld("DysNet bibliography on congenital limb difference and dysmelia", "Peer-reviewed references on limb differences, thalidomide embryopathy and their causes, verified against PubMed and Crossref; sources: Orphanet epidemiology, member associations' and registries' websites, fixed PubMed queries.", "/knowledge/bibliography/", "bibliography.json", ["dysmelia", "limb reduction defects", "thalidomide embryopathy", "bibliography", "PubMed"], f"{len(BIB.get('entries', []))} references")],
    "/knowledge/registries/": lambda: [dataset_ld("Registries recording congenital limb differences", "Population and disease registries listed on Orphanet for the site's ORPHAcodes, plus the French population registries per Santé publique France, with coverage and websites.", "/knowledge/registries/", "registries.json", ["registry", "congenital anomalies", "EUROCAT", "Orphanet"], f"{len(ORPHA_REGS.get('registries', []))} registries")],
    "/knowledge/care-centres/": lambda: [dataset_ld("Care centres for congenital limb difference in the DysNet register", "Reference and competence centres, prosthetics and rehabilitation centres and expert clinics, with coordinates, type, specialism and the source that names or verifies each one.", "/knowledge/care-centres/", "care-centres.json", ["care centres", "limb difference", "prosthetics", "reference centres"], f"{len(CARE_CENTRES)} centres")],
    "/knowledge/researchers/": lambda: [dataset_ld("Research teams publishing on congenital limb difference", "Institutions of first and senior authors of the DysNet bibliography, aggregated from PubMed affiliations, with publication counts, years, conditions and coordinates.", "/knowledge/researchers/", "researchers.json", ["researchers", "limb difference", "dysmelia", "PubMed"], f"{len(RESEARCHERS.get('teams', []))} teams")],
    "/knowledge/epidemiology/": lambda: [dataset_ld(
        "Live births a year by country, for the DysNet expected-births table",
        "Annual live births for every country, computed from the World Bank's population and crude birth rate series, used with registry birth prevalences to estimate how many affected births a year each limb difference means.",
        "/knowledge/epidemiology/", "births.json", ["births", "birth prevalence", "expected cases", "limb difference", "World Bank"],
        f"{len(BIRTHS['countries'])} countries")],
    "/about/": lambda: [{"@context": "https://schema.org", "@graph": PEOPLE_LD}],
    "/knowledge/teratogens/": lambda: [dataset_ld("Substances and products with effects on the unborn child (DysNet teratogens register)", "Substances classified for developmental toxicity in the EU harmonised classification (CLP Annex VI), the Japanese government's GHS classification (NITE), developmental toxicants on California's Proposition 65 list, medicines under EMA pregnancy prevention programmes, alcohol and tobacco; with source, level of evidence, regulatory status per jurisdiction, and the decisions authorities have taken: EU pesticide approvals and refusals, REACH restrictions, treaty bans and national bans.", "/knowledge/teratogens/", "teratogens.json", ["teratogens", "developmental toxicity", "reproductive toxicity", "CLP", "Proposition 65", "pregnancy"], f"{TERA.get('counts', {}).get('total', 0)} substances")],
}
DATA_FILES = {"teratogens.json": "teratogens.json", "births.json": "births.json", "bibliography.json": "bibliography.json", "registries.json": "orphanet-registries.json", "registry-areas.json": "registry-areas.json", "orphanet-hierarchy.json": "orphanet-hierarchy.json", "condition-prevalence.json": "condition-prevalence.json", "care-centres.json": "care-centres.json", "researchers.json": "researchers.json", "registry-zones.json": "registry-zones.json"}


def build():
    written = []
    import shutil
    (ROOT / "data").mkdir(exist_ok=True)
    for out_name, src_name in DATA_FILES.items():
        src = ROOT.parent / "tools" / src_name
        if src.exists(): shutil.copyfile(src, ROOT / "data" / out_name)
    PAYLOADS["conditions.json"] = _conditions_payload()   # read live by the registry's condition question
    for name, payload in PAYLOADS.items():       # the registers' client data, fetched after first paint
        (ROOT / "data" / name).write_text(payload, encoding="utf-8")
    page_mod = {}
    for path, page in PAGES.items():
        out_dir = ROOT / path.strip("/")
        out_dir.mkdir(parents=True, exist_ok=True)
        extra = list(page.get("jsonld") or []) + (EXTRA_LD[path]() if path in EXTRA_LD else [])
        probe = head(page["title"], page["desc"], path, page.get("is_home", False), page.get("og"), extra) + header_html(path if path != "/" else "-") + (crumbs(*page["crumbs"]) if page.get("crumbs") else "") + page["body"].replace("__MAP_HERO__", MAP_HERO) + FOOTER
        dates = page_dates(path, rebase(probe)); page_mod[path] = dates["modified"]
        html = head(page["title"], page["desc"], path, page.get("is_home", False), page.get("og"), extra, dates)
        html += header_html(path if path != "/" else "-")
        if page.get("crumbs"):
            html += crumbs(*page["crumbs"])
        html += page["body"]
        html = html.replace("__MAP_HERO__", MAP_HERO)
        html += FOOTER.replace("__PAGE_DATE__", __import__("datetime").date.fromisoformat(dates["modified"]).strftime("%-d %B %Y"))
        (out_dir / "index.html").write_text(rebase(html), encoding="utf-8")
        written.append(path)

    # Redirect stubs for the old Wix URLs
    for old_path, new_path in REDIRECTS.items():
        d = ROOT / old_path.strip("/")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(redirect_html(new_path), encoding="utf-8")
    print(f"  + {len(REDIRECTS)} redirect stubs for old Wix URLs")

    # Root 404.html (GitHub Pages convention, as on the HDS site)
    import shutil
    shutil.copyfile(ROOT / "404" / "index.html", ROOT / "404.html")

    # Search index for the ⌘K search (HDS Search.astro pattern)
    cond_kw = " ".join([c[0] for c in CONDITIONS]
                       + [t for kids in SUBCONDITIONS.values() for _d, t in kids]
                       + [x for kids in SUBCONDITIONS.values() for d, _t in kids
                          for x in (HIER["nodes"].get(d) or {}).get("synonyms") or []])
    search_index = []
    for p, page in PAGES.items():
        if p == "/404/":
            continue
        kw = cond_kw if "understanding-dysmelia" in p else ""
        search_index.append({"url": p, "title": "Home" if p == "/" else page["title"],
                             "desc": page["desc"][:140], "keywords": kw})
    (ROOT / "search-index.json").write_text(json.dumps(search_index, ensure_ascii=False), encoding="utf-8")

    # sitemap.xml — demonstrates the SEO deliverable for the real launch
    urls = "\n".join(
        f"  <url><loc>{SITE}{p}</loc><lastmod>{page_mod[p]}</lastmod></url>" for p in PAGES if p != "/404/")
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding="utf-8")

    # GitHub Pages: serve the folder verbatim, no Jekyll processing
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")

    # Custom domain for GitHub Pages; absent on the project-URL build
    cname = ROOT / "CNAME"
    if DEPLOY == "prod":
        cname.write_text("www.dysnet.org\n", encoding="utf-8")
    elif cname.exists():
        cname.unlink()

    # One-page briefing PDF of the five demands, rendered from the same data
    print("  " + build_brief_pdf())
    print("  " + build_pilot_pdf())

    # robots.txt — everything is open, to search engines and to AI systems alike. The AI crawlers are
    # named one by one because silence reads as an oversight; this is a knowledge site and being quoted,
    # with attribution, is the point.
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot",
               "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot",
               "meta-externalagent", "Bingbot", "Amazonbot", "Bytespider", "DuckAssistBot", "cohere-ai", "MistralAI-User"]
    (ROOT / "robots.txt").write_text(
        "# DysNet welcomes search engines and AI systems. Everything here is public, and the registers\n"
        "# are published as data under CC BY 4.0: see /llms.txt and /data/.\n"
        "User-agent: *\nAllow: /\n\n"
        + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in ai_bots)
        + f"Sitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    # IndexNow: the key file Bing, Yandex and Seznam fetch to check that a submission really comes
    # from this site. tools/ping-indexnow.sh submits the sitemap's URLs after a deploy.
    (ROOT / "f1faf0b594023c386c5540e7b7fad1a0.txt").write_text("f1faf0b594023c386c5540e7b7fad1a0\n", encoding="utf-8")

    # llms.txt — the map an AI system needs: what this is, which pages hold what, which files hold the data
    reg = [("Bibliography", "/knowledge/bibliography/", f"{len(BIB.get('entries', []))} peer-reviewed references on limb difference, thalidomide embryopathy and their causes", "bibliography.json"),
           ("Registries", "/knowledge/registries/", f"{len(ORPHA_REGS.get('registries', []))} registries that record congenital limb differences, with their coverage", "registries.json"),
           ("Researchers", "/knowledge/researchers/", f"{len(RESEARCHERS.get('teams', []))} research teams, from the affiliations of the bibliography's authors", "researchers.json"),
           ("Care centres", "/knowledge/care-centres/", f"{len(CARE_CENTRES)} centres of care, each named by a member association or verified on its own institutional page", "care-centres.json"),
           ("Teratogens", "/knowledge/teratogens/", f"{TERA.get('counts', {}).get('total', 0)} substances with known, presumed or suspected effects on the unborn child, with evidence level and legal status", "teratogens.json")]
    llms = ["# DysNet", "",
            "> DysNet is the international network for people with congenital limb differences (dysmelia), "
            "registered in Sweden in 2009. It maintains five public registers, publishes them as data under "
            "CC BY 4.0, and is building a registry of limb malformations owned by the patient community itself, with Health Data Safe as the registry's technical and operational partner.", "",
            "Everything on this site may be quoted and reused with attribution to DysNet. Figures are sourced "
            "line by line; where the evidence is thin, the pages say so.", "",
            "## Registers (HTML, with the data behind each)", ""]
    for name, path, desc, f in reg:
        llms.append(f"- [{name}]({SITE}{path}): {desc}. Data: [{f}]({SITE}/data/{f})")
    llms += ["", "## Reference pages", "",
             f"- [Understanding dysmelia]({SITE}/knowledge/understanding-dysmelia/): what dysmelia is, condition by condition, with ORPHAcodes, ICD-10 and ICD-11 codes and the Oberg-Manske-Tonkin group. Data: [orphanet-hierarchy.json]({SITE}/data/orphanet-hierarchy.json), where each code sits in Orphanet's classification.",
             f"- [Epidemiology]({SITE}/knowledge/epidemiology/): birth prevalence per condition with its source and confidence interval, and expected affected births a year for {len(BIRTHS['countries'])} countries. Data: [births.json]({SITE}/data/births.json), [condition-prevalence.json]({SITE}/data/condition-prevalence.json)",
             f"- [Causes of dysmelia]({SITE}/knowledge/causes-of-dysmelia/): a referenced review of what is known about causes, and how often a cause is found.",
             f"- [What is a patient-owned registry?]({SITE}/knowledge/guides/patient-owned-registry/): the guide in two minutes.",
             f"- [The registry project]({SITE}/registry/): the registry DysNet is building, and how it is governed.",
             f"- [Our voice]({SITE}/voice/): DysNet's seats at EURORDIS, the European Disability Forum and ERN BOND.",
             f"- [Member associations]({SITE}/about/members/): the associations families belong to, country by country.",
             "", "## Filtered views can be linked", "",
             f"- Bibliography by condition: {SITE}/knowledge/bibliography/?condition=2911 (ORPHAcode), by theme: ?topic=meta, by year: ?from=2015&to=2026",
             f"- Teratogens by source, level, kind or use: {SITE}/knowledge/teratogens/?source=clp&level=known",
             f"- Expected affected births by condition and region: {SITE}/knowledge/epidemiology/?condition=amelia-all-forms&region=Sub-Saharan%20Africa",
             "", "## The registry's technical partner", "",
             "- [Health Data Safe](https://www.healthdatasafe.org/en/): a Swiss non-profit foundation that builds "
             "open-source infrastructure for people to gather, read and share their own health data, for their care "
             "and for research. By decision of DysNet's Annual General Meeting of 26 August 2026 it is the registry's "
             "technical and operational partner, contributing its infrastructure in kind. Wikidata: "
             "[Q141112222](https://www.wikidata.org/wiki/Q141112222).",
             f"- How the two fit together: {SITE}/registry/?for=registries explains the interoperability and portability "
             "offered to other registries; every person holds their own data account and nothing is pooled without a "
             "granular, revocable consent.",
             "", "## Licence and contact", "",
             "- Text and data: CC BY 4.0, attribution to DysNet (www.dysnet.org).",
             "- Corrections, additions and questions: info@dysnet.org.",
             f"- Last built: {__import__('time').strftime('%Y-%m-%d')}.", ""]
    # Every page the site builds, so that a page added to PAGES is never missing here. The curated
    # sections above keep their richer wording; this lists what they have not already named.
    mentioned = set(re.findall(r"\]\(" + re.escape(SITE) + r"(/[^)?#]*)", "\n".join(llms)))
    rest = [f"- [{PAGES[p]['title']}]({SITE}{p}): {PAGES[p]['desc']}" for p in sorted(PAGES)
            if p not in mentioned and p not in ("/", "/404/")]
    if rest:
        at = llms.index("## Licence and contact")
        llms[at:at] = ["## Every other page", ""] + rest + [""]
    (ROOT / "llms.txt").write_text("\n".join(llms), encoding="utf-8")

    print(f"Built {len(written)} pages:")
    for p in written:
        print("  ", p)


if __name__ == "__main__":
    build()
