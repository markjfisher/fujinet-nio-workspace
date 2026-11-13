#!/usr/bin/env bash
# Checks that every submodule pin changed since BASE points at a commit on a
# branch of the submodule's own repository (the .gitmodules URL, i.e.
# fujinet-nio/...). A pin to a commit that is only on a fork, or only in an
# open pull request, breaks `git submodule update` for everyone else: merge
# the submodule PR first, then bump the pin.
#
# Usage: scripts/check-submodule-pins.sh [BASE]      (default: origin/master)
#        scripts/check-submodule-pins.sh --all       (every pin, not just changed)
set -euo pipefail

cd "$(dirname "$0")/.."

mode=changed
base=origin/master
case "${1:-}" in
    --all) mode=all ;;
    "") ;;
    *) base=$1 ;;
esac

# "<path> <sha>" for each pin to check.
pins=$(
    if [ "$mode" = all ]; then
        git ls-tree -r HEAD | awk '$1 == "160000" { print $4, $3 }'
    else
        # New mode 160000: a submodule added or moved to a new commit.
        git diff --raw --no-abbrev "$(git merge-base "$base" HEAD)" HEAD |
            awk '$2 == "160000" && $5 != "D" { split($0, f, "\t"); print f[2], $4 }'
    fi
)

if [ -z "$pins" ]; then
    echo "No submodule pins to check."
    exit 0
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
failed=0

while read -r path sha; do
    url=$(git config -f .gitmodules "submodule.$path.url")
    # Anonymous HTTPS, so CI needs no keys (the repositories are public).
    https=$(echo "$url" | sed -E 's#^git@github\.com:#https://github.com/#')
    repo="$work/$(echo "$path" | tr / _).git"
    git init -q --bare "$repo"
    # Branches only (not refs/pull/*), commits only (no trees or blobs).
    if ! git -C "$repo" fetch -q --filter=tree:0 "$https" '+refs/heads/*:refs/heads/*'; then
        echo "FAIL $path: cannot fetch $https"
        failed=1
        continue
    fi
    if git -C "$repo" cat-file -e "$sha^{commit}" 2>/dev/null &&
       branch=$(git -C "$repo" for-each-ref --contains "$sha" --format='%(refname:short)' refs/heads | head -1) &&
       [ -n "$branch" ]; then
        echo "ok   $path ${sha:0:8} (on $branch)"
    else
        echo "FAIL $path ${sha:0:8} is not on any branch of $url"
        failed=1
    fi
done <<< "$pins"

if [ "$failed" -ne 0 ]; then
    echo
    echo "Pin submodules only to commits merged into their own repositories:"
    echo "merge the submodule PR first, then bump the pin. See CONTRIBUTING.md."
    exit 1
fi
