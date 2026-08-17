# Amiga HDF and RDB media support

Status: `TODO`

## Goal

Extend the completed DD/high-density-floppy DiskDevice path to validated
whole-volume HDF and partitioned RDB media without changing existing floppy
behavior or creating a second user-facing mount workflow.

The durable design constraints and alternatives are documented in
[`docs/amiga/disk-media-architecture.md`](../docs/amiga/disk-media-architecture.md).

## Dependencies

- Amiga DiskDevice Phase 2 is complete and archived in
  `completed/amiga-diskdevice-phase-2.md`.
- Geometry-changing replacement recovery is hardened before multi-partition
  group replacement is enabled.
- Existing version-1 DD/high-density-floppy mappings and resident-device
  commands remain backward compatible.

## Work

### Replacement recovery prerequisite

- [ ] Define and test rollback when media commit succeeds but inactive
      DosEnvec update or first handler restart fails.
- [ ] Preserve the old mount or return a documented recoverable state without
      leaving stale geometry attached to the new media.

### Discovery and contracts

- [ ] Build fixtures for valid and corrupt whole-volume HDF, single- and
      multi-partition RDB, unusual bounds, and writable media.
- [ ] Define a non-mutating, versioned inspection result that distinguishes a
      raw whole volume from an RDB disk and reports stable partition identity,
      bounds, sector size, DosType, relevant DosEnvec data, boot priority, and
      metadata provenance.
- [ ] Keep the existing media type/sector size/sector count/boot-byte Inspect
      response backward compatible; add partition data rather than overloading
      its boot-byte field.

### Validation and addressing

- [ ] Parse and validate `RDSK`/`PART` checksums, linked lists, block sizes,
      cylinder arithmetic, partition bounds, overlaps, and termination before
      exposing any partition.
- [ ] Define whole-volume HDF metadata ownership when no RDB supplies a
      complete DosEnvec.
- [ ] Audit sector-size support, 32-bit sector/LBA limits, Amiga byte-offset
      overflow, and the supported maximum image size.
- [ ] Add versioned 64-bit operations only if required by the chosen supported
      size boundary.

### Partition bindings and AmigaDOS nodes

- [ ] Represent one mounted host disk as a shared object with explicit
      partition bindings and partition-relative I/O bounds.
- [ ] Deliver explicit one-partition-to-one-`DNx:` selection first; retain the
      option to expose multiple partitions automatically later.
- [ ] Derive each DosEnvec from validated whole-volume or partition metadata
      and serialize it through the existing public helper.
- [ ] Define DOS-device naming, RDB-name sanitisation, collisions, unit
      exhaustion, partial mount failure, and handler ownership.
- [ ] Define supported DosTypes and filesystem-handler policy; treat embedded
      RDB filesystem binaries as a separate trust and lifetime decision.

### Writable lifecycle and persistence

- [ ] Serialize access, dirty state, flush ordering, and errors across writable
      sibling partitions of one host image.
- [ ] Define disk-scoped versus binding-scoped replacement and eject semantics,
      including notification and failure atomicity across affected handlers.
- [ ] Version `config-nio/mappings` to store catalogue slot, RO/RW mode, and a
      stable partition selector while restoring version-1 floppy mappings
      unchanged.
- [ ] Keep `FMOUNT`, `FUMOUNT`, and `FMOUNTRESTORE` as the standard workflow;
      add partition selection without introducing a competing mount tool.

### Verification

- [ ] Add host parser tests for valid, corrupt, overlapping, out-of-bounds, and
      fuzzed RDB metadata.
- [ ] Add native tests for partition translation, overflow rejection, shared
      locking/flush, independent bindings, ABI versioning, and unchanged
      floppy requests.
- [ ] Add focused Amiberry tests for whole-volume HDF and one-/multi-partition
      RDB access, copies to/from `DH0:`, partition-to-partition copies, RO/RW
      enforcement, durability, replacement, notification, concurrency,
      timeout, and requester-free recovery.
- [ ] Add two-process restore coverage for versioned partition mappings and
      unchanged version-1 DD/high-density-floppy mappings.
- [ ] Document the supported HDF/RDB subset and rejected variants only after
      the corresponding acceptance evidence passes.

## Exit criteria

An Amiga user can select a documented supported whole-volume HDF or RDB
partition through the standard catalogue workflow, expose it as a normal
`DNx:` device, use it safely in RO or RW mode, eject/replace/restore it without
desynchronising sibling partitions, and retain all completed DD and
high-density-floppy regressions.
