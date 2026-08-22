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

**Problem:** Stage 2 cannot implement `fujinet-nio.device` until the public `IORequest` ABI exists, abort has a first-class FN code that does not collide with `FN_ERR_UNKNOWN`, and `fn_session.c` can compile into the broker without `fn_internal.h`.

**Approach:** Publish `fujinet_nio_device.h` from architecture §2, add `FN_ERR_ABORTED` (`0x13`) to the shared error header (and its string helper), drop the unused session include, and record the native malformed-request `io_Error` symbol by inspecting the Amiga GCC `exec/errors.h` used in this workspace.

## Boundaries & Constraints

**Always:**
- Match architecture §2 layout, names, and command (`FUJINET_NIO_CMD_EXCHANGE` = `CMD_NONSTD + 0`). Base type `IORequest`, not `IOStdReq`.
- `FN_ERR_ABORTED` is `0x13` in `fujinet-nio.h` only. Do not reuse `0xFF` or any existing `FN_ERR_*`.
- Length fields are `UWORD`. Do not hard-code 1024 in the public ABI; oversize policy is vs platform `FN_MAX_PACKET_SIZE`.
- v1 `fn_struct_size` exact-match policy in comments only; no broker device yet.
- Malformed-request rule: native Exec/device validation `io_Error` + `FN_ERR_INVALID`. Tests and docs must use `exec/errors.h` symbols, never guessed numeric `IOERR_*` literals.
- Source `scripts/env.sh` before Amiga/lib builds. After lib changes, run complete `make check` in `repos/fujinet-nio-lib`.

**Ask First:**
- If NDK `exec/errors.h` has no suitable request-validation symbol for flags/pad or NULL+nonzero, stop; do not invent a numeric.

**Never:**
- Implement `amiga/nio.device/`, rewrite `fn_transport.c`, change DiskDevice, or load the broker.
- Dual `OpenDevice("serial.device")` work, idle-close changes, or Stage 5 backends.
- Change `FN_MAX_PACKET_SIZE` or Atari/BBC `fn_protocol.inc` error numbering (those files are not the C ABI).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Compile public ABI | New header included with NDK `exec/io.h` / `devices.h` | Warning-clean Amiga GCC compile of a TU that includes only that header | Fail the stage if warnings or missing `CMD_NONSTD` |
| Abort code | `FN_ERR_ABORTED` | Equals `0x13`; distinct from `0x12` and `0xFF` | Collision is a spec violation |
| Session isolation | `fn_session.c` without `fn_internal.h` | Same session behavior; `make test-session` and `make check` pass | Restore nothing; do not reintroduce the include |
| Malformed `io_Error` | Inspect toolchain `exec/errors.h` | Named symbol recorded in architecture §2.1 (flags/pad and NULL+nonzero rows) | HALT if no symbol exists |

</frozen-after-approval>

## Code Map

- `docs/amiga/nio-broker-architecture.md` §2 — ABI owner (struct ~L107–144). Copy names/layout; the architecture snippet currently has a stray `*/` on the `fn_request_length` comment — emit a valid C comment in the header. §2.1 matrix still says “native invalid-request error”; replace those cells with the sourced symbol after inspection.
- `repos/fujinet-nio-driver/amiga/include/fujinet_disk_device.h` — sibling header style (`CMD_NONSTD + n`, device name `#define`, include `<exec/io.h>`).
- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` — **create**. Not referenced by the disk device or lib yet (Stage 3 opens it).
- `repos/fujinet-nio-lib/include/fujinet-nio.h` L72–109 — insert `#define FN_ERR_ABORTED 0x13` after `FN_ERR_NO_HANDLES`, before `FN_ERR_UNKNOWN`.
- `repos/fujinet-nio-lib/src/common/fn_util.c` L3–19 — add `fn_error_string` case for abort (default already maps unknown).
- `repos/fujinet-nio-lib/docs/api.md` ~L580 — error table; add `0x13`.
- `repos/fujinet-nio-lib/src/common/fn_session.c` L1–5 — `#include "fn_internal.h"` is unused (file never references internals; uses `fn_session.h`, `fujinet-nio.h`, `fn_protocol.h` / SLIP). Delete that include only.
- `repos/fujinet-nio-lib/include/fn_protocol.h` L250–255 — Amiga/non-cc65 `FN_MAX_PACKET_SIZE` is 1024; header comments may cite the macro, not a literal 1024.
- `repos/fujinet-nio-driver/amiga/tests/stubs/exec/errors.h` — host-test stub (`IOERR_OPENFAIL` … `IOERR_BADADDRESS`). Not the NDK source of truth.
- Toolchain NDK `exec/errors.h` via `AMIGA_TOOLCHAIN_BIN` / NDK include path from `scripts/env.sh` — inspect for the malformed-request symbol (candidates in the stub set include `IOERR_BADADDRESS`; pick what the real header documents, do not assume).
- `repos/fujinet-nio-lib/Makefile` — `TARGETS` includes `amiga`; `EXTRA_TARGETS` includes `amiga-driver`; `check` = `all` then `test` (includes `test-session`).
- `backlog/nio-broker.md` Stage 1 checkboxes — mark done only after verification; do not start Stage 2.

## Tasks & Acceptance

**Execution:**
- [ ] `repos/fujinet-nio-lib/include/fujinet-nio.h` -- add `FN_ERR_ABORTED` `0x13` -- Stage 1 ABI coordination
- [ ] `repos/fujinet-nio-lib/src/common/fn_util.c` -- map abort in `fn_error_string` -- keep public string helper complete
- [ ] `repos/fujinet-nio-lib/docs/api.md` -- document `0x13` -- API table matches header
- [ ] `repos/fujinet-nio-lib/src/common/fn_session.c` -- remove `#include "fn_internal.h"` -- broker can compile session by path
- [ ] `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` -- emit architecture §2 public ABI -- Stage 2 compile surface
- [ ] `docs/amiga/nio-broker-architecture.md` -- record sourced `io_Error` symbol on malformed-request rows -- source-check, not invention
- [ ] `backlog/nio-broker.md` -- check Stage 1 boxes that this work completes -- workspace tracker

**Acceptance Criteria:**
- Given the Amiga GCC/NDK from `scripts/env.sh`, when a translation unit includes only `fujinet_nio_device.h`, then it compiles with no warnings.
- Given `fujinet-nio.h`, when `FN_ERR_ABORTED` is used, then its value is `0x13` and existing `FN_ERR_*` values are unchanged.
- Given `fn_session.c` without `fn_internal.h`, when `make check` runs in `repos/fujinet-nio-lib`, then all configured library targets and host tests pass.
- Given `make TARGET=amiga` and `make TARGET=amiga-driver` in `repos/fujinet-nio-lib`, when Stage 1 files are in place, then those library builds still pass.
- Given toolchain `exec/errors.h`, when Stage 1 finishes, then architecture §2.1 names the real symbol for unsupported flags/pad and NULL+nonzero, and no test or doc hard-codes a guessed `IOERR_*` number.
- Given the repo, when Stage 1 is done, then there is still no `amiga/nio.device/` implementation.

## Spec Change Log

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh"` -- expected: Amiga toolchain and NDK on PATH / readable headers
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make check` -- expected: all configured targets build; host tests including `test-session` pass
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-lib" && make TARGET=amiga-driver lib` -- expected: amiga-driver archive still builds (also covered by `make all` inside `check` if `EXTRA_TARGETS` is in `all`; if not, run this explicitly — `all` loops `TARGETS` only, so **must** run `amiga-driver` separately)
- Compile-check the new header with Amiga GCC `-Wall -Werror` against NDK includes -- expected: no warnings

**Manual checks (if no CLI):**
- Confirm `FN_ERR_ABORTED` is absent from Atari/BBC `fn_protocol.inc` (those are not this ABI) unless a test fails for missing it — do not add there without a failure.
- Confirm architecture §2.1 no longer says only “native invalid-request error” for flags/NULL rows.
