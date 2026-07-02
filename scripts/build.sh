#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

usage() {
  cat <<EOF
Usage: scripts/build.sh <target> [target...]

Targets:
  all                 Build the usual integrated stack
  fujinet             Build/test fujinet-nio TCP debug, TCP release, PTY debug, RS-232 debug
  fujinet-tcp         Build/test fujinet-nio TCP debug and build TCP release
  fujinet-pty         Build/test fujinet-nio PTY debug
  fujinet-rs232       Build/test fujinet-nio RS-232 debug
  lib                 Build fujinet-nio-lib Linux and MS-DOS libraries
  lib-linux           Build fujinet-nio-lib Linux library
  lib-msdos           Build fujinet-nio-lib MS-DOS libraries
  msdos-driver        Build fujinet-msdos FUJINET.SYS with FUJINET_TRANSPORT=NIO
  apps-msdos          Build nio-apps MS-DOS tools
  msdos-image         Build raw FAT image from nio-apps/msdos/bin
  qemu-image          Build qcow2 image through fujinet-qemu-msdos/build-nio-qcow
  qemu-run            Run fujinet-qemu-msdos/run-qemu-nio with workspace defaults
  manifest            Write build/manifest.txt only

Environment overrides live in local/config.env.
EOF
}

log_name() {
  printf '%s' "$1" | tr '/: ' '___'
}

run() {
  local name="$1"
  shift
  local log="$NIO_LOG_DIR/$(log_name "$name").log"
  echo "==> $name"
  echo "    log: $log"
  "$@" 2>&1 | tee "$log"
}

run_in() {
  local name="$1"
  local dir="$2"
  shift 2
  run "$name" bash -lc "cd \"\$1\" && shift && \"\$@\"" _ "$dir" "$@"
}

require_dir() {
  if [ ! -d "$1" ]; then
    echo "Missing directory: $1" >&2
    echo "Run: git submodule update --init --recursive" >&2
    exit 1
  fi
}

git_ref_line() {
  local name="$1"
  local dir="$2"
  if [ ! -d "$dir/.git" ] && [ ! -f "$dir/.git" ]; then
    printf '%s=missing\n' "$name"
    return
  fi
  local ref dirty branch
  if git -C "$dir" rev-parse --verify HEAD >/dev/null 2>&1; then
    ref="$(git -C "$dir" rev-parse --short HEAD)"
  else
    ref="unborn"
  fi
  branch="$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null || printf detached)"
  dirty=""
  if [ -n "$(git -C "$dir" status --porcelain 2>/dev/null)" ]; then
    dirty=" dirty"
  fi
  printf '%s=%s branch=%s%s\n' "$name" "$ref" "$branch" "$dirty"
}

write_manifest() {
  mkdir -p "$NIO_BUILD_DIR"
  {
    printf 'built_at=%s\n' "$(date -Is)"
    printf 'workspace=%s\n' "$NIO_WORKSPACE"
    git_ref_line workspace "$NIO_WORKSPACE"
    git_ref_line fujinet-nio "$FUJINET_NIO"
    git_ref_line fujinet-nio-lib "$FUJINET_NIO_LIB"
    git_ref_line nio-apps "$NIO_APPS"
    git_ref_line nio-docs "$NIO_DOCS"
    git_ref_line fujinet-qemu-msdos "$FUJINET_QEMU_MSDOS"
    git_ref_line fujinet-msdos "$FUJINET_MSDOS"
    git_ref_line fn-rom "$FN_ROM"
    git_ref_line bounce-world-client-nio "$BOUNCE_WORLD"
    printf 'fujinet_nio_tcp_debug_bin=%s\n' "$FUJINET_NIO_TCP_DEBUG_BIN"
    printf 'fujinet_nio_tcp_release_bin=%s\n' "$FUJINET_NIO_TCP_RELEASE_BIN"
    printf 'msdos_apps_image=%s\n' "$NIO_IMAGE_DIR/nio-apps.img"
    printf 'qemu_image=%s\n' "${OUTPUT_IMAGE:-$FUJINET_QEMU_MSDOS/build/msdos-nio-apps.qcow2}"
  } > "$NIO_BUILD_DIR/manifest.txt"
  echo "Wrote $NIO_BUILD_DIR/manifest.txt"
}

build_fujinet_tcp() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-tcp-debug-build "$FUJINET_NIO" ./build.sh -cp fujibus-tcp-debug
  run_in fujinet-tcp-debug-test "$FUJINET_NIO" ctest --test-dir build/fujibus-tcp-debug --output-on-failure
  run_in fujinet-tcp-release-build "$FUJINET_NIO" ./build.sh -cp fujibus-tcp-release
}

build_fujinet_pty() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-pty-debug-build "$FUJINET_NIO" ./build.sh -cp fujibus-pty-debug
  run_in fujinet-pty-debug-test "$FUJINET_NIO" ctest --test-dir build/fujibus-pty-debug --output-on-failure
}

build_fujinet_rs232() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-rs232-debug-build "$FUJINET_NIO" ./build.sh -cp fujibus-rs232-debug
  run_in fujinet-rs232-debug-test "$FUJINET_NIO" ctest --test-dir build/fujibus-rs232-debug --output-on-failure
}

build_lib_linux() {
  require_dir "$FUJINET_NIO_LIB"
  run_in lib-linux "$FUJINET_NIO_LIB" make linux
}

build_lib_msdos() {
  require_dir "$FUJINET_NIO_LIB"
  run_in lib-msdos "$FUJINET_NIO_LIB" make msdos
}

build_msdos_driver() {
  require_dir "$FUJINET_MSDOS"
  run_in msdos-driver "$FUJINET_MSDOS/sys" make FUJINET_TRANSPORT=NIO
}

build_apps_msdos() {
  require_dir "$NIO_APPS_MSDOS"
  run_in apps-msdos "$NIO_APPS_MSDOS" make FUJINET_NIO_LIB="$FUJINET_NIO_LIB"
}

build_msdos_image() {
  require_dir "$NIO_APPS_MSDOS"
  mkdir -p "$NIO_IMAGE_DIR"
  run msdos-image "$NIO_APPS_MSDOS/scripts/create_msdos_img.py" \
    -i "$NIO_APPS_MSDOS/bin" \
    -o "$NIO_IMAGE_DIR/nio-apps.img" \
    -l NIOAPPS
}

build_qemu_image() {
  require_dir "$FUJINET_QEMU_MSDOS"
  require_dir "$FUJINET_MSDOS"
  local args=()
  if [ -n "${APPS_MANIFEST:-}" ]; then
    args+=(--apps-manifest "$APPS_MANIFEST")
  elif [ -f "$FUJINET_QEMU_MSDOS/manifests/apps.yaml" ]; then
    args+=(--apps-manifest "$FUJINET_QEMU_MSDOS/manifests/apps.yaml")
  fi
  run qemu-image env \
    FUJINET_MSDOS="$FUJINET_MSDOS" \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    NIO_APPS_MSDOS="$NIO_APPS_MSDOS" \
    BOUNCE_WORLD="$BOUNCE_WORLD" \
    DRIVER="${DRIVER:-$FUJINET_MSDOS/sys/fujinet.sys}" \
    "$FUJINET_QEMU_MSDOS/build-nio-qcow" "${args[@]}"
}

run_qemu() {
  require_dir "$FUJINET_QEMU_MSDOS"
  run qemu-run env \
    FUJINET_NIO_PATH="$FUJINET_NIO" \
    FUJINET_NIO_BIN="${FUJINET_NIO_BIN:-$FUJINET_NIO_TCP_DEBUG_BIN}" \
    "$FUJINET_QEMU_MSDOS/run-qemu-nio" "$@"
}

target_all() {
  build_fujinet_tcp
  build_fujinet_pty
  build_fujinet_rs232
  build_lib_linux
  build_lib_msdos
  build_msdos_driver
  build_apps_msdos
  build_msdos_image
  if [ -n "${BASE_IMAGE:-}" ] || [ -f "$FUJINET_QEMU_MSDOS/build/msdos-nio.qcow2" ]; then
    build_qemu_image
  else
    echo "==> qemu-image skipped: set BASE_IMAGE or create $FUJINET_QEMU_MSDOS/build/msdos-nio.qcow2"
  fi
  write_manifest
}

if [ $# -eq 0 ]; then
  usage
  exit 1
fi

for target in "$@"; do
  case "$target" in
    all) target_all ;;
    fujinet) build_fujinet_tcp; build_fujinet_pty; build_fujinet_rs232; write_manifest ;;
    fujinet-tcp) build_fujinet_tcp; write_manifest ;;
    fujinet-pty) build_fujinet_pty; write_manifest ;;
    fujinet-rs232) build_fujinet_rs232; write_manifest ;;
    lib) build_lib_linux; build_lib_msdos; write_manifest ;;
    lib-linux) build_lib_linux; write_manifest ;;
    lib-msdos) build_lib_msdos; write_manifest ;;
    msdos-driver) build_msdos_driver; write_manifest ;;
    apps-msdos) build_apps_msdos; write_manifest ;;
    msdos-image) build_msdos_image; write_manifest ;;
    qemu-image) build_qemu_image; write_manifest ;;
    qemu-run) shift; run_qemu "$@"; exit $? ;;
    manifest) write_manifest ;;
    -h|--help|help) usage ;;
    *)
      echo "Unknown target: $target" >&2
      usage >&2
      exit 1 ;;
  esac
done
