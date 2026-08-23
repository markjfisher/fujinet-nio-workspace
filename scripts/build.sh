#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

export PYTHONPATH="$ROOT/tools/build:$ROOT/tools${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
if python3 -c 'import yaml' >/dev/null 2>&1; then
    exec python3 -m nio_build.cli "$@"
fi

if command -v uv >/dev/null 2>&1; then
    exec uv run --no-project --with 'PyYAML>=6' python -m nio_build.cli "$@"
fi

echo "PyYAML is required by the workspace build tools; install it or install uv." >&2
exit 1
