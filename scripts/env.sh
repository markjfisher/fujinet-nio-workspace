#!/usr/bin/env bash
set -euo pipefail

workspace_dir() {
  local src="${BASH_SOURCE[0]}"
  while [ -L "$src" ]; do
    local dir
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    case "$src" in
      /*) ;;
      *) src="$dir/$src" ;;
    esac
  done
  cd -P "$(dirname "$src")/.." && pwd
}

export NIO_WORKSPACE="${NIO_WORKSPACE:-$(workspace_dir)}"

export FUJINET_NIO="$NIO_WORKSPACE/repos/fujinet-nio"
export FUJINET_NIO_LIB="$NIO_WORKSPACE/repos/fujinet-nio-lib"
export NIO_APPS="$NIO_WORKSPACE/repos/nio-apps"
export FUJINET_QEMU_MSDOS="$NIO_WORKSPACE/repos/fujinet-qemu-msdos"
export FUJINET_MSDOS="$NIO_WORKSPACE/repos/fujinet-msdos"
export FUJINET_LIB="$NIO_WORKSPACE/repos/fujinet-lib"
export FN_ROM="$NIO_WORKSPACE/repos/fn-rom"
export BOUNCE_WORLD_CLIENT_NIO="$NIO_WORKSPACE/repos/bounce-world-client-nio"
export BOUNCE_WORLD="$BOUNCE_WORLD_CLIENT_NIO"

if [ -f "$HOME/.local/bin/add_watcom.sh" ]; then
  # shellcheck source=/dev/null
  set +e
  source "$HOME/.local/bin/add_watcom.sh"
  set -e
fi

if [ -f "$NIO_WORKSPACE/local/config.env" ]; then
  # shellcheck source=/dev/null
  source "$NIO_WORKSPACE/local/config.env"
fi

export NIO_BUILD_DIR="${NIO_BUILD_DIR:-$NIO_WORKSPACE/build}"
export NIO_LOG_DIR="${NIO_LOG_DIR:-$NIO_BUILD_DIR/logs}"
export NIO_IMAGE_DIR="${NIO_IMAGE_DIR:-$NIO_BUILD_DIR/images}"

export FUJINET_NIO_TCP_DEBUG_BIN="${FUJINET_NIO_TCP_DEBUG_BIN:-$FUJINET_NIO/build/fujibus-tcp-debug/fujinet-nio}"
export FUJINET_NIO_TCP_RELEASE_BIN="${FUJINET_NIO_TCP_RELEASE_BIN:-$FUJINET_NIO/build/fujibus-tcp-release/fujinet-nio}"

export NIO_APPS_MSDOS_BIN="${NIO_APPS_MSDOS_BIN:-$NIO_APPS/build/msdos/bin}"
export NIO_APPS_ATARI_BIN="${NIO_APPS_ATARI_BIN:-$NIO_APPS/build/atari/bin}"
export BOUNCE_WORLD_CLIENT_NIO="${BOUNCE_WORLD_CLIENT_NIO:-$BOUNCE_WORLD}"
export BOUNCE_WORLD="${BOUNCE_WORLD:-$BOUNCE_WORLD_CLIENT_NIO}"

mkdir -p "$NIO_LOG_DIR" "$NIO_IMAGE_DIR"
