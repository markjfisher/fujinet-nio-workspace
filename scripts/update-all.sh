#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

usage() {
  cat <<EOF
Usage: scripts/update-all.sh [--remote]

Without --remote, initialize/update submodules to the commits pinned by this
workspace repository.

With --remote, fetch each submodule's configured remote branch and update the
submodule working tree. Review and commit the changed submodule pointers in the
workspace repo afterwards.
EOF
}

remote=false
case "${1:-}" in
  "") ;;
  --remote) remote=true ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
esac

if [ "$remote" = true ]; then
  git -C "$NIO_WORKSPACE" submodule update --init --recursive --remote
else
  git -C "$NIO_WORKSPACE" submodule update --init --recursive
fi

"$SCRIPT_DIR/status-all.sh"
