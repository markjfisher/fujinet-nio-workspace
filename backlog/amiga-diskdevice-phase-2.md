# Amiga DiskDevice Phase 2 — general media and standard tools

Status: `COMPLETE`

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

- [x] Add host/native tests covering raw-image geometry inference, hint
      interactions, malformed sizes, and independent retained geometry on all
      eight driver units. `repos/fujinet-nio/tests/test_disk_device_protocol.cpp`
      proves raw DD (`512 x 1760`) and HD (`512 x 3520`) ADF inference,
      inferred geometry winning over a conflicting 256-byte hint, and rejection
      of truncated and unsupported 1680-sector ADFs. The native
      `amiga/tests/test_fujinet_disk_driver.c` fixture mounts alternating DD/HD
      geometry on units 0..7, changes unit 0, and queries units 1..7 to prove
      retained independent geometry/state.
- [x] Add native tests for dynamic `TD_GETGEOMETRY` and standard-tool device
      calls. `amiga/tests/test_fujinet_disk_resident.c` compiles the production
      `disk.device/fujinet_disk_device.c` dispatcher with local Exec ABI stubs,
      commits simultaneous DD/HD unit state, and submits public `IOExtTD`
      requests. It verifies DD `512/1760/80/2/22/11`, HD
      `512/3520/80/2/44/22`, repeated per-unit queries, and public
      `FUJINET_DISK_CMD_MOUNT` dispatch through the same ABI used by FMOUNT.
- [x] Add Amiberry tests mounting at least DD and HD images through catalogue
      slots using `FMOUNT`, accessing them through `DNx:`, ejecting with
      `FUMOUNT`, and remounting persisted assignments. The two-process
      `diskdevice-fmount-restore` case terminates Amiberry after DD/HD FMOUNT
      and access, preserves only the host AppStore mapping state, starts a
      fresh AmigaOS process with no `FMOUNT` command in phase two, runs
      `FMOUNTRESTORE`, verifies both `DNx:` filesystems, then FUMOUNTs both and
      confirms the mapping record is clear.
- [x] Preserve Stage 8 writable durability, replacement, concurrent access,
      and change-notification regressions for every supported geometry. The
      existing `diskdevice-fmount` case retains the DD writable eject/remount
      durability and A -> B -> A replacement checks. The focused
      `diskdevice-hd-stage8` case proves the same operations on 512 x 3520 HD
      media. The `diskdevice-adf` and `diskdevice-hd-adf` boundary runs submit
      concurrent resident-device requests and exercise two registered change
      interrupts, removal, repeated notification, and abort cleanup against DD
      and HD mounts respectively.
- [x] Document the exact supported media families and distinguish current
      limitations from permanent interfaces. The architecture now includes a
      user workflow, exact DD/high-density-floppy and OFS/FFS support matrix,
      classified implementation limits and public contracts, and a staged
      HDF/RDB roadmap. HDF/RDB remains explicitly outside Phase 2.

## Exit criteria

Users mount and eject supported Amiga disk images with the standard
`FMOUNT`/`FUMOUNT` tools. Catalogue selection, device-unit state, persistence,
geometry, and AmigaDOS mounting remain consistent without a competing mount
utility or a hidden 1760-sector fallback.

**Phase 2 is complete.** Standard DD and high-density-floppy ADF media are the
current production boundary. Nonstandard whole-volume media, whole-partition
HDF, RDB partition discovery, partition bindings, embedded filesystem policy,
and large/64-bit media are post-Phase-2 roadmap work, not incomplete Phase 2
acceptance items.

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

## Verification Gap Analysis

All Phase 2 acceptance gaps are closed. The sections below record the evidence
and the boundary between completed work and future media support.

### Geometry inference and all-unit coverage

- Closed by the host and native tests named in the completed verification
  checkbox above. Broader nonstandard geometry and hint combinations remain
  outside this checkbox and are tracked under the architecture's future work.

### Native geometry and standard-tool calls

- Closed by `amiga/tests/test_fujinet_disk_resident.c`, which invokes the real
  resident `BeginIO` dispatcher with the public request ABI and verifies the
  committed DD/HD geometry fields and per-unit isolation.

### Standard-tool DD/HD eject and persistence matrix

- Closed by the two-process `diskdevice-fmount-restore` case. Process A mounts
  and accesses DD slot 11 and HD slot 14 using standard FMOUNT, then exits.
  Process B is a fresh AmigaOS/Amiberry process sharing only the host AppStore;
  its Startup-Sequence contains no FMOUNT command, uses FMOUNTRESTORE to mount
  both saved assignments, verifies both filesystems, FUMOUNTs both, and proves
  `config-nio/mappings` is clear. The companion stale-slot case confirms an
  invalid persisted entry fails without creating a node.

### Stage 8 durability across every supported geometry

- Closed by the existing DD `diskdevice-fmount` writable durability and
  replacement assertions plus the focused HD `diskdevice-hd-stage8` case.
  The HD case performs A -> B -> A same-geometry replacement, verifies each
  mounted file, writes through the filesystem to writable HD media, ejects,
  remounts, and reads the persisted file while asserting monotonic change
  counters and protection/absence state.
- Concurrent access and change-notification mechanics do not branch on media
  geometry after a mount commits: they operate on the resident device's
  per-unit FIFO and change-request list. The boundary diagnostic is therefore
  reused rather than duplicated; it now accepts the mounted URI, and the
  `diskdevice-adf` and `diskdevice-hd-adf` cases run that identical production
  path with DD and HD media. Both assert `queue=1 multi=2`, four notification
  operations, two simultaneous listeners, removal, repeat delivery, and abort
  cleanup.

### Supported-media documentation

- Closed by `amiga-disk-media-architecture.md`. Its Phase 2 support table names
  standard 512 x 1760 DD floppy ADF and 512 x 3520 high-density floppy ADF,
  each with `DOS\0` OFS or `DOS\1` FFS, as the only currently supported media.
  It separately identifies rejected nonstandard/DOS-family variants and
  unimplemented HDF/RDB media.
- The same document records the normal `FMOUNT`/`FUMOUNT`/`FMOUNTRESTORE` user
  workflow, classifies current implementation policy versus public interface
  contracts and extension points, and moves all partitioned-media work into a
  staged post-Phase-2 HDF/RDB roadmap.
