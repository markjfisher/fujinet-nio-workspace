---
title: 'Amiga NIO broker Stage 1 — public ABI and framing isolation'
type: 'feature'
created: '2026-08-22'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-nio-broker/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-amiga-nio-broker/stages.md'
  - '{project-root}/docs/amiga/nio-broker-architecture.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Stage 2 cannot implement `fujinet-nio.device` until the public `IORequest` ABI exists, abort has a first-class local FN code that does not collide with `FN_ERR_UNKNOWN`, and `fn_session.c` can compile into the broker without `fn_internal.h`.

**Approach:** Publish a self-sufficient `fujinet_nio_device.h` from architecture §2, add client-visible `FN_ERR_ABORTED` (`0x13`) to the shared C error header (and its string helper), drop the unused session include, and inspect the real NDK `exec/errors.h` to choose a semantically appropriate native `io_Error` **per validation class**.

## Boundaries & Constraints

**Always:**
- Match architecture §2 layout, names, and command (`FUJINET_NIO_CMD_EXCHANGE` = `CMD_NONSTD + 0`). Base type `IORequest`, not `IOStdReq`.
- `fujinet_nio_device.h` must include everything it requires (`exec/io.h`, the header that actually defines `CMD_NONSTD`, Amiga integer types, etc.). A TU whose only include is this public header must compile; the test TU must not pre-include NDK headers to paper over an incomplete header.
- `FN_ERR_ABORTED` is `0x13` in `fujinet-nio.h` only. It is a **local/client-visible FN error**, not a new FujiBus wire-status requirement. Do not reuse `0xFF` or any existing `FN_ERR_*`.
- Do not add `FN_ERR_ABORTED` to Atari/BBC `fn_protocol.inc`. Those tables are not this C ABI; do not “synchronize” numeric error tables across platforms.
- Length fields are `UWORD`. Do not hard-code 1024 in the public ABI; oversize policy is vs platform `FN_MAX_PACKET_SIZE`.
- v1 `fn_struct_size` exact-match policy is **documentation only** in Stage 1. There is no broker yet to enforce it.
- Malformed-request FN side is always `FN_ERR_INVALID`. Native `io_Error` is chosen **per validation class** from the real NDK `exec/errors.h` (e.g. NULL pointer vs unsupported flags/pad need not share a symbol). Tests and docs use those symbols, never guessed numeric `IOERR_*` literals.
- Source `scripts/env.sh` before Amiga/lib builds. After lib changes, run complete `make check` in `repos/fujinet-nio-lib`.

**Ask First:**
- If NDK `exec/errors.h` has no suitable symbol for a given validation class, stop and report that class; do not invent a numeric or force one symbol onto every class.

**Never:**
- Implement `amiga/nio.device/`, rewrite `fn_transport.c`, change DiskDevice, or load the broker.
- Dual `OpenDevice("serial.device")` work, idle-close changes, or Stage 5 backends.
- Change `FN_MAX_PACKET_SIZE`.
- Treat `FN_ERR_ABORTED` as a FujiBus on-the-wire status that other platforms must emit.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Compile public ABI | TU contains only `#include <fujinet_nio_device.h>` (or the equivalent quoted include of that public header) | Warning-clean Amiga GCC compile; header pulled in `CMD_NONSTD` and types itself | Fail the stage if warnings or missing includes |
| Abort code | `FN_ERR_ABORTED` in `fujinet-nio.h` | Equals `0x13`; distinct from `0x12` and `0xFF`; client-visible FN only | Collision is a spec violation |
| Session isolation | `fn_session.c` without `fn_internal.h` | Same session behavior; `make check` (includes `test-session`) passes | Restore nothing; do not reintroduce the include |
| Native `io_Error` per class | Inspect toolchain `exec/errors.h` | Architecture §2.1 records the appropriate symbol **per class** (flags/pad vs NULL+nonzero may differ) | HALT and report any class with no suitable symbol |

</frozen-after-approval>

## Code Map

- `docs/amiga/nio-broker-architecture.md` §2 — ABI owner (struct ~L107–144). Copy names/layout; the architecture snippet currently has a stray `*/` on the `fn_request_length` comment — emit a valid C comment in the header. §2.1 rows that say “native invalid-request error” become sourced **per-class** symbols after inspection, not one shared symbol forced onto every row.
- `repos/fujinet-nio-driver/amiga/include/fujinet_disk_device.h` — sibling header style (`CMD_NONSTD + n`, device name `#define`, include `<exec/io.h>`). The new header must still be self-sufficient even if the disk header is not a complete model.
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` — **create**. Not referenced by the disk device or lib yet (Stage 3 opens it).
- `repos/fujinet-nio-lib/include/fujinet-nio.h` L72–109 — insert `#define FN_ERR_ABORTED 0x13` after `FN_ERR_NO_HANDLES`, before `FN_ERR_UNKNOWN`. Comment: local/client-visible, not a FujiBus wire status.
- `repos/fujinet-nio-lib/src/common/fn_util.c` L3–19 — add `fn_error_string` case for abort (default already maps unknown).
- `repos/fujinet-nio-lib/docs/api.md` ~L580 — error table; add `0x13` as client-visible FN, not wire status.
- `repos/fujinet-nio-lib/src/common/fn_session.c` L1–5 — `#include "fn_internal.h"` is unused (file never references internals; uses `fn_session.h`, `fujinet-nio.h`, `fn_protocol.h` / SLIP). Delete that include only.
- `repos/fujinet-nio-lib/include/fn_protocol.h` L250–255 — Amiga/non-cc65 `FN_MAX_PACKET_SIZE` is 1024; header comments may cite the macro, not a literal 1024.
- `repos/fujinet-nio-driver/amiga/tests/stubs/exec/errors.h` — host-test stub (`IOERR_OPENFAIL` … `IOERR_BADADDRESS`). Not the NDK source of truth; do not copy stub values into architecture or tests as guesses.
- Toolchain NDK `exec/errors.h` via `AMIGA_TOOLCHAIN_BIN` / NDK include path from `scripts/env.sh` — inspect **per validation class**. A NULL pointer may map to something like `IOERR_BADADDRESS` if the NDK documents that; unsupported flags may use a different symbol or have none (then HALT).
- `repos/fujinet-nio-lib/Makefile` — `TARGETS` includes `amiga`; `EXTRA_TARGETS` includes `amiga-driver`; `check` = `all` then `test` (`all` does **not** loop `EXTRA_TARGETS`).
- `backlog/nio-broker.md` Stage 1 checkboxes — mark done only after verification; do not start Stage 2.

## Tasks & Acceptance

**Execution:**
- [ ] `repos/fujinet-nio-lib/include/fujinet-nio.h` -- add client-visible `FN_ERR_ABORTED` `0x13` -- Stage 1 FN API, not FujiBus wire
- [ ] `repos/fujinet-nio-lib/src/common/fn_util.c` -- map abort in `fn_error_string` -- keep public string helper complete
- [ ] `repos/fujinet-nio-lib/docs/api.md` -- document `0x13` as local FN -- API table matches header
- [ ] `repos/fujinet-nio-lib/src/common/fn_session.c` -- remove `#include "fn_internal.h"` only -- broker can compile session by path
- [ ] `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` -- self-sufficient architecture §2 public ABI -- Stage 2 compile surface
- [ ] `docs/amiga/nio-broker-architecture.md` -- record per-class sourced `io_Error` symbols -- source-check, not one symbol for all classes
- [ ] `backlog/nio-broker.md` -- check Stage 1 boxes that this work completes -- workspace tracker

**Acceptance Criteria:**
- Given a translation unit whose only preprocessor include is `fujinet_nio_device.h`, when it is compiled with Amiga GCC/NDK from `scripts/env.sh` and `-Wall -Werror`, then it compiles with no warnings (the public header includes `exec/io.h`, `CMD_NONSTD`, and Amiga types itself).
- Given `fujinet-nio.h`, when `FN_ERR_ABORTED` is used, then its value is `0x13`, existing `FN_ERR_*` values are unchanged, and it is documented as a local/client-visible FN error, not a FujiBus wire status.
- Given `fn_session.c` without `fn_internal.h`, when `make check` runs in `repos/fujinet-nio-lib`, then all configured library targets and host tests pass.
- Given Stage 1 files in place, when the canonical Makefile invocations for the normal Amiga library target and the `amiga-driver` library/archive target are run, then both build successfully.
- Given toolchain `exec/errors.h`, when Stage 1 finishes, then architecture §2.1 names a semantically appropriate native `io_Error` **per validation class** (flags/pad vs NULL+nonzero need not match); any class without a suitable symbol was reported and not invented; no test or doc hard-codes a guessed `IOERR_*` number.
- Given the repo, when Stage 1 is done, then there is still no `amiga/nio.device/` implementation.

## Spec Change Log

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh"` -- expected: Amiga toolchain and NDK on PATH / readable headers
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make check` -- expected: all configured `TARGETS` (including `amiga`) build; host tests including `test-session` pass
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make TARGET=amiga-driver lib` -- expected: `amiga-driver` archive builds (`make all` / `make check` do not include `EXTRA_TARGETS`)
- Compile a TU that contains only `#include "fujinet_nio_device.h"` (plus an empty `main` if the driver requires it) with Amiga GCC `-Wall -Werror` and NDK include paths, **without** extra NDK includes in the TU -- expected: no warnings

**Manual checks (if no CLI):**
- Confirm `FN_ERR_ABORTED` was not added to Atari/BBC `fn_protocol.inc`.
- Confirm architecture §2.1 records per-class native symbols, not a single forced symbol for every malformed-request row.
