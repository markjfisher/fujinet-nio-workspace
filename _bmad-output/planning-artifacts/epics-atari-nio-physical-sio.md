---
stepsCompleted: [1, 2, 3, 4]
feature: atari-nio-physical-sio
requirementsConfirmed: 2026-10-19
epicStructureApproved: 2026-10-19
storySetApproved: 2026-10-19
planningValidation: pass
inputDocuments:
  - _bmad-output/specs/spec-atari-nio-physical-sio/SPEC.md
  - _bmad-output/specs/spec-atari-nio-physical-sio/wire-and-acceptance.md
  - _bmad-output/planning-artifacts/architecture/architecture-fujinet-nio-workspace-2026-10-19/ARCHITECTURE-SPINE.md
---

# Atari NIO Physical SIO - Epic Breakdown

## Overview

This document decomposes the finalized Atari NIO physical-SIO contract into independently deliverable implementation stories. It is scoped to native packet SIO, standard Atari disk boot/media behavior, and physical acceptance; it does not revive legacy FujiNet transport or compatibility behavior.

## Requirements Inventory

### Functional Requirements

FR1: Reserve SIO device address `0x7F` exclusively for the Atari NIO application channel and route only its native `Q`/`W`/`P`/`R` commands to FujiBus.

FR2: Implement the exact bounded packet-native NIO contract: optional `Q`, `W` only while idle, three-byte `P`, exact-length `R`, one outstanding request, 512-byte v1 baseline, and defined rejection/recovery transitions.

FR3: Provide a supported `fujinet-nio-lib` Atari backend using the public API, polling by default, optional application-owned PROC notification, and no automatic post-timeout retry.

FR4: Provide standard Atari SIO `D1:`–`D8:` boot and mounted-ATR service through a disk frontend that composes `DiskService` directly and shares its media/boot state with the NIO DiskDevice path.

FR5: Apply config-mode and normal-mode boot policy so the flashed configuration ATR can boot as `D1:` and restored URI mappings drive `D1:`–`D8:` in normal mode.

FR6: Supply a cc65 XEX on the configuration ATR that uses the public library API and accepts Clock, Network, File, Disk, delayed readiness, PROC opt-in, and recovery scenarios.

FR7: Replace Atari SLIP/padded-read/`0x71` compatibility paths in the library, ESP32 channel, NetSIO, AltirraSDL, profile selection, and v1 conformance tests with the native `0x7F` contract.

FR8: Create canonical independent literal fixtures and scenario manifests for NIO, disk, boot, malformed/recovery, and virtual-environment conformance.

FR9: Deliver the official FujiNet v1 16 MB physical SIO profile at 19,200 baud, with released-idle open-drain DATA OUT/PROC and electrically benign unused SIO lines.

FR10: Provide diagnostics, build/flash, boot-mode, URI mapping, and real-hardware acceptance documentation that distinguishes virtual regression evidence from electrical/timing proof.

FR11: Provide a relocatable, CA65-only Atari BASIC CIO `N:` handler installed during the user's DOS startup, resident below adjusted `MEMLO` and registered in `HATABS`. MyDOS 4.53/4 is the first verified environment. The configuration ATR remains a transient configuration/boot-selection environment, with its existing boot contract unchanged. IOCBs own native NetworkService handles over `$7F`; read/write/update maps to GET/PUT/POST, output uses `BODY_UNKNOWN`, bounded 128-byte buffers and exactly one terminal commit. STATUS and CLOSE use the existing native service semantics; uncertain side effects are never automatically replayed. Total permanent RAM is at most 3,072 bytes.

### NonFunctional Requirements

NFR1: Preserve explicit exclusions: no `LegacyTransport`, legacy FujiNet framing/application compatibility, legacy `N:`/`R:` wire behavior, proprietary legacy commands, SLIP on `0x7F`, or high-speed SIO claim. The native CIO `N:` handler is permitted because it uses the native NIO protocol and NetworkService.

NFR2: The v1 NIO payload baseline is 512 bytes; every v1 device supports it, no implicit segmentation is allowed, and an optional `Q` must never become a bootstrap requirement.

NFR3: The cc65 client remains bounded and low-footprint: it does not install/replace `VPRCED`, retains no cancel protocol or transaction-ID system, and polling stays fully correct without PROC.

NFR4: Production framing code cannot be the fixture oracle; AltirraSDL and NetSIO independently exercise the same literal scenarios.

NFR5: Virtual acceptance never substitutes for physical proof. Real-hardware evidence records topology, revisions, idle/no-contention levels, timing, checksums, recovery, and polling/PROC behavior.

NFR6: Each touched repository follows the workspace test policy; any `fujinet-nio-lib` change passes complete `make check`.

### Additional Requirements

- Preserve the architecture's ports-and-adapters boundary: `DiskDevice` is the FujiBus wrapper; Atari disk SIO composes `DiskService` directly.
- The first fixture story fixes the canonical source/projection format before adapter implementation consumes it.
- The first disk story fixes the v1 command/sector/geometry/status-error matrix before disk-adapter implementation; it covers boot and mounted ATR read/write/status only. Formatting, PERCOM, high-speed, and non-ATR media are excluded.
- `Q` and `P` DCB receive sizes are client/fixture invariants because physical SIO does not expose Atari DCB byte counts to the device; firmware validates only observable AUX, command, checksum, state, and data.
- A local timeout does not cancel an accepted request. A later call observes `P`; a valid terminal `R` consumes the response. Retrying remains an application decision based on operation semantics.
- The ESP32 profile owns GPIO/UART sequencing and boot projection; the library owns only the application channel; AltirraSDL and NetSIO are separate conformance adapters.
- The native BASIC `N:` handler owns only Atari CIO/IOCB adaptation. It maps each IOCB to a native NetworkService handle over `0x7F`, not an Atari-specific network slot; it must not address `0x71`–`0x78`, translate legacy `O/C/R/W/S`, or invoke `LegacyTransport`.

### UX Design Requirements

None. This scope has an operator/configuration workflow but no standalone UX design contract.

### FR Coverage Map

FR1: Epic 2 - Native `0x7F` application channel.

FR2: Epic 2 - Exact packet-native `Q`/`W`/`P`/`R` contract.

FR3: Epic 2 - Public cc65 backend, polling, and PROC hook.

FR4: Epic 1 - Standard Atari `D1:`–`D8:` ATR drive experience.

FR5: Epic 1 - Config/normal boot-mode disk projection.

FR6: Epic 2 - Public-API cc65 guest acceptance.

FR7: Epic 2 - Replace SLIP/padded/`0x71` paths across Atari adapters.

FR8: Epic 1 - Canonical fixtures and disk bootstrap scenarios.

FR9: Epic 3 - Official v1 physical SIO deployment and proof.

FR10: Epic 3 - Operator diagnostics and evidence-oriented documentation.

FR11: Epic 2 - Native BASIC CIO `N:` handler using public NIO handles.

## Epic List

### Epic 1: Atari boots and uses NIO-backed ATR drives

Atari users can boot the selected configuration ATR as `D1:` and use configured URI-backed ATR media through standard `D1:`–`D8:` SIO behavior.

**FRs covered:** FR4, FR5, FR8

### Epic 2: Atari applications and BASIC use native NIO services

**Status: done.** Stories 2.1–2.5 are complete; platform and physical reset
verification is deferred to Epic 3.

Atari developers can use the public cc65 NIO API and BASIC users can use native `N1:` URI opens; both reach the same modern services through packet-native `0x7F`, without legacy transport or compatibility adapters.

**FRs covered:** FR1, FR2, FR3, FR6, FR7, FR11

### Epic 3: Operators can deploy and trust physical Atari NIO

Operators can build, flash, configure, diagnose, and prove the official FujiNet v1 deployment, with virtual conformance clearly separated from physical electrical and timing evidence.

**FRs covered:** FR9, FR10

## Epic 1: Atari boots and uses NIO-backed ATR drives

Atari users can boot the selected configuration ATR as `D1:` and use configured URI-backed ATR media through standard `D1:`–`D8:` SIO behavior.

**Status:** done (2026-10-21). Story 1.1 fixtures, Story 1.2's single-ingress
DiskService frontend, and Story 1.3's cold-start policy and deterministic
virtual boot gate are complete. This is virtual boot/protocol evidence only;
physical electrical and timing acceptance remains Epic 3.

### Story 1.1: Freeze Atari ATR disk conformance fixtures

As a maintainer,
I want literal, implementation-independent fixtures for Atari boot and ATR disk traffic,
So that every SIO adapter implements the same standard disk behavior before real media code is added.

**Acceptance Criteria:**

**Given** accepted DiskService ATR behavior and the legacy firmware only as a reference source,
**When** the disk v1 conformance matrix is authored,
**Then** it fixes supported commands, sector numbering, byte counts, boot-sector geometry, status/error outcomes, and `D1:`–`D8:` routing for config and normal boot modes,
**And** it explicitly excludes formatting, PERCOM, high-speed SIO, and non-ATR media.

**Given** the matrix,
**When** canonical vectors and manifests are added under `integration-tests/atari-sio`,
**Then** they are literal SIO expectations rather than generated by production framing code,
**And** they cover boot, mounted ATR read/write/status, invalid sector/command paths, and config-versus-restored-slot selection.

**Given** a firmware, NetSIO, or AltirraSDL adapter,
**When** it consumes a fixture projection,
**Then** it reports scenario identifiers,
**And** the projection makes no physical electrical or timing claim.

### Story 1.2: Serve standard Atari ATR drives through DiskService

As an Atari user,
I want mounted ATR images to behave as standard `D1:`–`D8:` drives,
So that boot software and ordinary disk applications work without FujiBus awareness.

**Acceptance Criteria:**

**Given** the approved disk v1 matrix,
**When** a standard supported disk SIO command targets `D1:`–`D8:`,
**Then** the Atari disk frontend maps it directly to the corresponding DiskService slot,
**And** it never routes sector traffic through DiskDevice, FujiBus framing, or LegacyTransport.

**Given** mounted writable and read-only ATR media,
**When** supported read, write, and status operations occur,
**Then** data, geometry, protection, and standard SIO success/error behavior match the fixture,
**And** unsupported disk commands remain outside the v1 surface.

**Given** a disk request at `0x7F` or an NIO request at a disk device ID,
**When** the multiplexer dispatches it,
**Then** it rejects/correctly isolates the wrong plane,
**And** no disk parser consumes application-channel traffic.

### Story 1.3: Boot the selected configuration or mapped ATR disk

As an Atari operator,
I want config mode to boot the supplied configuration ATR and normal mode to boot my chosen mapped drive,
So that FujiNet-NIO is usable as the machine's only disk peripheral.

**Acceptance Criteria:**

**Given** `boot.mode=config` and a valid flashed configuration ATR URI,
**When** Atari startup probes `D1:`,
**Then** the disk frontend serves that ATR using the Story 1.1 boot fixture,
**And** the ATR contains the configuration and acceptance programs required by this feature.

**Given** normal boot mode with restored URI-backed slot mappings,
**When** startup and later applications address `D1:`–`D8:`,
**Then** each device ID resolves to its configured DiskService slot,
**And** the configuration boot image does not overwrite a restored active boot slot.

**Given** the packaged boot ATR,
**When** its build is run in the supported workspace environment,
**Then** the generated media is reproducible and its boot scenarios run in the configured virtual Atari environment.

## Epic 2: Atari applications and BASIC use native NIO services

Atari developers can use the public cc65 NIO API and BASIC users can use native `N1:` URI opens; both reach the same modern services through packet-native `0x7F`, without legacy transport or compatibility adapters.

### Story 2.1: Implement the bounded native Atari NIO client backend

As an Atari application developer,
I want the public NIO library to exchange one bounded packet-native request and response over `0x7F`,
So that my code uses the same FujiBus service API as other NIO hosts without SIO framing logic.

**Acceptance Criteria:**

**Given** the literal NIO fixtures,
**When** the Atari backend performs a request,
**Then** it implements optional idle-only `Q`, idle-only `W`, fixed `P`, and exact `R` with the stated AUX/DCB client invariants,
**And** it enforces the 512-byte v1 limit without SLIP, padding, or implicit segmentation.

**Given** a pending or ready response, a malformed command, a wrong `R` AUX length, or a client-side terminal `R` interruption,
**When** the backend observes the state machine,
**Then** it follows the adopted one-outstanding-request and consume/retain rules,
**And** it does not add cancellation commands, transaction IDs, or automatic application retries.

**Given** a normal application that does not call capability discovery,
**When** it uses the backend,
**Then** it uses the 512-byte baseline,
**And** an opt-in caller can use the lesser of its compiled capacity and the `Q` maximum.

**Given** any change under `repos/fujinet-nio-lib`,
**When** the story is verified,
**Then** complete `make check` passes,
**And** focused host-side wire tests cover the new Atari backend.

### Story 2.2: Serve packet-native NIO on the Atari SIO channel

As an Atari NIO client,
I want the FujiNet channel to route native `0x7F` transactions into existing FujiBus services,
So that Clock, Network, File, and Disk work without legacy adapters.

**Acceptance Criteria:**

**Given** a valid `0x7F` `W` request,
**When** the Atari SIO ingress multiplexer receives it,
**Then** it dispatches exactly one packet-native FujiBus request to the core,
**And** it holds only one NIO transaction until valid terminal `R` or reset.

**Given** `Q`, `P`, and `R` traffic,
**When** the channel responds,
**Then** observable AUX/state/checksum rules and fixed reply sizes match the canonical fixtures,
**And** device validation does not claim visibility of the Atari DCB byte-count field.

**Given** existing Atari SLIP/padded-read/`0x71` implementations and profile selection,
**When** the native channel is enabled,
**Then** the v1 path removes those aliases and framing behaviors from conformance,
**And** retained historical legacy tests cannot satisfy v1 acceptance.

### Story 2.3: Establish independent virtual Atari NIO parity

As a maintainer,
I want NetSIO and AltirraSDL to independently execute the native channel scenarios,
So that protocol regressions are found before a physical Atari run.

**Acceptance Criteria:**

**Given** the canonical fixture projections,
**When** NetSIO and AltirraSDL run NIO and disk scenarios,
**Then** each independently implements the `0x7F` contract and reports the same scenario identifiers,
**And** neither reuses the production framer as its fixture oracle.

**Given** the old `0x71` alias, SLIP framing, and padded reads,
**When** virtual conformance executes,
**Then** those paths are absent from native v1 scenarios,
**And** an old-path pass cannot be reported as a native conformance pass.

**Given** the config ATR and approved fixture harness,
**When** the virtual environment boots and runs its disk/NIO fixture scenarios,
**Then** disk bootstrap, native channel traffic, and recovery scenarios succeed,
**And** the result is labeled protocol/scheduling evidence only.

### Story 2.4: Deliver public-API Atari NIO guest acceptance

As an Atari application developer,
I want a cc65 acceptance XEX on the configuration ATR,
So that I can verify the supported public API and recovery behavior on each Atari target.

**Acceptance Criteria:**

**Given** the public Atari NIO backend and a booted configuration ATR,
**When** the guest XEX runs,
**Then** it performs verified Clock, File persistent write/read, Network open/write/read/close, and Disk read/write exchanges,
**And** it contains no application-owned SIO framing implementation.

**Given** delayed Network readiness,
**When** the guest uses default polling,
**Then** it reaches the response through `P`,
**And** an optional application-owned PROC path only latches a notification then confirms with `P` before `R`.

**Given** rejected `W`, malformed-length `R`, interrupted terminal `R`, and device reset scenarios,
**When** the guest recovers,
**Then** it demonstrates the specified subsequent successful exchange,
**And** it never reports an uncertain timed-out operation as safely retried.

### Story 2.5: Deliver native BASIC URI networking

**Status: done** (closure evidence in the feature-specific Story 2.5 record).

As an Atari BASIC user,
I want to open a supported URI through `N1:` syntax,
So that I can use modern FujiNet networking from BASIC without a legacy FujiNet transport.

**Acceptance Criteria (rebaselined 2026-10-25):**

**Given** the user's supported DOS startup, **when** the relocatable CA65
handler is installed, **then** it initializes its resident state, reserves its
whole allocation below adjusted `MEMLO`, registers `HATABS`, and survives
subsequent BASIC/DOS program loads. Installation is idempotent for its own
handler, rejects a foreign `N:` without replacement, and rolls back failures.
MyDOS 4.53/4 is the first verified environment. The configuration ATR retains
its existing transient configuration and boot-selection contract and does not
install this handler as a Story 2.5 requirement.

**Given** BASIC opens an `N1:` URI, **then** modes 4, 8 and 12 select native
GET, PUT and POST respectively; output sets `BODY_UNKNOWN`, and the returned
service handle is owned by the IOCB. Exhaustion and errors preserve ownership
of other IOCBs. GET/PUT, STATUS and CLOSE use native `$7F` NetworkService,
bounded 128-byte caches, ordered partial acknowledgements and exactly one
terminal zero-length commit before the first STATUS, read or CLOSE. Uncertain
writes or commits are never automatically replayed. Foreground calls are
serialized, and the CIO error/status table and behavior across all supported
IOCBs are recorded and tested.

**Given** a NetSIO host-reset event, **then** sessions owned by that Atari
client are reclaimed without flushing or committing abandoned output. A cold
boot reinstalls cleanly through DOS startup. Stale remote handles return
appropriate CIO errors, release local ownership safely and permit a later OPEN
without replaying uncertain operations or affecting another client.

Genuine OS warm-start persistence and physical SIO reset detection are
**deferred to platform/physical acceptance**. They are not established by the
NetSIO reset-event test and do not block Story 2.5 closure.

**Given** genuine DOS/BASIC acceptance, **then** READ, PUT and POST fixtures
execute against production NetworkDevice over native `$7F`, including correct
bytes and exactly-once commit, and installer, error, recovery and RAM gates
pass. The permanent allocation, including code, data, BSS, buffers, zero page
and retained workspace, is at most 3,072 bytes. MyDOS BASIC READ/PUT/POST acceptance is verified through the embedded AltirraSDL
adapter as well as NetSIO. Neither virtual result establishes physical SIO
reset detection or electrical behavior.

**Follow-on compatibility targets:** Atari DOS 2.0S and 2.5, SpartaDOS and
SpartaDOS X, using the same resident module with DOS-appropriate installation.
These environments are not yet verified. Future `config://` access to files on
the original configuration/boot disk after selecting a DOS is a deferred idea,
not an implemented feature or current acceptance requirement.

## Epic 3: Operators can deploy and trust physical Atari NIO

Operators can build, flash, configure, diagnose, and prove the official FujiNet v1 deployment, with virtual conformance clearly separated from physical electrical and timing evidence.

### Story 3.1: Build the official Atari FujiNet v1 deployment profile

As an operator,
I want a documented official 16 MB Atari v1 build and diagnostics surface,
So that I can install the intended firmware and verify its selected configuration before testing a real Atari.

**Acceptance Criteria:**

**Given** the supported workspace environment,
**When** the Atari v1 profile is built,
**Then** it selects `FN_BUILD_ATARI_FUJIBUS_SIO`, the configuration ATR inputs, and packet-native Atari channel,
**And** it does not enable legacy transport, high-speed SIO, or a legacy network alias.

**Given** a built/flashed device,
**When** an operator uses the documented diagnostics path,
**Then** it can inspect boot mode, config ATR/URI mappings, active disk slots, native NIO capability/profile information, and actionable failure state,
**And** configurable values have Python-tool support as required by workspace cross-repository rules.

### Story 3.2: Validate physical SIO electrical and timing behavior

As a hardware maintainer,
I want the official v1 board's SIO electrical behavior measured against the physical contract,
So that the Atari can safely share its bus with the device at standard speed.

**Acceptance Criteria:**

**Given** the official v1 board, a stated Atari model, cable, and peripheral topology,
**When** physical SIO is exercised at 19,200 baud,
**Then** CMD/UART sequencing, ACK/COMPLETE timing, data/checksum timing, and reset recovery are recorded,
**And** DATA OUT and PROC are verified released-idle open-drain with no contention.

**Given** an installed resident N: handler on a supported platform,
**When** genuine OS warm start and physical host reset are validated,
**Then** record HATABS, MEMLO, handler usability, and how remote sessions are
reclaimed without flushing or committing abandoned output. These behaviors
are unverified by the virtual Story 2.5 reset-event test.

**Given** unused SIO lines INT, MTR, CKI, and CKO,
**When** the v1 profile runs,
**Then** measurements show they are electrically benign and carry no NIO semantics,
**And** no high-speed claim is made.

### Story 3.3: Publish operator acceptance and evidence

As an Atari FujiNet-NIO operator,
I want one procedure for configuration, BASIC networking, disks, and recovery,
So that I can reproduce a supported deployment and understand what has been proven.

**Acceptance Criteria:**

**Given** the completed virtual and physical acceptance runs,
**When** the operator documentation is published,
**Then** it covers flash/build, boot-mode choice, URI-to-drive mapping, configuration ATR launch, guest XEX, native BASIC `N:` usage, diagnostics, and recovery,
**And** it explicitly distinguishes emulator/NetSIO proof from real-bus proof.

**Given** a real Atari acceptance run,
**When** its evidence is recorded,
**Then** it identifies board/Atari/cable topology, firmware/client commits, fixture scenario identifiers, electrical/timing observations, disk boot, Clock/Network/File/Disk service results, and polling/PROC results,
**And** failures and limitations are recorded without claiming broad legacy FujiNet compatibility.
