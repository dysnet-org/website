#!/usr/bin/env bash
# One git worktree per working session.
#
# Two Claude Code sessions (or two terminals) in the same checkout share one git
# index and one HEAD. A `git add` in one is visible to a `git commit` in the
# other, so a commit silently swallows work that is not its own, and switching
# branch in one makes the other's next commit land on the wrong branch. That
# happened on 13 September 2026 and cost an afternoon of untangling.
#
# A worktree gives each session its own checkout, its own index and its own
# HEAD, all sharing the one object database. Nothing can collide.
#
#   tools/session-worktree.sh new china-centres   # make one and print where it is
#   tools/session-worktree.sh list                # what exists now
#   tools/session-worktree.sh done china-centres  # put it away when finished
#
# The main checkout keeps `main` and is where the site is built and published.
# Sessions work on a branch in their own worktree and merge back to main.

set -euo pipefail

# The shared .git lives in the main checkout, whether we were called from there
# or from inside a worktree.
GIT_COMMON=$(git rev-parse --path-format=absolute --git-common-dir)
MAIN_CHECKOUT=$(dirname "$GIT_COMMON")
WORKTREE_ROOT="$(dirname "$MAIN_CHECKOUT")/dysnet-worktrees"

usage() {
  # the header comment block, minus its leading hashes
  awk 'NR>1 && !/^#/{exit} NR>1{sub(/^# ?/,""); print}' "$0"
  exit "${1:-1}"
}

die() { printf '\nerror: %s\n\n' "$1" >&2; exit 1; }

slug() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9-' '-' | sed 's/^-*//;s/-*$//'
}

cmd_new() {
  [ $# -ge 1 ] || die "give the session a short name, e.g. 'new china-centres'"
  local name branch path base
  name=$(slug "$1")
  [ -n "$name" ] || die "that name reduces to nothing usable; try letters and digits"
  branch="session/$name"
  path="$WORKTREE_ROOT/$name"

  git -C "$MAIN_CHECKOUT" show-ref --verify --quiet "refs/heads/$branch" &&
    die "branch $branch already exists. Use a different name, or 'done $name' to put the old one away."
  [ -e "$path" ] && die "$path already exists. Remove it, or pick another name."

  base=$(git -C "$MAIN_CHECKOUT" rev-parse --short main)
  mkdir -p "$WORKTREE_ROOT"
  git -C "$MAIN_CHECKOUT" worktree add -b "$branch" "$path" main

  cat <<EOF

Worktree ready.

  path     $path
  branch   $branch
  based on main at $base

Work there, not in the main checkout:

  cd "$path"
  python3 build-demo.py
  python3 tools/serve.py 8732 docs

Notes
  · The main checkout keeps 'main' checked out. A worktree can never be on main,
    which is exactly what stops two sessions fighting over it.
  · The git-ignored raw inputs (tools/ghs, tools/ne10m, tools/pop, tools/geo,
    tools/terato, about 1 GB) exist only in the main checkout. Regenerate map
    tiles there, not here.
  · Each worktree carries its own copy of docs/, about 135 MB, mostly the two
    .pmtiles basemaps.

When the work is merged, put it away with:

  tools/session-worktree.sh done $name

EOF
}

cmd_list() {
  printf '\nWorktrees\n\n'
  git -C "$MAIN_CHECKOUT" worktree list
  printf '\nUncommitted work in each\n\n'
  git -C "$MAIN_CHECKOUT" worktree list --porcelain | awk '/^worktree /{print substr($0,10)}' |
    while IFS= read -r wt; do
      local_n=$(git -C "$wt" status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')
      local_b=$(git -C "$wt" branch --show-current 2>/dev/null || echo '(detached)')
      printf '  %-26s %-18s %s modified\n' "$local_b" "$(basename "$wt")" "$local_n"
    done
  printf '\n'
}

cmd_done() {
  [ $# -ge 1 ] || die "which one? e.g. 'done china-centres'"
  local name branch path force dirty
  name=$(slug "$1"); shift
  force=""
  [ "${1:-}" = "--force" ] && force=1
  branch="session/$name"
  path="$WORKTREE_ROOT/$name"

  [ -d "$path" ] || die "no worktree at $path. 'list' shows what exists."

  dirty=$(git -C "$path" status --porcelain --untracked-files=no | wc -l | tr -d ' ')
  if [ "$dirty" != "0" ] && [ -z "$force" ]; then
    printf '\n%s has %s uncommitted file(s):\n\n' "$branch" "$dirty"
    git -C "$path" status --short --untracked-files=no
    die "commit them first, or repeat with --force to throw them away"
  fi

  git -C "$MAIN_CHECKOUT" worktree remove ${force:+--force} "$path"
  printf '\nWorktree removed: %s\n' "$path"

  if git -C "$MAIN_CHECKOUT" branch --merged main | grep -qx "  $branch"; then
    git -C "$MAIN_CHECKOUT" branch -d "$branch"
    printf 'Branch %s was merged into main, so it is deleted too.\n\n' "$branch"
  else
    printf 'Branch %s is NOT merged into main and is kept.\n' "$branch"
    printf 'Merge it, or delete it deliberately with: git branch -D %s\n\n' "$branch"
  fi
}

case "${1:-}" in
  new)  shift; cmd_new "$@" ;;
  list) cmd_list ;;
  done) shift; cmd_done "$@" ;;
  -h|--help|help) usage 0 ;;
  *)    usage 1 ;;
esac
