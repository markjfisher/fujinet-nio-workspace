#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

echo "== workspace"
git -C "$NIO_WORKSPACE" status --short --branch
echo

echo "== submodule pointers"
git -C "$NIO_WORKSPACE" submodule status --recursive
echo

for repo in \
  "$FUJINET_NIO" \
  "$FUJINET_NIO_LIB" \
  "$FUJINET_NIO_DRIVER" \
  "$NIO_APPS" \
  "$NIO_CORE_APPS" \
  "$NIO_CONFIG" \
  "$FUJINET_QEMU_MSDOS" \
  "$FN_ROM" \
  "$BOUNCE_WORLD" \
  "$FUJINET_EMULATOR_BRIDGE" \
  "$CC65_HOME" \
  "$QEMU_MSDOS_INIT"
do
  if [ ! -d "$repo" ]; then
    echo "== $repo"
    echo "missing"
    echo
    continue
  fi

  echo "== ${repo#$NIO_WORKSPACE/}"
  git -C "$repo" status --short --branch
  echo
done
