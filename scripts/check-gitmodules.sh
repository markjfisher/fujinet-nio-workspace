#!/usr/bin/env bash
# Every submodule under repos/ must point at the project's repositories
# (github.com/markjfisher/..., github.com/fujinet-nio/... or github.com/FujiNetWIFI/... (upstream forks we track)). Submodules under external/ are other people's
# tools that NIO uses but does not control: they must be anonymous https://github.com/
# URLs (no fork, no ssh) and opt-in (update = none). To work on forks, see CONTRIBUTING.md: add a
# `fork` remote inside the submodule, or override the URL in local git config
# instead of committing it:
#   git config submodule.repos/fujinet-nio.url git@github.com:<you>/fujinet-nio.git
#   git submodule sync repos/fujinet-nio
set -euo pipefail

cd "$(dirname "$0")/.."
bad=$(git config -f .gitmodules --get-regexp '^submodule\..*\.url$' |
      awk '$1 ~ /^submodule\.external\// { next }
           $2 !~ /^(git@github\.com:|https:\/\/github\.com\/)(markjfisher|fujinet-nio|FujiNetWIFI)\// { print "  " $0 }')
for key in $(git config -f .gitmodules --name-only --get-regexp '^submodule\.external/.*\.url$'); do
    name=${key%.url}
    url=$(git config -f .gitmodules "$key")
    case "$url" in
        https://github.com/*) ;;
        *) bad="$bad
  $key $url (external/ needs an https://github.com/ URL)" ;;
    esac
    [ "$(git config -f .gitmodules "$name.update" || true)" = none ] ||
        bad="$bad
  $name needs update = none (external/ submodules are opt-in)"
done
if [ -n "$bad" ]; then
    echo ".gitmodules points submodules away from markjfisher/, fujinet-nio/ and FujiNetWIFI/:"
    echo "$bad"
    echo "Use 'git config submodule.<path>.url <fork>' locally; don't commit fork URLs."
    exit 1
fi
echo ".gitmodules: $(git config -f .gitmodules --get-regexp '^submodule\..*\.url$' | wc -l) submodule URLs OK (repos/ at markjfisher/, fujinet-nio/ or FujiNetWIFI/, external/ opt-in https)"
