---
title: 'Reduce Atari public client library footprint with CA65'
type: refactor
created: '2026-10-25'
status: done
review_loop_iteration: 0
baseline_commit: 'a25fc1ee9c33e2acdbbd5274a7fd4680ce3af024'
baseline_library_commit: '86431220c78ffbdb40cbf1596f2b394fef3e8801'
context:
  - AGENTS.md
  - docs/agent-test-policy.md
  - repos/fujinet-nio-lib/AGENTS.md
---

<frozen-after-approval reason="User explicitly authorized baseline, implementation, measurement and verification as one uninterrupted task">

## Intent

Reduce code and RAM costs of the Atari public NIO library with compact handwritten CA65, preserving all existing public C API/ABI and native device $7F behavior. Measure fnaccept and a minimal client before and after. Support assembly clients without a C runtime. Keep the original implementation selectable and make the new backend default only when measured savings and full acceptance justify it.

## Boundaries & Constraints

Always preserve Clock, File, Network, Disk, raw calls, handle/session operations, limits, errors, capability discovery and optional PROC reporting. Preserve bounded W/P/R recovery, malformed response rejection and no replay of uncertain side effects. No new copies or fixed packet workspaces. Hybrid C is acceptable where measured size or compatibility favors it. User authorized implementation and local commits/pins; never push.

Escalate only concrete blockers to API/native protocol preservation. Never modify resident CIO handler, public headers to simplify assembly, firmware, wire protocol, DOS installation, or Epic 3 hardware behavior. Existing resident 3072-byte budget stays untouched. This is independent of numbered epic artifact namespaces.

## I/O & Edge-Case Matrix

| Scenario | State | Required behavior |
|---|---|---|
| Services | Clock/File/Network/Disk public calls | Identical packets, results and durable effects |
| Raw bounds | NULL payload with nonzero size, >506-byte payload | Existing invalid error, no W |
| Response | Wrong device/command, malformed length/checksum/descriptors, insufficient output | Existing errors, no request replay |
| Recovery | rejected W; malformed R length; interrupted accepted R; reset after READY | Preserve distinction between unaccepted and uncertain W; bounded P/R before next distinct W |
| ABI | C fastcall and assembly parameter blocks | Existing C arguments/results; assembly core links without C runtime |
| Capabilities | explicit Q, failure and PROC latch | Existing flags and limits, no invented interrupts |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-lib/makefiles/build.mk`: selects common C and platform CA65 objects; needs reliable separate baseline/compact archives and object selection.
- `repos/fujinet-nio-lib/src/platform/atari/fn_transport.s`: already CA65 native Q/W/P/R with bounded recovery; keep semantics, remove runtime dependence for assembly callers if necessary using compatible scratch storage.
- `repos/fujinet-nio-lib/src/common/fn_raw.c`: auto-init, default response INTERNAL/0, <=506 payload, no replay, identity check, parse and bounded copy. NULL output with adequate capacity is allowed.
- `repos/fujinet-nio-lib/src/common/fn_packet_header.c`, `fn_checksum_fold.c`, `fn_packet_checksum*.c`, `fn_packet_parse_common.c`: packet construction and descriptor parser; ideal compact CA65 seam. All descriptor widths/chains remain supported.
- `repos/fujinet-nio-lib/src/common/fn_state.c`, `fn_init.c`: state and session helpers. Separate archive members where this avoids unwanted dependencies.
- `repos/fujinet-nio-lib/src/common/fn_clock_common.c`, `fn_rw.c`, `fn_packet_build_*.c`: shared hot operations; measure before replacing.
- `repos/fujinet-nio-lib/src/common/fn_disk.c`: 2708-byte monolithic object; cc65 aliases request to response buffer and reply to request buffer. Preserve copy ordering; improve archive granularity or use assembly where worthwhile.
- `repos/nio-core-apps/apps/platform/atari/resident/fnresident_asm.s`: read-only proven packet/transaction reference, never edit.
- `repos/fujinet-nio-lib/tests/atari_transport_soft65c02.*`: assembled real-CPU transport cases; extend meaningful coverage for assembly public APIs and malformed packets.
- `test-evidence/atari-library-size-baseline/`: original archive and fnaccept xex/map/lbl captured before edits.
- Atari Story 2.1–2.4 implementation artifacts and native physical-SIO specification: accepted service/recovery contracts. Investigation agent supplies distilled findings to parent.

## Tasks & Acceptance

Implementation agent owns library production code, build selection, assembly ABI documentation and focused new tests. Baseline agent owns workspace measurement tooling and saved baseline. Parent owns workspace spec, final integration acceptance and commits. Agents share files: do not revert others' edits; accommodate them. No implementation delegation is required.

- [x] Save reproducible fnaccept/minimal/control baseline with canonical revisions, maps and segment/runtime attribution.
- [x] Implement compact assembly packet/core ABI and useful measured service optimizations under library Atari directory, retaining original selectable backend.
- [x] Add real-6502 tests for compatibility/edge cases and runtime-free assembly link/execution.
- [x] Compare full final maps and XEX sizes, CODE/RODATA/DATA/BSS/ZP, stack/workspace, occupied ranges and incremental library cost; report absolute bytes and percentages.
- [x] Run complete library check and both adapters' public service and four recovery acceptance cases; preserve original reference comparison.
- [x] Document measured hybrid decisions, default selection rationale, assembly interface and verification; commit verified library/workspace changes and update pins.

Given unchanged public clients, when linked against compact backend, then all accepted API/service/recovery behavior remains equivalent. Given the same compiler and linker settings, when comparing original and compact images, then substantial measured savings justify default selection. Given assembly-only client, when linked with compact entry points, then no cc65 runtime is required.

## Verification

Source `scripts/env.sh` with NIO_WORKSPACE set before every build/test.

- `make -C repos/fujinet-nio-lib check`: all configured target builds and host/public archive/real-CPU transport tests. Baseline passed 2026-10-25, log `/tmp/atari-library-baseline-check.log`.
- `make -C repos/nio-core-apps -f makefiles/build.mk TARGET=atari fnaccept`: unchanged acceptance client build.
- `cd repos/fujinet-nio-lib && bash tests/run_atari_compact_test.sh`: 13,137 compiled-C differential 6502 checks, runtime-free assembly link/execution, and 128 compact transport assertions passed.
- `python3 integration-tests/atari-sio/run_boot_acceptance.py --public-api-clock --write-evidence --json`; replace `clock` with `rejected-w-recovery`, `malformed-r-recovery`, `interrupted-r-recovery`, `reset-recovery`; repeat each flag with `-altirra-embedded`. All ten original and all ten final compact runs passed.
- `python3 integration-tests/atari-sio/library-size/measure.py --archive repos/fujinet-nio-lib/build/fujinet-nio-atari-compact.lib --output test-evidence/atari-library-size-compact-provenance`; repeat for original archive/new output. Both passed; original and compact images reproduce saved measurements byte-for-byte.

## Spec Change Log

## Completion and review audit

Three independent review layers found build-default/backend-selection issues and
coverage/provenance gaps. Fixed the default make target and preserved the selected
canonical archive during compact tests. Added large raw replies, initialization
failure/retry, boundary checks and full assembly layout assertions. Measurement
outputs now retain the archive, record dirty state/input hashes and reject
nonempty directories. No wire/API algorithm change was required by review.

Full final library check passed: `/tmp/atari-compact-review-check.log`.
Workspace runner suite: 65 tests passed. Archive export audit retained all 103
original `fn_*` exports. The unchanged resident handler and firmware have no diff.
Final measured fnaccept: 18,584 → 16,114 XEX bytes; 22,345 → 19,933 RAM bytes;
13,126 → 10,713 linked NIO bytes. Minimal Clock: 3,521 → 2,318 XEX bytes.
The workspace measurement README owns full segment tables and live evidence paths.

The measured hybrid is default for the existing Atari defaults. Original C
remains selectable, including for custom compile-time limits. Service validation
and higher-level session/Network/Disk behavior remain C; packet/raw operations
and native transport use CA65. There are no new packet buffers or resident dependencies.

## Suggested Review Order

- Read backend boundaries and runtime-free assembly calling conventions.
  [compact-library.md:1](../../repos/fujinet-nio-lib/docs/atari/compact-library.md#L1)

- Inspect raw validation, alias-safe copying, and single-exchange error handling.
  [fn_compact_raw.s:1](../../repos/fujinet-nio-lib/src/platform/atari/fn_compact_raw.s#L1)

- Check full descriptor grammar and response validation.
  [fn_compact_parse.s:1](../../repos/fujinet-nio-lib/src/platform/atari/fn_compact_parse.s#L1)

- Inspect compact packet construction with unchanged C arguments.
  [fn_compact_build.s:1](../../repos/fujinet-nio-lib/src/platform/atari/fn_compact_build.s#L1)

- Review measured savings, reservations, and both-adapter acceptance evidence.
  [README.md:1](../../integration-tests/atari-sio/library-size/README.md#L1)

- Review differential ABI and edge-case coverage.
  [atari_compact_test.c:1](../../repos/fujinet-nio-lib/tests/atari_compact_test.c#L1)

- Check default selection and isolated original/compact archives.
  [build.mk:1](../../repos/fujinet-nio-lib/makefiles/build.mk#L1)

