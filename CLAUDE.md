# Working in this repository

## Before you change anything: take a worktree

Loïc runs several Claude Code sessions at once against this project. They share
one git index and one `HEAD`, so two sessions in the same checkout collide:
a `git add` in one is visible to a `git commit` in the other, and a commit
swallows work that is not its own. This happened on 13 September 2026 and took
an afternoon to untangle.

So, first thing, give yourself your own checkout:

```bash
tools/session-worktree.sh new <short-name>     # e.g. new china-centres
```

It prints a path under `../dysnet-worktrees/`. Move the session there and work
there. When the branch is merged, `tools/session-worktree.sh done <short-name>`
puts it away; it refuses if you have uncommitted work, and it keeps the branch
if it is not merged.

`tools/session-worktree.sh list` shows what exists and what is dirty in each.

## Before you commit: check who else is awake

Even in a worktree, `main` is shared. Before touching it:

```bash
pgrep -f "build-demo.py|build-bibliography.py"   # a build running means a session is working
git worktree list                                 # and what they are on
git reflog -5                                     # has HEAD moved under you?
```

If another session is active, do not merge to `main` and do not rewrite history.
Commit on your own branch and hand the merge to Loïc.

## The main checkout is special

`main` stays checked out at `dysnet-website/`. That is where the site is built
for publication, and it holds about 1 GB of git-ignored raw inputs that no
worktree has:

| Path | What it is |
|---|---|
| `tools/ne10m/`, `tools/ghs/`, `tools/pop/` | Natural Earth and GHSL sources behind the map tiles |
| `tools/geo/`, `tools/terato/` | geocoding and teratogen working files |

Regenerate map tiles (`tools/build-tiles.sh`, `tools/build-pop-tiles.sh`) in the
main checkout only. Everything else builds anywhere.

## Publishing

GitHub Pages serves `docs/` from `main`. **Committing a rebuilt `docs/` to `main`
publishes to www.dysnet.org.** Never push without being asked. Never commit a
`DEPLOY=pages` build to `main`: it deletes `docs/CNAME` and takes the custom
domain off Pages.

## Registers

The four knowledge registers are built from `tools/*.json` by `build-demo.py`.
Each entry records where it came from, and the wording of that provenance is
load-bearing, not decoration:

- **named by** — a DysNet member association listed the centre on its own site,
  or the board visited it. This is the strong form.
- **verified from** — no member association exists in that country, so the entry
  rests on the institution's own page stating congenital limb difference in its
  scope, or on a peer-reviewed series from that centre. Weaker, and said so.

Set `via_verb` on an entry to switch it. Refusals belong in the matching
`*-harvest.json` with the reason, so a later reader knows what was considered
and rejected. Do not list a centre on the strength of a commercial physician
directory.
