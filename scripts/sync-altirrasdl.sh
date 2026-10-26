#!/usr/bin/env bash
# Brings the AltirraSDL fork up to date with ilmenit/AltirraSDL.
#
# The fork keeps the NIO work as a stack of two branches:
#
#   upstream/main
#     └─ nio-upstream      the embedded device and its hooks only (PR-ready)
#          └─ nio-integration   plus the embedded tests and fixtures (pinned)
#
# This fetches upstream, rebases nio-upstream onto upstream/main, then replays
# nio-integration's own commits on top of the rebased nio-upstream. Nothing is
# pushed. Both branches are rewritten, so pushing needs --force-with-lease.
#
# Usage: scripts/sync-altirrasdl.sh [--pin]
#   --pin   after a successful sync, commit the new AltirraSDL pin in the
#           workspace (local commit only)
#
# If a rebase stops on a conflict, resolve it, run `git rebase --continue`
# inside repos/AltirraSDL, then run this script again: it resumes. To give up
# instead: `git rebase --abort`, then restore the branches from the backup
# refs the script prints (refs/sync-backup/...).
#
# ALTIRRA_DIR overrides the repository path (used for testing the script).
set -euo pipefail

workspace=$(cd "$(dirname "$0")/.." && pwd)
repo=${ALTIRRA_DIR:-$workspace/repos/AltirraSDL}
base_branch=nio-upstream
top_branch=nio-integration
upstream_ref=upstream/main

pin=0
for arg in "$@"; do
    case $arg in
        --pin) pin=1 ;;
        -h|--help) sed -n '2,/^set -e/p' "$0" | sed '$d;s/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown argument: $arg (see --help)" >&2; exit 2 ;;
    esac
done

g() { git -C "$repo" "$@"; }
die() { echo "error: $*" >&2; exit 1; }

[ -d "$repo/.git" ] || [ -f "$repo/.git" ] || die "$repo is not a git checkout (git submodule update --init repos/AltirraSDL)"
g rev-parse --verify -q "$base_branch" >/dev/null || die "branch $base_branch does not exist locally"
g rev-parse --verify -q "$top_branch" >/dev/null || die "branch $top_branch does not exist locally"
g remote get-url upstream >/dev/null 2>&1 || die "no 'upstream' remote (git -C $repo remote add upstream https://github.com/ilmenit/AltirraSDL)"

git_dir=$(g rev-parse --absolute-git-dir)
state=$git_dir/altirrasdl-sync-state

if g status --porcelain --untracked-files=no | grep -q .; then
    # A rebase stopped on a conflict also shows here; only refuse when idle.
    if [ ! -d "$git_dir/rebase-merge" ] && [ ! -d "$git_dir/rebase-apply" ]; then
        die "uncommitted changes in $repo; commit or stash them first"
    fi
fi
if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; then
    die "a rebase is still in progress in $repo: resolve it, run 'git rebase --continue', then rerun this script"
fi

echo "Fetching upstream..."
g fetch upstream

if [ -f "$state" ]; then
    # shellcheck disable=SC1090
    . "$state"
    echo "Resuming a previous sync (old $base_branch tip ${old_base:0:8})."
else
    old_base=$(g rev-parse "$base_branch")
    old_top=$(g rev-parse "$top_branch")
    stamp=$(date +%Y%m%d-%H%M%S)
    g update-ref "refs/sync-backup/$base_branch-$stamp" "$old_base"
    g update-ref "refs/sync-backup/$top_branch-$stamp" "$old_top"
    printf 'old_base=%s\nold_top=%s\nstamp=%s\n' "$old_base" "$old_top" "$stamp" > "$state"
    echo "Backups: refs/sync-backup/$base_branch-$stamp, refs/sync-backup/$top_branch-$stamp"
fi

# 1. nio-upstream on top of upstream/main.
if g merge-base --is-ancestor "$upstream_ref" "$base_branch"; then
    echo "$base_branch already contains $upstream_ref."
else
    echo "Rebasing $base_branch onto $upstream_ref..."
    g checkout -q "$base_branch"
    if ! g rebase "$upstream_ref"; then
        echo
        echo "Conflict while rebasing $base_branch. Resolve it, 'git rebase --continue' in $repo, then rerun." >&2
        exit 1
    fi
fi

# 2. nio-integration's own commits (those after the old nio-upstream tip) on top.
if g merge-base --is-ancestor "$base_branch" "$top_branch" &&
   [ "$(g merge-base "$base_branch" "$top_branch")" = "$(g rev-parse "$base_branch")" ]; then
    echo "$top_branch is already on top of $base_branch."
else
    echo "Replaying $top_branch onto $base_branch..."
    g checkout -q "$top_branch"
    if ! g rebase --onto "$base_branch" "$old_base" "$top_branch"; then
        echo
        echo "Conflict while rebasing $top_branch. Resolve it, 'git rebase --continue' in $repo, then rerun." >&2
        exit 1
    fi
fi

rm -f "$state"
g checkout -q "$top_branch"

echo
echo "Done."
g log --oneline "$upstream_ref..$top_branch"
echo
echo "$top_branch: $(g rev-list --count "$upstream_ref..$top_branch") commit(s) ahead of $upstream_ref," \
     "$(g rev-list --count "$top_branch..$upstream_ref") behind."

if [ "$pin" = 1 ]; then
    git -C "$workspace" add repos/AltirraSDL
    if git -C "$workspace" diff --cached --quiet -- repos/AltirraSDL; then
        echo "Workspace pin already up to date."
    else
        git -C "$workspace" commit -q -m "Pin AltirraSDL to the rebased $top_branch" -- repos/AltirraSDL
        echo "Committed the workspace pin (not pushed)."
    fi
fi

cat <<EOF

Next (nothing has been pushed):
  git -C $repo push --force-with-lease origin $base_branch $top_branch
EOF
[ "$pin" = 1 ] || echo "  scripts/sync-altirrasdl.sh --pin   # or: git add repos/AltirraSDL && git commit"
echo "  git push origin master   # workspace, after the submodule push"
