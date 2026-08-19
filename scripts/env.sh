#!/usr/bin/env bash

# avoid zd/zoxide/z interfering with cd functionality via aliases in shell
CD=cd

pathadd_end() {
  [ -d "$1" ] || return 1
  [[ ":$PATH:" == *":$1:"* ]] || export PATH="$PATH:$1"
}

workspace_dir() {
  local src="${BASH_SOURCE[0]}"

  while [ -L "$src" ]; do
    local dir
    dir="$(${CD} -P "$(dirname "$src")" && pwd)" || return 1
    src="$(readlink "$src")" || return 1

    case "$src" in
      /*) ;;
      *) src="$dir/$src" ;;
    esac
  done

  ${CD} -P "$(dirname "$src")/.." && pwd
}

setup_nio_environment() {
  local workspace

  if [[ -n ${NIO_WORKSPACE:-} ]]; then
    workspace="$NIO_WORKSPACE"
  else
    workspace="$(workspace_dir)" || return 1
  fi

  export NIO_WORKSPACE="$workspace"
  export FUJINET_NIO="$NIO_WORKSPACE/repos/fujinet-nio"
  export FUJINET_NIO_LIB="$NIO_WORKSPACE/repos/fujinet-nio-lib"
  export NIO_APPS="$NIO_WORKSPACE/repos/nio-apps"
  export NIO_CORE_APPS="$NIO_WORKSPACE/repos/nio-core-apps"
  export NIO_CONFIG="$NIO_WORKSPACE/repos/nio-config"
  export FUJINET_QEMU_MSDOS="$NIO_WORKSPACE/repos/fujinet-qemu-msdos"
  export FUJINET_NIO_DRIVER="$NIO_WORKSPACE/repos/fujinet-nio-driver"
  export FUJINET_LIB="$NIO_WORKSPACE/repos/fujinet-lib"
  export FN_ROM="$NIO_WORKSPACE/repos/fn-rom"
  export BOUNCE_WORLD_CLIENT_NIO="$NIO_WORKSPACE/repos/bounce-world-client-nio"
  export BOUNCE_WORLD="$BOUNCE_WORLD_CLIENT_NIO"
  export CC65_HOME="$NIO_WORKSPACE/repos/cc65"
  export CC65_ROOT="${CC65_ROOT:-$CC65_HOME}"
  export CC65_SRC="${CC65_SRC:-$CC65_ROOT}"
  export CC65_CLIB="$NIO_WORKSPACE/repos/cc65-clib"
  export QEMU_MSDOS_INIT="$NIO_WORKSPACE/repos/qemu-msdos-init"
  export PDCURSES_DIR="${PDCURSES_DIR:-$NIO_WORKSPACE/repos/PDCurses}"

  if [ -f "$NIO_WORKSPACE/local/config.env" ]; then
    # shellcheck source=/dev/null
    source "$NIO_WORKSPACE/local/config.env"
  fi

  # amiga-gcc is commonly installed by the official cross-toolchain bundle.
  # Keep the location configurable for developers using a different install.
  export AMIGA_TOOLCHAIN_BIN="${AMIGA_TOOLCHAIN_BIN:-/opt/amiga/bin}"
  pathadd_end "$AMIGA_TOOLCHAIN_BIN"
  
  export NIO_BUILD_DIR="${NIO_BUILD_DIR:-$NIO_WORKSPACE/build}"
  export NIO_LOG_DIR="${NIO_LOG_DIR:-$NIO_BUILD_DIR/logs}"
  export NIO_IMAGE_DIR="${NIO_IMAGE_DIR:-$NIO_BUILD_DIR/images}"
  export UV_CACHE_DIR="${UV_CACHE_DIR:-$NIO_BUILD_DIR/uv-cache}"
  export UV_TOOL_DIR="${UV_TOOL_DIR:-$NIO_BUILD_DIR/uv-tools}"
  
  export FUJINET_NIO_TCP_DEBUG_BIN="${FUJINET_NIO_TCP_DEBUG_BIN:-$FUJINET_NIO/build/fujibus-tcp-debug/fujinet-nio}"
  export FUJINET_NIO_TCP_RELEASE_BIN="${FUJINET_NIO_TCP_RELEASE_BIN:-$FUJINET_NIO/build/fujibus-tcp-release/fujinet-nio}"
  export FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN="${FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN:-$FUJINET_NIO/build/atari-fujibus-netsio-debug/fujinet-nio}"
  export AMIBERRY_BIN="${AMIBERRY_BIN:-amiberry}"
  export AMIBERRY_ASSET_ROOT="${AMIBERRY_ASSET_ROOT:-${HOME}/dev/amiga/amigaOS3.2}"
  export AMIBERRY_KICKSTART="${AMIBERRY_KICKSTART:-$AMIBERRY_ASSET_ROOT/ROM/kickCDTVa1000a500a2000a600.rom}"
  export AMIBERRY_WORKBENCH_ADF="${AMIBERRY_WORKBENCH_ADF:-$AMIBERRY_ASSET_ROOT/ADF/Workbench3.2.adf}"
  export AMIBERRY_OS_ROOT="${AMIBERRY_OS_ROOT:-$AMIBERRY_ASSET_ROOT}"
  export AMIBERRY_FAST_FILE_SYSTEM="${AMIBERRY_FAST_FILE_SYSTEM:-$AMIBERRY_OS_ROOT/L/FastFileSystem}"
  export AMIGA_WORKBENCH_CONFIG_FILE="${AMIGA_WORKBENCH_CONFIG_FILE:-$NIO_WORKSPACE/configs/amiga/workbenches.yaml}"
  export AMIGA_WORKBENCH_CONFIG="${AMIGA_WORKBENCH_CONFIG:-}"
  export AMIBERRY_HOST="${AMIBERRY_HOST:-127.0.0.1}"
  export AMIBERRY_PORT="${AMIBERRY_PORT:-23462}"
  export FUJINET_NIO_AMIGA_BIN="${FUJINET_NIO_AMIGA_BIN:-$FUJINET_NIO_TCP_DEBUG_BIN}"
  export AMIGA_TEST_APP="${AMIGA_TEST_APP:-wifitest}"
  export AMIGA_TEST_PROJECT="${AMIGA_TEST_PROJECT:-apps}"
  export AMIGA_TEST_COMMAND="${AMIGA_TEST_COMMAND:-$AMIGA_TEST_APP}"
  export AMIGA_TEST_INTERACTIVE="${AMIGA_TEST_INTERACTIVE:-0}"
  export AMIGA_TEST_DISK="${AMIGA_TEST_DISK:-$NIO_BUILD_DIR/images/amiga-$AMIGA_TEST_APP.hdf}"
  export ALTIRRA_WORKSPACE_BIN="${ALTIRRA_WORKSPACE_BIN:-$NIO_WORKSPACE/repos/AltirraSDL/build/linux-debug/src/AltirraSDL/AltirraSDL}"
  export FUJINET_EMULATOR_BRIDGE="${FUJINET_EMULATOR_BRIDGE:-$NIO_WORKSPACE/repos/fujinet-emulator-bridge}"
  export ATARI_DOS_BOOT_DISK="${ATARI_DOS_BOOT_DISK:-$HOME/dev/atari/fujinet-apps/netcat/atari/ados20d.atr}"
  
  export NIO_APPS_MSDOS_BIN="${NIO_APPS_MSDOS_BIN:-$NIO_APPS/build/msdos/bin}"
  export NIO_APPS_ATARI_BIN="${NIO_APPS_ATARI_BIN:-$NIO_APPS/build/atari/bin}"
  export NIO_CORE_APPS_MSDOS_BIN="${NIO_CORE_APPS_MSDOS_BIN:-$NIO_CORE_APPS/build/msdos/bin}"
  export NIO_CORE_APPS_ATARI_BIN="${NIO_CORE_APPS_ATARI_BIN:-$NIO_CORE_APPS/build/atari/bin}"
  export NIO_CONFIG_MSDOS_BIN="${NIO_CONFIG_MSDOS_BIN:-$NIO_CONFIG/build/msdos/bin}"
  export NIO_CONFIG_ATARI_BIN="${NIO_CONFIG_ATARI_BIN:-$NIO_CONFIG/build/atari/bin}"
  export PDCURSES_MSDOS_LIB="${PDCURSES_MSDOS_LIB:-$NIO_BUILD_DIR/pdcurses/msdos-small/pdcurses.lib}"

  mkdir -p "$NIO_LOG_DIR" "$NIO_IMAGE_DIR" || return 1
}

setup_nio_environment
status=$?

unset -f setup_nio_environment

return "$status"

