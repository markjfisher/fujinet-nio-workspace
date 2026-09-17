---
id: SPEC-amiga-zorro-ii-packet-native-backend
companions:
  - ../../planning-artifacts/epics.md
  - execution-gates.md
sources: []
---

> **Canonical contract.** This SPEC and its companions define what to build, test and validate. The adopted epic companion retains the approved requirements, code evidence, ownership, story scopes, acceptance criteria and verification commands; it is required input, not an audit-only source. Its repository paths are workspace-relative. Approval of this plan does not mean its implementation or hardware gates have passed.

# Amiga Zorro-II packet-native backend

## Why

Amiga users need a future Zorro-II connection through an RP2350B bridge to ESP32-S3 without changing FujiBus semantics, applications or established service/device behavior. The current C++ codec still wraps/requires SLIP and the native framer does not preserve packet boundaries. Establish a tested raw-packet path before committing a physical ABI, then validate a Zorro-only installation against the existing separately deployed serial compatibility baseline.

## Capabilities

- **CAP-1**
  - **intent:** Developers can exchange canonical raw FujiBus packets without changing the established serial wire contract.
  - **success:** Independent literal fixtures and production codec/framer tests verify unchanged header, byte order, parameters, payload, checksum and status semantics; native packets have no SLIP wrapping and serial compatibility tests pass (1.1–1.3).
- **CAP-2**
  - **intent:** Native packet I/O preserves complete-packet boundaries with bounded ownership, capacity and observable failures.
  - **success:** Production framing passes deterministic queued-packet, partial/oversize/truncation, send-failure, backpressure and reset tests without guessing boundaries from byte reads or poll timing (1.4).
- **CAP-3**
  - **intent:** Amiga callers retain safe ordered exchanges, response ownership and meaningful errors across native transport failures.
  - **success:** Actual broker and existing retry callers demonstrate one remotely in-flight exchange, one reply per request, correct buffer/error ownership and no stale-response misattribution or unsafe replay after ambiguous completion; the canonical software packet/failure contract is explicitly accepted (1.5–1.6, 1.10, 1.14, 3.1, 3.6).
- **CAP-4**
  - **intent:** Developers can prove native service and device parity before physical Zorro hardware exists.
  - **success:** Real core handlers, the actual Amiga exchange tool and resident driver pass file-list, clock, disposable-media disk read/write, catalogue and media-lifecycle checks against independent storage/time expectations without serial controls on the native path (1.7–1.14).
- **CAP-5**
  - **intent:** Bridge developers can independently establish a reproducible project and decision-grade physical feasibility evidence.
  - **success:** The isolated RP2350B skeleton cross-builds and its shared PIO implementation passes independent native behavioral tests from reproducible dependency setup without affecting POSIX/ESP targets; instrumented Zorro/PIO and bridge-to-ESP experiments report measured capabilities, reset limitations and explicit proceed/hold conclusions, not hardware claims from mocks (2.1–2.3).
- **CAP-6**
  - **intent:** Endpoint implementers can agree a hardware packet ABI grounded in accepted software semantics and physical evidence.
  - **success:** Explicit 2.4 approval cites accepted 1.6 raw representation, packet boundaries, ownership and relevant failure behavior plus positive relevant 2.2/2.3 evidence; missing or conflicting evidence withholds approval.
- **CAP-7**
  - **intent:** Amiga users can operate the complete Zorro-only RP2350B/ESP32-S3 path without service or application API forks.
  - **success:** ABI-conforming Amiga, bridge and ESP implementations pass complete-chain file, clock and disposable-disk operations using the real exchange tool, with no assumed serial backend (3.1–3.4).
- **CAP-8**
  - **intent:** Users can install a validated Zorro-only system with preserved media workflows and known recovery/performance limits.
  - **success:** Actual hardware passes existing DD/HD ADF, catalogue, independent-drive and lifecycle assertions; reviewed fault traces support documented recovery, and reproducible installation plus measured latency/throughput are published (3.5–3.7).

## Constraints

- Preserve existing FujiBus IDs, commands, field widths, length/checksum/status mapping and service payloads, the public Amiga exchange ABI, and higher-layer behavior. Reuse the existing Amiga backend contract and C++ `IFramer`/`FujiBusTransport` extension points; justify any narrow packet-I/O addition against demonstrated gaps.
- Preserve observable ordering/ownership initially without permanently freezing the single-worker FIFO implementation. Multiple requests may queue locally, but multiple remotely in-flight exchanges are prohibited unless a future design introduces safe correlation. No correlation identifier is added by this spec.
- A running Zorro installation uses only Zorro: no assumed RS-232 backend, dynamic physical switching, serial fallback or automatic failover. Serial is a separate compatibility/test deployment.
- Test actual existing retry paths. Abort is not rollback; timeout/reopen does not prove remote quiescence. If unchanged higher layers cannot be safely contained, stop for a scope decision rather than quietly changing retry or service semantics.
- Keep ownership boundaries, bounded memory/work, native error/reset handling and platform limits explicit. Do not equate SLIP-expanded length, raw packet length and physical transfer capacity. Services remain outside the bridge and hardware adapters.
- User amendment, 2026-09-14: Stories 1.5 and 1.6 use evidence-backed technical acceptance by the implementing/reviewing agent, with no routine human checkpoints. Audit requirement coverage as well as passing tests and record the decision and revisions. Consult the user only for unresolved limitations, scope changes or meaningful tradeoffs; missing coverage still blocks acceptance. Story 3.6 retains human review before implementation and acceptance of results; 2.4 retains explicit human ABI approval.
- Project setup and physical feasibility (2.1–2.3) may proceed independently of Epic 1. ABI sign-off requires accepted 1.6 and positive relevant 2.2/2.3 evidence. Physical implementation requires accepted 1.14, approved 2.4 and suitable hardware.
- Story 3.2 may be subdivided after ABI design; preserve its acceptance criteria, traceability and downstream dependencies. All required replacement slices must be accepted before 3.4.
- Use production-code-driven mocks, independent wire fixtures, controlled time/faults and disposable write media. Do not claim real-service parity from canned replies or hardware validity from a host/guest mock. Follow each owner's cheapest sufficient verification; actual library edits require complete `make check`.
- Keep the bridge project isolated from existing firmware build source collection and reuse established protocol/fixture locations. Do not assume the external legacy FujiNet firmware repository is a workspace dependency.

- Bridge hardware/PIO development is test-first with epio tests of shared apio C program/configuration sources; no `.pio` text programs or pioasm generation workflow. Story 2.1 requires independent native tests and a Pico SDK RP2350B firmware build, compatible pinned dependencies and a clean bootstrap; its adopted epic contract defines acceptance and verification. This policy also applies to later feasibility and production PIO work.

## Non-goals

- No code implementation, hardware ordering or fabricated readiness evidence as part of creating this package.
- No electrical, pin-mapping or routing changes; no HDF/RDB expansion or reopening accepted broker/media work without a demonstrated regression or separate scope decision.
- No premature register map, mailbox layout, RP2350 task/core/PIO architecture, bridge-to-ESP protocol, queue depth, timing value or numerical performance target.
- No new plugin/runtime-backend framework, duplicate service stack or automatic physical failover.

## Success signal

The native software path passes real-service and Amiga guest parity without SLIP or serial setup; its accepted packet contract and measured physical feasibility enable an agreed ABI. A subsequent Zorro-only installation passes existing application/media behavior and reviewed physical fault recovery, with reproducible installation and measured performance. A software-only pass never closes the physical readiness gate.

## Open Questions

- At 1.4–1.6: resolved at the software boundary by the [2026-09-15 acceptance record](stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#technical-acceptance-record--2026-09-15): explicit packet outcomes, backend quarantine and independent quiescence proof contain ambiguous completion through unchanged callers. Known-completion application replay remains documented existing policy. Physical realization of the proof remains Epic 2 work; an incompatible later adapter still requires scope review.
- At 1.9: which verified guest/host test facility will connect the real Amiga tool/backend to real core services?
- At 2.1–2.4: which verified toolchain, PIO/link capabilities and evidence-backed physical ABI satisfy the accepted packet contract? These remain deliberately unresolved until their gates.
- After 2.4: does 3.2 require smaller implementation slices? Runtime tuning and throughput claims remain dependent on measured hardware data.
