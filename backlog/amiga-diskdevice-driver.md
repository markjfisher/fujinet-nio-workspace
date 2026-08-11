# Amiga DiskDevice driver over FujiBus

Status: `IN PROGRESS`

Repositories:

- `repos/fujinet-nio` — protocol, architecture, and contract documentation
- `repos/fujinet-nio-lib` — shared client/session library and test vectors
- `repos/fujinet-nio-driver` — MS-DOS/driver-side implementation patterns
- Jeff's Amiga repository — Amiga driver integration and review reference

## Goal

Deliver an Amiga DiskDevice driver over FujiBus whose units follow the same
catalogue-slot-to-active-drive model as Atari, BBC, and MS-DOS. Direct URI
mounting remains available as an expert/diagnostic path.

## Library change gate

Any change under `repos/fujinet-nio-lib` must run:

```text
make check
```

This builds every configured library target and then runs the host-side wire,
session, and public archive-link tests. If a required cross-toolchain is not
available, record the exact unavailable target/toolchain in the change review;
do not silently treat a partial build as an all-target pass.

## Ordered work

### 1. Documentation and contracts — `DONE`

- [x] Resolve Jeff's responses and update the architecture/protocol documents.
- [x] Define use of `fujinet-nio-lib` for shared packet/session behavior.
- [x] Mark PaulaNet as approach-level reference material only.
- [x] Rename the MS-DOS repository and update local/remote references.
- [x] Add DiskDevice contract clarifications and test vectors.

### 2. Shared codec and target policy — `DONE`

- [x] Implement and test the shared DiskDevice codec.
- [x] Cover the 12-byte and 13-byte Info response forms with named tests.
- [x] Keep cc65-specific workspace handling from constraining non-cc65 builds.
- [x] Document the cross-target implementation rule in `repos/fujinet-nio-lib/AGENTS.md`.

### 3. Shared channel/session interface — `DONE`

- [x] Define the byte-channel/session contract.
- [x] Route stream transports through the shared session implementation.
- [x] Add RS-232/session wire tests for escaping, timeout, busy, and oversized frames.
- [x] Add a public API library-link test.
- [x] Validate Atari, Linux, and the host test suite where toolchains are available.

### 4. MS-DOS driver repository relocation — `IN REVIEW`

- [x] Move the existing MS-DOS implementation, headers, and tests under
      `repos/fujinet-nio-driver/msdos/`.
- [x] Retain root `make`, `make tests`, and `make clean` entry points.
- [x] Preserve the generated artifact at `build/dos/fujinet.sys`.
- [x] Update workspace build, QEMU image, 86Box, and workflow documentation
      consumers to use the renamed driver repository.
- [x] Remove the obsolete `fujinet-msdos` workspace submodule and its legacy
      build/FTP targets.
- [x] Validate `msdos-driver`, `msdos-tests`, `qemu-msdos-image`, and the full
      `msdos` workflow.

Exit criteria: the relocation is reviewed and committed with the documented
MS-DOS driver artifact and integrated workflow intact.

### 5. Amiga driver skeleton — `IN REVIEW`

Library-side prerequisite:

- [x] Replace the duplicate Amiga SLIP path with the shared channel/session interface.

Driver-side work:

- [x] Create the Amiga driver/channel skeleton under
      `repos/fujinet-nio-driver/amiga/` after the MS-DOS relocation is reviewed.
- [x] Map one read-only DiskDevice unit to slot 1.
- [x] Connect the driver to the shared session contract through the typed
      `fujinet-nio-lib` DiskDevice API and its Amiga RS-232 transport.
- [x] Add named host contract tests and link the production adapter against a
      built `fujinet-nio-lib` archive.
- [x] Complete the native build verification with the Amiga-specific toolchain
      and memory model.

The native Exec device entry points and build target are implemented. The
resident device links against a dedicated `fujinet-nio-amiga-driver.a` variant
that uses explicit device lifecycle instead of application `atexit()` cleanup.
The native 68000 build, portable policy tests, production-adapter archive-link
test, existing MS-DOS tests, and complete library `make check` pass.

Exit criteria: the driver builds with the Amiga toolchain and can issue a
well-formed read-only Mount request for slot 1.

### 6. Read-only standard ADF validation — `IN REVIEW`

- [x] Validate Mount using the standard ADF profile.
- [x] Validate Info and geometry.
- [x] Validate block/sector reads.
- [x] Validate Dir.
- [x] Validate Type.
- [x] Add or retain deterministic protocol vectors and driver-side tests.
- [ ] Make the native Amiga serial receive path honor the session timeout when
      a peer remains silent; its current fallback performs a blocking one-byte
      `serial.device` read. Shared session malformed/timeout vectors are
      covered, but this hardware-channel deadline still needs implementation
      and native validation.

The Amiberry acceptance test creates a deterministic 880 KiB ADF containing
`KNOWN.TXT`, mounts it through the native device, and checks both `Dir` and
`Type` output. During integration, filesystem task stacks exposed the 1 KiB
stack-local DiskDevice codec reply buffer. The dedicated resident-driver
library variant now explicitly uses synchronous static codec storage; normal
Amiga application and MS-DOS builds keep their local-buffer policy.

Exit criteria: all read-only operations pass against the agreed ADF profile,
with documented behavior for malformed responses and media errors.

### 7. Reentrant resident-driver client state — `IN REVIEW / REQUIRED BEFORE STAGE 8`

Stage 6 exposed a concrete conflict rather than a theoretical architecture
choice. Function-local 1 KiB DiskDevice codec buffers overflow caller-owned
AmigaDOS filesystem task stacks. Moving those buffers to static storage avoids
the stack failure but makes the resident driver non-reentrant, while the
common raw transport and parser contexts are already singleton state.

The temporary `FN_DISK_STATIC_BUFFERS` policy has now been replaced by an
explicit driver-owned context. The full native concurrent-caller and
regression runs pass.

- [x] Define an explicit client/context object for the non-cc65 DiskDevice raw,
      transport, parser, request, response, and codec scratch state.
- [x] Make each resident driver unit own its context and scratch storage, so
      filesystem callers do not supply the stack space and separate units or
      requests do not share mutable codec state.
- [x] Route the Amiga driver adapter through the context-based API without
      changing the existing public API used by 8-bit clients.
- [x] Define and document request serialization and ownership at the Exec
      device boundary, including whether one unit may queue or overlap I/O.
- [x] Add a named host test that interleaves two independent client contexts
      and proves request, response, parser, and codec state cannot cross-talk.
- [x] Add an Amiga driver test exercising requests from distinct caller tasks
      or an equivalent native harness that demonstrates the ownership rule.
- [x] Remove `FN_DISK_STATIC_BUFFERS` from the Amiga-driver build after the
      driver-owned context replaces both large stack locals and shared static
      buffers.
- [x] Retain all-target `make check`, native driver builds, and the standard
      ADF Amiberry acceptance test as regression gates.

Exit criteria: the resident driver does not rely on large caller-stack codec
buffers or mutable process-global DiskDevice request state, and tests
demonstrate isolation between at least two independent client contexts.

### 7a. Standalone Jeff handoff — `IN REVIEW / REQUIRED BEFORE STAGE 8`

The driver and library must be consumable as sibling git submodules without
the FujiNet NIO workspace scripts or environment setup.

- [x] Expose and document the `fujinet-nio-lib` Amiga application and resident
      driver build targets, prerequisites, and artifacts.
- [x] Document the sibling-submodule layout and `LIB_ROOT` override supported
      by `fujinet-nio-driver`.
- [x] Document independent Amiga driver build, host tests, installation,
      MountList configuration, and the initial mount sequence.
- [x] Record the compatible driver/library revisions and current limitations.
- [x] Validate the default sibling build using only an explicit Amiga
      toolchain `PATH`, without sourcing workspace scripts.
- [x] Validate a non-sibling library location through `LIB_ROOT`.

Validation (2026-08-10): both the default sibling layout and an explicit
absolute `LIB_ROOT` completed `make -B amiga` with a minimal system plus Amiga
toolchain `PATH`. The builds ran the portable driver contract and library-link
tests, rebuilt the resident Amiga library, and linked `fujinet-disk.device`
and `fujinet-mount` without workspace scripts.

Exit criteria: a consumer can add both repositories as git submodules, build
the resident device and mount utility, install the documented files, and mount
the read-only standard ADF profile without relying on workspace tooling.

### 8. Write, cache, flush, and media-change policy — `IN PROGRESS`

The original one-unit skeleton was an implementation milestone, not an Amiga
architecture constraint. Stage 8 must remove that shortcut before completion:
catalogue slots 0–255 are persistent choices, while Amiga units 0–7 map to
active DiskDevice slots 1–8 and appear as `DN0:`–`DN7:`.

- [x] Define no driver block cache; NIO owns buffering and dirty state.
- [x] Define `CMD_UPDATE`/`ETD_UPDATE` as DiskDevice flush barriers,
      `CMD_CLEAR`/`ETD_CLEAR` as no-flush cache invalidation, and Exec
      `CMD_FLUSH` as queued-request cancellation only.
- [x] Define additive DiskDevice v1 `Flush (0x0E)` and transactional
      unmount/replacement behavior.
- [x] Define deterministic local media counts and persistent change
      notifications; out-of-band slot changes remain unsupported.
- [x] Test dirty set/clear, clean and failed flush, partial multi-write,
      failed removal/replacement, and exact 0x0E vectors in NIO.
- [x] Add context and legacy library APIs for write, flush, unmount, and
      clear-changed; run sourced `make check`.
- [x] Add writable standard-ADF mounting, writes, ETD validation, FIFO queue
      policy, update/clear/flush, eject, and media notification behavior.
- [x] Pass portable queue/media policy tests, native builds, and Amiberry
      writable persistence/replacement regressions.
- [x] Refresh standalone documentation, compatible revisions, and known
      limitations; stop for review before Stage 9.
- [x] Replace the singleton resident unit/media/queue/change state with eight
      independent Amiga units sharing one serialized physical session.
- [x] Map Amiga unit N to active DiskDevice slot N+1 and provide MountLists
      `DN0` through `DN7`.
- [x] Add `fujinet-mount <catalog-slot> <drive> [RW|RO]` and
      `fujinet-mount --eject [drive]` using Slot Catalog and the shared
      `config-nio/mappings` contract. The `nio-config` port may later present
      these operations through the common `FMOUNT`/`FUMOUNT` command surface.
- [x] Retain direct URI mounting under the explicit
      `fujinet-mount --uri <drive> <URI> [RW|RO]` compatibility form.
- [x] Prove simultaneous multi-drive access, per-unit protection/change state,
      independent eject/replacement, and mapping persistence in host/native
      and Amiberry tests.
- [x] Resolve the apparent multi-unit state regression: the resident state
      remained intact, while the diagnostic utility reused a completed
      `IOExtTD` without restoring its Exec message state. Normalize the
      request before every status `DoIO`; the complete `amiga-tests` gate now
      preserves DN1 across writable DN2 activity.
- [x] Define and verify Phase 1's user-visible replacement operation for an
      already mounted DNx: explicitly dismount the DOS handler, replace the
      device media, and recreate the handler. Attempts to hide that lifecycle
      inside the transitional mount tool reproduced `You MUST replace volume`
      and out-of-range validation requesters and were removed.

The Amiberry durability regression uses the explicit, safe sequence: dismount
the old DN2 handler, replace the device media, and recreate the handler. Phase 2
owns a requester-free single-command implementation in standard
`FMOUNT`/`FUMOUNT`; this remains a visible acceptance gate, not a hidden retry
or a claimed seamless Phase 1 operation. The complete Amiberry suite retains
framebuffer evidence showing the explicit replacement, persisted content, and
per-unit state without a requester or Guru.

Exit criteria: write and media-change behavior is contract-defined, tested,
and does not rely on undocumented singleton state.

### Deliberate Stage 8 boundary

Stage 8 supports standard 880 KiB ADF media only: 512-byte sectors, 1760
sectors, 80 cylinders, two heads, and 11 sectors per track. The `DN0`–`DN7`
MountLists describe that profile and are not a general geometry mechanism.

General inferred geometry and consolidation onto the standard
`nio-core-apps` `FMOUNT`/`FUMOUNT` interface are tracked in
[`amiga-diskdevice-phase-2.md`](amiga-diskdevice-phase-2.md). The private
`fujinet-mount` program is transitional and must not become the permanent
parallel user interface.

### 9. Stage 8 hardening and Phase 2 foundation — `IN PROGRESS / HIGH PRIORITY`

The Stage 8 happy path is working, but the clean review of the last five
`fujinet-nio-driver` commits found failure-path, lifecycle, and test-boundary
gaps that must be closed before Phase 2 builds on this device. The recent
intermittent Guru (`Error 8000 0004`) was reproduced as a caller-stack-risk
area and fixed by moving the 768-byte catalog URI scratch buffer from
`BeginIO()` to the resident device base. That fix passed four focused
Amiberry runs and the complete `amiga-tests` gate, but it does not by itself
prove the rest of the Stage 8 contract.

#### Evidence and tickets

- [ ] **Replacement state consistency:**
      `amiga/common/fujinet_disk_driver.c:109-147` retains local media state
      when NIO has already removed the old image and the replacement then
      fails to open, probe, or validate. `fujinet-nio/src/lib/disk/disk_service.cpp:78-181`
      confirms that replacement removes the old image after a successful flush
      before attempting the new image. Add an explicit state transition and
      tests for failed replacement after remote removal, invalid geometry, and
      failed follow-up Info.
- [ ] **Eject change acknowledgement:** `fujinet_disk_eject()` increments the
      local change count but never calls `clear_changed()` or sets
      `change_ack_pending`, unlike Mount. NIO can therefore remain marked
      changed indefinitely after eject. Add success, failure, and retry tests.
- [ ] **Mapping persistence failure semantics:**
      `amiga/disk.device/fujinet_disk_device.c:369-389` mounts before writing
      `config-nio/mappings`, while `:489-496` ejects before clearing it. A
      failed AppStore write can report an error while media and persistent
      mapping disagree. Define rollback or authoritative-state semantics,
      implement them, and inject read/write failures in host/native tests.
- [ ] **Change-registration ownership and cleanup:** `TD_ADDCHANGEINT`
      retains a raw caller `IORequest *` in resident memory. `device_close()`
      and expunge do not clean registrations, so a later transition can call
      `Cause()` through a freed request. Define caller/device ownership,
      cleanup on close/abort/expunge, and test task/request lifetime changes,
      repeated notifications, multiple registrations, and removal.
- [ ] **Bound direct URI requests:** private Mount commands consume
      `io_Data` as an unchecked NUL-terminated string and ignore `io_Length`.
      `fujinet-nio-lib/src/common/fn_disk.c` subsequently calls `strlen()`.
      Validate request length and termination, copy queued URI data into
      device-owned storage, and test malformed and queued requests.
- [ ] **Test the production queue:** the resident device now uses the shared
      `fujinet_io_queue_t` abstraction, so portable FIFO tests cover the
      production queue implementation. An integrated native harness still
      needs concurrent BeginIO, FIFO barriers, AbortIO, and multi-unit draining.
- [ ] **Test media notifications at the Exec boundary:** add tests for
      `TD_ADDCHANGEINT`, repeated `Cause()`, `TD_REMCHANGEINT`, AbortIO,
      multiple registrations, per-unit registrations, and TD_REMOVE. Current
      Amiberry tests only inspect status and successful workflow output.
- [ ] **Expand Amiberry failure coverage:** add acceptance cases for failed
      flush, failed replacement after removal, invalid replacement geometry,
      failed mapping persistence, notification lifecycle, STOP/START,
      CMD_FLUSH, AbortIO, malformed URI requests, and transport reopen while
      requests are queued. Assert the currently unasserted `--uri` unit-7
      operation is now asserted; failed replacement preservation is also
      covered, while the remaining failure cases are still open.
- [ ] **Native serial deadline:**
      `repos/fujinet-nio-lib/src/platform/amiga/fn_transport.c:70-145`
      ignores the shared session `timeout_ms` and blocks in a one-byte
      `serial.device` read after an empty query. Implement a deadline-aware
      native receive path and validate silent-peer timeout behavior on the
      native Amiga build/harness.
- [ ] **CLI contract:** usage advertises `--eject [DRIVE]`, while
      `fujinet-mount.c` accepts only `--eject DRIVE`. Align documentation and
      parser behavior and add a parser test.

#### Stage 9 acceptance gates

- [ ] No failed replacement leaves local and NIO media state divergent.
- [ ] Mount, replacement, and eject media-change flags are acknowledged or
      explicitly retained for retry with deterministic tests.
- [ ] Persistent mappings have defined failure semantics and cannot silently
      disagree with active media.
- [ ] No resident notification registration can outlive its request safely;
      close, abort, removal, and expunge ownership is documented and tested.
- [ ] All asynchronous/queued device requests have bounded input lifetimes
      and no large caller-stack scratch allocation.
- [ ] Production queue and Exec device boundary have integrated host/native
      coverage, not only standalone policy tests. The native smoke command now
      covers real DoIO dispatch for change count, STOP/START, CMD_FLUSH, and
      TD_REMCHANGEINT; asynchronous cancellation and notification lifetime
      coverage remain open.
- [ ] Native serial receive honors the shared timeout contract.
- [ ] Focused Amiberry stability passes repeatedly, the complete `amiga-tests`
      gate passes, `fujinet-nio` tests pass, and library changes pass sourced
      `make check` with all configured targets.

Exit criteria: Stage 8 behavior is failure-safe at the NIO, library, Exec
device, and native transport boundaries; the tests demonstrate state,
ownership, notification, queue, mapping, and timeout behavior; and Phase 2 can
reuse the device without inheriting an undocumented lifecycle or rollback
assumption.

#### Stage 9 implementation log

- [x] Make NIO replacement transactional through image preparation and
      validation before committing removal of the old image. Added a host test
      proving a missing replacement preserves the active image and flushed
      state.
- [x] Clear Amiga local media state after a post-mount validation/Info/flush
      failure and acknowledge eject media changes, including retry coverage in
      `test_fujinet_disk_driver`.
- [x] Move direct URI input into resident device-owned storage and validate
      `io_Length` plus NUL termination before queue processing.
- [x] Remove change registrations when their request closes and discard all
      retained registrations during expunge; integrated lifecycle tests remain
      outstanding.
- [x] Implement a timer-backed native Amiga serial one-byte receive deadline
      that honors the shared session timeout. Native compilation and the
      focused Amiberry workflow pass; a silent-peer native harness remains to
      be added.
- [x] Align `fujinet-mount --eject` parser behavior with its documented
      optional-drive syntax.
- [x] Stage catalog mapping bytes before the corresponding mount/eject and
      restore the previous mapping when the media operation fails. Explicit
      AppStore failure injection and crash/restart consistency tests remain
      outstanding before this item can be considered complete.
- [x] Integrate the shared FIFO queue into the resident device and add a native
      Amiberry Exec boundary smoke command covering DoIO, STOP/START, CMD_FLUSH,
      and TD_REMCHANGEINT.
- [ ] Add a complete resident-device harness for request lifetime,
      notifications, AbortIO, queue cancellation, mapping persistence,
      malformed URI requests, and transport reopen.
- [ ] Run repeated focused stability and complete `amiga-tests` validation
      after all Stage 9 changes, then update this section with evidence and
      close only the acceptance items actually demonstrated.

Validation snapshot (2026-08-11): the transactional replacement test and
Amiga driver policy tests pass; `fujinet-nio` passes 262 C++ tests plus 23
Python tests; sourced `repos/fujinet-nio-lib make check` passes all configured
targets and wire/context/link tests; the native Amiga driver builds; the full
`scripts/build.sh amiga-tests` gate passes all three Amiberry cases; focused
`diskdevice-adf` also passes direct unit-7 mounting, failed replacement
preservation, and the native Exec boundary smoke command. Stage 9 remains open
because full asynchronous Exec cancellation/notification coverage, AppStore
failure injection, and the silent-peer native timeout harness are not yet
present.

Follow-up (2026-08-11): added the initial host
`test_fujinet_exec_boundary` contract harness under
`repos/fujinet-nio-driver/amiga/tests/`. It is wired into `make tests` and
currently validates queue selection, STOP/START, queued flush/abort removal,
repeated change-registration delivery, removal, and close cleanup. It does not
yet exercise the production resident Exec-list implementation or native Amiga
message-port/interrupt ABI; those remain the next expansion decision.

Follow-up (2026-08-11): the resident device now uses `fujinet_io_queue_t`
directly, with native queue-node allocation and cleanup. Added
`fujinet-mount --boundary DRIVE`, which executes real Amiga `DoIO` requests for
`TD_CHANGENUM`, `CMD_STOP`, `CMD_START`, `CMD_FLUSH`, and `TD_REMCHANGEINT`.
The disk Amiberry case asserts its pass marker, direct unit-7 mount, and failed
replacement state preservation. Native asynchronous AbortIO and change
notification lifetime tests remain the next boundary work.

## Review points

Stop for user review after stages 4, 5, and 6. Do not advance past the raw-
state gate by silently carrying an unresolved architectural assumption.
