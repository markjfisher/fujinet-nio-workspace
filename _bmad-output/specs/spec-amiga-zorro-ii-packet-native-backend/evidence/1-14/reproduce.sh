#!/usr/bin/env bash
# Diagnostic: exit 0 means the unsafe late-reply behavior was reproduced.
set -euo pipefail
probe_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export NIO_WORKSPACE=$(git -C "$probe_dir" rev-parse --show-toplevel)
source "$NIO_WORKSPACE/scripts/env.sh"
cd "$NIO_WORKSPACE"
probe_build=$(mktemp -d /tmp/story114-late-reply.XXXXXX)
trap 'rm -rf "$probe_build"' EXIT
cc -std=c99 -Wall -Wextra -Werror -pedantic -Wno-unused-function \
  -DFUJINET_NIO_NATIVE_TEST -DFUJINET_NIO_DIRECTORY_TRANSFER_TIMEOUT_MS=100 \
  -Irepos/fujinet-nio-driver/amiga/include \
  -Irepos/fujinet-nio-driver/amiga/nio.device \
  -Irepos/fujinet-nio-driver/amiga/tests \
  -Irepos/fujinet-nio-lib/include -Irepos/fujinet-nio-driver/amiga/tests/stubs \
  "$probe_dir/late_reply.c" \
  repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_directory_backend.c \
  repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_packet_backend.c \
  repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c \
  repos/fujinet-nio-driver/amiga/common/fujinet_io_queue.c \
  repos/fujinet-nio-lib/src/common/fn_packet_checksum_packet.c \
  repos/fujinet-nio-lib/src/common/fn_packet_checksum.c \
  repos/fujinet-nio-lib/src/common/fn_checksum_fold.c \
  -o "$probe_build/late_reply"
"$probe_build/late_reply"
