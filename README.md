# DysNet website

Proposal for a new [dysnet.org](https://www.dysnet.org), prepared for the DysNet
Annual General Meeting of 26 August 2026.

The site is the working tool of Mission 1 of the *Refocused Strategy 2026-2029*:
four maintained registers (research library, ongoing studies, researchers, care
centres) replacing the blog and static pages, plus the registry flagship
(Mission 2) and structured delegate reports (Mission 3).

## What is in this repository

| Path | What it is |
|---|---|
| `build-demo.py` | Generates the whole site. One layout (SEO head, header, footer) with page bodies injected. |
| `demo/` | The generated site: 19 pages, assets, `sitemap.xml`, `search-index.json`. |
| `demo/assets/css/site.css` | Stylesheet: golden-ratio design tokens, DysNet brand colours. |
| `demo/assets/js/site.js` | Search, condition finder, donate widget, click-to-play video. |

## Build and preview

```bash
python3 build-demo.py                       # regenerate demo/
python3 -m http.server 8732 --directory demo # then open http://localhost:8732
```

No dependencies beyond Python 3. The pages are plain static HTML, so they can be
hosted anywhere (GitHub Pages included) at near-zero cost.

## Status: demonstration preview

Every page carries a ribbon saying so. Register entries marked **example** are
placeholders for the named maintainers to replace. `robots.txt` blocks search
indexing while the site is a demo. The Health Data Safe registry partnership is
described as *proposed*, pending the AGM vote.

This repository holds the website only. The documents it was built from (the
Refocused Strategy 2026-2029, the statutes, the Board-approved November 2023
website structure, the chair's July 2026 activities report, board
correspondence, logo and photo originals) stay in the working folder and are
not published here. Condition pages link to
[Orphanet](https://www.orpha.net) by ORPHAcode, verified August 2026.
