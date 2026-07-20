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
  fujinet-tcp-debug   Build fujinet-nio TCP debug only
  fujinet-pty         Build/test fujinet-nio PTY debug
  fujinet-rs232       Build/test fujinet-nio RS-232 debug
  fujinet-atari-netsio Build/test fujinet-nio Atari FujiBus over NetSIO debug
  lib                 Build fujinet-nio-lib Linux and MS-DOS libraries
  lib-linux           Build fujinet-nio-lib Linux library
  lib-msdos           Build fujinet-nio-lib MS-DOS libraries
  lib-atari           Build fujinet-nio-lib Atari library
  msdos-driver        Build fujinet-nio-msdos FUJINET.SYS
  msdos-tests         Run fujinet-nio-msdos host unit tests
  msdos-driver-legacy Build fujinet-msdos FUJINET.SYS with FUJINET_TRANSPORT=NIO
  msdos-tests-legacy  Run fujinet-msdos host unit tests
  msdos-niodump       Build fujinet-msdos NIODUMP.EXE diagnostics utility
  pdcurses-msdos      Fetch/build PDCurses for Open Watcom MS-DOS
  apps-all            Build all nio-apps targets
  apps-clean          Clean all nio-apps targets
  apps-msdos          Build nio-apps MS-DOS tools
  apps-atari          Build nio-apps Atari tools
  boot-disks          Build/install platform boot disks into fujinet-nio distfiles
  bbc-boot-disk       Build/install BBC fn-rom FN-UTLS.ssd as autorun.ssd
  master-boot-disk    Build/install Master fn-rom FN-UTLS-M.ssd as autorun.ssd
  confnio-bbc-disk    Attempt standalone BBC CONFNIO SSD build at \$1900
  confnio-master-disk Build standalone Master CONFNIO SSD
  bbc-pty             Build/install BBC boot disk, create PTY config, run fujinet-nio
  master-pty          Build/install Master boot disk, create PTY config, run fujinet-nio
  atari-run           Run an Atari app under the configured emulator
  atari-stop          Stop stale Atari emulator sidecars started by atari-run
  bounce-world        Build bounce-world-client-nio
  bounce-world-disk   Build Bounce World MS-DOS raw FAT disk image
  msdos-apps-image    Build workspace raw FAT MS-DOS apps image
  msdos-boot-config-image
                      Build workspace raw FAT MS-DOS FUJINET.SYS/config image
  qemu-msdos-image    Build workspace QEMU MS-DOS qcow2 image
  msdos-image         Compatibility alias for msdos-apps-image
  apps-image          Compatibility alias for msdos-apps-image
  qemu-image          Compatibility alias for qemu-msdos-image
  qemu-run            Run fujinet-qemu-msdos/run-qemu-nio with workspace defaults
  qemu-monitor        Send a command/key to the active qemu-run monitor socket
  msdos-dev-curses    Build and run MS-DOS NIO app image in QEMU curses mode
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
  local msdos_apps_manifest qemu_msdos_apps_manifest msdos_boot_config_manifest qemu_image
  msdos_apps_manifest="$(default_msdos_apps_manifest)"
  qemu_msdos_apps_manifest="$(default_qemu_msdos_apps_manifest)"
  msdos_boot_config_manifest="$(default_msdos_boot_config_manifest)"
  qemu_image="$(default_qemu_image)"
  mkdir -p "$NIO_BUILD_DIR"
  {
    printf 'built_at=%s\n' "$(date -Is)"
    printf 'workspace=%s\n' "$NIO_WORKSPACE"
    git_ref_line workspace "$NIO_WORKSPACE"
    git_ref_line fujinet-nio "$FUJINET_NIO"
    git_ref_line fujinet-nio-lib "$FUJINET_NIO_LIB"
    git_ref_line nio-apps "$NIO_APPS"
    git_ref_line fujinet-qemu-msdos "$FUJINET_QEMU_MSDOS"
    git_ref_line fujinet-nio-msdos "$FUJINET_NIO_MSDOS"
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
    printf 'msdos_apps_manifest=%s\n' "$msdos_apps_manifest"
    printf 'qemu_msdos_apps_manifest=%s\n' "$qemu_msdos_apps_manifest"
    printf 'msdos_boot_config_manifest=%s\n' "$msdos_boot_config_manifest"
    printf 'msdos_apps_image=%s\n' "$NIO_IMAGE_DIR/msdos-apps.img"
    printf 'msdos_boot_config_image=%s\n' "$NIO_IMAGE_DIR/msdos-boot-config.img"
    printf 'legacy_msdos_image=%s\n' "$NIO_IMAGE_DIR/nio-apps.img"
    printf 'legacy_manifest_apps_image=%s\n' "$NIO_IMAGE_DIR/msdos-nio-apps.img"
    printf 'bounce_world_msdos_image=%s\n' "$NIO_IMAGE_DIR/bwcn-msdos.img"
    printf 'qemu_image=%s\n' "$qemu_image"
  } > "$NIO_BUILD_DIR/manifest.txt"
  echo "Wrote $NIO_BUILD_DIR/manifest.txt"
}

default_qemu_image() {
  if [ -n "${OUTPUT_IMAGE:-}" ]; then
    printf '%s\n' "$OUTPUT_IMAGE"
  elif [ -n "${APPS_MANIFEST:-}" ] || [ -f "$NIO_WORKSPACE/manifests/disks/qemu-msdos-apps.yaml" ] || [ -f "$FUJINET_QEMU_MSDOS/manifests/apps.yaml" ]; then
    printf '%s\n' "$FUJINET_QEMU_MSDOS/build/msdos-nio-apps.qcow2"
  else
    printf '%s\n' "$FUJINET_QEMU_MSDOS/build/msdos-nio.qcow2"
  fi
}

default_msdos_apps_manifest() {
  if [ -n "${APPS_MANIFEST:-}" ]; then
    printf '%s\n' "$APPS_MANIFEST"
  elif [ -f "$NIO_WORKSPACE/manifests/disks/msdos-apps.yaml" ]; then
    printf '%s\n' "$NIO_WORKSPACE/manifests/disks/msdos-apps.yaml"
  elif [ -f "$FUJINET_QEMU_MSDOS/manifests/apps.yaml" ]; then
    printf '%s\n' "$FUJINET_QEMU_MSDOS/manifests/apps.yaml"
  else
    printf '%s\n' "$FUJINET_QEMU_MSDOS/manifests/apps.example.yaml"
  fi
}

default_qemu_msdos_apps_manifest() {
  if [ -n "${APPS_MANIFEST:-}" ]; then
    printf '%s\n' "$APPS_MANIFEST"
  elif [ -f "$NIO_WORKSPACE/manifests/disks/qemu-msdos-apps.yaml" ]; then
    printf '%s\n' "$NIO_WORKSPACE/manifests/disks/qemu-msdos-apps.yaml"
  elif [ -f "$FUJINET_QEMU_MSDOS/manifests/apps.yaml" ]; then
    printf '%s\n' "$FUJINET_QEMU_MSDOS/manifests/apps.yaml"
  else
    printf '%s\n' "$FUJINET_QEMU_MSDOS/manifests/apps.example.yaml"
  fi
}

default_msdos_boot_config_manifest() {
  if [ -n "${MSDOS_BOOT_CONFIG_MANIFEST:-}" ]; then
    printf '%s\n' "$MSDOS_BOOT_CONFIG_MANIFEST"
  else
    printf '%s\n' "$NIO_WORKSPACE/manifests/disks/msdos-boot-config.yaml"
  fi
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
  build_fujinet_tcp_debug
  run_in fujinet-tcp-debug-test "$FUJINET_NIO" ctest --test-dir build/fujibus-tcp-debug --output-on-failure
  run_in fujinet-tcp-release-build "$FUJINET_NIO" ./build.sh -cp fujibus-tcp-release
}

build_fujinet_tcp_debug() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-tcp-debug-build "$FUJINET_NIO" ./build.sh -cp fujibus-tcp-debug
}

ensure_fujinet_tcp_debug() {
  require_dir "$FUJINET_NIO"
  if [ ! -x "$FUJINET_NIO_TCP_DEBUG_BIN" ]; then
    build_fujinet_tcp_debug
  fi
}

build_fujinet_pty() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-pty-debug-build "$FUJINET_NIO" ./build.sh -cp fujibus-pty-debug
  run_in fujinet-pty-debug-test "$FUJINET_NIO" ctest --test-dir build/fujibus-pty-debug --output-on-failure
}

build_fujinet_pty_debug() {
  require_dir "$FUJINET_NIO"
  run_in fujinet-pty-debug-build "$FUJINET_NIO" ./build.sh -cp fujibus-pty-debug
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
  require_dir "$FUJINET_NIO_MSDOS"
  run_in msdos-driver-clean "$FUJINET_NIO_MSDOS" make clean
  run_in msdos-driver-build "$FUJINET_NIO_MSDOS" make
}

build_msdos_tests() {
  require_dir "$FUJINET_NIO_MSDOS"
  run_in msdos-tests "$FUJINET_NIO_MSDOS" make tests
}

build_msdos_driver_legacy() {
  require_dir "$FUJINET_MSDOS"
  run_in msdos-driver-legacy-clean "$FUJINET_MSDOS/sys" make FUJINET_TRANSPORT=NIO clean
  run_in msdos-driver-legacy-build "$FUJINET_MSDOS/sys" make FUJINET_TRANSPORT=NIO
  build_msdos_niodump
}

build_msdos_tests_legacy() {
  require_dir "$FUJINET_MSDOS"
  run_in msdos-tests-legacy "$FUJINET_MSDOS/tests" make test
}

build_msdos_niodump() {
  require_dir "$FUJINET_MSDOS"
  if [[ ! -f "$FUJINET_MSDOS/niodump/makefile" && ! -f "$FUJINET_MSDOS/niodump/Makefile" ]]; then
    echo "Skipping msdos-niodump: $FUJINET_MSDOS/niodump not present on this branch"
    return 0
  fi
  run_in msdos-niodump "$FUJINET_MSDOS/niodump" make
}

build_pdcurses_msdos() {
  run pdcurses-msdos "$NIO_WORKSPACE/scripts/build-pdcurses-msdos.sh"
}

build_apps_msdos() {
  require_dir "$NIO_APPS"
  build_pdcurses_msdos
  run_in apps-msdos "$NIO_APPS" make \
    TARGET=msdos \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    PDCURSES_DIR="$PDCURSES_DIR" \
    PDCURSES_MSDOS_LIB="$PDCURSES_MSDOS_LIB"
}

build_apps_atari() {
  require_dir "$NIO_APPS"
  build_lib_atari
  run_in apps-atari "$NIO_APPS" make TARGET=atari FUJINET_NIO_LIB="$FUJINET_NIO_LIB"
}

build_apps_all() {
  require_dir "$NIO_APPS"
  build_pdcurses_msdos
  run_in apps-all "$NIO_APPS" make \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    PDCURSES_DIR="$PDCURSES_DIR" \
    PDCURSES_MSDOS_LIB="$PDCURSES_MSDOS_LIB"
}

build_boot_disks() {
  require_dir "$NIO_APPS"
  require_dir "$FUJINET_NIO"
  require_dir "$FUJINET_NIO_LIB"
  build_pdcurses_msdos

  run_in boot-disk-msdos "$NIO_APPS" make \
    TARGET=msdos \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    PDCURSES_DIR="$PDCURSES_DIR" \
    PDCURSES_MSDOS_LIB="$PDCURSES_MSDOS_LIB" \
    FUJINET_NIO="$FUJINET_NIO" \
    install-boot-disk
  run_in boot-disk-atari "$NIO_APPS" make \
    TARGET=atari \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    FUJINET_NIO="$FUJINET_NIO" \
    install-boot-disk
  build_boot_disk_bbc
}

build_boot_disk_msdos() {
  require_dir "$NIO_APPS"
  require_dir "$FUJINET_NIO"
  require_dir "$FUJINET_NIO_LIB"
  build_pdcurses_msdos

  run_in boot-disk-msdos "$NIO_APPS" make \
    TARGET=msdos \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    PDCURSES_DIR="$PDCURSES_DIR" \
    PDCURSES_MSDOS_LIB="$PDCURSES_MSDOS_LIB" \
    FUJINET_NIO="$FUJINET_NIO" \
    install-boot-disk
}

confnio_load_addr_for_machine() {
  case "$1" in
    BBC) printf '0x1900' ;;
    MASTER) printf '0x0E00' ;;
    *)
      echo "Invalid config-nio machine: $1" >&2
      exit 1
      ;;
  esac
}

confnio_inf_addr_for_machine() {
  python3 - "$(confnio_load_addr_for_machine "$1")" <<'PY'
import sys
addr = int(sys.argv[1], 0)
print(f"{addr:06X}")
PY
}

build_confnio_bbc_binary_for_machine() {
  local machine="$1"
  local label="$2"
  local load_addr
  local himem
  local shadow_mode
  load_addr="$(confnio_load_addr_for_machine "$machine")"
  if [ "$machine" = "MASTER" ]; then
    himem="0x8000"
    shadow_mode="1"
  else
    himem="0x7C00"
    shadow_mode="0"
  fi

  require_dir "$NIO_APPS"
  require_dir "$FUJINET_NIO_LIB"

  run_in "confnio-$label-build" "$NIO_APPS" make \
    -f makefiles/build.mk \
    TARGET=bbc \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    BBC_CONFIG_NIO_START_ADDRESS="$load_addr" \
    BBC_CONFIG_NIO_HIMEM="$himem" \
    BBC_CONFIG_NIO_SHADOW_MODE="$shadow_mode" \
    config-nio
}

stage_confnio_bbc_for_machine() {
  local machine="$1"
  local label="$2"
  local stage="$3"
  local inf_addr
  inf_addr="$(confnio_inf_addr_for_machine "$machine")"

  build_confnio_bbc_binary_for_machine "$machine" "$label"
  rm -rf "$stage"
  mkdir -p "$stage"
  cp "$NIO_APPS/build/bbc/bin/config-nio" "$stage/CONFNIO"
  printf '$.CONFNIO %s %s\n' "$inf_addr" "$inf_addr" > "$stage/CONFNIO.inf"
}

build_confnio_bbc_disk_for_machine() {
  local machine="$1"
  local label="$2"
  local stage="$NIO_BUILD_DIR/confnio-$label-ssd"
  local out="$NIO_BUILD_DIR/images/confnio-$label.ssd"

  require_dir "$FUJINET_NIO_LIB"
  mkdir -p "$NIO_BUILD_DIR/images"
  stage_confnio_bbc_for_machine "$machine" "$label" "$stage"
  run "confnio-$label-ssd" python3 "$FUJINET_NIO_LIB/scripts/create_ssd.py" \
    -i "$stage" \
    -o "$out" \
    -t CONFNIO
  echo "Built config-nio $label SSD: $out"
}

build_confnio_bbc_disk() {
  build_confnio_bbc_disk_for_machine BBC bbc
}

build_confnio_master_disk() {
  build_confnio_bbc_disk_for_machine MASTER master
}

build_boot_disk_for_machine() {
  local machine="$1"
  local label="$2"
  local ssd_name="$3"
  local confnio_stage="$NIO_BUILD_DIR/confnio-$label-fn-utls"

  require_dir "$FN_ROM"
  require_dir "$FUJINET_NIO"

  if [ "$machine" = "MASTER" ]; then
    stage_confnio_bbc_for_machine "$machine" "$label" "$confnio_stage"
    extra_stage_env=(FN_UTLS_EXTRA_STAGE="$confnio_stage")
  else
    extra_stage_env=()
  fi

  run_in "$label-fn-utls" "$FN_ROM" env \
    BUILD_MACHINE="$machine" \
    FN_UTLS_SSD="$FN_ROM/build/$ssd_name" \
    "${extra_stage_env[@]}" \
    ./scripts/build_fn_utls.sh

  local src="$FN_ROM/build/$ssd_name"
  local posix_dir="$FUJINET_NIO/distfiles/boot/bbc"
  local esp32_dir="$FUJINET_NIO/distfiles/esp32-data/boot/bbc"
  mkdir -p "$posix_dir" "$esp32_dir"
  cp "$src" "$posix_dir/autorun.ssd"
  cp "$src" "$esp32_dir/autorun.ssd"
  echo "Installed $label boot utility disk from $src"
  echo "  $posix_dir/autorun.ssd"
  echo "  $esp32_dir/autorun.ssd"
}

build_boot_disk_bbc() {
  build_boot_disk_for_machine BBC bbc FN-UTLS.ssd
}

build_boot_disk_master() {
  build_boot_disk_for_machine MASTER master FN-UTLS-M.ssd
}

write_bbc_pty_config() {
  local label="${1:-bbc}"
  local run_dir="$FUJINET_NIO/build/fujibus-pty-debug"
  local data_dir="$run_dir/fujinet-data"
  local pty_path boot_uri
  if [ "$label" = "master" ]; then
    pty_path="${MASTER_PTY_PATH:-${BBC_PTY_PATH:-/tmp/fujinet-pty}}"
    boot_uri="${MASTER_BOOT_URI:-${BBC_BOOT_URI:-persist:/boot/bbc/autorun.ssd}}"
  else
    pty_path="${BBC_PTY_PATH:-/tmp/fujinet-pty}"
    boot_uri="${BBC_BOOT_URI:-persist:/boot/bbc/autorun.ssd}"
  fi

  mkdir -p "$data_dir"
  cat > "$data_dir/fujinet.yaml" <<EOF
fujinet:
  device_name: fuji-nio
boot:
  mode: config
  config_uri: $boot_uri
  readonly: true
channel:
  pty_path: $pty_path
EOF
  echo "Wrote $label PTY config: $data_dir/fujinet.yaml"
  echo "PTY symlink: $pty_path"
  echo "Boot URI: $boot_uri"
}

run_bbc_pty_for_machine() {
  local label="$1"
  local boot_builder="$2"

  require_dir "$FUJINET_NIO"
  "$boot_builder"
  build_fujinet_pty_debug
  write_bbc_pty_config "$label"

  local run_dir="$FUJINET_NIO/build/fujibus-pty-debug"
  if [ ! -x "$run_dir/run-fujinet-nio" ]; then
    echo "Missing runner: $run_dir/run-fujinet-nio" >&2
    exit 1
  fi

  echo "==> $label-pty"
  echo "    cwd: $run_dir"
  if [ "$label" = "master" ]; then
    echo "    connect B2 to: ${MASTER_PTY_PATH:-${BBC_PTY_PATH:-/tmp/fujinet-pty}}"
  else
    echo "    connect BBC emulator to: ${BBC_PTY_PATH:-/tmp/fujinet-pty}"
  fi
  cd "$run_dir"
  ./run-fujinet-nio
}

run_bbc_pty() {
  run_bbc_pty_for_machine bbc build_boot_disk_bbc
}

run_master_pty() {
  run_bbc_pty_for_machine master build_boot_disk_master
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

build_bounce_world_ioctl() {
  require_dir "$BOUNCE_WORLD_CLIENT_NIO"
  run_in bounce-world-clean "$BOUNCE_WORLD_CLIENT_NIO" make clean
  run_in bounce-world-build "$BOUNCE_WORLD_CLIENT_NIO" make FUJINET_NIO_LIB="$FUJINET_NIO_LIB" MSDOS_NIO_BACKEND="ioctl"
}

build_bounce_world_f5() {
  require_dir "$BOUNCE_WORLD_CLIENT_NIO"
  run_in bounce-world-clean "$BOUNCE_WORLD_CLIENT_NIO" make clean
  run_in bounce-world-build "$BOUNCE_WORLD_CLIENT_NIO" make FUJINET_NIO_LIB="$FUJINET_NIO_LIB" MSDOS_NIO_BACKEND="f5"
}

build_bounce_world_disk() {
  require_dir "$BOUNCE_WORLD_CLIENT_NIO"
  mkdir -p "$NIO_IMAGE_DIR"
  run_in bounce-world-disk "$BOUNCE_WORLD_CLIENT_NIO" make \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    CREATE_MSDOS_IMG="$NIO_APPS/msdos/scripts/create_msdos_img.py" \
    MSDOS_IMAGE="$NIO_IMAGE_DIR/bwcn-msdos.img" \
    disk-msdos
}

build_manifest_msdos_image() {
  local name="$1"
  local apps_manifest="$2"
  local output="$3"
  local label="$4"
  shift 4
  require_dir "$FUJINET_QEMU_MSDOS"
  mkdir -p "$NIO_IMAGE_DIR"
  run "$name" env \
    NIO_APPS_MSDOS="$NIO_APPS_MSDOS_BIN" \
    NIO_APPS_MSDOS_BIN="$NIO_APPS_MSDOS_BIN" \
    FUJINET_NIO_MSDOS="$FUJINET_NIO_MSDOS" \
    FUJINET_MSDOS="$FUJINET_MSDOS" \
    BOUNCE_WORLD_CLIENT_NIO="$BOUNCE_WORLD_CLIENT_NIO" \
    BOUNCE_WORLD="$BOUNCE_WORLD_CLIENT_NIO" \
    "$NIO_WORKSPACE/scripts/build-msdos-manifest-img" \
    --apps-manifest "$apps_manifest" \
    --output "$output" \
    --label "$label" \
    "$@"
}

build_msdos_apps_image() {
  require_dir "$NIO_APPS"
  local apps_manifest
  apps_manifest="$(default_msdos_apps_manifest)"
  build_apps_msdos
  build_manifest_msdos_image msdos-apps-image \
    "$apps_manifest" \
    "$NIO_IMAGE_DIR/msdos-apps.img" \
    NIOAPPS
}

build_msdos_boot_config_image() {
  require_dir "$NIO_APPS"
  require_dir "$FUJINET_NIO_MSDOS"
  local apps_manifest
  apps_manifest="$(default_msdos_boot_config_manifest)"
  build_msdos_driver
  build_apps_msdos
  build_manifest_msdos_image msdos-boot-config-image \
    "$apps_manifest" \
    "$NIO_IMAGE_DIR/msdos-boot-config.img" \
    FNCONFIG
}

build_msdos_image() {
  echo "msdos-image is a compatibility alias; use msdos-apps-image."
  build_msdos_apps_image
  cp "$NIO_IMAGE_DIR/msdos-apps.img" "$NIO_IMAGE_DIR/nio-apps.img"
  echo "Wrote compatibility copy: $NIO_IMAGE_DIR/nio-apps.img"
}

build_apps_image() {
  echo "apps-image is a compatibility alias; use msdos-apps-image."
  build_msdos_apps_image
  cp "$NIO_IMAGE_DIR/msdos-apps.img" "$NIO_IMAGE_DIR/msdos-nio-apps.img"
  echo "Wrote compatibility copy: $NIO_IMAGE_DIR/msdos-nio-apps.img"
}

build_qemu_image() {
  require_dir "$FUJINET_QEMU_MSDOS"
  require_dir "$FUJINET_NIO_MSDOS"
  build_msdos_driver
  build_apps_msdos
  build_boot_disk_msdos
  local args=()
  args+=(--apps-manifest "$(default_qemu_msdos_apps_manifest)")
  run qemu-image env \
    FUJINET_MSDOS="$FUJINET_MSDOS" \
    FUJINET_NIO_LIB="$FUJINET_NIO_LIB" \
    NIO_APPS="$NIO_APPS" \
    NIO_APPS_MSDOS_BIN="$NIO_APPS_MSDOS_BIN" \
    BOUNCE_WORLD_CLIENT_NIO="$BOUNCE_WORLD_CLIENT_NIO" \
    BOUNCE_WORLD="$BOUNCE_WORLD_CLIENT_NIO" \
    DRIVER="${DRIVER:-$FUJINET_NIO_MSDOS/build/dos/fujinet.sys}" \
    "$FUJINET_QEMU_MSDOS/build-nio-qcow" \
    --repo-root "$NIO_WORKSPACE" \
    --apps-dir FNAPPS \
    "${args[@]}"
}

build_qemu_msdos_image() {
  build_qemu_image
}

run_qemu() {
  require_dir "$FUJINET_QEMU_MSDOS"
  if [ "${1:-}" = "--" ]; then
    shift
  fi
  local arg next_is_display
  if [ "${QEMU_DISPLAY:-}" = "curses" ]; then
    run_qemu_interactive -- "$@"
    return $?
  fi
  next_is_display=false
  for arg in "$@"; do
    if [ "$next_is_display" = true ]; then
      if [ "$arg" = "curses" ]; then
        run_qemu_interactive -- "$@"
        return $?
      fi
      next_is_display=false
    elif [ "$arg" = "--display" ]; then
      next_is_display=true
    elif [ "$arg" = "--display=curses" ]; then
      run_qemu_interactive -- "$@"
      return $?
    fi
  done
  local hda
  hda="${HDA:-$(default_qemu_image)}"
  run qemu-run env \
    HDA="$hda" \
    FUJINET_NIO_PATH="$FUJINET_NIO" \
    FUJINET_NIO_BIN="${FUJINET_NIO_BIN:-$FUJINET_NIO_TCP_DEBUG_BIN}" \
    NIO_BOOT_DISK="${NIO_BOOT_DISK:-$FUJINET_NIO/distfiles/boot/msdos/autorun.img}" \
    "$FUJINET_QEMU_MSDOS/run-qemu-nio" "$@"
}

run_qemu_interactive() {
  require_dir "$FUJINET_QEMU_MSDOS"
  if [ "${1:-}" = "--" ]; then
    shift
  fi
  local hda
  hda="${HDA:-$(default_qemu_image)}"
  echo "==> qemu-run"
  echo "    interactive terminal mode; output is not piped to a log"
  HDA="$hda" \
    FUJINET_NIO_PATH="$FUJINET_NIO" \
    FUJINET_NIO_BIN="${FUJINET_NIO_BIN:-$FUJINET_NIO_TCP_DEBUG_BIN}" \
    NIO_BOOT_DISK="${NIO_BOOT_DISK:-$FUJINET_NIO/distfiles/boot/msdos/autorun.img}" \
    "$FUJINET_QEMU_MSDOS/run-qemu-nio" "$@"
}

run_qemu_monitor() {
  require_dir "$FUJINET_QEMU_MSDOS"
  if [ "${1:-}" = "--" ]; then
    shift
  fi
  "$FUJINET_QEMU_MSDOS/qemu-nio-monitor" "$@"
}

run_msdos_dev_curses() {
  require_dir "$FUJINET_QEMU_MSDOS"
  ensure_fujinet_tcp_debug
  build_qemu_image
  write_manifest
  run_qemu_interactive -- --display curses
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
  build_msdos_apps_image
  build_qemu_msdos_image
  write_manifest
}

if [ $# -eq 0 ]; then
  usage
  exit 1
fi

while [ $# -gt 0 ]; do
  target="$1"
  shift
  case "$target" in
    all) target_all ;;
    altirra) build_altirra; write_manifest ;;
    fujinet) build_fujinet_tcp; build_fujinet_pty; build_fujinet_rs232; write_manifest ;;
    fujinet-tcp) build_fujinet_tcp; write_manifest ;;
    fujinet-tcp-debug) build_fujinet_tcp_debug; write_manifest ;;
    fujinet-pty) build_fujinet_pty; write_manifest ;;
    fujinet-rs232) build_fujinet_rs232; write_manifest ;;
    fujinet-atari-netsio) build_fujinet_atari_fujibus_netsio; write_manifest ;;
    lib) build_lib_linux; build_lib_msdos; build_lib_atari; write_manifest ;;
    lib-linux) build_lib_linux; write_manifest ;;
    lib-msdos) build_lib_msdos; write_manifest ;;
    lib-atari) build_lib_atari; write_manifest ;;
    msdos-driver) build_msdos_driver; write_manifest ;;
    msdos-tests) build_msdos_tests; write_manifest ;;
    msdos-driver-legacy) build_msdos_driver_legacy; write_manifest ;;
    msdos-tests-legacy) build_msdos_tests_legacy; write_manifest ;;
    msdos-niodump) build_msdos_niodump; write_manifest ;;
    pdcurses-msdos) build_pdcurses_msdos; write_manifest ;;
    apps-all) build_apps_all; write_manifest ;;
    apps-clean) clean_apps_all; write_manifest ;;
    apps-msdos) build_apps_msdos; write_manifest ;;
    apps-atari) build_apps_atari; write_manifest ;;
    boot-disks|boot-disk) build_boot_disks; write_manifest ;;
    bbc-boot-disk) build_boot_disk_bbc; write_manifest ;;
    master-boot-disk) build_boot_disk_master; write_manifest ;;
    confnio-bbc-disk) build_confnio_bbc_disk; write_manifest ;;
    confnio-master-disk) build_confnio_master_disk; write_manifest ;;
    bbc-pty) run_bbc_pty; exit $? ;;
    master-pty) run_master_pty; exit $? ;;
    atari-run) run_atari "$@"; exit $? ;;
    atari-stop) stop_atari_sidecars; exit $? ;;
    bounce-world) build_bounce_world; write_manifest ;;
    bounce-world-f5) build_bounce_world_f5; write_manifest ;;
    bounce-world-ioctl) build_bounce_world_ioctl; write_manifest ;;
    bounce-world-disk) build_bounce_world_disk; write_manifest ;;
    msdos-apps-image) build_msdos_apps_image; write_manifest ;;
    msdos-boot-config-image) build_msdos_boot_config_image; write_manifest ;;
    qemu-msdos-image) build_qemu_msdos_image; write_manifest ;;
    msdos-image) build_msdos_image; write_manifest ;;
    apps-image) build_apps_image; write_manifest ;;
    qemu-image) build_qemu_image; write_manifest ;;
    qemu-run) run_qemu "$@"; exit $? ;;
    qemu-monitor) run_qemu_monitor "$@"; exit $? ;;
    msdos-dev-curses) run_msdos_dev_curses; exit $? ;;
    manifest) write_manifest ;;
    -h|--help|help) usage ;;
    *)
      echo "Unknown target: $target" >&2
      usage >&2
      exit 1 ;;
  esac
done
