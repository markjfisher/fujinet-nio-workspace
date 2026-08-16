# Amiga DiskDevice Phase 2 — general media and standard tools

Status: `IN PROGRESS`

## Goal

Turn the standard-ADF Stage 8 implementation into the normal FujiNet Amiga
disk experience: the standard `nio-core-apps` tools map persistent catalogue
slots to `DNx:` drives, and the driver/NIO combination supplies the media
geometry and lifecycle mechanics without requiring users to know private
device commands or fixed 880 KiB assumptions.

Stage 8 may be signed off with its documented 512-byte, 1760-sector ADF
profile. That restriction is an implementation boundary to remove here, not a
user-facing convention to preserve.

The media model, RDB/HDF distinction, intended user experience, and delivery
progression are specified in the associated
[`amiga-disk-media-architecture.md`](amiga-disk-media-architecture.md).

## Dependencies

- [x] Stage 8 writable, multi-unit DiskDevice behavior is complete and
      reviewed. The historical writable-DN2 requester failure was traced to
      deferred IORequests entering the private FIFO without `NT_MESSAGE` and
      is covered by an explicit native Exec-boundary regression.
- NIO DiskDevice Info continues to report authoritative sector size and sector
  count inferred by the mounted image handler.

## Standard command ownership

- [x] Make the Amiga build of `nio-core-apps` `FMOUNT` perform the complete
      catalogue-slot-to-`DNx:` operation through `fujinet-disk.device`,
      including RO/RW selection, replacement, local change notification, and
      persistent `config-nio/mappings` updates.
- [x] Provide the corresponding standard `FUMOUNT` operation for an Amiga
      drive, with driver-mediated flush/eject and mapping removal.
- [x] Define Amiga-appropriate arguments (`FMOUNT slot drive [RO|RW]`, where
      drive accepts `DN0:`–`DN7:` or the documented numeric equivalent)
      without forcing BBC or MS-DOS syntax onto Amiga users.
- [x] Move the required resident-device interface into a shared, versioned
      Amiga platform header/library boundary that `nio-core-apps` can consume.
      Treat this as a normal cross-repository build dependency.
- [x] Stop installing or documenting `fujinet-mount` as a second mounting
      application once `FMOUNT`/`FUMOUNT` cover its supported operations.
      Preserve only narrowly named driver diagnostics that are not duplicate
      end-user functions.
- [x] Add tests proving the standard tools cannot bypass or desynchronise the
      resident driver's media state, change counter, protection state, flush,
      or replacement behavior. Existing `diskdevice-adf` proves the resident
      baseline; extend the standard-tool (`FMOUNT`/`FUMOUNT`) path specifically.
- [x] Coordinate replacement with the existing AmigaDOS filesystem handler so
      `FMOUNT` can retire the old volume and rescan the inserted one without a
      `You MUST replace volume`, `Not a DOS disk`, or invalid-block requester.
      The validated mechanism detects the active DOS handler, calls
      `Inhibit(TRUE)`, performs the catalogue/device replacement, then calls
      `Inhibit(FALSE)`; the existing `DNx` handler rescans the new media, so no
      `Assign`/`Mount` recreation is required.

## Media geometry

- [x] Specify which image families can be presented as an Amiga filesystem in
      a whole-disk device, beginning with standard DD and HD ADF profiles and
      separating those from partitioned RDB/HDF media.

- [x] Treat NIO's mounted-media sector size and sector count as authoritative;
      hints may assist raw-image probing but must not override successfully
      inferred geometry.

- [x] Remove the driver's unconditional 1760-sector validation and fixed
      `TD_GETGEOMETRY` result. Validate supported media from the committed NIO
      Info response and retain that geometry independently per unit.

- [x] Define how AmigaDOS receives matching DosEnvec geometry. Do not assume
      that `TD_GETGEOMETRY` rewrites `Surfaces`, `BlocksPerTrack`, `LowCyl`, or
      `HighCyl` from a static MountList.

- [x] Choose and test the mounting strategy for variable media: known geometry
      profiles, dynamically constructed DOS device nodes, or a verified linear
      logical geometry. The choice must preserve existing filesystem layout
      and allocation semantics.

persistent dynamic DeviceNode
+ profile-driven DosEnvec
+ ACTION_DIE to retire active handler
+ update DosEnvec only while dn_Task == 0
+ natural restart on next access

- [x] Replace the eight fixed standard-ADF MountLists as the universal story.
      Static `DN0`–`DN7` files remain explicit DD-ADF compatibility/bootstrap
      assets only; the standard `FMOUNT` path does not require them and creates
      absent nodes dynamically.

- [x] Reject unsupported, malformed, partitioned, or ambiguous images with a
      clear error before announcing insertion; never silently reinterpret an
      image using the 880 KiB defaults.

## Verification

- [ ] Add host tests for inferred geometry, hints, malformed sizes, and
      independent geometry on all eight units.
- [ ] Add native tests for dynamic `TD_GETGEOMETRY` and standard-tool device
      calls.
- [x] Add Amiberry tests mounting at least DD and HD images through catalogue
      slots using `FMOUNT`, accessing them through `DNx:`, ejecting with
      `FUMOUNT`, and remounting persisted assignments. (Direct HD and
      read-only `FMOUNT`/`FUMOUNT` coverage exists; writable replacement and
      persisted standard-tool remount coverage remain.)
- [ ] Preserve Stage 8 writable durability, replacement, concurrent access,
      and change-notification regressions for every supported geometry.
- [ ] Document the exact supported media families and distinguish current
      limitations from permanent interfaces.

## Exit criteria

Users mount and eject supported Amiga disk images with the standard
`FMOUNT`/`FUMOUNT` tools. Catalogue selection, device-unit state, persistence,
geometry, and AmigaDOS mounting remain consistent without a competing mount
utility or a hidden 1760-sector fallback.

## Validated Baseline

- [x] Handler-safe live replacement is validated by the focused
      `diskdevice-fmount` case and the complete Amiberry suite. Both A->B and
      B->A replacements pass with the existing `DNx` handler, preserve the
      handler task, update the change counter, and complete `Dir`/`Type`
      access without a requester.

- [x] The current production driver passes the unchanged foreground
      `diskdevice-adf` workflow at the default harness timeout in five of five
      runs. Each run reaches `disk-copy-rw.result`, `disk-update.result`,
      `disk-remount-rw.result`, `disk-dos-remount-2.result`,
      `disk-persist.result`, and the final redirected status checkpoint.
- [x] Historical A/B isolates the first stable fix: pre-fix driver `53716d3c`
      failed three of five normal runs; `6c9bf6af`, whose only relevant
      production change is setting queued request `ln_Type = NT_MESSAGE`,
      passed three of three. See `amiga-diskdevice-phase-2-findings.md`.

## Remaining Verification Gap Analysis

The following items remain unchecked because the current evidence does not
cover the complete wording of each acceptance criterion.

### Host geometry and all-unit coverage

- Existing evidence: the production classifier and focused Amiberry cases
  prove the 512-byte DD/HD profiles, malformed URI rejection, and per-unit
  geometry in the exercised units.
- Missing coverage: host-level tests for every inferred-geometry boundary and
  hint interaction, malformed image sizes, and independent geometry on all
  eight units.
- Smallest closure: add a table-driven host classifier test for valid DD, valid
  HD, unsupported sizes, conflicting hints, and eight unit descriptors.

### Native geometry and standard-tool calls

- Existing evidence: native driver contract, FIFO, and Exec-boundary tests
  pass; Amiberry covers FMOUNT and the dynamic-node geometry path.
- Missing coverage: native assertions for production `TD_GETGEOMETRY` on DD
  and HD plus a native standard-tool request boundary case.
- Smallest closure: extend the native driver fixture with DD/HD geometry and
  one standard-tool request assertion.

### Standard-tool DD/HD eject and persistence matrix

- Existing evidence: the full current Amiberry suite is green; it covers
  inspect-first FMOUNT, existing-node DD -> HD -> DD, same-geometry DD A -> B
  -> A with `Inhibit()`, absent-node DD and HD creation without static
  MountLists, filesystem startup, writable replacement, and mapping
  persistence across the focused cases.
- Missing coverage: one complete standard-tool case whose assertions jointly
  prove DD and HD `FMOUNT`, `FUMOUNT`, and persisted remount behavior.
- Smallest closure: add one sequence and assertions for DD mount/FUMOUNT/
  reload followed by HD mount/FUMOUNT/reload.

### Stage 8 durability across every supported geometry

- Existing evidence: DD writable durability, replacement, queue, change
  notification, and timeout regressions pass; HD read-only access and DD/HD
  geometry transitions pass.
- Missing coverage: writable durability, concurrent access, replacement, and
  change-notification assertions repeated specifically for HD media.
- Smallest closure: add a writable HD Amiberry sequence mirroring the proven DD
  copy/update/remount/status and notification checkpoints.

### Supported-media documentation

- Existing evidence: this backlog and the architecture document define
  standard DD/HD ADF profiles and list HDF/RDB, nonstandard geometries,
  filesystem validation, and large-media I/O as unsupported or future work.
- Missing coverage: a single support statement tying those limits to the
  permanent FMOUNT/SDK interface and named test evidence.
- Smallest closure: add a supported-media table naming DD/HD ADF as production
  supported and all other current families as rejected or unimplemented.
