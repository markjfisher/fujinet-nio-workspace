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
  - repos/fujinet-nio/docs/protocol_reference.md
status: story-set-review
storyReviewMode: complete-set-at-user-request
requirementsConfirmed: 2026-09-11
epicStructureApproved: 2026-09-11
feature: amiga-zorro-ii-packet-native-backend
updated: 2026-09-11
---

# fujinet-nio-workspace - Epic Breakdown

## Overview

Planning-only input for a future Amiga Zorro-II packet-native backend, using an RP2350B bridge to ESP32-S3. The corrected requirements and three-epic structure were approved on 2026-09-11, including the ABI sign-off dependency below. At the user's request, all stories are drafted together for review, overriding per-story/per-epic review pauses while retaining the existing BMAD structure. Stories are proposed, not implemented or individually accepted. Hardware-gated stories are bounded planning envelopes: they require the named evidence before implementation details can be finalized.

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

- Use the supplemental code evidence and ownership recommendations below when refining implementation tasks. Recheck affected code at story execution; do not treat directory names as proof of physical transport ownership.
- Specify software packet ownership and fault semantics without selecting hardware register widths, endianness of register access, FIFO/mailbox depth, doorbells, interrupt wiring, DMA, PIO programs, clocks, or physical transport.
- Defer register/mailbox ABI until agreement and feasibility evidence; defer PIO allocation and firmware concurrency model until RP2350 evidence; defer actual access/reset behavior until suitable hardware; defer throughput and queue optimization until measurement.
- Multiple remotely in-flight exchanges require a future safe-correlation design; internal queueing changes or throughput measurements alone cannot authorize them. No correlation identifier or protocol change is defined by this plan.
- Keep mock broker tests, C++ native framing tests, real-service parity, Amiga guest exchange integration, and physical hardware integration as separate evidence gates.
- External legacy FujiNet Pico code has not been used for these conclusions. It may be consulted later as explicitly labeled reference material only; it is not current-project behavior or a required workspace dependency.
- No greenfield starter template or UI design contract is required. A future bridge skeleton is a separately owned build deliverable, not a reason to restructure existing firmware.

#### Supplemental implementation evidence

- **Raw packets already exist on the Amiga side.** `repos/fujinet-nio-lib/src/common/fn_raw.c`, `fn_raw_call`, builds a header, payload, and checksum before `fn_transport_exchange`. `src/common/fn_disk.c`, `context_disk_call`, independently builds raw requests and invokes the context's exchange callback; `context_parse_response` checks device, command, length, and checksum. Neither requires SLIP at this boundary. Reuse `include/fn_protocol.h`, `include/fn_raw.h`, and the existing context/public declarations in `include/fujinet-nio.h`; no second Amiga packet format is needed.
- **The resident disk adapter is not a serial owner.** `repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c`, `nio_transport`, calls `fn_transport_exchange_buffers`; `fujinet_nio_disk_context_init` binds `nio_exchange` into the disk context. Its historical directory name does not justify moving it or adding Zorro branches to disk code. `amiga/Makefile` builds this adapter into the disk device but links the broker separately using `NIO_OBJECTS`, currently including the serial backend and `fn_session`/`fn_slip` objects.
- **Existing retry behavior is a real constraint.** `repos/fujinet-nio-driver/common/fujinet_disk_retry.c`, `is_retryable_sector_request` and `fujinet_disk_retry_exchange`, retry qualifying 512-byte sector reads AND writes on transport/timeout errors. `repos/fujinet-nio-lib/src/common/fn_raw.c`, `fn_raw_call`, can replay a failed call once except on timeout. Therefore “the native backend does not retry” is insufficient proof of no unsafe replay. Story 1.5 must exercise actual callers and require safe containment; any incompatibility needing changed higher-layer semantics is an explicit scope decision, not permission to silently rewrite accepted retry policy.
- **C++ dispatch remains transport-neutral.** `repos/fujinet-nio/src/lib/fujinet_core.cpp`, `FujinetCore::tick`, pumps `IOService::serviceOnce`; `src/lib/io_service.cpp` receives, calls `IRequestHandler::handleRequest`, and sends on the same transport. `src/lib/routing_manager.cpp`, `RoutingManager::handleRequest`, delegates to `IODeviceManager::handleRequest` in `src/lib/io_device_manager.cpp`, which invokes the registered `VirtualDevice::handle`. `DiskDevice`, `FileDevice`, and `ClockDevice` in their corresponding `src/lib/*_device.cpp` consume `IORequest`, not backend selection. Preserve storage, catalogue, mount persistence, and service payload behavior here.
- **Selection lives at composition/build boundaries.** `repos/fujinet-nio/include/fujinet/build/profile.h` defines separate `TransportKind` and `ChannelKind`; neither currently supplies a physical Zorro channel. `src/platform/posix/channel_factory.cpp` and `src/platform/esp32/channel_factory.cpp`, `create_channel_for_profile`, select OS/hardware channels. `src/lib/bootstrap.cpp`, `setup_transports`, selects framing. The Amiga broker is instead linked from a chosen backend object set. These are different mechanisms; the exchange tool does not select the ESP profile or dynamically switch the Amiga physical backend.
- **Reusable protocol sources are already split by language.** `repos/fujinet-nio/docs/protocol_reference.md` defines a six-byte header with little-endian length, descriptors/params/payload and folded checksum. `src/lib/fuji_bus_packet.cpp` currently keeps `FujiBusHeader` private and copies its native representation; preserve wire endianness explicitly during codec work rather than exporting that C++ struct as a hardware ABI. Reuse `include/fujinet/io/protocol/fuji_bus_packet.h`, `wire_device_ids.h`, and existing device codecs on the ESP side. `py/fujinet_tools/fujibus.py`, `build_fuji_packet_decoded`, supplies a separate-language raw encoder, and `build_fuji_packet` adds SLIP. It is useful cross-check evidence, not the sole oracle for literal fixtures. The RP2350 bridge need not parse service IDs or link either service library just to move opaque packets.
- **Test facilities are available, but native guest I/O is not established.** `repos/fujinet-nio/tests/test_embed_core.cpp` demonstrates an embedded production core with an in-memory byte channel and echo endpoint; it is a composition exemplar, not real-service parity evidence. `tests/test_disk_device_protocol.cpp`, `test_file_device_protocol.cpp`, `test_clock_device.cpp`, and `test_slot_catalog_service.cpp` provide service fixtures. The clock implementation calls `platform::unix_time_seconds` and related functions; use an isolated test-time provider, not privileged host clock changes. `FileDevice` has a process-global directory cache: isolate fixture instances/processes or URIs so one backend cannot warm the other's expected result. `integration-tests/amiberry/conftest.py`, `run_amiga_case`, already builds disposable images, injects a selected broker binary, and collects evidence, but its serial/socket machinery does not itself provide a native packet channel. Stories 1.9–1.10 must supply and test that missing connection explicitly.

#### Minimal extension and responsibility boundary

The **Amiga extension** is the current internal `backend_open`/`backend_close`/`backend_exchange` interface. Keep the public `FujiNetNIORequest` layout, opaque buffers, and caller-facing service APIs. Native build composition must omit serial framing objects and make serial-only controls explicitly unsupported; do not encode a physical selector in reserved fields.

The **C++ extension** is `IFramer` under the existing `FujiBusTransport : ITransport`. First make its packet contract unambiguously raw. A test `IFramer` bound to an explicit packet queue can exercise production FujiBus handling without a new public abstraction. Real packet I/O must provide boundaries, capacity/truncation, and failure/reset information missing from `Channel`; Story 1.4 must select the smallest adapter/capability addition needed, not redesign `ITransport`, add a parallel FujiBus parser, or assume one byte read equals one packet. No concrete C++ packet-source signature is imposed by this plan.

| Owner | Required responsibility | Must not acquire |
| --- | --- | --- |
| Amiga backend | Transfer caller-owned raw request/response packets, serialize remote execution, respect capacities/deadlines, expose existing error domains, preserve safe recovery state across lifecycle operations | Service interpretation, automatic physical failover, invented transaction IDs |
| RP2350B bridge | Transfer complete opaque packets; implement agreed readiness, ownership, integrity/error reporting and reset guarantees once feasible | Disk/file/clock service implementation or an unapproved mailbox/ESP protocol |
| ESP32-S3 adapter | Connect the agreed bridge link to raw framing; bound I/O and handle transport faults without blocking the cooperative core indefinitely | Zorro details in services or SLIP on the native packet path |
| ESP/core services | Existing FujiBus validation/mapping and device/service behavior | Physical backend selection or bridge firmware policy |

#### Recommended repository placement

Use **`repos/fujinet-nio/bridges/rp2350-zorro/`** (proposed, not created) for the bridge's standalone build, README, bounded transport firmware, feasibility tests, and later PIO assets. Keep durable design notes in `repos/fujinet-nio/docs/` and cross-repository scope/acceptance in this workspace's BMAD/backlog locations. Amiga code stays in `repos/fujinet-nio-driver/amiga/nio.device/`; the ESP link adapter stays in `repos/fujinet-nio/src/platform/esp32/` with its matching platform header.

Reason: `repos/fujinet-nio/CMakeLists.txt` chooses ESP-IDF or POSIX, `src/CMakeLists.txt` is generated, and `scripts/update_cmake_sources.py`, `collect_cpp_files`/ESP filtering, recursively collect `src/` while excluding POSIX sources from ESP. A new `src/platform/rp2350/` would need build filtering before it was safe. An independent bridge directory avoids adding Pico SDK dependencies to existing builds. Pin the SDK/toolchain only in the future skeleton story after checking available supported tools; no version is invented here. Do not link the complete ESP firmware into RP2350 or copy protocol constants unnecessarily. Any shared C-friendly transport-only definitions should be extracted only when an actual consumer needs them; shared test vectors can establish compatibility without a new shared production-header project.

#### Pre-hardware test strategy and implementation verification

Use separate evidence levels: (1) literal raw/SLIP codec vectors; (2) explicit packet queues and fault schedules around production framing; (3) actual broker and retry callers with instrumented packet I/O; (4) real core/service parity on isolated storage/time fixtures; (5) the real Amiga exchange tool plus resident device in a guest connected to that core; (6) later physical integration. A scripted responder is acceptable for broker ownership tests, not as the file/disk/clock oracle. Service tests must observe decoded replies and effects on backing storage. Queue tests count locally queued requests and assert no more than one remotely in-flight exchange. Malformed packet injection is not authorization for concurrent live requests.

Future story verification commands below are **planned, not executed in this documentation task**. Source `scripts/env.sh` first in the workspace environment. Use the cheapest relevant gate, adding a focused target/node when the story introduces one:

- **V-CXX:** in `repos/fujinet-nio`, `./build.sh -cp fujibus-pty-debug`, then `ctest --test-dir build/fujibus-pty-debug -R '^fujinet-nio-tests$' --output-on-failure`. New test sources are discovered by `tests/CMakeLists.txt`; changed production source lists require `./scripts/update_cmake_sources.py` and template edits rather than hand-editing generated lists. Native-profile stories additionally build/test their new named target; its exact name is chosen when introduced.
- **V-BROKER:** in `repos/fujinet-nio-driver/amiga/tests`, `make build/test_fujinet_nio_device` then `./build/test_fujinet_nio_device`. **V-RETRY:** `make build/test_fujinet_nio_client_retry` then `./build/test_fujinet_nio_client_retry`. **V-OPTS:** `make build/test_fujinet_nio_exchange_opts` then `./build/test_fujinet_nio_exchange_opts`. New backend tests add a focused sibling target. These existing targets are defined in `amiga/tests/Makefile`.
- **V-AMIGA:** compile only the affected broker/tool targets in `repos/fujinet-nio-driver/amiga/Makefile` (existing exchange target: `make ../build/amiga/fujinet-nio-exchange`), plus one relevant Amiberry pytest node introduced/selected by the story. Use the documented `--run-amiga --amiga-env wb32 --amiga-machine a1200-030` guest baseline for software tests; physical Zorro validation must identify the actual suitable machine separately. Do not claim emulator results validate a Zorro slot.
- **V-PY:** for changes under firmware Python tooling run `./scripts/run-python-tests`; for workspace harness changes run its focused pytest tests. **V-LIB:** if implementation actually changes `repos/fujinet-nio-lib`, complete `make check` there; reading or linking the unchanged library is not a library edit.
- **V-HW:** after the relevant gate, run the owning bridge build, configured ESP build `./build.sh -b`, affected Amiga build, and the named instrumented hardware experiment. Hardware stories must record exact board/toolchain/firmware versions and commands before execution; absence of a defined hardware procedure means that story is not ready to implement. No fabricated hardware test command is supplied here.

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

- Use the proposed standalone `repos/fujinet-nio/bridges/rp2350-zorro/` project and reuse protocol sources/fixtures as described above. Existing POSIX/ESP targets must not acquire Pico SDK dependencies; no new directory is created by this plan.
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

The complete proposed story set below implements FR16 as a planning deliverable. Every story is for review, not a record of completed work. References to other story numbers are implementation dependencies, not an instruction to implement during this planning task. “None” means no dependency on another new story; existing project contracts still apply.

## Epic 1: Developers can prove native FujiBus service parity before hardware exists

Deliver the canonical raw packet contract and a software-only path through production code, followed by Amiga-tool and media parity. All stories in this epic require no physical Zorro/RP2350/ESP hardware. Guest tests still require the existing Amiga toolchain and licensed guest environment. No UX design requirements apply; all nine NFRs remain binding where relevant.

### Story 1.1: Establish independent FujiBus wire-format regression fixtures

As a backend developer,
I want independently specified packet fixtures,
So that codec separation cannot silently change existing FujiBus semantics or serial bytes.

**Objective / scope:** Characterization tests only: literal raw/SLIP pairs, descriptors and parameter widths, length/checksum, binary payloads including `0xC0`/`0xDB`, and response status. No production behavior changes.

**Likely files/modules:** `repos/fujinet-nio/tests/test_fujipacket.cpp`, `tests/test_fujibus_transport_framing.cpp`, optional shared test fixture header; protocol documentation is the reference, not a generated oracle.

**Dependencies:** None. **Hardware required:** No. **Requirements:** FR1, FR4 prerequisite, FR7, FR13. **Verification:** V-CXX.

**Acceptance Criteria:**

**Given** independently reviewed literal fixtures
**When** production serialization and parsing run
**Then** output bytes and decoded fields match independently specified expectations
**And** expected bytes are not generated by the same codec under test.

**Given** targeted checksum corruption and inconsistent packet lengths
**When** parsed
**Then** packets are rejected
**And** existing serial framing tests pass unchanged. Differences between documentation and implementation are reported explicitly rather than encoded as new wire rules.

**Risks/unknowns:** Common-mode fixture errors and undocumented codec quirks. Raw fixture presence alone does not approve ownership/failure semantics or release the ABI gate.

### Story 1.2: Expose the canonical raw FujiBus codec without breaking serial callers

As a transport developer,
I want raw packet encoding and decoding separated from stream wrapping,
So that native links can use the existing FujiBus representation.

**Objective / scope:** Add an explicit raw codec entry path; retain compatible serial entry points while auditing their callers. Preserve six-byte header, little-endian fields, descriptors, checksum and payload semantics. Do not change `ITransport` or service code.

**Likely files/modules:** `repos/fujinet-nio/include/fujinet/io/protocol/fuji_bus_packet.h`, `src/lib/fuji_bus_packet.cpp`, codec tests and `docs/protocol_reference.md`. Cross-check unchanged C/Python encoders as evidence.

**Dependencies:** 1.1. **Hardware required:** No. **Requirements:** FR1, FR4, FR5. **Verification:** V-CXX; V-PY if Python changes prove necessary.

**Acceptance Criteria:**

**Given** the literal vectors
**When** raw encoding/decoding is requested
**Then** exactly the FujiBus bytes are produced/consumed without SLIP
**And** lengths, checksum, truncation, descriptors and trailing-data handling have explicit tested rules.

**Given** existing serial callers
**When** the compatibility path is used
**Then** existing wire bytes and outcomes are unchanged
**And** raw/SLIP selection is explicit rather than guessed from payload bytes. Native struct layout/host endianness is not the wire contract.

**Risks/unknowns:** Hidden codec callers and parser permissiveness. Resolve incompatible validity rules explicitly; do not bundle unrelated parser redesign.

### Story 1.3: Make framer composition use raw FujiBus packets consistently

As a firmware maintainer,
I want the framer boundary to carry raw packets,
So that selecting native framing genuinely bypasses SLIP.

**Objective / scope:** Route `FujiBusTransport` through the raw codec; make `SlipFramer` own escaping/unescaping and delimiters. Reuse framing helpers for legacy serial codec wrappers rather than duplicate SLIP algorithms. Preserve response mapping and construction-time selection.

**Likely files/modules:** `repos/fujinet-nio/src/lib/fujibus_transport.cpp`, `src/lib/slip_framer.cpp`, `include/fujinet/io/transport/iframer.h`, relevant framer headers, `src/lib/bootstrap.cpp`, tests and audited framer implementations such as `src/lib/transport/atari_sio_fujibus_framer.cpp` where affected.

**Dependencies:** 1.2. **Hardware required:** No. **Requirements:** FR1, FR4, FR5. **Verification:** V-CXX plus focused tests/builds for any other affected framer.

**Acceptance Criteria:**

**Given** the same request/response
**When** transported through a raw test framer or SLIP framer
**Then** decoded semantics match and only the SLIP path adds wrapping
**And** bytes equal Story 1.1's fixtures.

**Given** fragmented serial input and consecutive delimiters
**When** polled repeatedly
**Then** existing extraction behavior is preserved
**And** every implemented `IFramer` agrees on raw packet input/output. No service handler changes are required.

**Risks/unknowns:** Other framers may depend on the old inclusive-delimiter contract; include the full caller/implementer audit in review, not just `SlipFramer`.

### Story 1.4: Provide a bounded native packet adapter and deterministic I/O double

As a backend developer,
I want explicit packet boundaries and observable transfer failures,
So that native transport correctness can be tested without hardware.

**Objective / scope:** Replace the accumulate-all native stub with whole-packet behavior driven by an explicit packet source/sink. Reuse `IFramer`; justify the minimum adapter/capability needed for boundaries, capacity, failure and reset. Supply a test queue that moves opaque bytes and schedules faults, not a second FujiBus implementation.

**Likely files/modules:** `repos/fujinet-nio/src/lib/native_framer.cpp`, `include/fujinet/io/transport/native_framer.h`, `include/fujinet/io/core/channel.h` only if justified, `tests/test_native_framer.cpp`, framer/transport tests. Document the selected contract in proposed `docs/native-packet-contract.md`.

**Dependencies:** 1.3. **Hardware required:** No. **Requirements:** FR5, FR6, FR9, FR13. **Verification:** V-CXX.

**Acceptance Criteria:**

**Given** two queued complete datagrams, delayed arrival, and repeated polls
**When** packets are extracted
**Then** each boundary is preserved with no merging or premature partial delivery
**And** empty, exact-capacity, oversize and truncated transfers have tested outcomes.

**Given** full queues, send failure or reset
**When** I/O progresses
**Then** memory/work remain bounded and failure is observable through the chosen adapter contract
**And** stale buffers cannot become a later valid packet. Packet-queue tests do not authorize multiple live remote exchanges.

**Risks/unknowns:** `Channel::write` and `IFramer::sendPacket` currently return no status. The story must resolve this narrowly and test the result; do not silently convert failed sends into success or invent physical flow-control registers.

### Story 1.5: Prove native broker ownership and recovery against existing retry callers

As an Amiga backend developer,
I want deterministic ownership and failure tests through the real broker and retry paths,
So that native failures cannot mix responses or silently replay ambiguous writes.

**Objective / scope:** Bind an instrumented packet-I/O double to the existing backend contract in native tests. Exercise broker lifecycle, queued/in-progress abort and actual existing retry callers. Establish whether safe fault containment is possible with unchanged higher layers; this is not permission to redesign retry policy.

**Likely files/modules:** `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_device.c`, `test_fujinet_nio_client_retry.c`, focused new native-backend tests, `amiga/nio.device/fujinet_nio_device.c` only for necessary binding/lifecycle support. Read/link `common/fujinet_disk_retry.c` and library `fn_raw_call` unchanged.

**Dependencies:** 1.4. **Hardware required:** No. **Requirements:** FR2, FR3, FR6, FR9. **Verification:** V-BROKER, V-RETRY and new focused tests; V-LIB only if separately approved library changes become necessary.

**Acceptance Criteria:**

**Given** multiple callers locally queued
**When** processing and abort events interleave
**Then** remote execution remains serialized, buffers belong to the right caller, failed lengths are zero, error domains remain distinct, and each request gets one reply
**And** queued abort sends nothing while in-progress abort is not treated as rollback.

**Given** unknown remote completion followed by close/open, caller retry, or late response
**When** recovery is attempted
**Then** no new remote exchange is transmitted until safe reset/quiescence is established
**And** reopen alone cannot erase that uncertainty. Inject faults before send, after delivery, and after service effect but before response delivery; count actual transmissions and effects through both retry paths.

**Risks/unknowns:** Existing retries may expose an incompatibility that cannot be contained behind the backend. If so, record it as a blocking scope decision for 1.6; do not claim safety or silently change disk/library semantics. The hardware means of proving reset/quiescence remains deferred.

### Story 1.6: Accept the canonical software packet contract for bridge design

As a bridge designer,
I want an accepted, tested software packet contract,
So that hardware ABI decisions are based on stable semantics rather than mock conventions.

**Objective / scope:** Review and publish raw representation, packet boundaries, capacity/ownership, send/receive/reset outcomes, and relevant failure behavior established in 1.1–1.5. This is the explicit software prerequisite for Epic 2 ABI sign-off, not a hardware approval.

**Likely files/modules:** Proposed `repos/fujinet-nio/docs/native-packet-contract.md`, workspace `backlog/amiga-faster-backends.md` for the gate/evidence link, and this BMAD artifact's acceptance record; no implementation changes required for the review itself.

**Dependencies:** 1.1, 1.2, 1.3, 1.4, 1.5. **Hardware required:** No. **Requirements:** FR1, FR2, FR5, FR9, FR13, FR14. **Verification:** Review cited passing V-CXX/V-BROKER/V-RETRY evidence and contract-to-test traceability.

**Acceptance Criteria:**

**Given** passing evidence for the five preceding stories
**When** the contract is reviewed
**Then** an explicit acceptance record identifies canonical packet bytes, packet boundaries, ownership and relevant failure behavior
**And** unresolved safety/compatibility discrepancies prevent acceptance.

**Given** acceptance
**When** Epic 2 considers ABI approval
**Then** it cites this record and its revision
**And** neither project setup nor positive PIO results substitute for it. No address map, queue depth, link protocol or correlation field is defined here.

**Risks/unknowns:** Confusing tests with approval; accepting only the codec while leaving failure semantics open. Later contract changes require ABI impact review.

### Story 1.7: Prove file-list and clock parity through the real core

As a service maintainer,
I want serial and native fixtures to exercise real file and clock handlers,
So that framing changes do not alter ordinary operations.

**Objective / scope:** Two-configuration core integration using production codecs, routing and handlers. Isolate directory-cache effects and time. Reuse existing FS fixtures; provide only a test-level time source if needed.

**Likely files/modules:** `repos/fujinet-nio/tests/test_file_device_protocol.cpp`, `test_clock_device.cpp`, shared native parity fixture; `src/lib/file_device.cpp` and `clock_device.cpp` remain consumers, not mock implementations. Time substitution uses the existing platform-time boundary.

**Dependencies:** 1.4. **Hardware required:** No. **Requirements:** FR1, FR6, FR7. **Verification:** V-CXX.

**Acceptance Criteria:**

**Given** identical isolated directory contents and controlled time
**When** file-list/clock requests traverse serial and native framing through the core
**Then** decoded replies and statuses match
**And** expected directory entries/time are independently asserted.

**Given** missing paths, malformed service payloads or unavailable time
**When** handled
**Then** both paths retain existing service error behavior
**And** neither test changes the host clock or merely returns canned service responses.

**Risks/unknowns:** Process-global directory cache and time formatting configuration can contaminate comparisons. Avoid sleeps and ensure one configuration cannot seed the other's state.

### Story 1.8: Prove disk read/write parity with independently checked backing storage

As a disk-service maintainer,
I want native and serial disk operations checked against disposable image bytes,
So that a matching transport bug cannot masquerade as correct storage behavior.

**Objective / scope:** Production `DiskDevice`/`DiskService` integration using separate equivalent fixtures; test successful reads, writes/read-back, flush, read-only rejection, out-of-range requests and failed transfers.

**Likely files/modules:** `repos/fujinet-nio/tests/test_disk_device_protocol.cpp`, `tests/fake_fs.h`, shared parity fixtures; production `src/lib/disk_device.cpp` and `src/lib/disk/disk_service.cpp` are exercised unchanged.

**Dependencies:** 1.4, 1.5. **Hardware required:** No. **Requirements:** FR1, FR6, FR7, FR9, FR10. **Verification:** V-CXX plus retry integration tests where used.

**Acceptance Criteria:**

**Given** independent copies of disposable media
**When** equivalent read/write/flush operations traverse both paths
**Then** responses and resulting backing bytes match independent expected values
**And** surrounding sectors remain unchanged.

**Given** write protection, invalid ranges or injected failed/ambiguous delivery
**When** exercised
**Then** expected service errors and transport effects are distinguished
**And** effect/transmission counts expose any unsafe replay. No production media is used.

**Risks/unknowns:** In-memory fixtures do not prove physical persistence. Do not equate repeated identical sector contents with proof that a write executed only once.

### Story 1.9: Add a host-side native packet test endpoint for guest integration

As an integration-test author,
I want a controllable host endpoint backed by the production core,
So that an Amiga test backend can reach real services without Zorro hardware.

**Objective / scope:** Select and document a test-only guest/host exchange mechanism after checking available guest facilities; implement the host half and an independent host client. Preserve explicit record boundaries and timeouts. A temporary shared-directory record adapter or suitable guest socket facility is a harness choice, not a proposed bridge mailbox/ESP protocol; do not assume either already exists.

**Likely files/modules:** Proposed native-test runner in `repos/fujinet-nio/tests/` or `integration-tests/`, test build target/profile, existing `src/lib/bootstrap.cpp`/embedding seam; workspace `integration-tests/amiberry/` host tests/configuration. Do not advertise the PTY Zorro placeholder as a native endpoint.

**Dependencies:** 1.6, 1.7, 1.8. **Hardware required:** No. **Requirements:** FR3, FR6, FR7, FR13. **Verification:** V-CXX, focused runner/harness tests.

**Acceptance Criteria:**

**Given** the selected test-only mechanism and an independent host client
**When** records are exchanged
**Then** real core handlers process raw packets with bounded complete-record delivery
**And** disconnect, stale record, oversized input and cleanup are tested without the guest implementation.

**Given** runner startup
**When** configuration is inspected
**Then** it identifies itself as native-test, not real Zorro or SLIP
**And** no automatic serial fallback or new physical ABI is introduced.

**Risks/unknowns:** Guest transport availability and process cleanup. If neither facility is usable, record the harness blocker; host-only success does not meet guest acceptance.

### Story 1.10: Build an Amiga native-test broker binary using the host endpoint

As an Amiga test developer,
I want an installable test backend behind the existing broker ABI,
So that real Amiga callers exercise the packet-native path before hardware exists.

**Objective / scope:** Implement the guest half of 1.9's test mechanism; compile a separate broker binary with that backend and without serial framing objects. Reuse broker request/error/lifecycle semantics; make serial-only controls explicitly unsupported. Keep the test mechanism outside resident disk/service code.

**Likely files/modules:** Proposed test backend under `repos/fujinet-nio-driver/amiga/nio.device/`, `amiga/Makefile`, focused backend tests, narrow backend-binding changes in `fujinet_nio_device.c`; `integration-tests/amiberry/conftest.py` binary injection.

**Dependencies:** 1.5, 1.9. **Hardware required:** No; Amiga guest required for acceptance. **Requirements:** FR2, FR3, FR6, FR9, FR13. **Verification:** V-BROKER, new backend tests, V-AMIGA using a focused raw-exchange probe.

**Acceptance Criteria:**

**Given** the test broker installed under the normal device name
**When** a real guest probe submits EXCHANGE
**Then** the real host service responds through the packet path
**And** serial/timer stream setup and `fn_session`/`fn_slip` are not used for packet transport.

**Given** serial control commands, missing peer or guest teardown
**When** requested
**Then** unsupported/error outcomes and resource ownership are explicit and tested
**And** no fallback occurs. Test binaries cannot be mistaken for deployable Zorro firmware.

**Risks/unknowns:** Exec/DOS/socket facilities available to the broker worker and test-only scheduling. Do not confuse test I/O convenience with physical access architecture.

### Story 1.11: Let exchange-tool read-only operations run without serial setup

As an Amiga developer,
I want file-list and clock diagnostics on a native installation,
So that I can test the chosen backend without baud/device controls.

**Objective / scope:** Add explicit native-compatible operation planning while preserving existing CLI behavior and the lifecycle meaning of `--backend cold|warm`. Do not reinterpret that flag as a physical selector. Native lifecycle operations must be supported honestly or rejected, never simulated with SET_BAUD.

**Likely files/modules:** `repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.h`, `fujinet_nio_exchange_opts.c`, `fujinet-nio-exchange.c`, `amiga/tests/test_fujinet_nio_exchange_opts.c`, tool documentation.

**Dependencies:** 1.10. **Hardware required:** No; guest required for tool acceptance. **Requirements:** FR3, FR7, FR8. **Verification:** V-OPTS, V-AMIGA.

**Acceptance Criteria:**

**Given** a native test installation
**When** file-list and clock operations are run
**Then** they reach EXCHANGE without serial control requests
**And** malformed/incompatible options fail clearly before I/O.

**Given** existing serial CLI invocations
**When** parsed/planned
**Then** their supported behavior remains compatible
**And** output distinguishes installed backend context from lifecycle mode without dynamic switching.

**Risks/unknowns:** Current control-based cold mode does not imply a generic reset command exists. Choose the smallest explicit CLI change; no public device ABI expansion solely for benchmarking.

### Story 1.12: Add safe ordinary disk operations to the exchange tool

As an Amiga developer,
I want disk read/write diagnostics independent of serial provocation,
So that native parity can be measured safely on disposable media.

**Objective / scope:** Separate ordinary disk parity operations from `run_disk_provocation` and serial pacing assumptions. Use the established resident disk/client path; require explicit disposable-fixture/write intent and do not silently run destructive patterns against mounted user media.

**Likely files/modules:** The exchange tool/options/tests from 1.11 and a focused guest disk fixture; `amiga/disk.device/fujinet_disk_device.c` is exercised, not redesigned.

**Dependencies:** 1.8, 1.11. **Hardware required:** No; guest required for acceptance. **Requirements:** FR7, FR8, FR9, FR10. **Verification:** V-OPTS, V-AMIGA, V-RETRY.

**Acceptance Criteria:**

**Given** explicit test media and operation options
**When** disk read/write is requested
**Then** no baud/pacing controls are needed and errors remain distinguishable from service/device results
**And** write/read-back verifies expected bytes.

**Given** missing write intent, invalid slot/LBA or incompatible provocation options
**When** validated
**Then** the tool rejects them before issuing the write
**And** existing serial provocation remains a separate explicit workflow.

**Risks/unknowns:** Mapping tool slot arguments to resident units must retain existing semantics. A restore-after-write workflow alone is not adequate protection for production media.

### Story 1.13: Extend host parity to catalogue and media lifecycle contracts

As a maintainer,
I want existing media/catalogue behavior exercised through native framing,
So that a faster backend does not fork mount or multi-drive behavior.

**Objective / scope:** Run real Slot Catalog and DiskDevice workflows through the parity fixture: independent slots, read-only state, mount/eject/replacement/restoration and change flags. Reuse established DD/HD fixture contracts; do not introduce new image formats.

**Likely files/modules:** `repos/fujinet-nio/tests/test_slot_catalog_service.cpp`, `test_disk_device_protocol.cpp`, `test_boot_mount.cpp` and shared parity test fixtures.

**Dependencies:** 1.7, 1.8. **Hardware required:** No. **Requirements:** FR1, FR6, FR10. **Verification:** V-CXX.

**Acceptance Criteria:**

**Given** equivalent isolated backend configurations
**When** catalogue selection and media lifecycle operations run
**Then** independent slots, persisted state and change notifications match existing expectations
**And** catalogue entry numbers are not incorrectly restricted to resident unit numbers.

**Given** invalid/missing or read-only media
**When** selected or written
**Then** the established errors and protection behavior are unchanged
**And** no HDF/RDB or completed Phase 2 implementation is reopened.

**Risks/unknowns:** Host service parity does not prove Amiga mount/trackdisk integration; Story 1.14 supplies that separate gate.

### Story 1.14: Accept end-to-end native guest parity and fault isolation

As an Amiga maintainer,
I want a repeatable guest acceptance run against real services,
So that pre-hardware completion means more than host mocks passing.

**Objective / scope:** Parameterize the existing acceptance environment to install the native-test binary, retaining service/media assertions. Run the exchange operations and existing DD/HD, multi-drive, catalogue and lifecycle checks in focused groups; include an induced failure followed by safe recovery. No real Zorro claims.

**Likely files/modules:** `integration-tests/amiberry/conftest.py`, focused existing/new test nodes and startup scripts, workspace acceptance evidence/backlog. Owning repositories change only for demonstrated integration defects within approved scope.

**Dependencies:** 1.6, 1.10, 1.11, 1.12, 1.13. **Hardware required:** No; Amiga guest required. **Requirements:** FR1, FR2, FR3, FR7, FR8, FR9, FR10, FR13. **Verification:** V-AMIGA targeted nodes, focused harness pytest; owner tests for any fixes.

**Acceptance Criteria:**

**Given** independently deployed serial-reference and native-test environments
**When** the acceptance operations run
**Then** the same semantic/media assertions pass
**And** native execution does not open a serial transport or issue serial controls.

**Given** delayed/lost response and locally queued callers
**When** fault handling is exercised
**Then** no stale reply is attributed to a later request and ambiguous operations are not unsafely replayed
**And** the evidence names exactly which components are real, mocked and still hardware-unvalidated.

**Risks/unknowns:** Guest availability, timing-dependent harness failures, and effects obscured by disk caching. Failure of this gate leaves Epic 1 incomplete even if Story 1.6 has already released the ABI dependency.

## Epic 2: Bridge developers can make an evidence-backed feasibility and ABI decision

Deliver an isolated bridge project and independently useful feasibility evidence. Stories 2.1–2.3 can proceed alongside Epic 1. Story 2.4 cannot approve the ABI before Story 1.6 acceptance. No register map, mailbox layout, PIO program, firmware concurrency model, or ESP link protocol is specified by the story drafts below.

### Story 2.1: Create an isolated, reproducible bridge project skeleton

As a bridge developer,
I want a standalone RP2350B build and clear ownership boundaries,
So that feasibility work can begin without disturbing existing firmware builds.

**Objective / scope:** Create the proposed `bridges/rp2350-zorro/` project, minimal compile/link target, dependency setup documentation and test layout. Pin tooling from verified available SDK support during implementation. Keep external firmware repositories optional references only.

**Likely files/modules:** Proposed `repos/fujinet-nio/bridges/rp2350-zorro/{CMakeLists.txt,README.md,src/,tests/}` and a link from firmware docs. No existing root build selector or service library needs restructuring.

**Dependencies:** None; independent of Epic 1. **Hardware required:** No. **Requirements:** FR11, FR12, FR13. **Verification:** New isolated configure/build command recorded in the README; existing source-generation/build-isolation check and V-CXX as appropriate.

**Acceptance Criteria:**

**Given** the documented toolchain
**When** the bridge target builds independently
**Then** the output is explicitly a nonfunctional skeleton
**And** existing POSIX/ESP source lists and builds do not acquire Pico SDK or bridge sources.

**Given** protocol dependency review
**When** the project is inspected
**Then** it references existing definitions/fixtures rather than duplicating the service stack
**And** it contains no speculative physical packet ABI or required external FujiNet firmware checkout.

**Risks/unknowns:** SDK/board support and generator interactions. Compile success is not PIO feasibility or hardware support.

### Story 2.2: Establish RP2350B/Zorro bus and PIO feasibility evidence

As a hardware/firmware developer,
I want measured bus-facing feasibility results,
So that unsupported timing or PIO assumptions are discovered before ABI commitment.

**Objective / scope:** Implement a bounded experimental bus-access/PIO test using the existing hardware design and authoritative bus requirements. Record resources, tested conditions, observed timing and limitations. Experiments are disposable probes, not a production firmware architecture.

**Likely files/modules:** Proposed bridge `tests/feasibility/` and evidence under owning firmware docs; existing hardware documentation is read-only input. No electrical mapping/routing changes.

**Dependencies:** 2.1. No dependency on Epic 1. **Hardware required:** Yes: suitable RP2350B/Zorro fixtures and instrumentation. **Requirements:** FR13, FR14. **Verification:** V-HW with a reviewed experiment procedure and captured measurements.

**Acceptance Criteria:**

**Given** identified board/pin mapping and bus requirements
**When** the experiment runs under documented conditions
**Then** evidence states which access/timing obligations are met or unmet
**And** resource/clock assumptions are measured or explicitly unverified.

**Given** the results
**When** feasibility is reviewed
**Then** a proceed/hold conclusion and remaining experiments are recorded
**And** no ABI is approved merely because the probe works. A required hardware redesign is escalated outside this scope.

**Risks/unknowns:** Instrument availability, representative bus load, synchronization and PIO resource limits. Do not extrapolate untested timing conditions into production guarantees.

### Story 2.3: Establish bridge-to-ESP transfer and reset feasibility

As a bridge designer,
I want evidence for complete-packet transfer and recovery across the bridge link,
So that ABI design can account for actual endpoint behavior.

**Objective / scope:** Evaluate physically available link options using bounded opaque test data; investigate backpressure, capacity, peer absence, reset and stale transfer state. Keep candidate-specific probes provisional and service-independent; no permanent link protocol is selected in this planning artifact.

**Likely files/modules:** Bridge feasibility tests/docs from 2.1 and narrowly isolated ESP test fixtures under `repos/fujinet-nio`; no production service changes.

**Dependencies:** 2.1. May run in parallel with 2.2 and Epic 1. **Hardware required:** Yes: RP2350B, ESP32-S3 and suitable link/instrumentation. **Requirements:** FR5, FR9, FR11, FR13, FR14. **Verification:** V-HW.

**Acceptance Criteria:**

**Given** an identified candidate link and provisional test sizes
**When** transfer, peer reset and backpressure are exercised
**Then** measured capabilities and reset limitations are recorded
**And** no provisional test size is treated as the final packet capacity.

**Given** delayed data or unknown completion
**When** reset/quiescence is evaluated
**Then** evidence distinguishes guaranteed state clearance from an assumption
**And** inability to prevent stale completion is an explicit ABI/readiness blocker.

**Risks/unknowns:** Physical interconnect availability and reset domains. These experiments may begin before Story 1.6; final suitability must be checked against its accepted contract in 2.4.

### Story 2.4: Approve an evidence-backed bridge packet ABI

As an Amiga/bridge/ESP implementer,
I want one agreed hardware packet contract grounded in accepted software semantics and feasibility,
So that independently implemented endpoints interoperate safely.

**Objective / scope:** Only after prerequisites, specify the actual hardware packet ABI and required bridge-link contract with ownership, boundary/capacity/error/reset rules and test vectors. Select concrete hardware details from evidence, not from this draft. Keep canonical FujiBus packets unchanged and services outside the bridge.

**Likely files/modules:** Proposed bridge contract docs and minimal shared transport-only headers under its owning project if real consumers require them; references from Amiga/ESP docs and `docs/native-packet-contract.md`. Header location/language must suit the actual consumers, not assume C++ on Amiga.

**Dependencies:** 1.6 accepted; 2.2 and 2.3 with positive relevant feasibility evidence. **Hardware required:** Prior hardware evidence is mandatory; sign-off itself is a design review, with additional experiments where evidence is missing. **Requirements:** FR5, FR9, FR11, FR12, FR13, FR14. **Verification:** Contract-to-test/evidence review and transport-only header/fixture checks once defined.

**Acceptance Criteria:**

**Given** cited acceptance of the canonical raw representation, boundaries, ownership and failure behavior from 1.6, plus positive feasibility evidence
**When** the hardware ABI is reviewed
**Then** explicit agreement records how every requirement is satisfied
**And** unresolved discrepancies prevent sign-off.

**Given** no Story 1.6 acceptance or incomplete feasibility evidence
**When** approval is requested
**Then** it is withheld even if project/probe builds pass
**And** no downstream hardware story treats a provisional register/mailbox layout as approved.

**Risks/unknowns:** Hardware constraints may conflict with accepted packet capacity or recovery. Resolve explicitly; do not reduce protocol semantics or assume correlation exists. Unrelated unfinished Epic 1 tooling does not block this sign-off once 1.6 is accepted.

## Epic 3: Amiga users can operate a validated Zorro-only FujiNet installation

Implement only the agreed hardware contract, preserving existing services and Zorro-only deployment. These stories require suitable hardware and must be refined against the approved ABI before execution; this plan does not preselect register access, PIO allocation, or the RP2350-to-ESP link. Epic 1 must be accepted before production hardware implementation begins, consistent with the approved epic dependency.

### Story 3.1: Implement the Amiga Zorro access backend behind the broker

As an Amiga user,
I want the existing broker to exchange packets through my Zorro board,
So that applications do not need hardware-specific changes.

**Objective / scope:** Implement board discovery/access, open/close/exchange and bounded error/recovery handling from the approved ABI. Build a separate Zorro broker binary with unsupported serial controls and no serial transport dependency. Do not redesign the broker worker model.

**Likely files/modules:** Proposed `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_zorro_backend.c`, `amiga/Makefile`, backend binding, focused native/access tests and driver docs.

**Dependencies:** 1.14, 2.4 and suitable Zorro hardware. **Hardware required:** Yes; an ABI-conforming fixture/probe can validate access before production bridge firmware exists. **Requirements:** FR2, FR3, FR5, FR9, FR14. **Verification:** V-BROKER, V-AMIGA, V-HW access tests.

**Acceptance Criteria:**

**Given** the approved ABI and a conforming hardware fixture
**When** open/exchange/close are exercised
**Then** complete raw packets, capacities and ownership follow the contract
**And** absent/unsupported hardware fails cleanly without serial fallback.

**Given** timeout, abort or uncertain remote state
**When** lifecycle operations occur
**Then** the accepted recovery containment is retained and at most one exchange is remotely in flight
**And** the unchanged public request layout and client behavior remain compatible.

**Risks/unknowns:** Autoconfiguration/access details and actual bus errors are deferred to 2.4. A real-bridge dependency must not be hidden inside this access story; use the validated fixture for its standalone gate.

### Story 3.2: Implement the bridge's opaque packet transfer engine

As a bridge integrator,
I want the RP2350B firmware to implement the approved transfer contract,
So that Amiga requests and ESP replies cross the board without service translation.

**Objective / scope:** Implement only the agreed bus/link mechanics, packet buffering, ownership, backpressure and reset rules. Use ABI/link test peers to validate independently of the production ESP adapter. Firmware task/core/PIO structure follows feasibility and ABI decisions, not assumptions in this story.

**Likely files/modules:** Proposed `repos/fujinet-nio/bridges/rp2350-zorro/src/`, any justified PIO assets and focused tests/docs.

**Dependencies:** 1.14, 2.4. **Hardware required:** Yes. **Requirements:** FR5, FR9, FR11, FR14. **Verification:** Standalone bridge tests/build plus V-HW.

**Acceptance Criteria:**

**Given** conforming bus/link test peers
**When** packet transfer and backpressure run
**Then** bytes and boundaries are preserved with bounded storage
**And** device/command/payload semantics are not interpreted by the bridge.

**Given** peer loss or reset at each ownership transition
**When** recovery is exercised
**Then** the agreed fault/reset outcome is observed
**And** partial/stale data cannot be reported as a successful later transfer.

**Risks/unknowns:** Actual PIO/interrupt/firmware decomposition depends on 2.4. If implementation exceeds one reviewable transfer-engine slice, subdivide using the approved state machine before execution rather than inventing it now.

### Story 3.3: Connect the approved bridge link to the ESP FujiBus path

As a firmware integrator,
I want the ESP32-S3 link adapter to deliver raw packets into existing FujiBus handling,
So that all existing services remain reusable.

**Objective / scope:** Implement the approved physical-link adapter and construction/profile wiring using Epic 1's native contract. Validate against an ABI/link-conforming peer before full bridge integration. Keep the accepted ESP32 profile macro structure unless the selected build genuinely requires adjustment.

**Likely files/modules:** Proposed adapter/header under `repos/fujinet-nio/src/platform/esp32/` and `include/fujinet/platform/esp32/`, `channel_factory.cpp`, `build_profile.cpp`, source templates and focused tests.

**Dependencies:** 1.14, 2.4. **Hardware required:** Yes: ESP32-S3 and conforming link fixture. **Requirements:** FR1, FR4, FR5, FR11, FR14. **Verification:** V-CXX for shared adapter logic, configured ESP build and V-HW.

**Acceptance Criteria:**

**Given** literal native packets from the link fixture
**When** the ESP core services them
**Then** existing FujiBus mapping and handlers produce the correct raw response
**And** no SLIP wrapping or service-specific bridge branches are introduced.

**Given** backpressure, missing peer or repeated idle polls
**When** the core runs
**Then** bounded I/O and declared reset/error behavior hold
**And** the cooperative service loop remains responsive within measured, documented conditions.

**Risks/unknowns:** Current channel/framer send-status limitations must already be resolved by Epic 1; interrupt/wakeup policy follows hardware evidence, not an arbitrary core tick increase.

### Story 3.4: Validate complete hardware file-list, clock and disk exchanges

As an Amiga developer,
I want ordinary operations to traverse the complete Zorro bridge path,
So that individually tested endpoints are shown to interoperate.

**Objective / scope:** Integrate the three endpoint implementations; execute file-list, clock, disk-read and disposable-media disk-write/read-back using the real exchange tool. Record packet captures/diagnostics sufficient to distinguish endpoint failures.

**Likely files/modules:** Driver/bridge/ESP integration configuration and evidence, owning repository hardware test procedures; integration fixes limited to approved endpoint boundaries.

**Dependencies:** 3.1, 3.2, 3.3. **Hardware required:** Yes: complete working chain. **Requirements:** FR1, FR3, FR7, FR8, FR11, FR13. **Verification:** V-HW and focused tests in every owner changed by integration fixes.

**Acceptance Criteria:**

**Given** an installed Zorro-only broker and complete hardware chain
**When** the four operations run
**Then** responses and backing effects match the software baseline
**And** no serial transport or serial setup command is involved.

**Given** recorded version/configuration data
**When** another developer repeats the run
**Then** the setup and expected assertions are reproducible
**And** any failed operation blocks integration acceptance rather than being hidden by retries.

**Risks/unknowns:** Cross-endpoint reset and buffer lifetime may differ from fixture behavior; initial success is not full recovery or media readiness.

### Story 3.5: Validate existing Amiga media and catalogue workflows on Zorro

As an Amiga user,
I want existing disk mounting and multi-drive behavior on the Zorro installation,
So that changing hardware does not change my workflows.

**Objective / scope:** Execute existing DD/HD ADF, catalogue mapping, DN0–DN7 independence, writable/read-only policy, mount/eject/replacement/restoration and change-notification assertions on hardware. Adapt environment/runner plumbing, not service expectations.

**Likely files/modules:** Workspace Amiga acceptance procedures/fixtures based on `integration-tests/amiberry/`; durable media contract `docs/amiga/disk-media-architecture.md` is a reference, not a redesign target; owning hardware acceptance documentation.

**Dependencies:** 3.4. **Hardware required:** Yes. **Requirements:** FR1, FR10, FR13, FR15. **Verification:** Named physical equivalents of existing acceptance nodes, with evidence for each preserved assertion.

**Acceptance Criteria:**

**Given** disposable media and existing catalogue/mount fixtures
**When** normal workflows run
**Then** their established results and change notifications match the serial-reference contract
**And** catalogue selections are not restricted to entries 1–8.

**Given** missing, replaced or read-only media
**When** accessed
**Then** existing failure/protection behavior is retained
**And** no HDF/RDB expansion or completed Phase 2 redesign is needed for acceptance.

**Risks/unknowns:** Physical-machine observation differs from emulator tooling. If automation is unavailable, record a reproducible manual procedure and evidence, not an implied automated pass.

### Story 3.6: Validate hardware fault containment and recovery

As an Amiga user,
I want transport faults to fail safely without corrupting subsequent operations,
So that recovery does not silently misroute replies or duplicate writes.

**Objective / scope:** Inject controlled failures at agreed ownership transitions: absent peer, bridge/ESP reset, capacity pressure, response loss/delay and corruption where the fixture can create it. Exercise actual caller retries and broker lifecycle, not just standalone bridge code.

**Likely files/modules:** Bridge/ESP fault fixtures, Amiga diagnostics and cross-repository hardware procedures/evidence. Do not add destructive fault modes to normal production operation.

**Dependencies:** 3.4. **Hardware required:** Yes. **Requirements:** FR2, FR5, FR9, FR13, FR15. **Verification:** V-HW with per-fault traces, transmission/effect counts and owning regression tests for fixes.

**Acceptance Criteria:**

**Given** failure before delivery, after service effect, or before response receipt
**When** existing caller retries and recovery run
**Then** observed behavior satisfies the accepted failure contract
**And** no late response completes a later request or unsafe extra write is hidden by identical data.

**Given** inability to establish safe remote state
**When** further requests arrive
**Then** the documented fail-closed behavior persists without serial fallback
**And** unsupported recovery cases remain explicit production-readiness blockers.

**Risks/unknowns:** Some corruption/timing faults may be uninjectable on available fixtures. Record coverage gaps rather than asserting they passed; do not claim remote rollback or exactly-once execution.

### Story 3.7: Publish measured performance and Zorro-only installation readiness

As an Amiga user,
I want reproducible installation instructions and honest performance/recovery limits,
So that I can decide whether this hardware is suitable for my system.

**Objective / scope:** Document installation of the selected binary, hardware/firmware compatibility, unsupported serial controls, limitations and accepted recovery procedures. Measure throughput/latency on representative safe workloads after correctness/recovery acceptance; no optimization or invented speed target is bundled here.

**Likely files/modules:** Driver Amiga README/backend docs, firmware bridge README/docs, workspace `backlog/amiga-faster-backends.md` and a completed acceptance record only when its exit criteria are actually met.

**Dependencies:** 3.5, 3.6. **Hardware required:** Yes for measurements and installation validation. **Requirements:** FR3, FR13, FR15. **Verification:** Repeat documented install/smoke procedure and measured workload commands, document link/consistency checks.

**Acceptance Criteria:**

**Given** accepted parity/recovery evidence
**When** performance runs are recorded
**Then** they identify hardware, firmware, packet sizes, workload, error/retry counts, latency and useful throughput
**And** any comparison uses a separately deployed serial baseline rather than runtime fallback.

**Given** installation documentation
**When** followed on a supported system
**Then** it produces the tested Zorro-only setup
**And** readiness is declared only with all required evidence and remaining limitations listed. A speed shortfall informs future work; it does not authorize unsafe concurrency or weaker correctness.

**Risks/unknowns:** Workload representativeness and hardware variability. Do not close the backlog merely because firmware builds or one benchmark succeeds.

## Dependency and review summary

There are **25 proposed stories: 14 software/pre-hardware, 4 bridge setup/feasibility/ABI, and 7 physical implementation/acceptance**. Each lists a bounded outcome, owning modules, prerequisites, tests and unknowns. All are review drafts; conditional hardware stories are not ready to execute until their evidence gates exist.

```text
1.1 -> 1.2 -> 1.3 -> 1.4 -> 1.5 -> 1.6  [accepted software packet contract]
                         |         |
                         +-> 1.7   +-> 1.8
1.6 + 1.7 + 1.8 -> 1.9 -> 1.10 -> 1.11 -> 1.12
1.7 + 1.8 -> 1.13; guest/tool/media branches converge at 1.14

2.1 -> 2.2 and 2.3                  [may run alongside Epic 1]
1.6 + positive 2.2 + positive 2.3 -> 2.4 [ABI sign-off, not before]

1.14 + 2.4 -> 3.1 / 3.2 / 3.3 -> 3.4 -> 3.5 and 3.6 -> 3.7
```

The diagram highlights major gates; each story's dependency field is authoritative for all prerequisites. Hardware/PIO feasibility never waits for Epic 1 completion. ABI sign-off waits for **Story 1.6**, not merely raw codec tests and not unrelated later guest tooling. Physical implementation consumes both accepted Epic 1 integration and the approved hardware ABI. A later change to the accepted software contract requires revisiting the hardware contract.

### Story-level requirement coverage

| Requirement | Primary delivery/evidence stories |
| --- | --- |
| FR1 | 1.1–1.3, 1.7–1.8, 1.13–1.14, 3.3–3.5 |
| FR2 | 1.5–1.6, 1.10, 1.14, 3.1, 3.6 |
| FR3 | 1.5, 1.9–1.11, 1.14, 3.1, 3.4, 3.7 |
| FR4 | 1.1–1.3, 3.3 |
| FR5 | 1.2–1.4, 1.6, 2.3–2.4, 3.1–3.3, 3.6 |
| FR6 | 1.4–1.5, 1.7–1.10, 1.13 |
| FR7 | 1.1, 1.7–1.9, 1.11–1.12, 1.14, 3.4 |
| FR8 | 1.11–1.12, 1.14, 3.4 |
| FR9 | 1.4–1.6, 1.8, 1.10, 1.12, 1.14, 2.3–2.4, 3.1–3.2, 3.6 |
| FR10 | 1.8, 1.12–1.14, 3.5 |
| FR11 | 2.1, 2.3–2.4, 3.2–3.4 |
| FR12 | 2.1, 2.4 |
| FR13 | Explicit hardware/evidence fields throughout; 1.6, 1.14, 2.1–2.4, 3.4–3.7 |
| FR14 | 1.6, 2.2–2.4, 3.1–3.3 |
| FR15 | 3.5–3.7 |
| FR16 | This complete story set, dependency graph and review/acceptance fields; not a separate coding story |

### Deliberately deferred decisions and release risks

- **Until 1.6 acceptance:** exact software packet adapter API and failure/reset mapping, compatibility of existing replay policies, final documented raw validity/capacity contract. The existing wire representation is the baseline, not permission to invent a new FujiBus envelope.
- **Until PIO/link evidence and 2.4 agreement:** Zorro register/mailbox layout, access widths/alignment/ordering, ownership handshake, interrupt/poll strategy, buffering, transport integrity beyond existing FujiBus checks, reset protocol, firmware core/task/PIO organization, and RP2350-to-ESP physical/protocol choice. No values or addresses are specified here.
- **Until working hardware:** full bus correctness across supported machines, recovery across actual reset domains, physical transfer/backpressure/error behavior and real end-to-end compatibility. Host and guest mocks cannot close these risks.
- **Until measured data:** timeout/performance tuning and queue optimization. Local queueing may change later; multiple remotely in-flight exchanges remain prohibited unless a future design adds safe correlation. No new correlation field is proposed.
- **Existing replay policy conflict:** `fujinet_disk_retry_exchange` retries some writes and `fn_raw_call` replays some failures. Safe native containment must be demonstrated with actual callers. If incompatible with unchanged higher layers, stop for a specific scope decision; do not smuggle a DiskDevice/library rewrite into a backend story.
- **Test mechanism availability:** a native guest connection to the real core still needs implementation. Neither current serial socket plumbing nor a canned reply is native service-parity evidence. Missing guest/toolchains are named blockers, not substituted host passes.
- **No fallback:** serial is only a separate reference deployment. A running Zorro installation has no assumed RS-232 path and no automatic physical failover.
- **No external-project assumption:** the legacy external FujiNet Pico source was not needed for these conclusions; any later use must be labeled external reference and cannot establish current-project behavior.

### Recommended first story

Start with **1.1 — independent wire-format fixtures**. It is confined to one repository's tests, needs no hardware or production change, and provides a non-circular regression oracle for the necessary raw codec work. It does not alone release hardware ABI sign-off; that requires 1.6 acceptance.

### Planning verification record (2026-09-11)

Only this workspace planning document changed. After sourcing `scripts/env.sh`, an inline Node document check passed: 25 stories with all required fields and Given/When/Then/And criteria; no duplicate, unknown, cyclic or same-epic forward dependencies; Story 2.4 depends on 1.6; setup/feasibility has no Epic 1 dependency; all 16 FRs have story coverage; input document paths exist; no remaining template placeholders or trailing whitespace. `git diff --check` passed. These are structural/document checks, not implementation acceptance: no firmware, Amiga binaries, services or hardware tests were run for this planning-only change. The complete story set is awaiting user review; BMAD final-validation approval remains pending.
