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
  altirra             Configure/build AltirraSDL with the workspace preset
  fujinet             Build/test fujinet-nio TCP debug, TCP release, PTY debug, RS-232 debug
  fujinet-tcp         Build/test fujinet-nio TCP debug and build TCP release
  fujinet-pty         Build/test fujinet-nio PTY debug
  fujinet-rs232       Build/test fujinet-nio RS-232 debug
  fujinet-atari-netsio Build/test fujinet-nio Atari FujiBus over NetSIO debug
  lib                 Build fujinet-nio-lib Linux and MS-DOS libraries
  lib-linux           Build fujinet-nio-lib Linux library
  lib-msdos           Build fujinet-nio-lib MS-DOS libraries
  lib-atari           Build fujinet-nio-lib Atari library
  msdos-driver        Build fujinet-msdos FUJINET.SYS with FUJINET_TRANSPORT=NIO
  apps-all            Build all nio-apps targets
  apps-msdos          Build nio-apps MS-DOS tools
  apps-atari          Build nio-apps Atari tools
  atari-run           Run an Atari app under the configured emulator
  atari-stop          Stop stale Atari emulator sidecars started by atari-run
  bounce-world        Build bounce-world-client-nio
  msdos-image         Build raw FAT image from nio-apps/build/msdos/bin
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
    git_ref_line fujinet-qemu-msdos "$FUJINET_QEMU_MSDOS"
    git_ref_line fujinet-msdos "$FUJINET_MSDOS"
    git_ref_line fn-rom "$FN_ROM"
    git_ref_line bounce-world-client-nio "$BOUNCE_WORLD_CLIENT_NIO"
    git_ref_line fujinet-emulator-bridge "$FUJINET_EMULATOR_BRIDGE"
    git_ref_line AltirraSDL "$NIO_WORKSPACE/repos/AltirraSDL"
    printf 'fujinet_nio_tcp_debug_bin=%s\n' "$FUJINET_NIO_TCP_DEBUG_BIN"
    printf 'fujinet_nio_tcp_release_bin=%s\n' "$FUJINET_NIO_TCP_RELEASE_BIN"
    printf 'fujinet_nio_atari_fujibus_netsio_bin=%s\n' "$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN"
    printf 'altirra_workspace_bin=%s\n' "$ALTIRRA_WORKSPACE_BIN"
    printf 'nio_apps_msdos_bin=%s\n' "$NIO_APPS_MSDOS_BIN"
    printf 'nio_apps_atari_bin=%s\n' "$NIO_APPS_ATARI_BIN"
    printf 'msdos_apps_image=%s\n' "$NIO_IMAGE_DIR/nio-apps.img"
    printf 'qemu_image=%s\n' "${OUTPUT_IMAGE:-$FUJINET_QEMU_MSDOS/build/msdos-nio-apps.qcow2}"
  } > "$NIO_BUILD_DIR/manifest.txt"
  echo "Wrote $NIO_BUILD_DIR/manifest.txt"
}

build_altirra() {
  local altirra_repo="$NIO_WORKSPACE/repos/AltirraSDL"
  local preset="${ALTIRRA_CMAKE_PRESET:-linux-debug}"
  local jobs="${ALTIRRA_BUILD_JOBS:-$(nproc)}"
  require_dir "$altirra_repo"

  run_in altirra-configure "$altirra_repo" cmake --preset "$preset"
  run_in altirra-build "$altirra_repo" cmake --build "build/$preset" --target AltirraSDL -j "$jobs"
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

build_fujinet_atari_fujibus_netsio() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-atari-fujibus-netsio-build "$FUJINET_NIO" ./build.sh -cp atari-fujibus-netsio-debug
}

build_lib_linux() {
  require_dir "$FUJINET_NIO_LIB"
  run_in lib-linux "$FUJINET_NIO_LIB" make linux
}

build_lib_msdos() {
  require_dir "$FUJINET_NIO_LIB"
  run_in lib-msdos "$FUJINET_NIO_LIB" make msdos
}

build_lib_atari() {
  require_dir "$FUJINET_NIO_LIB"
  run_in lib-atari "$FUJINET_NIO_LIB" make atari
}

build_msdos_driver() {
  require_dir "$FUJINET_MSDOS"
  run_in msdos-driver-clean "$FUJINET_MSDOS/sys" make FUJINET_TRANSPORT=NIO clean
  run_in msdos-driver-build "$FUJINET_MSDOS/sys" make FUJINET_TRANSPORT=NIO
}

build_apps_msdos() {
  require_dir "$NIO_APPS"
  run_in apps-msdos "$NIO_APPS" make TARGET=msdos FUJINET_NIO_LIB="$FUJINET_NIO_LIB"
}

build_apps_atari() {
  require_dir "$NIO_APPS"
  build_lib_atari
  run_in apps-atari "$NIO_APPS" make TARGET=atari FUJINET_NIO_LIB="$FUJINET_NIO_LIB"
}

build_apps_all() {
  require_dir "$NIO_APPS"
  run_in apps-all "$NIO_APPS" make FUJINET_NIO_LIB="$FUJINET_NIO_LIB"
}

clean_apps_all() {
  require_dir "$NIO_APPS"
  run_in apps-all "$NIO_APPS" make FUJINET_NIO_LIB="$FUJINET_NIO_LIB" clean
}

build_bounce_world() {
  require_dir "$BOUNCE_WORLD_CLIENT_NIO"
  run_in bounce-world-clean "$BOUNCE_WORLD_CLIENT_NIO" make clean
  run_in bounce-world-build "$BOUNCE_WORLD_CLIENT_NIO" make FUJINET_NIO_LIB="$FUJINET_NIO_LIB"
}

build_msdos_image() {
  require_dir "$NIO_APPS"
  if [ ! -d "$NIO_APPS_MSDOS_BIN" ]; then
    build_apps_msdos
  fi
  mkdir -p "$NIO_IMAGE_DIR"
  run msdos-image "$NIO_APPS/msdos/scripts/create_msdos_img.py" \
    -i "$NIO_APPS_MSDOS_BIN" \
    -o "$NIO_IMAGE_DIR/nio-apps.img" \
    -l NIOAPPS
}

build_qemu_image() {
  require_dir "$FUJINET_QEMU_MSDOS"
  require_dir "$FUJINET_MSDOS"
  build_msdos_driver
  if [ ! -f "$BOUNCE_WORLD_CLIENT_NIO/build/bwcn.msdos.exe" ]; then
    build_bounce_world
  fi
  local args=()
  if [ -n "${APPS_MANIFEST:-}" ]; then
    args+=(--apps-manifest "$APPS_MANIFEST")
  elif [ -f "$FUJINET_QEMU_MSDOS/manifests/apps.yaml" ]; then
    args+=(--apps-manifest "$FUJINET_QEMU_MSDOS/manifests/apps.yaml")
  fi
  run qemu-image env \
    FUJINET_MSDOS="$FUJINET_MSDOS" \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    NIO_APPS="$NIO_APPS" \
    NIO_APPS_MSDOS_BIN="$NIO_APPS_MSDOS_BIN" \
    BOUNCE_WORLD_CLIENT_NIO="$BOUNCE_WORLD_CLIENT_NIO" \
    BOUNCE_WORLD="$BOUNCE_WORLD_CLIENT_NIO" \
    DRIVER="${DRIVER:-$FUJINET_MSDOS/sys/fujinet.sys}" \
    "$FUJINET_QEMU_MSDOS/build-nio-qcow" "${args[@]}"
}

run_qemu() {
  require_dir "$FUJINET_QEMU_MSDOS"
  if [ "${1:-}" = "--" ]; then
    shift
  fi
  run qemu-run env \
    FUJINET_NIO_PATH="$FUJINET_NIO" \
    FUJINET_NIO_BIN="${FUJINET_NIO_BIN:-$FUJINET_NIO_TCP_DEBUG_BIN}" \
    "$FUJINET_QEMU_MSDOS/run-qemu-nio" "$@"
}

port_in_use() {
  local port="$1"
  ss -ltnu "sport = :$port" 2>/dev/null | awk 'NR > 1 { found=1 } END { exit found ? 0 : 1 }'
}

print_port_owner() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -iUDP:"$port" 2>/dev/null || true
  else
    ss -ltnup "sport = :$port" 2>/dev/null || true
  fi
}

stop_atari_sidecars() {
  local rc=0
  if pgrep -f "python3 -m netsiohub --port ${ATARI_NETSIO_ATDEV_PORT:-9996} --netsio-port ${ATARI_NETSIO_PORT:-9997}" >/dev/null 2>&1; then
    pkill -TERM -f "python3 -m netsiohub --port ${ATARI_NETSIO_ATDEV_PORT:-9996} --netsio-port ${ATARI_NETSIO_PORT:-9997}" || rc=$?
  fi
  if pgrep -f "$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN" >/dev/null 2>&1; then
    pkill -TERM -f "$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN" || rc=$?
  fi
  sleep 1
  if pgrep -f "python3 -m netsiohub --port ${ATARI_NETSIO_ATDEV_PORT:-9996} --netsio-port ${ATARI_NETSIO_PORT:-9997}" >/dev/null 2>&1; then
    pkill -KILL -f "python3 -m netsiohub --port ${ATARI_NETSIO_ATDEV_PORT:-9996} --netsio-port ${ATARI_NETSIO_PORT:-9997}" || rc=$?
  fi
  if pgrep -f "$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN" >/dev/null 2>&1; then
    pkill -KILL -f "$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN" || rc=$?
  fi
  return "$rc"
}

atari_arg_profile() {
  local profile="$NIO_WORKSPACE/configs/atari/profiles/altirra.yaml"
  local arg
  while [ $# -gt 0 ]; do
    arg="$1"
    case "$arg" in
      -p|--profile)
        if [ $# -gt 1 ]; then
          profile="$2"
          shift 2
          continue
        fi
        ;;
      --profile=*)
        profile="${arg#--profile=}"
        ;;
    esac
    shift
  done
  case "$profile" in
    /*) printf '%s\n' "$profile" ;;
    *) printf '%s\n' "$NIO_WORKSPACE/$profile" ;;
  esac
}

atari_profile_embeds_fujinet_nio() {
  local profile="$1"
  [ -f "$profile" ] || return 1
  grep -Eq 'embedded_fujinet_nio:[[:space:]]*true|type:[[:space:]]*fujinetnio' "$profile"
}

run_atari() {
  require_dir "$NIO_APPS"
  if [ "${1:-}" = "--" ]; then
    shift
  fi
  if [ $# -eq 0 ] || [[ "${1:-}" == -* ]]; then
    set -- altirra "$@"
  fi

  local profile_path
  profile_path="$(atari_arg_profile "$@")"
  local embedded_fujinet_nio=false
  if atari_profile_embeds_fujinet_nio "$profile_path"; then
    embedded_fujinet_nio=true
  fi
  local run_args=("$@")
  if [ "$embedded_fujinet_nio" = true ]; then
    run_args+=("--profile" "$profile_path")
  fi

  if [ ! -d "$NIO_APPS_ATARI_BIN" ]; then
    build_apps_atari
  fi
  if [ "$embedded_fujinet_nio" != true ] && [ ! -x "$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN" ]; then
    build_fujinet_atari_fujibus_netsio
  fi

  local dry_run=false
  for arg in "$@"; do
    if [ "$arg" = "--dry-run" ]; then
      dry_run=true
      break
    fi
  done

  local netsio_port="${ATARI_NETSIO_PORT:-9997}"
  local atdev_port="${ATARI_NETSIO_ATDEV_PORT:-9996}"
  local run_id
  run_id="$(date +%Y%m%d-%H%M%S)"
  local hub_log="$NIO_LOG_DIR/atari-netsiohub-$run_id.log"
  local nio_log="$NIO_LOG_DIR/atari-fujinet-nio-$run_id.log"
  local latest_run_file="$NIO_LOG_DIR/atari-run-latest.txt"
  local run_root
  run_root="$(mktemp -d "${TMPDIR:-/tmp}/fujinet-atari-run.XXXXXX")"
  local fujinet_config_template="${ATARI_FUJINET_CONFIG_TEMPLATE:-$FUJINET_NIO/distfiles/atari-fdrive-fujinet.yaml}"
  if [ ! -f "$fujinet_config_template" ]; then
    echo "Missing Atari FujiNet config template: $fujinet_config_template" >&2
    exit 1
  fi
  mkdir -p "$run_root/fujinet-data/disks"
  : > "$run_root/fujinet-data/disks/slot0-fdrive-test.atr"
  : > "$run_root/fujinet-data/disks/slot1-readwrite-test.atr"
  sed "s/__NETSIO_PORT__/$netsio_port/g" "$fujinet_config_template" > "$run_root/fujinet-data/fujinet.yaml"

  local hub_cmd=(python3 -m netsiohub --port "$atdev_port" --netsio-port "$netsio_port")
  if [ "${ATARI_NETSIO_VERBOSE:-1}" != "0" ]; then
    hub_cmd+=(--verbose)
  fi
  if [ "${ATARI_NETSIO_DEBUG:-0}" != "0" ]; then
    hub_cmd+=(--debug)
  fi
  local nio_cmd=("$FUJINET_NIO_ATARI_FUJIBUS_NETSIO_BIN")

  if [ "$dry_run" = true ]; then
    printf 'ATARI_RUN_ROOT=%q\n' "$run_root"
    printf 'ATARI_FUJINET_CONFIG_TEMPLATE=%q\n' "$fujinet_config_template"
    printf 'ATARI_FUJINET_CONFIG=%q\n' "$run_root/fujinet-data/fujinet.yaml"
    if [ "$embedded_fujinet_nio" = true ]; then
      printf 'ALTIRRA_BIN=%q\n' "$ALTIRRA_WORKSPACE_BIN"
      printf 'ATARI_FUJINET_CONFIG_DIR=%q\n' "$run_root/fujinet-data"
      printf 'cd %q && %q ' "$run_root" "$NIO_WORKSPACE/scripts/atari-run"
      printf '%q ' "${run_args[@]}"
      printf '\n'
      (cd "$run_root" && ATARI_FUJINET_CONFIG_DIR="$run_root/fujinet-data" ALTIRRA_BIN="$ALTIRRA_WORKSPACE_BIN" "$NIO_WORKSPACE/scripts/atari-run" "${run_args[@]}" --dry-run)
    else
      printf 'ATARI_NETSIOHUB_LOG=%q\n' "$hub_log"
      printf 'ATARI_FUJINET_NIO_LOG=%q\n' "$nio_log"
      printf 'cd %q && %q ' "$FUJINET_EMULATOR_BRIDGE/fujinet-bridge" "${hub_cmd[0]}"
      printf '%q ' "${hub_cmd[@]:1}"
      printf '\n'
      printf 'cd %q && %q\n' "$run_root" "${nio_cmd[0]}"
      run atari-run "$NIO_WORKSPACE/scripts/atari-run" "$@"
    fi
    rm -rf "$run_root"
    return
  fi

  if [ "$embedded_fujinet_nio" = true ]; then
    if [ ! -x "$ALTIRRA_WORKSPACE_BIN" ]; then
      echo "Embedded FujiNet-NIO profile needs AltirraSDL." >&2
      echo "Missing ALTIRRA_WORKSPACE_BIN: $ALTIRRA_WORKSPACE_BIN" >&2
      exit 1
    fi

    {
      printf 'run_id=%s\n' "$run_id"
      printf 'run_root=%s\n' "$run_root"
      printf 'fujinet_config_template=%s\n' "$fujinet_config_template"
      printf 'fujinet_config=%s\n' "$run_root/fujinet-data/fujinet.yaml"
      printf 'fujinet_config_dir=%s\n' "$run_root/fujinet-data"
      printf 'altirra_bin=%s\n' "$ALTIRRA_WORKSPACE_BIN"
      printf 'atari_run_log=%s\n' "$NIO_LOG_DIR/atari-run.log"
    } > "$latest_run_file"
    echo "Atari embedded FujiNet-NIO run root: $run_root"
    echo "AltirraSDL: $ALTIRRA_WORKSPACE_BIN"

    local embedded_cleaned=false
    cleanup_embedded_atari_run() {
      if [ "$embedded_cleaned" = true ]; then
        return
      fi
      embedded_cleaned=true
      rm -rf "$run_root"
    }
    trap cleanup_embedded_atari_run EXIT INT TERM

    local rc=0
    set +e
    (cd "$run_root" && ATARI_FUJINET_CONFIG_DIR="$run_root/fujinet-data" ALTIRRA_BIN="$ALTIRRA_WORKSPACE_BIN" "$NIO_WORKSPACE/scripts/atari-run" "${run_args[@]}") 2>&1 | tee "$NIO_LOG_DIR/atari-run.log"
    rc=${PIPESTATUS[0]}
    set -e
    cleanup_embedded_atari_run
    trap - EXIT INT TERM
    return "$rc"
  fi

  require_dir "$FUJINET_EMULATOR_BRIDGE/fujinet-bridge"

  if port_in_use "$atdev_port"; then
    echo "Atari NetSIO custom-device port $atdev_port is already in use." >&2
    print_port_owner "$atdev_port" >&2
    echo "Run: $0 atari-stop" >&2
    exit 1
  fi
  if port_in_use "$netsio_port"; then
    echo "Atari NetSIO UDP port $netsio_port is already in use." >&2
    print_port_owner "$netsio_port" >&2
    echo "Run: $0 atari-stop" >&2
    exit 1
  fi

  local hub_pid=
  local nio_pid=
  local cleaned=false
  cleanup_atari_run() {
    if [ "$cleaned" = true ]; then
      return
    fi
    cleaned=true
    if [ -n "$nio_pid" ]; then kill "$nio_pid" 2>/dev/null || true; fi
    if [ -n "$hub_pid" ]; then kill "$hub_pid" 2>/dev/null || true; fi
    wait "$nio_pid" 2>/dev/null || true
    wait "$hub_pid" 2>/dev/null || true
    rm -rf "$run_root"
  }
  trap cleanup_atari_run EXIT INT TERM

  {
    printf 'run_id=%s\n' "$run_id"
    printf 'run_root=%s\n' "$run_root"
    printf 'fujinet_config_template=%s\n' "$fujinet_config_template"
    printf 'fujinet_config=%s\n' "$run_root/fujinet-data/fujinet.yaml"
    printf 'netsiohub_log=%s\n' "$hub_log"
    printf 'fujinet_nio_log=%s\n' "$nio_log"
    printf 'atari_run_log=%s\n' "$NIO_LOG_DIR/atari-run.log"
  } > "$latest_run_file"
  echo "Atari run root: $run_root"
  echo "netsiohub log: $hub_log"
  echo "fujinet-nio log: $nio_log"

  (cd "$FUJINET_EMULATOR_BRIDGE/fujinet-bridge" && stdbuf -oL -eL "${hub_cmd[@]}") >"$hub_log" 2>&1 &
  hub_pid=$!
  sleep "${ATARI_NETSIO_HUB_STARTUP_DELAY:-1}"
  if ! kill -0 "$hub_pid" 2>/dev/null; then
    echo "netsiohub exited during startup." >&2
    cleanup_atari_run
    exit 1
  fi
  (cd "$run_root" && stdbuf -oL -eL "${nio_cmd[@]}") >"$nio_log" 2>&1 &
  nio_pid=$!
  sleep 1
  if ! kill -0 "$nio_pid" 2>/dev/null; then
    echo "fujinet-nio exited during startup." >&2
    cleanup_atari_run
    exit 1
  fi

  local rc=0
  set +e
  run atari-run "$NIO_WORKSPACE/scripts/atari-run" "$@"
  rc=$?
  set -e
  cleanup_atari_run
  trap - EXIT INT TERM
  return "$rc"
}

target_all() {
  build_altirra
  build_fujinet_tcp
  build_fujinet_pty
  build_fujinet_rs232
  build_lib_linux
  build_lib_msdos
  clean_apps_all
  build_apps_all
  build_msdos_image
  build_qemu_image
  write_manifest
}

if [ $# -eq 0 ]; then
  usage
  exit 1
fi

for target in "$@"; do
  case "$target" in
    all) target_all ;;
    altirra) build_altirra; write_manifest ;;
    fujinet) build_fujinet_tcp; build_fujinet_pty; build_fujinet_rs232; write_manifest ;;
    fujinet-tcp) build_fujinet_tcp; write_manifest ;;
    fujinet-pty) build_fujinet_pty; write_manifest ;;
    fujinet-rs232) build_fujinet_rs232; write_manifest ;;
    fujinet-atari-netsio) build_fujinet_atari_fujibus_netsio; write_manifest ;;
    lib) build_lib_linux; build_lib_msdos; build_lib_atari; write_manifest ;;
    lib-linux) build_lib_linux; write_manifest ;;
    lib-msdos) build_lib_msdos; write_manifest ;;
    lib-atari) build_lib_atari; write_manifest ;;
    msdos-driver) build_msdos_driver; write_manifest ;;
    apps-all) build_apps_all; write_manifest ;;
    apps-clean) clean_apps_all; write_manifest ;;
    apps-msdos) build_apps_msdos; write_manifest ;;
    apps-atari) build_apps_atari; write_manifest ;;
    atari-run) shift; run_atari "$@"; exit $? ;;
    atari-stop) stop_atari_sidecars; exit $? ;;
    bounce-world) build_bounce_world; write_manifest ;;
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
