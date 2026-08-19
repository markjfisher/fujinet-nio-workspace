#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "$ROOT/scripts/env.sh"

: "${WB31_OS_ROOT:=/home/markf/dev/amiga/wb31-root/Workbench3.1}"
: "${WB31_WORKBENCH_ADF:=/home/markf/dev/amiga/AmigaForever/af11/Amiga_Files/Shared/adf/amiga-os-310-workbench.adf}"
: "${WB31_KICKSTART:=/home/markf/dev/amiga/AmigaForever/af11/Amiga_Files/Shared/rom/amiga-os-310-a1200.rom}"
: "${WB31_ROM_KEY:=/home/markf/dev/amiga/AmigaForever/af11/Amiga_Files/Shared/rom/rom.key}"

export AMIBERRY_OS_ROOT="$WB31_OS_ROOT"
export AMIBERRY_WORKBENCH_ADF="$WB31_WORKBENCH_ADF"
export AMIBERRY_KICKSTART="$WB31_KICKSTART"
export AMIBERRY_ROM_KEY="$WB31_ROM_KEY"
export AMIBERRY_FAST_FILE_SYSTEM="$AMIBERRY_OS_ROOT/L/FastFileSystem"

if [[ ! -d "$AMIBERRY_OS_ROOT" ]]; then
  echo "AMIBERRY_OS_ROOT is not a directory: $AMIBERRY_OS_ROOT" >&2
  exit 1
fi

for f in \
  "$AMIBERRY_WORKBENCH_ADF" \
  "$AMIBERRY_KICKSTART" \
  "$AMIBERRY_ROM_KEY" \
  "$AMIBERRY_FAST_FILE_SYSTEM"
do
  if [[ ! -f "$f" ]]; then
    echo "Missing required file: $f" >&2
    exit 1
  fi
done

echo "Workbench root : $AMIBERRY_OS_ROOT"
echo "Workbench ADF  : $AMIBERRY_WORKBENCH_ADF"
echo "Kickstart      : $AMIBERRY_KICKSTART"
echo "FastFileSystem : $AMIBERRY_FAST_FILE_SYSTEM"
echo

if (( $# == 0 )); then
  exec uv run --project "$ROOT/integration-tests/amiberry" \
    pytest --run-amiga "$ROOT/integration-tests/amiberry"
else
  exec uv run --project "$ROOT/integration-tests/amiberry" \
    pytest --run-amiga "$@"
fi