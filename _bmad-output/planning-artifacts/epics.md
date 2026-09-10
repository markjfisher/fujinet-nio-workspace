---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
inputDocuments:
  - backlog/amiga-faster-backends.md
  - backlog/nio-broker.md
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - _bmad-output/planning-artifacts/architecture/architecture-fujinet-nio-workspace-2026-08-22/ARCHITECTURE-SPINE.md
  - _bmad-output/completed-specs/spec-fujibus-slip-separation/backlog-fujibus-slip-separation.md
  - _bmad-output/completed-specs/spec-fujibus-slip-separation/brownfield.md
  - repos/fujinet-nio/docs/context_bootstrap.md
status: story-design-in-progress
requirementsConfirmed: 2026-09-11
epicStructureApproved: 2026-09-11
feature: amiga-zorro-ii-packet-native-backend
updated: 2026-09-11
---

# fujinet-nio-workspace - Epic Breakdown

## Overview

Planning-only input for a future Amiga Zorro-II packet-native backend, using an RP2350B bridge to ESP32-S3. The corrected requirements and three-epic structure were approved on 2026-09-11, including the ABI sign-off dependency below. Individual stories are being designed and reviewed sequentially under the existing BMAD workflow. This is not yet a complete implementation plan.

The user's detailed planning request and `backlog/amiga-faster-backends.md` supply feature requirements; no separate feature PRD was supplied. Existing broker architecture supplies the brownfield constraints. Completed specs are historical evidence, not instructions to repeat completed work. Sources under `_bmad-output/archive/` are excluded. Actual code takes precedence where a historical description no longer matches implementation; discrepancies below must be resolved explicitly, not silently interpreted as implemented capabilities.

No code, electrical design, routing, pin mapping, or hardware ABI changes are authorized by this planning task.

User corrections (2026-09-11) take precedence over inherited architecture constraints for this feature: preserve observable ordering and ownership initially without permanently mandating a single-worker FIFO implementation; allow future internal queueing, but prohibit multiple remotely in-flight exchanges until a future design adds safe correlation. A Zorro installation uses only its Zorro backend, with no assumed serial backend, runtime fallback, or automatic physical transport failover. Serial remains a separate-deployment compatibility/test baseline only.

## Requirements Inventory

### Functional Requirements

FR1: Preserve existing FujiBus device IDs, commands, parameter widths, payloads, packet length/checksum rules, status mapping, and higher-level service/device behavior across serial and native backends.

FR2: Preserve the Amiga broker exchange ABI, caller-owned buffers, reply ownership, and distinct Exec/FN error domains. Initially preserve observable ordering and ownership, without permanently freezing the existing single-worker FIFO implementation; future internal queueing is allowed. Because FujiBus currently has no on-wire correlation identifier, permit at most one remotely in-flight exchange and prohibit multiple remotely in-flight exchanges unless a future design adds safe correlation. Applications, the Amiga library transport shim, and `fujinet-disk.device` must not acquire physical-backend knowledge.

FR3: Implement the future Amiga backend behind the existing internal `backend_open`, `backend_close`, and `backend_exchange` contract. Separate binaries may serve different hardware deployments; install the appropriate implementation as `fujinet-nio.device`. A running Zorro installation uses only the Zorro backend: no RS-232 backend is assumed present, no dynamic switch to serial or runtime fallback is provided, and no automatic physical transport failover is permitted. Do not introduce a loadable backend/plugin ABI or runtime selection framework.

FR4: Provide a genuinely SLIP-free FujiBus path on the C++ side while retaining `FujiBusTransport` and its existing request/response mapping. Separate raw FujiBus encoding/decoding from SLIP where the actual codec still combines them; preserve existing serial wire behavior and audit affected callers.

FR5: Establish explicit whole-packet delivery, buffer ownership, capacity limits, truncation handling, and reset behavior for the native path. Do not infer packet boundaries from a byte-channel read or poll interval. Reuse `IFramer` where sufficient; justify any narrower packet-I/O addition against demonstrated gaps in `Channel`.

FR6: Provide pre-hardware test doubles that control packet delivery and failures while exercising production codecs, transports, broker logic, and real service handlers. A canned-response backend alone is not service-parity evidence.

FR7: Test deterministic file-list, disk-read, disk-write, and clock behavior through serial-framed and native paths in separate backend test configurations, comparing decoded semantics and persistent effects. Include literal protocol vectors independent of the implementation under test, embedded SLIP-reserved bytes, boundary sizes, multiple locally queued requests, and delayed delivery. Queued-request tests must verify serialized remote execution with at most one remotely in-flight exchange; local queueing does not authorize concurrent in-flight FujiBus requests. Framer packet-boundary tests do not imply permission for remote concurrency.

FR8: Extend `fujinet-nio-exchange` to exercise the native backend without requiring serial baud/device controls. Preserve the existing meaning and compatibility of `--backend cold|warm`; explicitly distinguish lifecycle scenarios from physical backend installation. Keep serial provocation diagnostics separate from ordinary native parity operations.

FR9: Cover failed open, timeout, malformed packet/checksum, oversize/truncation, unavailable peer, stale/late response, queued and in-progress abort, and reopen/reset behavior without hardware where possible. Show what a simulated failure proves and what still requires hardware evidence.

FR10: Preserve standard DD/HD ADF support, independent multi-drive mappings, Slot Catalog behavior, writable-media policy, mount/eject/replacement/restoration, and change notifications. Do not reopen accepted DiskDevice Phase 2, broker cut-over, or idle-close removal work, or introduce HDF/RDB support.

FR11: Keep the bridge's minimum logical responsibility to transferring complete opaque FujiBus packets between the Amiga backend and ESP32-S3, with bounded ownership, readiness, failure, and reset behavior. Keep service interpretation on the existing service side; specify no register addresses, mailbox layouts, firmware task architecture, or RP2350-to-ESP link protocol now.

FR12: Recommend a bridge firmware project location within the existing workspace, preferably owned by `repos/fujinet-nio`, based on its build/platform layout. Identify reusable protocol definitions and test fixtures; do not assume the external FujiNet firmware repository is checked out or required.

FR13: Separate software-only delivery from hardware-gated delivery. A mock, host integration pass, or firmware skeleton must never be reported as validating Zorro bus timing, PIO feasibility, RP2350B operation, or the ESP physical link.

FR14: Gate hardware ABI definition on agreed requirements and RP2350 PIO feasibility evidence. Hardware packet ABI finalization and approval also require Epic 1's accepted canonical raw FujiBus packet representation, packet-boundary semantics, ownership rules, and relevant failure behavior. Project setup and hardware/PIO feasibility may proceed independently in parallel with Epic 1; ABI sign-off may not precede that accepted software contract. Gate real Zorro access and integration on the agreed ABI and suitable hardware. Keep timing, throughput, buffering, interrupts/polling, and physical-link choices unresolved until their evidence exists.

FR15: Document installation, compatibility, recovery limitations, and measured performance before production readiness. Reuse existing integration assertions across separate backend deployments; record throughput/latency and recovery outcomes rather than inventing performance targets.

FR16: Decompose the confirmed design into small, dependency-ordered, independently reviewable and testable stories. Each must name objective, scope, likely owning files/modules, dependencies, acceptance criteria, hardware requirement, and risks/unknowns. Recommend the lowest-risk/highest-value first story.

### NonFunctional Requirements

NFR1: No changes to FujiBus semantics or electrical mapping/routing; no speculative hardware ABI or bridge-link protocol disguised as a software prerequisite.

NFR2: Minimize new abstractions and cross-repository changes. The existing Amiga backend contract is the default seam; the existing C++ transport/framer split is retained and corrected only where required for native packets.

NFR3: Bound memory use and work per exchange/poll. Test packet and response capacities against existing platform limits; do not equate SLIP-expanded size, raw packet size, and a future hardware transfer capacity.

NFR4: Preserve one reply per request, deterministic ownership, and existing abort semantics. Abort is not remote rollback. Do not promise exactly-once remote execution or introduce automatic retries that could duplicate writes after an ambiguous completion. Local timeout or abort alone does not prove remote completion; recovery must not allow a late response to be assigned to a subsequent exchange. FR2's remote-concurrency restriction and FR3's prohibition on physical transport failover apply independently of retry safety.

NFR5: Keep serial a compatibility/test baseline in its own backend deployment, with byte-exact codec regression tests and focused integration parity; it is not a dependency of a Zorro installation. Preserve the accepted ESP32 consolidated profile implementation unless a concrete new build requirement warrants changing it.

NFR6: Tests must use controlled clocks, fixtures, and fault schedules rather than wall-clock sleeps or mock implementations of the service logic. Disk-write tests must use disposable media and verify resulting bytes/read-back; clock tests must control time or compare appropriate semantic bounds.

NFR7: No hardware performance or safety claim may be inferred from a host mock. Report confidence, evidence, and remaining gates separately.

NFR8: Follow `docs/agent-test-policy.md`: cheapest sufficient verification in each changed owner; complete `make check` if future work changes `fujinet-nio-lib`; targeted guest tests when guest-visible behavior changes. No code builds are needed for this planning-only artifact.

NFR9: Cite concrete repository paths and symbols for major architectural claims, and distinguish existing behavior, recommended changes, historical intent, and deferred decisions.

### Additional Requirements

#### Code-grounded architecture constraints

All paths below are workspace-relative. These are evidence for requirements extraction, not proposed hardware interfaces.

| Concern | Current evidence and planning consequence |
| --- | --- |
| Amiga entry point | `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c`: `fn_transport_exchange_buffers` submits opaque request bytes using `FUJINET_NIO_CMD_EXCHANGE`, with a caller-task message port and local exchange request. It does not operate serial or SLIP. Preserve this seam. |
| Broker backend | `repos/fujinet-nio-driver/amiga/include/fujinet_nio_backend.h`: `backend_open`, `backend_close`, `backend_exchange`, and serial control functions. `amiga/nio.device/fujinet_nio_device.c`: `device_init` binds callbacks; `process_exchange` invokes the backend and closes on transport/timeout failure; the next request can lazy-open. Native tests can inject callbacks through `fujinet_nio_native_test_set_backend`. No service-specific backend is needed. |
| Backend packaging | Broker architecture spine AD-11 and `backlog/nio-broker.md`, Stage 5, adopt separate binaries with identical public ABI. Physical selection is installation/build selection, not an application-level switch. Per the user's correction, a running Zorro deployment has only its Zorro backend, with no assumed serial backend or physical transport failover. |
| Queueing versus remote concurrency | The existing broker's single-worker FIFO is current implementation, not a permanent architectural requirement for this feature. FR2 preserves observable ordering/ownership initially while allowing future internal queueing. FujiBus lacks on-wire correlation, so remote execution remains serialized until a future design adds safe correlation. |
| Actual public ABI | `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h`: `FujiNetNIORequest` now has SET/GET_BAUD and SET/GET_SERIAL commands alongside EXCHANGE; `fn_flags` and `fn_pad` must be zero on submission but carry reply diagnostics. Older architecture text saying only EXCHANGE/reserved fields must not overwrite this current contract. Define unsupported serial controls for native builds without relabeling serial diagnostic bits as invented Zorro status. |
| Amiga serial ownership | `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c`: `backend_open` opens serial/timer devices and initializes `fn_stream_session`; `backend_exchange` calls `fn_stream_session_request`. `repos/fujinet-nio-lib/include/fn_session.h` explicitly describes a byte-oriented SLIP session. Do not force native packets through it merely because the faster-backends backlog says “shared session interface.” |
| C++ composition | `repos/fujinet-nio/src/lib/bootstrap.cpp`: `setup_transports` selects `SlipFramer` or `NativeFramer` from `TransportKind`, then constructs `FujiBusTransport`. `include/fujinet/io/transport/transport.h`: `ITransport` is the service-facing transport contract. No new service-facing Zorro transport hierarchy is required. |
| C++ FujiBus mapping | `repos/fujinet-nio/src/lib/fujibus_transport.cpp`: `receive`, `send`, and `receiveResponse` map device/command/params/payload and response status through `FujiBusPacket`. Response IDs are synthetic, explicitly without on-wire correlation. Stale-response and ambiguous-write recovery cannot assume a transaction identifier exists. |
| Critical codec discrepancy | `repos/fujinet-nio/src/lib/fuji_bus_packet.cpp`: `serialize` still calls `encodeSLIP`; `parse` requires SLIP delimiters and calls `decodeSLIP`; `fromSerialized` invokes `parse`. `src/lib/slip_framer.cpp`: `nextPacket` returns delimiters too; `sendPacket` writes already-encoded bytes verbatim. The completed spec proves structural extraction, not a raw-packet codec contract. Simply selecting `NativeFramer` does NOT bypass SLIP today. A focused compatibility-preserving codec prerequisite is required. |
| Critical boundary discrepancy | `repos/fujinet-nio/include/fujinet/io/core/channel.h`: `Channel::read` returns bytes, not packet metadata, and `write` has no result. `src/lib/native_framer.cpp`: `poll` accumulates every available read and `nextPacket` returns the entire buffer. Multiple packets can merge even within one poll. `src/lib/build_profile/zorro.cpp` selects `FujiBusNative` with a PTY placeholder. Neither is working Zorro support. |
| Higher-layer isolation | `repos/fujinet-nio/include/fujinet/io/transport/io_service.h`: `IOService` pumps requests through `IRequestHandler` and replies using the originating transport. `include/fujinet/io/devices/disk_device.h`: `DiskDevice::handle` accepts `IORequest` and owns `disk::DiskService`, not a physical channel. Keep backend concerns below these contracts; trace the remaining service/client implementations during design. |
| Exchange-tool meaning | `repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.h`: backend enum is COLD/WARM. `fujinet_nio_exchange_opts.c`: validation/plan generation requires serial-oriented setup for current disk provocation. `fujinet-nio-exchange.c`: `run_disk_provocation` sets baud, then drives the resident disk device using CMD_READ/CMD_WRITE. This is not an existing generic physical-backend selector or safe ordinary parity command. |
| Existing test footholds | `repos/fujinet-nio/tests/test_native_framer.cpp` tests single-buffer pass-through only. `tests/test_fujibus_transport_framing.cpp` supplies a byte loopback and framer spy but creates fixtures using the production serializer. Extend coverage with independently specified raw and SLIP vectors; matching producer/consumer bugs must not be the only oracle. Broker-native callback injection tests and real service protocol tests provide distinct levels of evidence. |

#### Intended logical path (requirement, not current native implementation)

```text
Amiga apps / fujinet-disk.device
  -> existing fujinet-nio-lib FujiBus packet construction
  -> existing Amiga fn_transport shim and fujinet-nio.device broker
  -> packet-native backend implementing backend_exchange
  -> future RP2350B bridge (opaque complete packets)
  -> future ESP32-S3 link adapter / native framer
  -> existing FujiBusTransport mapping and existing services/devices
```

Native link traffic must carry raw FujiBus packets without SLIP wrapping. Separate serial deployments continue to use SLIP at their framing boundaries; they are not a fallback path for this installation. The broker may queue requests locally but must serialize remote execution under FR2. The raw packet codec prerequisite and explicit packet-boundary handling must exist before this path can be called native. Test-only in-memory packet delivery is not a proposed physical mailbox or ESP link protocol.

#### Evidence and decisions still needed for design

- Trace remaining Amiga packet/client and resident DiskDevice call paths, C++ platform factories and service dispatch, shared protocol/header ownership, build/test entry points, and bridge project placement before finalizing affected-file lists.
- Specify software packet ownership and fault semantics without selecting hardware register widths, endianness of register access, FIFO/mailbox depth, doorbells, interrupt wiring, DMA, PIO programs, clocks, or physical transport.
- Defer register/mailbox ABI until agreement and feasibility evidence; defer PIO allocation and firmware concurrency model until RP2350 evidence; defer actual access/reset behavior until suitable hardware; defer throughput and queue optimization until measurement.
- Multiple remotely in-flight exchanges require a future safe-correlation design; internal queueing changes or throughput measurements alone cannot authorize them. No correlation identifier or protocol change is defined by this plan.
- Keep mock broker tests, C++ native framing tests, real-service parity, Amiga guest exchange integration, and physical hardware integration as separate evidence gates.
- External legacy FujiNet Pico code has not been used for these conclusions. It may be consulted later as explicitly labeled reference material only; it is not current-project behavior or a required workspace dependency.
- No greenfield starter template or UI design contract is required. A future bridge skeleton is a separately owned build deliverable, not a reason to restructure existing firmware.

### UX Design Requirements

Not applicable: no graphical UI change. Exchange CLI compatibility, installation, and diagnostics are covered by FR8 and FR15.

### FR Coverage Map

FR1: Epic 1 — prove packet/service compatibility in software; Epic 3 — validate it on the physical path.

FR2: Epic 1 — preserve observable ordering, ownership, and errors with serialized remote execution; Epic 3 — verify those properties on hardware.

FR3: Epic 1 — exercise the existing backend seam using an explicitly test-only binary; Epic 3 — deliver the real Zorro-only backend binary without fallback.

FR4: Epic 1 — provide raw FujiBus codec/framer composition while preserving serial wire behavior.

FR5: Epic 1 — establish and test software packet-boundary/ownership semantics; Epic 2 — constrain the hardware contract from evidence; Epic 3 — implement and validate it.

FR6: Epic 1 — production-code-driven mocks and deterministic integration harnesses.

FR7: Epic 1 — file-list, disk-read, disk-write, and clock parity across separate software configurations; Epic 3 — repeat parity on real hardware.

FR8: Epic 1 — exchange-tool native test path without serial controls; Epic 3 — exercise the installed physical backend.

FR9: Epic 1 — deterministic software fault/recovery coverage; Epic 2 — establish feasible reset/ownership guarantees; Epic 3 — physical fault/recovery validation.

FR10: Epic 1 — preserve and exercise established device/service behavior in software; Epic 3 — validate the same media/catalogue/multi-drive contracts on hardware.

FR11: Epic 2 — establish the minimal bridge responsibility boundary without prematurely choosing a physical ABI; Epic 3 — implement the agreed boundary without moving services into the bridge.

FR12: Epic 2 — bridge project placement, isolated skeleton, and protocol/header/fixture reuse.

FR13: Epics 1–3 — maintain separate software-only, feasibility, and physical integration evidence gates.

FR14: Epic 2 — feasibility and ABI approval gates; Epic 3 — consume those gates before real hardware access and integration.

FR15: Epic 3 — installation, compatibility, recovery limitations, and measured performance for production readiness.

FR16: Epics 1–3 — planning obligation: subsequently decompose each epic into small, ordered stories with the requested fields. This is not a standalone implementation feature.

## Epic List

Approved structure, including the user's ABI sign-off clarification. Each epic delivers a usable outcome without depending on a later epic. The split follows evidence/risk boundaries, not source-code layers. All NFRs apply where relevant; no epic may relax the single-remotely-in-flight rule or introduce physical transport failover.

### Epic 1: Developers can prove native FujiBus service parity before hardware exists

Developers can run a genuine SLIP-free packet path through production FujiBus code and real service handlers, and exercise the Amiga broker/exchange path using a clearly test-only backend. Separate serial configurations remain regression/parity references, not a dependency or fallback within a native installation.

**FRs covered:** FR1, FR2, FR3 (test deployment/seam), FR4, FR5 (software contract), FR6, FR7, FR8, FR9 (software faults), FR10 (software parity), FR13, FR16.

**Dependencies:** Existing accepted broker and service contracts only; no dependency on Epic 2 or Epic 3.

**Hardware required:** No Zorro, RP2350B, or ESP32-S3 hardware. Amiga guest execution requires the existing emulator/toolchain environment; host-only tests cannot substitute for evidence that the actual Amiga tool drives its backend.

**Implementation notes and likely owners:**

- Keep the necessary C++ raw codec separation, packet-boundary work, production-code-driven test transport, and service-parity tests together in `repos/fujinet-nio`. Principal existing seams are `FujiBusPacket`, `IFramer`, `NativeFramer`, `FujiBusTransport`, and profile/bootstrap composition. Do not repeat the completed structural SLIP extraction or split ESP32 profile files as unrelated prerequisites.
- In `repos/fujinet-nio-driver`, reuse the internal broker backend contract and native callback test harness; make only the narrowly justified build/composition adjustments needed to bind a test backend. Extend exchange-tool operation planning so native tests do not require serial controls. Do not introduce a backend plugin ABI or runtime physical selector.
- Keep the Amiga library and resident disk service consumers unchanged unless an actual incompatibility is demonstrated. Workspace guest integration owns cross-repository evidence; repository tests own codec/framing and broker behavior independently.
- Use complete-packet fixtures and scheduled delivery/fault injection, not service-response reimplementations. A test connection between the Amiga guest and the real POSIX service instance is a test harness choice, not the future RP2350-to-ESP protocol. Its concrete mechanism must be selected from existing harness facilities during story design.
- Test-only packet adaptation may supply boundaries; it must not infer datagrams from arbitrary byte reads. Prefer the existing `IFramer` seam; add packet-I/O surface only where explicit boundary/error requirements demonstrate that `Channel` is insufficient.

**Epic acceptance boundary:** Independent raw/SLIP vectors prove unchanged FujiBus semantics and unchanged serial bytes; the native production path transmits no SLIP wrapping. Real-service tests cover file-list, disposable-media disk read/write with read-back, and controlled clock behavior. Broker tests show local queue ordering/ownership and at most one remotely in-flight exchange, including timeout/abort/late-response cases. The actual exchange tool exercises the native test backend without serial setup. Software media/catalogue/multi-drive checks retain existing assertions. No hardware readiness claim results.

**Risks/unknowns:** Residual SLIP coupling in codec callers, absence of packet metadata and send results in `Channel`, guest-to-host harness integration, current serial-specific exchange controls/diagnostics, and recovery without on-wire correlation. Resolve these through focused software contracts and tests, not speculative hardware fields.

### Epic 2: Bridge developers can make an evidence-backed feasibility and ABI decision

Bridge developers obtain an isolated, reproducible project starting point and decision-grade evidence about whether RP2350B can support the required Zorro-II packet bridge. The outcome is an explicit proceed/hold decision; an agreed hardware ABI becomes an implementation contract only after both positive feasibility evidence and acceptance of Epic 1's canonical software packet contract.

**FRs covered:** FR5 (hardware contract constraints), FR9 (recovery feasibility), FR11, FR12, FR13, FR14, FR16.

**Dependencies:** Project setup and RP2350/Zorro hardware/PIO feasibility work may begin independently and run in parallel with Epic 1; they do not require Epic 1 completion. Hardware packet ABI finalization and approval, however, must wait until Epic 1 has established the accepted canonical raw FujiBus packet representation, packet-boundary semantics, ownership rules, and relevant failure behavior. Positive feasibility evidence alone is insufficient for ABI sign-off. This dependency is on acceptance of that complete software contract, not on completion of unrelated remaining Epic 1 tooling/parity work. Any discrepancy between feasibility constraints and the accepted contract requires explicit resolution before ABI approval, not silent changes to FujiBus semantics.

**Hardware required:** Not for repository placement, dependency boundaries, or a compile-only skeleton. Suitable RP2350B/Zorro test hardware and instrumentation are required for physical timing/PIO/ownership evidence. A successful build or simulation alone does not meet that gate. A fully working production card is not a prerequisite for a feasibility experiment, but the evidence must state exactly which bus conditions were exercised.

**Implementation notes and likely owners:**

- Prefer `repos/fujinet-nio` as bridge firmware owner, with an isolated build boundary so existing POSIX/ESP targets do not acquire Pico SDK dependencies. Final subdirectory and reusable protocol/header locations require the remaining repository-structure inspection before story-level specification; no new directory is created by this plan.
- The minimum boundary assigns Amiga-side request ownership and broker error reporting to the Amiga backend, opaque packet transfer/readiness/reset handling to the bridge, and FujiBus parsing/dispatch plus service semantics to ESP32-S3. It does not choose firmware tasks/cores, bus registers, mailbox layout, or the ESP physical link now.
- Feasibility work must expose what can be guaranteed about transfer completion, capacity, backpressure, reset, and stale data. Register/mailbox and bridge-link decisions follow evidence and explicit agreement; no mock framing convention becomes the physical ABI by default.
- The external legacy Pico implementation may be a labeled reference only. Do not assume an external firmware checkout, import its service architecture as current behavior, or use it as proof of RP2350B/Zorro feasibility.

**Epic acceptance boundary:** Project setup and the feasibility verdict are independently reviewable outcomes: the bridge project builds without disturbing existing targets, and hardware/PIO evidence states its limitations. A positive feasibility verdict may be recorded while Epic 1 is still underway, but it does not approve the ABI. ABI finalization/sign-off requires both positive feasibility evidence and a cited acceptance record from Epic 1 covering the canonical raw FujiBus packet representation, packet-boundary semantics, ownership rules, and relevant failure behavior. The agreed ABI must satisfy that contract, serialized remote execution, and safe reset/recovery. Until both prerequisites and explicit ABI approval exist, Epic 3 remains blocked. A feasibility hold records unresolved conditions and cannot be treated as acceptance of an ABI or production implementation.

**Risks/unknowns:** PIO resources and response timing, electrical/bus access constraints, supported transfer sizes, packet storage, the RP2350-to-ESP transport, reset across both endpoints, toolchain placement, and instrumentation availability. This epic cannot alter electrical routing or pin mapping under the current scope; any required hardware change needs separate authority.

### Epic 3: Amiga users can operate a validated Zorro-only FujiNet installation

Amiga users can install the Zorro-backed `fujinet-nio.device` and use existing applications, services, and disk workflows with validated compatibility, documented recovery behavior, and measured performance. The installation uses only Zorro and never switches to an assumed serial backend.

**FRs covered:** FR1, FR2, FR3 (physical implementation/deployment), FR5 (physical transfer), FR7 (hardware parity), FR8 (physical exchange path), FR9 (hardware recovery), FR10, FR11 (agreed bridge implementation), FR13, FR14, FR15, FR16.

**Dependencies:** Epic 1's accepted software path/tests and Epic 2's positive feasibility evidence plus agreed ABI. Actual access also requires suitable working hardware. No placeholder ABI or mock-only pass satisfies these dependencies.

**Hardware required:** Yes: working Zorro-II hardware, RP2350B bridge, ESP32-S3 endpoint, and appropriate measurement facilities.

**Implementation notes and likely owners:**

- Implement real Amiga access in the driver repository behind `backend_open`/`backend_close`/`backend_exchange`, retaining public exchange behavior and Zorro-only deployment. Future internal queueing is allowed, but multiple remotely in-flight exchanges remain prohibited without a separately approved safe-correlation design.
- Implement bridge firmware in the Epic 2 owning project and the corresponding ESP platform link adapter in `repos/fujinet-nio`. Reuse the Epic 1 raw FujiBus/framer path and existing service dispatch. Hardware details enter only from the agreed contract.
- Reuse repository tests and workspace Amiga integration assertions across separately deployed serial-reference and Zorro configurations. Do not embed serial failover, new service formats, or media-support expansion in integration work.
- Collect measurements only after correctness is established. State workloads, fixture sizes, hardware/firmware versions, errors, and measurement conditions; make no unmeasured speed claim or invented numeric target.

**Epic acceptance boundary:** The installed Zorro backend passes existing service/media/catalogue/multi-drive/change-notification assertions and file-list/disk-read/disk-write/clock parity checks on the real path. Explicit physical fault tests substantiate documented recovery limits and absence of stale-response misattribution or unsafe replay after ambiguous writes. Installation is reproducible, serial controls are not required, and measured throughput/latency plus compatibility limitations are recorded. Unresolved physical correctness or recovery risks keep production readiness blocked.

**Risks/unknowns:** Hardware availability, real bus timing versus feasibility fixtures, cross-endpoint reset behavior, capacity/backpressure under load, write-completion ambiguity, and guest/hardware test observability. Performance results may motivate later queue optimization but cannot waive correlation safety or introduce failover.

#### Dependency and overlap review

Epic 1 delivers software validation independently. Epic 2 project setup and RP2350/Zorro feasibility may begin independently and run in parallel with Epic 1. Epic 2 hardware packet ABI sign-off must wait for both positive hardware/PIO feasibility evidence and Epic 1's accepted canonical raw packet representation, packet-boundary semantics, ownership rules, and relevant failure behavior. It need not wait for unrelated remaining Epic 1 tooling/parity work, but neither a skeleton nor feasibility evidence alone can authorize ABI approval. Epic 3 consumes Epic 1's accepted software path/tests and Epic 2's approved, feasible hardware contract. Within each epic, story design must order prerequisites before their consumers; no story may require a future story merely to be testable.

Codec/framer/mock/tool/parity changes are consolidated in Epic 1 rather than split into overlapping technical-layer epics. Epic 3 necessarily revisits composition and test entry points to replace simulated I/O with physical I/O, but that split is justified by hardware feedback and separate acceptance evidence. Epic 2's bridge project becomes Epic 3's implementation owner; it does not create a competing protocol or duplicate service stack.

FR16 is satisfied by the subsequent BMAD story-design output, not by claiming these epic descriptions are implementation-ready stories. The template below is retained until individual stories are reviewed and approved in sequence. Story review starts with Epic 1; an explicit software packet-contract acceptance checkpoint will supply Epic 2's ABI sign-off dependency.

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic {{N}}: {{epic_title_N}}

{{epic_goal_N}}

<!-- Repeat for each story (M = 1, 2, 3...) within epic N -->

### Story {{N}}.{{M}}: {{story_title_N_M}}

As a {{user_type}},
I want {{capability}},
So that {{value_benefit}}.

**Acceptance Criteria:**

<!-- for each AC on this story -->

**Given** {{precondition}}
**When** {{action}}
**Then** {{expected_outcome}}
**And** {{additional_criteria}}

<!-- End story repeat -->
