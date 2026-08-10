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

### 6. Read-only standard ADF validation — `TODO`

- [ ] Validate Mount using the standard ADF profile.
- [ ] Validate Info and geometry.
- [ ] Validate block/sector reads.
- [ ] Validate Dir.
- [ ] Validate Type.
- [ ] Add or retain deterministic protocol vectors and driver-side tests.

Exit criteria: all read-only operations pass against the agreed ADF profile,
with documented behavior for malformed responses and media errors.

### 7. Raw-state architecture gate — `TODO / REQUIRED BEFORE STAGE 8`

The current common client uses singleton raw request/response buffers and
transport/parse contexts. Before writes or hot swap are implemented, choose
one of these outcomes and document it:

- [ ] Refactor the non-cc65 path to an explicit client/context model; or
- [ ] Explicitly accept and document a single-client/single-request invariant,
      including its implications for Amiga units and future concurrency.

This gate is not optional housekeeping. Stage 7 cannot begin until the choice
has been reviewed.

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
