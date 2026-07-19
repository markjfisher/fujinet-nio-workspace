#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

PDCURSES_DIR="${PDCURSES_DIR:-$NIO_WORKSPACE/repos/PDCurses}"
PDCURSES_BUILD_DIR="${PDCURSES_BUILD_DIR:-$NIO_WORKSPACE/build/pdcurses/msdos-small}"
PDCURSES_MSDOS_LIB="${PDCURSES_MSDOS_LIB:-$PDCURSES_BUILD_DIR/pdcurses.lib}"

if [ ! -d "$PDCURSES_DIR" ]; then
  git clone --depth 1 https://github.com/wmcbrine/PDCurses.git "$PDCURSES_DIR"
fi

mkdir -p "$PDCURSES_BUILD_DIR"

cflags=(
  -bt=dos
  -ms
  -wx
  -zq
  -i="$PDCURSES_DIR"
  -oneatx
  -wcd=303
)

sources=(
  pdcurses/addch.c
  pdcurses/addchstr.c
  pdcurses/addstr.c
  pdcurses/attr.c
  pdcurses/beep.c
  pdcurses/bkgd.c
  pdcurses/border.c
  pdcurses/clear.c
  pdcurses/color.c
  pdcurses/delch.c
  pdcurses/deleteln.c
  pdcurses/getch.c
  pdcurses/getstr.c
  pdcurses/getyx.c
  pdcurses/inch.c
  pdcurses/inchstr.c
  pdcurses/initscr.c
  pdcurses/inopts.c
  pdcurses/insch.c
  pdcurses/insstr.c
  pdcurses/instr.c
  pdcurses/kernel.c
  pdcurses/keyname.c
  pdcurses/mouse.c
  pdcurses/move.c
  pdcurses/outopts.c
  pdcurses/overlay.c
  pdcurses/pad.c
  pdcurses/panel.c
  pdcurses/printw.c
  pdcurses/refresh.c
  pdcurses/scanw.c
  pdcurses/scr_dump.c
  pdcurses/scroll.c
  pdcurses/slk.c
  pdcurses/termattr.c
  pdcurses/touch.c
  pdcurses/util.c
  pdcurses/window.c
  pdcurses/debug.c
  dos/pdcclip.c
  dos/pdcdisp.c
  dos/pdcgetsc.c
  dos/pdckbd.c
  dos/pdcscrn.c
  dos/pdcsetsc.c
  dos/pdcutil.c
)

objects=()
for src in "${sources[@]}"; do
  obj="$PDCURSES_BUILD_DIR/$(basename "${src%.c}").obj"
  objects+=("$obj")
  wcc "${cflags[@]}" -fo="$obj" "$PDCURSES_DIR/$src"
done

rm -f "$PDCURSES_MSDOS_LIB"
wlib -q -n -b -c -t "$PDCURSES_MSDOS_LIB" "${objects[@]}"
echo "Built $PDCURSES_MSDOS_LIB"
