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
export FUJINET_NIO_MSDOS="$NIO_WORKSPACE/repos/fujinet-nio-msdos"
export FUJINET_MSDOS="$NIO_WORKSPACE/repos/fujinet-msdos"
export FUJINET_LIB="$NIO_WORKSPACE/repos/fujinet-lib"
export FN_ROM="$NIO_WORKSPACE/repos/fn-rom"
export BOUNCE_WORLD_CLIENT_NIO="$NIO_WORKSPACE/repos/bounce-world-client-nio"
export BOUNCE_WORLD="$BOUNCE_WORLD_CLIENT_NIO"
export CC65_HOME="$NIO_WORKSPACE/repos/cc65"
export QEMU_MSDOS_INIT="$NIO_WORKSPACE/repos/qemu-msdos-init"
export PDCURSES_DIR="${PDCURSES_DIR:-$NIO_WORKSPACE/repos/PDCurses}"

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
export UV_CACHE_DIR="${UV_CACHE_DIR:-$NIO_BUILD_DIR/uv-cache}"

export FUJINET_NIO_TCP_DEBUG_BIN="${FUJINET_NIO_TCP_DEBUG_BIN:-$FUJINET_NIO/build/fujibus-tcp-debug/fujinet-nio}"
export FUJINET_NIO_TCP_RELEASE_BIN="${FUJINET_NIO_TCP_RELEASE_BIN:-$FUJINET_NIO/build/fujibus-tcp-release/fujinet-nio}"
export FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN="${FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN:-$FUJINET_NIO/build/atari-fujibus-netsio-debug/fujinet-nio}"
export ALTIRRA_WORKSPACE_BIN="${ALTIRRA_WORKSPACE_BIN:-$NIO_WORKSPACE/repos/AltirraSDL/build/linux-debug/src/AltirraSDL/AltirraSDL}"
export FUJINET_EMULATOR_BRIDGE="${FUJINET_EMULATOR_BRIDGE:-$NIO_WORKSPACE/repos/fujinet-emulator-bridge}"
export ATARI_DOS_BOOT_DISK="${ATARI_DOS_BOOT_DISK:-$HOME/dev/atari/fujinet-apps/netcat/atari/ados20d.atr}"

export NIO_APPS_MSDOS_BIN="${NIO_APPS_MSDOS_BIN:-$NIO_APPS/build/msdos/bin}"
export NIO_APPS_ATARI_BIN="${NIO_APPS_ATARI_BIN:-$NIO_APPS/build/atari/bin}"
export BOUNCE_WORLD_CLIENT_NIO="${BOUNCE_WORLD_CLIENT_NIO:-$BOUNCE_WORLD}"
export BOUNCE_WORLD="${BOUNCE_WORLD:-$BOUNCE_WORLD_CLIENT_NIO}"
export PDCURSES_MSDOS_LIB="${PDCURSES_MSDOS_LIB:-$NIO_BUILD_DIR/pdcurses/msdos-small/pdcurses.lib}"

mkdir -p "$NIO_LOG_DIR" "$NIO_IMAGE_DIR"
