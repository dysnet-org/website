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
| `docs/` | The generated site, served by GitHub Pages: 19 pages, assets, `sitemap.xml`, `search-index.json`. |
| `docs/assets/css/site.css` | Stylesheet: golden-ratio design tokens, DysNet brand colours. |
| `docs/assets/js/site.js` | Search, condition finder, donate widget, click-to-play video. |

## Build and preview

```bash
python3 build-demo.py                       # regenerate docs/
python3 -m http.server 8732 --directory docs # then open http://localhost:8732
```

No dependencies beyond Python 3. The pages are plain static HTML, so they can be
hosted anywhere at near-zero cost.

## Deployment

GitHub Pages serves the `docs/` folder of `main` (Settings → Pages → Source:
*Deploy from a branch*, branch `main`, folder `/docs`). Committing a rebuilt
`docs/` publishes the site; `docs/.nojekyll` keeps Pages from running Jekyll
over it.

Internal links are root-absolute, so they need a path prefix on the project URL.
`DEPLOY` selects the target:

```bash
python3 build-demo.py              # DEPLOY=pages (default)
DEPLOY=prod python3 build-demo.py  # for www.dysnet.org
```

| `DEPLOY` | Served at | Link prefix |
|---|---|---|
| `pages` (default) | `https://dysnet-org.github.io/website/` | `/website` |
| `prod` | `https://www.dysnet.org` | none |

`prod` is the one-line switch for the move to the real domain: it also sets the
canonical, Open Graph and `sitemap.xml` URLs. Add a `docs/CNAME` file at that
point and flip the default in `build-demo.py`.

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
