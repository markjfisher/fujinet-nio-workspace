---
title: 'Deduplicate Amiga driver protocol helpers'
type: 'refactor'
created: '2026-09-05'
status: 'done'
baseline_commit: '8b886790930a7ccc98c60a395fade94c0ac4c75d'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Amiga NIO device and diagnostic tools contain identical little-endian helpers, while `fujinet-nio-exchange` contains duplicate checksum and packet-builder implementations inside the same executable. This increases drift risk in wire-format code.

**Approach:** Centralize Amiga-private little-endian primitives in one internal header and make the exchange opts module the sole owner of diagnostic packet construction and its checksum calculation.

## Boundaries & Constraints

**Always:** Preserve byte-for-byte packet formats, command behavior, public Amiga device ABI, and existing test independence. Keep exact buffer-capacity validation on centralized builders.

**Ask First:** Any change requiring a public `fujinet-nio-lib` API, any MS-DOS source change, or any externally visible command-line behavior change.

**Never:** Merge the retry classifier's checksum validation blindly with builder checksum generation; it intentionally excludes the stored checksum byte. Do not share production endian helpers with test-side packet encoders where doing so would weaken the independent oracle. Do not reopen broker or DiskDevice behavior.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Clock builders | GET and GET_TZ command packets | Six-byte packets retain their exact device, command, length, descriptor, and checksum bytes | Undersized output capacity returns failure |
| File-list marker | Completion URI and 256-byte response limit | Central builder produces the same request as the removed local builder | Invalid URI/capacity remains rejected |
| Baud control | 32-bit baud request/response | Shared LE32 helpers preserve existing wire bytes and decoded value | Existing device validation remains unchanged |
| Retry classification | Encoded READ/WRITE sector request | Shared LE16 read preserves strict request-shape classification | Retry checksum continues excluding byte 4 |

</frozen-after-approval>

## Code Map

- `repos/fujinet-nio-driver/amiga/include/fujinet_nio_endian.h` -- new Amiga-private, C99-compatible LE16/LE32 get/put primitives.
- `repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c` and `.h` -- existing validated packet-builder owner; add GET_TZ support and use shared LE writes.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c` -- remove duplicate checksum and local clock/file-list builders; call centralized builders; use shared LE32 helpers.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-baud.c` -- replace local LE32 pair.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c` -- replace local LE32 pair without changing control semantics.
- `repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c` -- replace manual LE16 extraction only; preserve retry-specific checksum validation.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_opts.c` -- verify exact GET/GET_TZ and file-list packet bytes and capacity failures.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c` and `test_fujinet_nio_client_retry.c` -- existing independent encoders exercise production LE32/LE16 consumers.
- `repos/fujinet-nio-driver/amiga/Makefile` -- record new header dependencies for affected native artifacts.

## Tasks & Acceptance

**Execution:**
- [x] Add the private endian header and migrate Amiga production/tool call sites while leaving test encoders independent.
- [x] Consolidate all exchange diagnostic packet builders in the opts module and remove redundant local implementations.
- [x] Extend focused packet-builder tests for GET_TZ, exact checksums/length fields, and capacity rejection.
- [x] Update native build dependencies and run the driver-owner verification commands.

**Acceptance Criteria:**
- Given the existing exchange diagnostic modes, when their packets are built after refactoring, then their wire bytes are unchanged and only one builder checksum implementation remains in the diagnostic executable.
- Given baud control and retry request classification, when native tests exercise them, then values decode identically and retry eligibility remains strict.
- Given all affected Amiga targets, when compiled with warnings as errors and the m68k toolchain, then they build successfully.

## Spec Change Log

- 2026-09-05: Human review confirmed that generation and validation use the same checksum algorithm; added one shared helper with an explicit skip-byte mode and direct vector coverage, avoiding duplicate production/test implementations.

## Design Notes

Generation and validation use one shared checksum helper with an explicit `skip_checksum_byte` parameter; all FujiBus packet callers skip encoded byte 4, while direct tests cover both modes. MS-DOS endian helpers retain their `NIO_PROTO_PTR` contract and are out of scope. The helper is Amiga-private rather than exposing internal `fujinet-nio-lib` macros.

## Verification

**Commands:**
- `source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga/tests build/test_fujinet_nio_exchange_opts build/test_fujinet_nio_device build/test_fujinet_nio_client_retry && repos/fujinet-nio-driver/amiga/tests/build/test_fujinet_nio_exchange_opts && repos/fujinet-nio-driver/amiga/tests/build/test_fujinet_nio_device && repos/fujinet-nio-driver/amiga/tests/build/test_fujinet_nio_client_retry` -- focused host-native behavior passes.
- `source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga ../build/amiga/fujinet-nio-exchange ../build/amiga/fujinet-nio-baud ../build/amiga/fujinet-nio.device ../build/amiga/channels/rs232/fujinet_nio_client.o` -- affected Amiga binaries and retry client compile with the configured m68k toolchain.

## Suggested Review Order

**Centralized packet construction**

- Shared checksum and command construction now have one implementation.
  [`fujinet_nio_exchange_opts.c:15`](../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L15)

- GET, GET_TZ, and file-list callers preserve the original diagnostic flows.
  [`fujinet-nio-exchange.c:557`](../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L557)

- Completion-marker construction now uses validated capacity handling.
  [`fujinet-nio-exchange.c:695`](../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L695)

**Wire-format helpers**

- Amiga-only LE16/LE32 primitives remove repeated byte arithmetic.
  [`fujinet_nio_endian.h:6`](../../repos/fujinet-nio-driver/amiga/include/fujinet_nio_endian.h#L6)

- Device baud control consumes the shared helpers without ABI changes.
  [`fujinet_nio_device.c:189`](../../repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c#L189)

- Retry parsing uses shared LE16 reads while retaining its distinct checksum contract.
  [`fujinet_nio_client.c:14`](../../repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c#L14)

**Verification**

- Exact packet bytes and failure capacities are covered by native tests.
  [`test_fujinet_nio_exchange_opts.c:80`](../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_opts.c#L80)

- Header changes invalidate all affected incremental test targets.
  [`tests/Makefile:36`](../../repos/fujinet-nio-driver/amiga/tests/Makefile#L36)
