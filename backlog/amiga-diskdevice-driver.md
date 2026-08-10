# Amiga DiskDevice driver over FujiBus

Status: `IN PROGRESS`

Repositories:

- `repos/fujinet-nio` — protocol, architecture, and contract documentation
- `repos/fujinet-nio-lib` — shared client/session library and test vectors
- `repos/fujinet-nio-driver` — MS-DOS/driver-side implementation patterns
- Jeff's Amiga repository — Amiga driver integration and review reference

## Goal

Deliver a read-only Amiga DiskDevice driver over the documented FujiBus
channel, then make an explicit raw-state architecture decision before adding
write or hot-swap behavior.

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

### 8. Write, cache, flush, and media-change policy — `TODO`

- [ ] Define cache ownership and dirty-state behavior.
- [ ] Define flush ordering and failure semantics.
- [ ] Define media-change detection and acknowledgement.
- [ ] Add write support only after those contracts are stable.
- [ ] Add hot-swap behavior and tests.

Exit criteria: write and media-change behavior is contract-defined, tested,
and does not rely on undocumented singleton state.

### 9. Faster backends — `TODO`

- [ ] Develop the Pico/native packet backend.
- [ ] Develop faster-channel backends behind the same packet/session contract.
- [ ] Add backend capability tests and performance measurements.

## Review points

Stop for user review after stages 4, 5, and 6. Do not advance past the raw-
state gate by silently carrying an unresolved architectural assumption.
