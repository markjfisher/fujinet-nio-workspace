---
title: 'Amiga NIO broker Stage 2B — serial backend and isolated guest'
type: 'feature'
created: '2026-08-22'
status: 'ready-for-dev'
review_loop_iteration: 0
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - backlog/nio-broker.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2a.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** After 2A, the broker still does not own `serial.device`/`timer.device` or prove a FujiBus round-trip without the old shim, so parent Stage 2 is open.

**Approach:** Replace the injectable backend with architecture §11 serial: `backend_open` / `backend_close` / `backend_exchange`, session/SLIP, recovery. Produce `fujinet-nio.device` via `make native`. Prove with one isolated Amiberry node and a dedicated tool. Do not start until 2A Verification has run and passed. Parent Stage 2 completes only with 2A **and** this spec accepted.

## Boundaries & Constraints

**Always:**
- §11 signatures; `backend_close` idempotent; lazy-open; OpenCnt 0 does not `backend_close`; fatal → close/reset current fail, next may lazy-reopen; session/framing reset on close.
- Named serial-backend constants: baud default 19200 (current shim), serial/timer units, poll interval, timeout; `FN_ERR_TIMEOUT` when the deadline is exceeded.
- Path-compile `fn_session.c` / `fn_slip.c` into the broker; do not pull `fn_internal.h` or process-global transport.
- Isolated guest: `fujinet-nio.device` + loader + dedicated tool only. No FLS, no `fujinet-disk.device`, no `fujinet-mount`, no client whose `fn_transport` still opens `serial.device`.
- Run named Verification commands. Check Stage 2 backlog boxes only after 2A and 2B both passed.

**Ask First:**
- Changing public `FujiNetNIORequest` or `FUJINET_NIO_CMD_EXCHANGE`.
- Installing the broker on any existing Amiberry case that still uses the serial-direct shim.

**Never:**
- Edit `fn_transport.c`. Involve FLS or `fujinet-disk.device` in this delivery.
- Load broker and old shim in the same test environment.
- Treat 2B as a second Stage 2 checkpoint or skip 2A.
- Default to `scripts/amiga-tests` or DiskDevice pytest. Create epics/stories.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Isolated guest exchange | Dedicated tool; known FujiBus frame; broker only | Matching response; close | Fail if disk.device, FLS, or serial-direct shim is loaded |
| Lazy-open | First exchange; backend closed | `backend_open` then exchange; later exchanges reuse | FN setup error if open fails |
| Resident-lifetime | OpenCnt 0; serial still open | Next exchange without reopen-as-if-never-opened | N/A |
| Fatal recovery | Backend transport/fatal | Current fails FN-space; `backend_close`; next lazy-reopen or fail while closed | Do not copy FN into `io_Error` |
| Timeout | No response within named deadline | `FN_ERR_TIMEOUT`; `fn_response_length` 0 | Bounded; worker not stuck forever |

</frozen-after-approval>

## Code Map

- 2A `nio.device/` BeginIO/FIFO/expunge — **extend**, do not rewrite ABI validation.
- `docs/amiga/nio-broker-architecture.md` §7, §11 L724–771 — recovery and backend C API.
- `repos/fujinet-nio-lib/src/common/fn_session.c` + `fn_slip.c` + `include/fn_slip.h` (from 2A) — path-compile; broker must not include `fn_transport.c`.
- `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c` — **read-only**. Copy ideas: `FN_AMIGA_BAUD` default 19200, OpenDevice unit 0, 8N1, timer wait (~L37–39, ~L211). Constants live in the serial backend TU.
- `repos/fujinet-nio-driver/amiga/Makefile` — `native` emits `../build/amiga/fujinet-nio.device` and the dedicated tool; disk.device must not depend on the broker.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-load-resident.c` — register `fujinet-nio.device` in the isolated image.
- `integration-tests/amiberry/conftest.py` ~L825–831 — `driver: true` installs **disk** device. Need a **new** tests.toml flag that copies `fujinet-nio.device` + loader **without** `--disk-device` / mount / FLS.
- `integration-tests/amiberry/tests.toml` + `startup/` + `test_nio_broker.py` — case e.g. `nio-broker-isolated`; **do not** set `driver = true`.
- `backlog/nio-broker.md` Stage 2 suite — guest rows that need real serial; boxes after 2A+2B commands ran.

## Tasks & Acceptance

**Execution:**
- [ ] Serial backend TU: `backend_open`/`close`/`exchange`; serial+timer ownership; named constants; path-compile session/slip -- physical backend
- [ ] Wire 2A worker to real backend (drop injectable-only linkage in the Amiga binary) -- Stage 2 device
- [ ] `amiga/Makefile` `native` -- `fujinet-nio.device` + dedicated guest tool
- [ ] Isolated tests.toml/startup/pytest + harness flag without disk.device -- isolation
- [ ] Two independent Amiga tasks submit concurrent exchanges; FIFO serialize; each correct response; single backend ownership -- Stage 2 suite, guest not host 2A
- [ ] `backlog/nio-broker.md` -- Stage 2 boxes only after 2A and 2B Verification ran

**Acceptance Criteria:**
- Given 2A is `done`, when 2B builds, then `make native` produces `fujinet-nio.device`.
- Given the isolated guest image, when `test_isolated_exchange` runs, then a known frame round-trips and neither `fujinet-disk.device` nor a serial-direct `fn_transport` client is present.
- Given two independent Amiga tasks submit broker exchanges at the same time, when the isolated Stage 2 suite runs, then the worker serializes them, each task receives its own correct response, and the backend remains singly owned.
- Given 2B Verification passed, when 2A also passed, then parent Stage 2 may be marked complete; otherwise it stays open.

## Spec Change Log

- 2026-08-22: Carried two-task concurrent FIFO + single backend ownership into 2B acceptance; not a 2A host-test item.

## Design Notes

Host 2A tests may keep an injectable backend. The Amiga `fujinet-nio.device` binary and the guest tool use **real** serial (backlog: not a static stub as the Stage 2 suite). Guest need not re-prove every 2A BeginIO row if host tests already did.

## Verification

2B is incomplete if these were not run. Do not substitute DiskDevice pytest or the full Amiberry suite. If guest media/toolchain is missing, stop and report.

**Commands (after `source "$NIO_WORKSPACE/scripts/env.sh"`):**
- `cd "$NIO_WORKSPACE/repos/fujinet-nio-driver/amiga" && make native` -- expected: `../build/amiga/fujinet-nio.device` and the dedicated tool build
- `cd "$NIO_WORKSPACE" && uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_broker.py::test_isolated_exchange` -- expected: PASS; fail if disk.device/FLS/shim appear in that image
