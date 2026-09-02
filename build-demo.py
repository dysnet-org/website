#!/usr/bin/env python3
"""Build the DysNet demo site into docs/ (GitHub Pages source folder).

Architecture mirrors the HDS website (Astro BaseLayout pattern):
one layout carrying SEO head + header + footer, page bodies injected.
Run:  python3 build-demo.py
"""
import json
import os
import pathlib
import re

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
# the /website prefix. When the site moves to www.dysnet.org, set
# DEPLOY=prod (or flip the default below) and rebuild — nothing else changes.
DEPLOY = os.environ.get("DEPLOY", "pages")
ORIGIN, BASE = {
    "pages": ("https://dysnet-org.github.io", "/website"),
    "prod": ("https://www.dysnet.org", ""),
}[DEPLOY]
SITE = ORIGIN + BASE

# Internal links are written root-absolute ("/knowledge/"); rebase() prefixes
# them with BASE at write time, so page bodies stay prefix-agnostic.
_ABS_ATTR = re.compile(r'\b(href|src)="(/(?!/)[^"]*)"')

def rebase(html):
    if not BASE:
        return html
    return _ABS_ATTR.sub(lambda m: f'{m.group(1)}="{BASE}{m.group(2)}"', html)

BRAND = "DysNet"
DESC_DEFAULT = ("DysNet is the global network for people affected by congenital limb "
                "differences (dysmelia): a curated research library, ongoing studies, "
                "a researcher register, a map of specialist care centres worldwide, and an "
                "international patient-owned registry.")

FAVICON = "/assets/img/favicon-64.png"

ORG_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "NGO",
    "name": "DysNet",
    "legalName": "DysNet Ideell Förening",
    "alternateName": "EDRIC – European Dysmelia Reference Information Centre",
    "url": SITE,
    "logo": f"{SITE}/assets/img/dysnet-logo-512.png",
    "description": DESC_DEFAULT,
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
               "https://www.youtube.com/user/DysmeliaNetwork"],
}

NAV = [
    ("/about/", "About"),
    ("/knowledge/", "Knowledge"),
    ("/registry/", "Registry"),
    ("/voice/", "Voice"),
    ("/contact/", "Contact"),
]


def head(title, desc, path, is_home=False, og=None):
    full = title if BRAND in title else f"{title} · {BRAND}"
    canonical = SITE + path
    ld = [ORG_SCHEMA] if is_home else [{
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
        ]}]
    ld_json = "\n".join(
        f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>'
        for x in ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="DysNet">
<meta property="og:title" content="{full}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}{og or "/assets/img/board-inail-2024.jpg"}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="{FAVICON}">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_V}">
<script>window.SITE_BASE={json.dumps(BASE)};</script>
{ld_json}
</head>"""


def header_html(active):
    links = "".join(
        f'<a href="{href}"{" aria-current=\"true\"" if active.startswith(href) else ""}>{label}</a>'
        for href, label in NAV)
    return f"""<body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="demo-ribbon"><strong>Demonstration preview</strong> · proposal for the DysNet AGM of 26 August 2026 · not the live site</div>
<header class="site">
  <div class="container site-bar">
    <a class="logo" href="/" aria-label="DysNet home"><img src="/assets/img/dysnet-logo.png" alt="DysNet — The Online Dysmelia Community" width="269" height="176"></a>
    <nav class="main" aria-label="Main">
      {links}
      <button id="search-btn" type="button" class="search-trigger" aria-label="Search the site">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        Search <kbd>⌘K</kbd>
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
          <li><a href="/knowledge/research-library/">Research library</a></li>
          <li><a href="/knowledge/ongoing-studies/">Ongoing studies</a></li>
          <li><a href="/knowledge/researchers/">Researchers</a></li>
          <li><a href="/knowledge/care-centres/">Care centres</a></li>
          <li><a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a></li>
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
          <li><a href="https://www.youtube.com/user/DysmeliaNetwork">YouTube</a></li>
          <li><a href="https://www.youtube.com/watch?v=P8M2n7Gr3V0">The chair’s address</a></li>
        </ul>
      </div>
    </div>
    <div class="legal">
      © 2026 DysNet Ideell Förening · <a href="#">Privacy</a> · <a href="#">Terms of use</a> · <a href="#">Legal notices</a> · Demonstration preview built for the 2026 AGM; register entries marked “example” are placeholders for the named maintainers to replace.
    </div>
  </div>
</footer>
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


def opener(num, label, heading, acc=None, big=False):
    style = f' style="--acc:var(--acc-{acc});--acc-text:var(--acc-{acc}-text)"' if acc else ""
    h = "h2-lg" if big else "h2"
    return f"""<div{style}>
      <div class="tick"></div>
      <p class="eyebrow">{num} · {label}</p>
      <h2 class="{h}">{heading}</h2>
    </div>"""


PAGES = {}

# ────────────────────────────── HOME ──────────────────────────────
PAGES["/"] = {
    "title": "DysNet · The dysmelia network — knowledge, registry and voice for congenital limb differences",
    "desc": DESC_DEFAULT,
    "is_home": True,
    "body": f"""
__MAP_HERO__

<section style="padding-top:0">
  <div class="container">
    <div class="grid cols-4 aud-grid">
      <div class="card acc-library"><h3 class="h4">For families</h3><p>Understand the diagnosis and find the association near you.</p><p class="go">Start here →</p><a class="cover" href="/knowledge/understanding-dysmelia/" aria-label="For families: understanding dysmelia"></a></div>
      <div class="card acc-research"><h3 class="h4">For clinicians</h3><p>Reference centres, expert registers and the research library.</p><p class="go">Care centres →</p><a class="cover" href="/knowledge/care-centres/" aria-label="For clinicians: care centres"></a></div>
      <div class="card acc-studies"><h3 class="h4">For researchers</h3><p>The registry, ongoing studies and how to be listed.</p><p class="go">The registry →</p><a class="cover" href="/registry/" aria-label="For researchers: the registry"></a></div>
      <div class="card acc-centres"><h3 class="h4">For associations</h3><p>Join the network, feed the registers, share your studies.</p><p class="go">Membership →</p><a class="cover" href="/about/members/" aria-label="For associations: membership"></a></div>
    </div>
  </div>
</section>

<section>
  <div class="container">
    {opener("01", "Four registers", "What is known, being studied, and where expertise lives.")}
    <p>Four living registers, each maintained by a named volunteer and dated, so families and clinicians always know how current the information is.</p>
    <div class="grid cols-4" style="margin-top:var(--space-4)">
      <div class="card acc-library">
        <h3 class="h4"><a href="/knowledge/research-library/">Research library</a></h3>
        <p>Curated publications on limb-difference research, summarised in plain language.</p>
        <p class="meta">Updated August 2026</p>
      </div>
      <div class="card acc-studies">
        <h3 class="h4"><a href="/knowledge/ongoing-studies/">Ongoing studies</a></h3>
        <p>A live overview of studies recruiting or in progress across Europe.</p>
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
    <p>From Reach in the UK and Raggiungere in Italy to Aussiehands in Australia and AVITE in Spain: more than thirty organisations across fourteen countries, on four continents.</p>
    <p style="margin-top:var(--space-3)"><a class="btn btn-ghost" href="/about/members/">Meet the member associations</a></p>
  </div>
</section>
""",
}

# ─────────────────────────── KNOWLEDGE HUB ────────────────────────
PAGES["/knowledge/"] = {
    "title": "Knowledge",
    "desc": "The DysNet knowledge base: four maintained registers covering limb-difference research, ongoing studies, researchers and specialist care centres, plus a plain-language guide to dysmelia conditions.",
    "crumbs": [("/knowledge/", "Knowledge")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Mission 1 · The international reference point</p>
    <h1 class="display">Knowledge, kept current.</h1>
    <p>Families and clinicians come to DysNet to find what is known, what is being studied, and where expertise lives. Each register below is maintained by a named volunteer and shows its last update. Current beats polished.</p>
    <div class="grid cols-2" style="margin-top:var(--space-4)">
      <div class="card acc-library">
        <h3 class="h3"><a href="/knowledge/research-library/">Research library</a></h3>
        <p>Curated publications, each with a plain-language summary and a link to the source.</p>
        <p class="meta">Register 1 · updated August 2026</p>
      </div>
      <div class="card acc-studies">
        <h3 class="h3"><a href="/knowledge/ongoing-studies/">Ongoing studies</a></h3>
        <p>Studies recruiting or in progress, with status and contact for each.</p>
        <p class="meta">Register 2 · updated August 2026</p>
      </div>
      <div class="card acc-research">
        <h3 class="h3"><a href="/knowledge/researchers/">Researchers</a></h3>
        <p>Research teams working on limb difference around the world.</p>
        <p class="meta">Register 3 · updated August 2026</p>
      </div>
      <div class="card acc-centres">
        <h3 class="h3"><a href="/knowledge/care-centres/">Care centres</a></h3>
        <p>Reference and competence centres, in Europe and beyond, on a map.</p>
        <p class="meta">Register 4 · updated August 2026</p>
      </div>
    </div>
    <div style="margin-top:var(--space-4)" class="card">
      <h3 class="h4"><a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a></h3>
      <p>New to limb difference? Start here: what dysmelia is, and a plain-language guide to some forty conditions, sourced from Orphanet.</p>
    </div>
  </div>
</section>
""",
}

REGISTER_FOOT = ('<div class="register-note"><span>Maintained by: <strong>to be named at the '
                 'AGM</strong> (Documentation lead coordinates).</span>'
                 '<span>See something missing? <a href="mailto:info@dysnet.org?subject=Register%20suggestion">'
                 'Suggest an addition</a>.</span></div>')

PAGES["/knowledge/research-library/"] = {
    "title": "Research library",
    "desc": "Curated publications on congenital limb difference research, each summarised in plain language by DysNet volunteers, with links to the original sources.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/research-library/", "Research library")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-library);--acc-text:var(--acc-library-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 1 · Research library <span class="badge live">updated Aug 2026</span></p>
    <h1 class="display">The research, readable.</h1>
    <p>Every entry: a citation, a one-paragraph plain-language summary, and a link to the source. Tagged by condition and topic so families and clinicians find what concerns them.</p>

    <div style="margin-top:var(--space-4)">
      <article class="entry">
        <h3>Orphanet condition sheets on limb reduction defects <span class="badge live">source</span></h3>
        <p>The European reference database for rare diseases documents the conditions grouped under dysmelia, from amelia to ulnar hemimelia. Our <a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a> guide is built on it.</p>
        <p class="src">Orphanet · <a href="https://www.orpha.net/en/disease/encyclopedia" target="_blank" rel="noopener external">orpha.net · encyclopedia for patients</a> · topic: conditions</p>
      </article>
      <article class="entry">
        <h3>Rare Barometer: how rare-disease patients experience care <span class="badge live">source</span></h3>
        <p>EURORDIS’s large-scale survey programme, to which DysNet contributed content and translations, gives an updated picture of life with rare conditions including bone and limb diseases.</p>
        <p class="src">EURORDIS · <a href="https://www.eurordis.org/rare-barometer/">eurordis.org/rare-barometer</a> · topic: lived experience</p>
      </article>
      <article class="entry">
        <h3>Biorobotics for limb difference: conference proceedings, Milan 2026 <span class="badge live">DysNet event</span></h3>
        <p>Findings from the conference DysNet co-organised at Regione Lombardia (Palazzo Pirelli, 26 March 2026) with university researchers, prosthetics producers and patient associations.</p>
        <p class="src">DysNet &amp; Regione Lombardia · report available to members · topic: prosthetics, biorobotics</p>
      </article>
      <article class="entry">
        <h3>Example entry: a peer-reviewed paper summarised for families <span class="badge example">example</span></h3>
        <p>This is what a library entry looks like. The named maintainer replaces it with real curated publications: citation, plain-language summary, source link, and condition tags.</p>
        <p class="src">Journal · DOI link · topic tags</p>
      </article>
    </div>
    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/ongoing-studies/"] = {
    "title": "Ongoing studies",
    "desc": "A live overview of limb-difference studies recruiting or in progress around the world: the ERN BOND Patient Journey, the Rare Barometer surveys, prosthesis reimbursement comparisons and more.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/ongoing-studies/", "Ongoing studies")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-studies);--acc-text:var(--acc-studies-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 2 · Ongoing studies <span class="badge live">updated Aug 2026</span></p>
    <h1 class="display">What is being studied, right now.</h1>
    <p>Studies our community can join or follow. Each entry shows who runs it, its status, and whom to contact. Associations: tell us about studies in your country.</p>

    <div style="margin-top:var(--space-4)">
      <article class="entry">
        <h3>Patient Journey · ERN BOND / EURORDIS <span class="badge live">in progress</span></h3>
        <p>A five-step research project promoted by DysNet on behalf of Raggiungere, tracking the experiences of patients, families, doctors and researchers through a shared questionnaire, to give families updated medical and scientific knowledge.</p>
        <p class="src">ERN BOND ePAG · approved, in progress · contact via <a href="mailto:info@dysnet.org">info@dysnet.org</a></p>
      </article>
      <article class="entry">
        <h3>How the brain adapts to congenital upper-limb loss · University of Zurich <span class="badge live">recruiting</span></h3>
        <p>An observational study combining MRI and behavioural measures to understand how the central nervous system reorganises in people born with upper-limb amelia, compared with controls. About 70 participants; adults with congenital upper-limb loss can take part in Zurich.</p>
        <p class="src">University of Zurich, Switzerland · recruiting until 2027 · <a href="https://clinicaltrials.gov/study/NCT06043518" target="_blank" rel="noopener external">ClinicalTrials.gov · NCT06043518 ↗</a></p>
      </article>
      <article class="entry">
        <h3>Prosthesis reimbursement across the EU <span class="badge live">workgroup</span></h3>
        <p>A DysNet workgroup compares the subsidies each EU country grants for prostheses: amounts due, and which prosthesis technologies qualify. A regional initiative at Regione Lombardia (2026) is the working example other countries can replicate.</p>
        <p class="src">DysNet workgroup · data collection open to all member associations</p>
      </article>
      <article class="entry">
        <h3>Rare Barometer surveys <span class="badge live">recurring</span></h3>
        <p>EURORDIS’s survey programme on living with a rare disease. DysNet contributes content and translations and relays each wave to members.</p>
        <p class="src">EURORDIS · <a href="https://www.eurordis.org/rare-barometer/">join the panel</a></p>
      </article>
      <article class="entry">
        <h3>Orphanet research directories <span class="badge live">source</span></h3>
        <p>Orphanet catalogues ongoing clinical trials, research projects, registries and biobanks per rare disease. The maintainer screens it for limb-difference studies each quarter.</p>
        <p class="src">Orphanet · <a href="https://www.orpha.net/en/research-trials/clinical-trials" target="_blank" rel="noopener external">clinical trials</a> · <a href="https://www.orpha.net/en/research-trials/research-projects" target="_blank" rel="noopener external">research projects</a></p>
      </article>
      <article class="entry">
        <h3>“What if” phase 2: a European survey on dysmelia <span class="badge example">planned</span></h3>
        <p>A workgroup prepares a European-level survey across cultural, medical, scientific and technological dimensions, drawing on university and research centres, hospitals and orthopaedic units in the countries DysNet represents.</p>
        <p class="src">DysNet workgroup · in preparation</p>
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
    <p class="eyebrow">Register 3 · Researchers <span class="badge live">updated Aug 2026</span></p>
    <h1 class="display">Who works on limb difference.</h1>
    <p>A factual register: teams that publish or run studies on congenital limb difference. Listing is by activity, not endorsement, so no one is preferred and no one is left out.</p>

    <div style="margin-top:var(--space-4)">
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
      <article class="entry">
        <h3>Example entry: your research team <span class="badge example">example</span></h3>
        <p>Each entry: team, institution, research focus, representative publication, contact. Researchers on limb difference: ask to be listed, the criterion is simply documented activity in the field.</p>
        <p class="src">Institution · focus · link</p>
      </article>
    </div>
    {REGISTER_FOOT}
  </div>
</section>
""",
}

PAGES["/knowledge/care-centres/"] = {
    "og": "/assets/img/inail-lab-tour.jpg",
    "title": "Care centres",
    "desc": "The DysNet map of reference and competence centres for congenital limb difference, in Europe and beyond: specialist prosthetics centres, expert clinics and ERN BOND network hospitals.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/care-centres/", "Care centres")],
    "body": f"""
<section>
  <div class="container" style="--acc:var(--acc-centres);--acc-text:var(--acc-centres-text)">
    <div class="tick"></div>
    <p class="eyebrow">Register 4 · Care centres <span class="badge live">updated Aug 2026</span></p>
    <h1 class="display">Where expertise lives.</h1>
    <p>The map of reference and competence centres for limb difference, in Europe and beyond, validated with our member associations so a family anywhere knows where the nearest expertise is. The interactive map arrives with the first validated batch; the register opens as a list.</p>

    <div style="margin-top:var(--space-4)">
      <article class="entry">
        <h3>INAIL Centro Protesi · Vigorso di Budrio, Italy <span class="badge live">visited by the board</span></h3>
        <p>One of Europe’s leading prosthetics centres: fitting, rehabilitation and applied research under one roof. “I was looking for active prostheses, not passive ones: something alive. I wanted to humanise the prosthesis” (Johannes Schmidl, its first technical director).</p>
        <p class="src">Emilia-Romagna, Italy · prosthetics &amp; rehabilitation · <a href="https://www.inail.it">inail.it</a></p>
      </article>
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
      <article class="entry">
        <h3>Example entry: a national competence centre <span class="badge example">example</span></h3>
        <p>Each entry: centre, city and country, what it specialises in, how families are referred, and which member association validated it.</p>
        <p class="src">City, country · specialism · validated by</p>
      </article>
    </div>

    <figure class="photo" style="margin-top:var(--space-4)">
      <img src="/assets/img/inail-lab-tour.jpg" alt="The DysNet board touring a prosthetics workshop at the INAIL centre, with casts and tools on the benches" loading="lazy">
      <figcaption>The DysNet board visiting the INAIL prosthetics workshops, Vigorso di Budrio, August 2024. Photo: DysNet.</figcaption>
    </figure>
    {REGISTER_FOOT}
  </div>
</section>
""",
}

# (name, description, ORPHAcode or None, Orphanet preferred name, limbs, type, other-signs)
# Codes carried from the old dysnet.org encyclopedia, verified on Orphanet 2026-08-10.
# The last three fields feed the condition finder (plain-language triage tags):
#   limbs: arms / legs / several   type: reduction / fusion / extra / band   other: other / limbsonly
ORPHA_URL = "https://www.orpha.net/en/disease/detail/{}"
CONDITIONS = [
    ("Adams-Oliver syndrome", "limb differences combined with scalp and skull defects.", 974, "Adams-Oliver syndrome", "arms legs several", "reduction", "other", "genetic"),
    ("Amelia", "complete absence of one or more limbs.", 1027, "Autosomal recessive amelia", "arms legs several", "reduction", "limbsonly", "genetic"),
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
    ("Symbrachydactyly", "short, webbed or missing fingers on one hand.", 1570, "Symbrachydactyly of hands and feet", "arms", "reduction fusion", "limbsonly", "nongenetic"),
    ("Syndactyly", "webbing between two or more fingers or toes.", 93458, "Non-syndromic polydactyly, syndactyly and/or hyperphalangy", "arms legs", "fusion extra", "limbsonly", "genetic"),
    ("Tetra-amelia", "absence of all four limbs, with other malformations.", 3301, "Tetraamelia-multiple malformations syndrome", "several", "reduction", "other", "genetic"),
    ("Thrombocytopenia-absent radius (TAR)", "absent radius with low platelet counts.", 3320, "Thrombocytopenia-absent radius syndrome", "arms", "reduction", "other", "genetic"),
    ("Tibial aplasia–ectrodactyly", "tibial deficiency together with split hand–foot.", 3329, "Tibial aplasia-ectrodactyly syndrome", "legs several", "reduction", "limbsonly", "genetic"),
    ("Tibial hemimelia", "deficiency of the tibia with an intact fibula.", 93322, "Isolated tibial hemimelia", "legs", "reduction", "limbsonly", "nongenetic"),
    ("Ulnar hemimelia", "partial or complete absence of the ulna.", 93320, "Isolated ulnar hemimelia", "arms", "reduction", "limbsonly", "nongenetic"),
]


def condition_card(name, desc, code, orpha_name, limbs, ctype, other, genetic):
    if code:
        link = (f'<p class="src"><a href="{ORPHA_URL.format(code)}" target="_blank" '
                f'rel="noopener external" title="{orpha_name} — Orphanet">'
                f'Orphanet · ORPHA:{code} ↗</a></p>')
    else:
        link = ('<p class="src">Umbrella term; see the specific types on '
                '<a href="https://www.orpha.net/en/disease" target="_blank" rel="noopener external">Orphanet</a>.</p>')
    return (f'<div class="card" data-limbs="{limbs}" data-type="{ctype}" data-other="{other}" data-genetic="{genetic}">'
            f'<h3 class="h4">{name}</h3><p>{desc}</p>{link}</div>')

PAGES["/knowledge/understanding-dysmelia/"] = {
    "title": "Understanding dysmelia",
    "desc": "What dysmelia means: a plain-language guide to congenital limb differences and the conditions behind the term, sourced from Orphanet, for families and clinicians.",
    "crumbs": [("/knowledge/", "Knowledge"), ("/knowledge/understanding-dysmelia/", "Understanding dysmelia")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Start here · For families and clinicians</p>
    <h1 class="display">Understanding dysmelia.</h1>
    <p>Dysmelia is the generic term for all types of congenital limb differences: limbs that formed differently, incompletely or not at all before birth. It concerns about 5 in 10,000 people. Behind the word are many distinct conditions; the guide below introduces the main ones in plain language, with links to Orphanet, the European reference database for rare diseases.</p>

    {opener("01", "The conditions", "Many conditions, one community.")}

    <div class="finder" id="cond-finder">
      <p class="finder-title">Find the pages that concern you</p>
      <p class="finder-sub">Three questions to narrow the list below. This helper does not diagnose anything: only a clinician or geneticist can. It simply helps you find the right Orphanet pages to read and to bring to your consultation.</p>
      <fieldset>
        <legend>Which limbs are concerned?</legend>
        <div class="finder-chips" data-q="limbs">
          <button type="button" data-v="" aria-pressed="true">Not sure / any</button>
          <button type="button" data-v="arms" aria-pressed="false">Arms or hands</button>
          <button type="button" data-v="legs" aria-pressed="false">Legs or feet</button>
          <button type="button" data-v="several" aria-pressed="false">Several or all four</button>
        </div>
      </fieldset>
      <fieldset>
        <legend>What best describes the difference?</legend>
        <div class="finder-chips" data-q="type">
          <button type="button" data-v="" aria-pressed="true">Not sure / any</button>
          <button type="button" data-v="reduction" aria-pressed="false">A part is missing or shorter</button>
          <button type="button" data-v="fusion" aria-pressed="false">Fingers or toes joined</button>
          <button type="button" data-v="extra" aria-pressed="false">Extra fingers or toes</button>
          <button type="button" data-v="band" aria-pressed="false">Ring-shaped constriction marks</button>
        </div>
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

    <div class="grid cols-3" id="cond-grid">
      {"".join(condition_card(*c) for c in CONDITIONS)}
    </div>
    <p style="margin-top:var(--space-3)">Each card links to the condition’s page on Orphanet, the European reference database for rare diseases, through its permanent ORPHAcode; the codes were carried over from the previous DysNet site and re-verified in August 2026. Know one we have not covered, or have information to add? <a href="mailto:info@dysnet.org">Tell us</a>.</p>

    {opener("02", "Not alone", "The associations that know your condition.")}
    <p>Whatever the diagnosis, a member association near you has walked this road: from Poland-syndrome groups in France and Italy to thalidomide organisations across the world. <a href="/about/members/">Find yours</a>.</p>
  </div>
</section>
""",
}

# ───────────────────────────── REGISTRY ───────────────────────────
PAGES["/registry/"] = {
    "title": "The registry",
    "desc": "DysNet's flagship: the first international, interoperable registry of limb malformations owned by the patient community itself, developed with member associations and Health Data Safe.",
    "crumbs": [("/registry/", "The registry")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick" style="background:var(--dys-green)"></div>
    <p class="eyebrow" style="color:var(--dys-green-text)">Mission 2 · Flagship project</p>
    <h1 class="display">A registry owned by the people it describes.</h1>
    <p>Research on limb agenesis is starved of data: cases are rare, scattered across countries, and recorded in incompatible systems, when they are recorded at all. Families answer the same questions again and again, and science still cannot see the whole picture.</p>

    {opener("01", "The answer", "The first international, patient-owned registry of limb malformations.")}
    <p>DysNet carries a registry that is international and interoperable by design, owned by the patient community itself, developed with member associations, and replicable for other rare conditions. It is the concrete answer to what DysNet membership returns to families: their data, working for their care. Once live, the registry will be declared in <a href="https://www.orpha.net/en/research-trials/registries" target="_blank" rel="noopener external">Orphanet’s European directory of rare-disease registries</a>, where researchers already look for data sources.</p>

    {opener("02", "How it works", "Associations contribute; the community governs.")}
    <div class="grid cols-3">
      <div class="card acc-studies"><h3 class="h4">Families contribute</h3><p>Through their national association, on explicit consent, in their own language.</p></div>
      <div class="card acc-studies"><h3 class="h4">Data stays governed</h3><p>The community decides what is collected and who may use it, for care and research only.</p></div>
      <div class="card acc-studies"><h3 class="h4">Research gets fuel</h3><p>Interoperable, comparable data across countries, at last.</p></div>
    </div>

    <p style="margin-top:var(--space-3)"><a class="btn btn-ghost" href="/knowledge/guides/patient-owned-registry/">New to the idea? The two-minute guide</a></p>

    {opener("03", "The partner", "Built with Health Data Safe.")}
    <p><a href="https://www.healthdatasafe.org">Health Data Safe</a>, a Swiss non-profit foundation specialised in patient-governed health data infrastructure, is proposed as the registry’s technical and operational partner. The mandate is submitted to the DysNet AGM of 26 August 2026.</p>

    {opener("04", "Progress", "The log.")}
    <div class="report"><p class="seat">Registry</p><h3 class="h4">Mandate proposal before the AGM</h3><time datetime="2026-08">August 2026</time><p>The refocused strategy, including the registry mandate, is on the AGM agenda. Every board member commits to seeking grants for the registry.</p></div>
    <div class="report"><p class="seat">Funding</p><h3 class="h4">First grant application in preparation</h3><time datetime="2026-07">Summer 2026</time><p>A rare-disease research application is in preparation on the French side; EU rare-disease calls are being screened.</p></div>
  </div>
</section>

<section>
  <div class="sheet sheet-cta">
    <div class="tick" style="background:#4cc42c"></div>
    <p class="eyebrow">Take part</p>
    <h2 class="h2">Your association can be a pilot.</h2>
    <p>The registry grows association by association. Write to <a href="mailto:info@dysnet.org">info@dysnet.org</a> to join the first wave.</p>
  </div>
</section>
""",
}

# ─────────────────────────────── VOICE ────────────────────────────
PAGES["/voice/"] = {
    "title": "Where DysNet sits",
    "desc": "DysNet's chosen seats in European rare-disease and disability bodies: EURORDIS, the European Disability Forum and ERN BOND, each with a named delegate, a written mandate and public reports.",
    "crumbs": [("/voice/", "Voice")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">Mission 3 · The voice of families</p>
    <h1 class="display">Where it counts, with a mandate.</h1>
    <p>DysNet keeps its seats but chooses them: a restricted list of international bodies active alongside researchers. Each seat has a named delegate, a written mandate, and a short written report to members after every meeting.</p>

    <div class="grid cols-2" style="margin-top:var(--space-4)">
      <div class="card">
        <h3 class="h4">EURORDIS · Rare Diseases Europe</h3>
        <p>Member. Active in the Rare Barometer programme and the European Regional Task Force on Rare Diseases (with Rare Diseases International, supporting the WHO resolution on rare diseases).</p>
        <p class="meta">Delegate: to be determined at the AGM</p>
      </div>
      <div class="card">
        <h3 class="h4">EDF · European Disability Forum</h3>
        <p>Member. General assemblies and workstreams on the EU Disability Card, AI, assistive technology for employment, and accessibility.</p>
        <p class="meta">Delegate: to be determined at the AGM</p>
      </div>
      <div class="card">
        <h3 class="h4">ERN BOND · patient advocacy group</h3>
        <p>Patient representative seat in the European Reference Network for bone diseases; promoter of the Patient Journey project.</p>
        <p class="meta">Delegate: to be determined at the AGM</p>
      </div>
      <div class="card" style="--acc:var(--acc-centres);--acc-text:var(--acc-centres-text)">
        <h3 class="h4">EESC · European Economic and Social Committee</h3>
        <p>Standing contacts. The EU’s consultative body for organised civil society advises the Parliament, Council and Commission, and carries a permanent group on disability rights: opinions on the EU Disability Card and on the rights of persons with disabilities are shaped here.</p>
        <p class="meta">Delegate: to be determined at the AGM</p>
      </div>
    </div>

    {opener("01", "Also active in", "Projects we joined by invitation.")}
    <ul>
      <li><strong>VOTE4ALL / VOICE4ALL</strong> (Cerebral Palsy Europe, EU-supported): autonomous voting rights for persons with disabilities; study visits to The Hague and the Portuguese Parliament.</li>
      <li><strong>Local lectures</strong>: Milan Civil Week, and an event planned around the Milano-Cortina 2026 Winter Paralympics.</li>
    </ul>
    <p style="margin-top:var(--space-3)"><a class="btn btn-primary" href="/voice/reports/">Read the delegate reports</a></p>
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
    <h1 class="display">After every meeting, a report.</h1>
    <p>What our delegates heard, said and brought home, in a few paragraphs each. This feed replaces the old blog.</p>

    <div style="margin-top:var(--space-4)">
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
        <p>Following VOTE4ALL (study visits to The Hague’s Parliament and the Ministry of the Interior, meetings with the mayors of Lisbon and Porto), DysNet joins the successor project: webinars and in-person workshops across the EU.</p>
      </article>
      <article class="report">
        <p class="seat">DysNet event · Regione Lombardia</p>
        <h2 class="h3">Biorobotics conference at Palazzo Pirelli</h2>
        <time datetime="2026-03-26">26 March 2026 · Claudio Pirola</time>
        <p>DysNet organised a conference on biorobotics for persons with disability at the seat of Regione Lombardia in Milan: university professors and researchers, prosthetics producers and association representatives. Follow-up: an audition before the region’s competent commission.</p>
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
    </div>

    <figure class="photo" style="margin-top:var(--space-4)">
      <img src="/assets/img/limbloss-day-2012.jpg" alt="A speaker presents DysNet and EDRIC at European LimbLoss Day 2012" loading="lazy">
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
    "desc": "DysNet, formerly EDRIC, is the global network for people affected by congenital limb differences, founded by thalidomide family organisations and registered in Sweden in 2009.",
    "crumbs": [("/about/", "About")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · Built by families</p>
    <h1 class="display">DysNet exists because families built it.</h1>
    <p>In 2009, the Swedish thalidomide organisations FfdN and Ex-Center and the UK Thalidomide Trust registered EDRIC, the European Dysmelia Reference Information Centre, in Sweden. The portal opened in 2012 and the network became DysNet: the only global network dedicated to congenital limb differences.</p>

    {opener("01", "Vision", "What we work towards.")}
    <p>A world where every family affected by a congenital limb difference can find the knowledge that concerns them, and where the community’s own data drives the research that shapes their care. DysNet pools what member associations know at national level into a shared international resource: documented research, a registry owned by patients themselves, and one voice in the institutions where decisions are made.</p>

    {opener("02", "Three missions", "Everything DysNet does fits one of three missions.")}
    <div class="grid cols-3">
      <div class="card acc-library"><h3 class="h4"><a href="/knowledge/">Knowledge</a></h3><p>The international reference point for limb-difference research: four maintained registers.</p></div>
      <div class="card acc-studies"><h3 class="h4"><a href="/registry/">Registry</a></h3><p>The international associative registry of limb malformations, our flagship.</p></div>
      <div class="card"><h3 class="h4"><a href="/voice/">Voice</a></h3><p>Families represented where European decisions are made, with mandates and reports.</p></div>
    </div>

    {opener("03", "History", "From Malmö 2012 to today.")}
    <div class="grid cols-2">
      <figure class="photo">
        <img src="/assets/img/dysnet-banner-2012.jpg" alt="The original DysNet launch banner: Let the conversation begin" loading="lazy">
        <figcaption>The launch banner, 2012: “Let the conversation begin.” Photo: DysNet.</figcaption>
      </figure>
      <div>
        <p><strong>2008-2009</strong> · EDRIC founded and registered in Sweden (org. no. 802444-3015).</p>
        <p><strong>2012</strong> · The web portal opens; first network meeting in Malmö.</p>
        <p><strong>2015</strong> · Stockholm meeting; the network grows across Europe.</p>
        <p><strong>2025</strong> · Co-organiser of a biorobotics conference with Regione Lombardia.</p>
        <p><strong>2026</strong> · The refocused strategy: three missions, four registers, one registry.</p>
        <div class="yt-embed" data-yt="P8M2n7Gr3V0" data-title="The chair’s address to members">
          <img src="/assets/img/chair-address-thumb.jpg" alt="Video: Claudio Pirola, DysNet’s chair, addresses the members" loading="lazy" width="640" height="480">
          <button type="button" aria-label="Play: the chair’s address to members"><span></span></button>
        </div>
        <p style="font-size:var(--text-small);color:var(--dys-muted)">The chair’s address to members · plays on YouTube (no cookies before you press play) · <a href="https://www.youtube.com/watch?v=P8M2n7Gr3V0" target="_blank" rel="noopener external">open on YouTube ↗</a></p>
      </div>
    </div>

    {opener("04", "Documents", "The texts that govern us.")}
    <ul>
      <li><a href="/about/transparency/">Statutes, accounts and AGM documents</a></li>
      <li><a href="/about/people/">The board</a> and <a href="/about/members/">the member associations</a></li>
    </ul>
  </div>
</section>
""",
}

# (name, role, bio, initials, email, mission chip)
BOARD = [
    ("Claudio Pirola", "Chair · Italy", "Joined Raggiungere in 1999; at DysNet since its 2012 foundation. Carries representation, external voice and member relations.", "CP", "claudio.pirola@dysnet.org", "Mission 3 · Voice"),
    ("Michaela Moik", "Vice-president · Austria", "Thalidomide survivor, co-founder of the Austrian thalidomide self-help group, former youth social worker in Vienna.", "MM", "michi.moik@dysnet.org", "Member relations"),
    ("Monika Eisenberg-Geginat", "Secretary · Germany", "Thalidomide survivor, former head teacher, family therapist specialised in the protection of disabled children.", "ME", "moni.eisenberg@dysnet.org", "Statutes · AGM"),
    ("Salvatore Giambruno", "Treasurer · Italy", "Past president of Raggiungere and of LEDHA; a career in sales management; parent of a daughter with dysmelia.", "SG", "sal.giambruno@dysnet.org", "Accounts"),
    ("Tobias Arndt", "Chief Operating Officer · Belgium", "IT expert and researcher, author on electronic commerce; supporting thalidomide projects across Europe since 2007.", "TA", "tobias.arndt@dysnet.org", "Operations"),
]


def person_card(name, role, bio, init, email, chip):
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
          <p><a href="mailto:{email}">{email}</a></p>
        </div>
      </div>
    </div>"""

PAGES["/about/people/"] = {
    "title": "People",
    "desc": "The DysNet board: volunteers from the limb-difference community, each carrying one of DysNet's three missions.",
    "crumbs": [("/about/", "About"), ("/about/people/", "People")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · People</p>
    <h1 class="display">Volunteers who carry a mission each.</h1>
    <p>Most of the board live with dysmelia or are parents of children with limb differences, as the statutes require. Under the 2026-2029 strategy, every seat owns a mission: no seat without a mission. Hover or tap a card to read the bio and write to the person directly.</p>
    <div class="grid cols-3" style="margin-top:var(--space-4)">
      {"".join(person_card(*p) for p in BOARD)}
      <div class="card person" style="--acc:var(--dys-green)">
        <div class="avatar" style="background:var(--dys-green)">?</div>
        <h3 class="h4">Your name here</h3>
        <p class="role">Documentation lead · Registry lead</p>
        <p>The AGM of 26 August 2026 elects the bureau on the basis of missions accepted, not seats filled.</p>
      </div>
    </div>
    <figure class="photo" style="margin-top:var(--space-4)">
      <img src="/assets/img/board-inail-2024.jpg" alt="DysNet board members and guests at the INAIL prosthetics centre, August 2024" loading="lazy">
      <figcaption>The board and member-association guests at INAIL Centro Protesi, Vigorso di Budrio, August 2024. Photo: DysNet.</figcaption>
    </figure>
  </div>
</section>
""",
}

# (country, [(name, url or None), ...]) — URLs from the previous dysnet.org
# member pages plus known member sites, each verified reachable on 2026-08-18.
# Unreachable sites (taionlus.org, vitachi.cl, ITSS on webs.com, aussiehands,
# neurosedyn.se, steps-charity) deliberately stay unlinked until confirmed.
MEMBERS = [
    ("Australia", [("Aussiehands", None), ("Thalidomide Australia", "https://thalidomidegroupaustralia.com"), ("Limbs 4 Life", "https://www.limbs4life.org.au")]),
    ("Austria", [("Contergan Austria", None)]),
    ("Belgium", [("A.V.S.B.", None), ("Dysmelia ASBL", "https://www.facebook.com/DysmeliaBelgium")]),
    ("Chile", [("Vitachi – Talidomida en Chile", None)]),
    ("France", [("Assédea", "http://www.assedea.fr"), ("Syndrome de Poland France", None)]),
    ("Germany", [("Contergan NRW", None), ("HICOHA Hamburg", None), ("Interessenverband Contergangeschädigter", None), ("Contergangeschädigte Hessen", "https://www.contergan-hessen.de")]),
    ("Ireland", [("Irish Thalidomide Survivors Society", None)]),
    ("Italy", [("Raggiungere", "http://www.raggiungere.it"), ("Thalidomidici Italiani (TAI onlus)", None), ("V.I.TA – Vittime Talidomide Italia", "https://www.vittimetalidomideitalia.it"), ("AISP – Sindrome di Poland", None)]),
    ("Netherlands", [("Stichting NESOS", "https://www.softenon.nl")]),
    ("Norway", [("Den Norske Thalidomide Forening", None)]),
    ("Spain", [("AVITE", "https://www.avite.org")]),
    ("Sweden", [("FfdN", None), ("FfdN Stockholm", None), ("FfdN Väst", None), ("Ex-Center", "https://ex-center.org"), ("Svensk Dysmeliförening", "https://www.dysmeli.se")]),
    ("United Kingdom", [("Thalidomide Trust", "https://thalidomidetrust.org"), ("Reach", "https://www.reach.org.uk/", "https://www.reach.org.uk/support-us"), ("In Our Hands", None), ("PiP UK", "https://www.pip-uk.org"), ("Thalidomide Society", "https://thalidomidesociety.org")]),
    ("United States", [("STEPS", None)]),
]


# ─────────────── Landing map: registry participants by country ───────────────
# ISO 3166-1 numeric ids (as used by Natural Earth / world-atlas).
ISO_NUM = {"Australia": "036", "Austria": "040", "Belgium": "056", "Canada": "124", "Chile": "152",
           "France": "250", "Germany": "276", "Ireland": "372", "Italy": "380", "Netherlands": "528",
           "Norway": "578", "Spain": "724", "Sweden": "752", "United Kingdom": "826", "United States": "840"}
# Registry (Mission 2) participation status. Candidates are grounded in the
# strategy: a grant application in preparation on the French side; Raggiungere
# (Italy) promoter of the Patient Journey. Both remain to be confirmed at the AGM.
REGISTRY_STATUS = {"250": "candidate", "380": "candidate", "124": "contact"}
MAP_LABELS = {"member": "Member association", "candidate": "Registry pilot candidate · to confirm at the AGM",
              "contact": "Contact opened"}
MAP_COUNTRIES = {}
for _country, _orgs in MEMBERS:
    _id = ISO_NUM[_country]
    MAP_COUNTRIES[_id] = {"name": _country, "status": REGISTRY_STATUS.get(_id, "member"), "orgs": _orgs}
MAP_COUNTRIES["124"] = {"name": "Canada", "status": "contact", "orgs": ["The War Amps (contact opened, 2026)"]}
MAP_OFFICES = [{"name": "Solna", "lat": 59.36, "lon": 17.99}, {"name": "Brussels", "lat": 50.85, "lon": 4.35}]
MAP_DATA = json.dumps({"countries": MAP_COUNTRIES, "offices": MAP_OFFICES, "labels": MAP_LABELS}, ensure_ascii=False)

# Injected into the home page at build time (placeholder __MAP_HERO__), because
# it needs MEMBERS, which is defined after the home page body.
MAP_HERO = """
<section class="map-hero" aria-label="The DysNet network on the world map">
  <div id="worldmap" aria-hidden="true"></div>
  <div class="map-panel">
    <p class="kicker">Mission 2 · The international associative registry</p>
    <h1>The registry of limb malformations, <em>owned by the families it describes.</em></h1>
    <p>Each highlighted country is an association ready to bring its families’ knowledge into one shared, patient-governed registry. Hover a country to see who.</p>
    <ul class="map-stats">
      <li><strong data-count="countries">–</strong>countries</li>
      <li><strong data-count="orgs">–</strong>associations</li>
      <li><strong data-count="candidate">–</strong>pilot candidates</li>
    </ul>
    <div class="hero-actions">
      <a class="btn btn-primary" href="/registry/">The registry project</a>
      <a class="btn btn-ghost" href="/about/members/">Join the network</a>
    </div>
  </div>
  <div class="map-side">
  <div class="map-views" role="group" aria-label="Map view">
    <button type="button" data-view="world" aria-pressed="true">World</button>
    <button type="button" data-view="europe" aria-pressed="false">Europe</button>
    <button type="button" data-view="americas" aria-pressed="false">Americas</button>
    <button type="button" data-view="asiapacific" aria-pressed="false">Asia-Pacific</button>
    <button type="button" data-view="africa" aria-pressed="false">Africa &amp; Middle East</button>
  </div>
  <p class="map-guess" aria-live="polite"></p>
  <div class="map-legend" aria-label="Legend">
    <span class="l-member">Member association</span>
    <span class="l-candidate">Registry pilot candidate</span>
    <span class="l-contact">Contact opened</span>
    <span class="l-office">DysNet office</span>
  </div>
  </div>
  <div class="map-tip" role="tooltip"></div>
  <script>window.DYSNET_MAP = __MAP_DATA__;</script>
</section>
""".replace("__MAP_DATA__", MAP_DATA)


def member_li(entry):
    name, url = entry[0], entry[1]
    support = entry[2] if len(entry) > 2 else None
    if url:
        h = f'<a href="{url}" target="_blank" rel="noopener external">{name} ↗</a>'
    else:
        h = name
    if support:
        h += f' · <a href="{support}" target="_blank" rel="noopener external">support them</a>'
    return f"<li>{h}</li>"

PAGES["/about/members/"] = {
    "title": "Member associations",
    "desc": "DysNet's members are the national associations families actually belong to: more than thirty limb-difference and thalidomide organisations across fourteen countries, on four continents.",
    "crumbs": [("/about/", "About"), ("/about/members/", "Member associations")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · The network</p>
    <h1 class="display">The associations families belong to.</h1>
    <p>DysNet is a federation: our members are national associations of people with limb differences and their families. Find yours below, or bring your association in.</p>

    <div style="margin-top:var(--space-4)">
      {"".join(f'<div class="country"><h3>{c}</h3><ul>{"".join(member_li(m) for m in ms)}</ul></div>' for c, ms in MEMBERS)}
    </div>

    {opener("01", "Join", "Two ways in.")}
    <div class="grid cols-2">
      <div class="card"><h3 class="h4">Full member</h3><p>For associations ready to take part in governance: voting rights, a voice at the AGM, and a duty to feed the registers. Annual fee €50.</p></div>
      <div class="card" style="--acc:var(--dys-green);--acc-text:var(--dys-green-text)"><h3 class="h4">Associate (observer)</h3><p>For associations that want to support one mission, typically the registry, without governance duties or fees, returning to full membership when capacity allows.</p></div>
    </div>
    <p style="margin-top:var(--space-3)"><a class="btn btn-primary" href="mailto:info@dysnet.org?subject=Membership">Write to us about membership</a></p>
    <p style="font-size:var(--text-small);color:var(--dys-muted)">Member associations are also encouraged to register in <a href="https://www.orpha.net/en/patient-organisations" target="_blank" rel="noopener external">Orphanet’s directory of patient organisations</a>, where families and clinicians across Europe and beyond search for support groups.</p>
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
    <h1 class="display">Our documents, in the open.</h1>
    <p>An organisation of volunteers runs on trust. The texts that govern DysNet and the accounts that trace its funds are published here.</p>
    <div style="margin-top:var(--space-4)">
      <article class="entry"><h3>Statutes of DysNet <span class="badge live">2011</span></h3><p>Adopted by the Extraordinary Meetings of 20 October 2011. Name, objectives, membership, decision-making bodies, board, accounts and audit.</p><p class="src"><a href="/about/statutes/">Read online</a> · PDF · English</p></article>
      <article class="entry"><h3>A Refocused Strategy 2026-2029 <span class="badge live">AGM 2026</span></h3><p>Three missions, one task each, a governance built to carry them, and funding tied to each. Proposal before the AGM of 26 August 2026.</p><p class="src">PDF · English</p></article>
      <article class="entry"><h3>Annual accounts <span class="badge example">to publish</span></h3><p>The previous year’s operating statement, accounts and auditor’s report, as considered by each AGM.</p><p class="src">Published after each AGM</p></article>
      <article class="entry"><h3>AGM minutes and reports <span class="badge example">to publish</span></h3><p>Minutes of general meetings and the first mission reports, from the AGM 2027 onward.</p><p class="src">Published after each meeting</p></article>
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
    <h1 class="display">Talk to us.</h1>
    <p>One address reaches the whole network: <a href="mailto:info@dysnet.org"><strong>info@dysnet.org</strong></a>.</p>
    <div class="grid cols-3" style="margin-top:var(--space-4)">
      <div class="card"><h3 class="h4">Families</h3><p>Looking for information or an association near you? Start with <a href="/knowledge/understanding-dysmelia/">Understanding dysmelia</a> and <a href="/about/members/">the member directory</a>.</p></div>
      <div class="card acc-research"><h3 class="h4">Researchers &amp; clinicians</h3><p>Ask to be listed in the <a href="/knowledge/researchers/">researcher register</a> or propose a study for <a href="/knowledge/ongoing-studies/">the overview</a>.</p></div>
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
    "og": "/assets/img/inail-lab-2.jpg",
    "title": "Support DysNet",
    "desc": "Support the dysmelia network: a one-off or monthly gift, association membership or in-kind help carries DysNet's three missions — knowledge, registry and voice.",
    "crumbs": [("/donate/", "Support DysNet")],
    "body": """
<section>
  <div class="container don-grid">
    <div>
      <div class="tick" style="background:var(--dys-green)"></div>
      <p class="eyebrow" style="color:var(--dys-green-text)">Support · Every gift carries a mission</p>
      <h1 class="display">Power the network families rely on.</h1>
      <p>DysNet runs entirely on volunteers, so a small gift goes remarkably far: it keeps the registers current, the registry moving, and a delegate in the room when European decisions are made.</p>
      <ul class="don-carry">
        <li><strong>Knowledge</strong> · hosting &amp; translation of the four registers</li>
        <li><strong>Registry</strong> · the patient-owned data flagship</li>
        <li><strong>Voice</strong> · delegates where decisions are made</li>
      </ul>
      <figure class="don-photo">
        <img src="/assets/img/inail-lab-2.jpg" alt="Prosthetics being crafted in the INAIL workshop visited by the DysNet board" loading="lazy">
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
        <button type="button" aria-pressed="true">€50<small>member level</small></button>
        <button type="button" aria-pressed="false">€100<small>supporter</small></button>
        <button type="button" aria-pressed="false">€250<small>patron</small></button>
        <button type="button" aria-pressed="false">€500<small>benefactor</small></button>
        <button type="button" aria-pressed="false">Other<small>you choose</small></button>
      </div>
      <button type="button" class="btn-go" id="bank-toggle">Give by bank transfer</button>
      <div class="bank-reveal" id="bank-details">
        <strong>Beneficiary:</strong> DysNet Ideell Förening, Solna, Sweden<br>
        <strong>Reference:</strong> your name + “donation”<br>
        <strong>Account details:</strong> confirmed by the treasurer before publication; request them at
        <a href="mailto:sal.giambruno@dysnet.org">sal.giambruno@dysnet.org</a> or
        <a href="mailto:info@dysnet.org">info@dysnet.org</a>.
      </div>
      <p class="fine">Online card payment arrives with the live site. Accounts are published after each AGM on the <a href="/about/transparency/" style="color:#d8fcc8">transparency page</a>.</p>
    </div>
  </div>
</section>

<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">01 · Other ways to help</p>
    <h2 class="h2">Not all gifts are money.</h2>
    <div class="grid cols-3" style="margin-top:var(--space-4)">
      <div class="card"><h3 class="h4">Association membership</h3><p>€50 a year gives your association a vote and a voice, and your families the registers. An associate status without fees exists for associations with limited capacity.</p><p class="meta"><a href="/about/members/">How to join</a></p></div>
      <div class="card" style="--acc:var(--dys-green);--acc-text:var(--dys-green-text)"><h3 class="h4">In-kind contributions</h3><p>Design, hosting, translation or research hours: the most valuable gifts for the registers come from partners of member associations.</p><p class="meta"><a href="mailto:info@dysnet.org?subject=In-kind%20contribution">Offer a skill</a></p></div>
      <div class="card acc-centres"><h3 class="h4">Follow the money</h3><p>Funding is tied to missions, and the accounts are public. See exactly what your support carried.</p><p class="meta"><a href="/about/transparency/">Transparency</a></p></div>
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
    "desc": "The statutes of DYSNET (EDRIC), adopted 20 October 2011: objective, membership, general meetings, board, accounts, audit and amendment rules, readable online.",
    "crumbs": [("/about/", "About"), ("/about/statutes/", "Statutes")],
    "body": f"""
<section>
  <div class="container">
    <div class="tick"></div>
    <p class="eyebrow">About · Governing text</p>
    <h1 class="display">The statutes, readable online.</h1>
    <p>Adopted by the two Extraordinary Meetings of 20 October 2011, replacing the founding regulations of 13 October 2008. This page is an abridged, plain-language rendering for orientation; the signed PDF remains the authoritative text and is available from the secretary.</p>
    {statute_html()}
  </div>
</section>
""",
}

PAGES["/knowledge/guides/patient-owned-registry/"] = {
    "title": "What is a patient-owned registry?",
    "desc": "A two-minute, plain-language guide: what a patient-owned registry of limb malformations is, who owns the data, and what it changes for families and researchers.",
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
    <p>In most registries, a hospital or a company decides what is collected and who may use it. In a patient-owned registry, the patient community governs those decisions. Families contribute on explicit consent, can withdraw at any time, and the data serves care and research only; it is never bought or sold.</p>

    <div class="tick"></div><p class="eyebrow">03 · For families</p>
    <h2 class="h2">Answer questions once, help every family after you.</h2>
    <p>Every entry makes the picture sharper: how frequent each condition is, which treatments help at which age, where expertise lives. The next family gets better answers because yours were recorded.</p>

    <div class="tick"></div><p class="eyebrow">04 · For researchers</p>
    <h2 class="h2">Comparable data across countries, at last.</h2>
    <p>Limb-difference research is starved of data because cases are rare and scattered. An interoperable registry pools them across borders in one comparable format, large enough to study.</p>

    <div class="tick"></div><p class="eyebrow">05 · How DysNet builds it</p>
    <h2 class="h2">Association by association, with a technical partner.</h2>
    <p>Member associations bring their families in, country by country. <a href="https://www.healthdatasafe.org">Health Data Safe</a>, a Swiss non-profit foundation, is proposed as technical and operational partner; the mandate is before the AGM of 26 August 2026. Read more on <a href="/registry/">the registry page</a>.</p>
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
    <p style="margin-top:var(--space-4);font-size:var(--text-small);color:var(--dys-muted)">Or jump to:
      <a href="/knowledge/">Knowledge</a> · <a href="/registry/">The registry</a> · <a href="/voice/reports/">Reports</a> · <a href="/about/members/">Member associations</a> · <a href="/donate/">Support DysNet</a></p>
  </div>
</section>
""",
}


def build():
    written = []
    for path, page in PAGES.items():
        out_dir = ROOT / path.strip("/")
        out_dir.mkdir(parents=True, exist_ok=True)
        html = head(page["title"], page["desc"], path, page.get("is_home", False), page.get("og"))
        html += header_html(path if path != "/" else "-")
        if page.get("crumbs"):
            html += crumbs(*page["crumbs"])
        html += page["body"]
        html = html.replace("__MAP_HERO__", MAP_HERO)
        html += FOOTER
        (out_dir / "index.html").write_text(rebase(html), encoding="utf-8")
        written.append(path)

    # Root 404.html (GitHub Pages convention, as on the HDS site)
    import shutil
    shutil.copyfile(ROOT / "404" / "index.html", ROOT / "404.html")

    # Search index for the ⌘K search (HDS Search.astro pattern)
    cond_kw = " ".join(c[0] for c in CONDITIONS)
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
        f"  <url><loc>{SITE}{p}</loc><changefreq>weekly</changefreq></url>" for p in PAGES if p != "/404/")
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding="utf-8")

    # GitHub Pages: serve the folder verbatim, no Jekyll processing
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")

    # robots.txt — the DEMO must not be indexed; the live site would allow all
    (ROOT / "robots.txt").write_text(
        "# Demonstration preview — do not index.\n"
        "# The production robots.txt allows all and points to /sitemap.xml.\n"
        "User-agent: *\nDisallow: /\n", encoding="utf-8")

    print(f"Built {len(written)} pages:")
    for p in written:
        print("  ", p)


if __name__ == "__main__":
    build()
