# Amiga Disk-Media Architecture Direction

This document records the architecture established by the Phase 2 media
geometry investigation. It distinguishes behavior proven in the Amiberry
end-to-end tests from the selected production design and from future work.

## Current User Experience

FujiNet presents each supported image selected in the catalogue as a normal
AmigaDOS device named `DN0:` through `DN7:`. Users select a catalogue slot and
a destination drive; media geometry, DOS-node creation, and handler lifecycle
remain below the command interface.

Each unit is independent. Supported images can be mounted read-only or
read/write, used with ordinary commands such as `Dir`, `Type`, and `Copy`,
replaced while the device remains registered, ejected, and remounted. Files
can be copied between a FujiNet disk and a normal volume such as `DH0:`, or
between two mounted FujiNet disks. Successful mappings retain their RO/RW mode
and can be restored during a later AmigaOS session with `FMOUNTRESTORE`.

Typical commands are:

```text
FMOUNT 11 DN0: RO
Dir DN0:
Copy DN0:README TO DH0:README

FMOUNT 18 DN1: RW
Copy DH0:WORK/REPORT TO DN1:REPORT
Copy DN0:README TO DN1:README

FMOUNT 12 DN0: RO
FUMOUNT DN1:
FMOUNTRESTORE
```

`FMOUNT slot drive [RO|RW]` accepts `DN0:`-`DN7:` (or the corresponding bare
digit). Specify the mode explicitly in scripts; the current command defaults
to RW when it is omitted. `FMOUNT` may create an absent DOS node dynamically,
so normal use does not require a static MountList. Mounting another slot on an
occupied unit replaces its media using the lifecycle appropriate to the old
and new filesystems. `FUMOUNT drive` unmounts the unit: it retires the
AmigaDOS filesystem handler (`ACTION_DIE`), then ejects the media, and removes
the persisted mapping. `FMOUNTRESTORE` replays all valid saved mappings; it
takes no arguments.

These commands operate on images already selected in FujiNet catalogue slots.
They do not accept a host path directly, expose partitions, or turn an
arbitrary hard-disk image into a `DNx:` device.

## Phase 2 Supported-Media Contract

The production support boundary is deliberately narrow and exact:

| Image family | Required raw capacity | Recognized filesystem identifier | Current result |
| --- | --- | --- | --- |
| Amiga DD floppy ADF | 512-byte sectors x 1760 (880 KiB) | `DOS\0` OFS or `DOS\1` FFS | Supported RO and RW |
| Amiga HD high-density floppy ADF | 512-byte sectors x 3520 (1760 KiB) | `DOS\0` OFS or `DOS\1` FFS | Supported RO and RW |
| 1680-sector/nonstandard floppy image | Any | Any | Rejected as ambiguous/unsupported |
| Other raw whole-volume capacity | Any | Any | Rejected by the current Amiga profile policy |
| `DOS\2` and later DOS-family boot identifiers | DD or high-density floppy capacity | `DOS\2+` | Recognized as DOS-family data but rejected by current policy |
| Whole-partition HDF | Any | Any | Not implemented or supported |
| Whole-disk HDF with RDB partitions | Any | Any | Not implemented or supported |
| Malformed, truncated, partitioned, or unclassifiable image | Any | Any | Rejected before insertion is announced |

Here “HD” always means an Amiga **high-density floppy**, not a hard disk. A
filename suffix alone does not grant support: the non-mutating inspection must
report raw media with one of the two exact capacities, and the first four boot
bytes must be a currently accepted DosType.

Recognition of `DOS\0` or `DOS\1` is intentionally only a first-pass
filesystem identity check. Phase 2 does not claim full boot-block checksum,
root-block, allocation-map, or filesystem-structure validation.

## Current Status

### Proven

- Per-unit NIO `fn_disk_info_t` sector size and sector count are authoritative.
- Standard `512 x 1760` DD and `512 x 3520` HD geometry classification.
- Recognition of DOS boot identifiers `DOS\0` and `DOS\1`.
- Complete effective classic `DosEnvec` generation, including AmigaDOS
  defaults verified against the active static `DN0:` node.
- Correct classic `MakeDosNode()` packet construction and explicit classic
  `DE_*` serialization.
- Dynamic `DeviceNode` insertion with `AddDosNode(..., 0, node)`.
- Natural first-access filesystem-handler startup.
- `ACTION_DIE` retirement to a registered node with `dn_Task == 0`.
- Restart of the handler from the same persistent node.
- DD -> HD -> DD transitions on one persistent dynamic node.
- Same-geometry A -> B -> A replacement using `Inhibit()` without handler
  recreation or requester.
- Generic non-mutating NIO Disk Inspect is implemented and tested,
  returning image type, authoritative sector size/count, and bounded
  boot-sector bytes without changing runtime slot state.
- Amiga INSPECT_CATALOG consumes those raw facts and applies the
  Amiga-side DD/HD and filesystem classifiers without changing live
  unit or handler state.
- Production `FMOUNT` inspects and classifies the candidate before selecting
  the existing-node or absent-node lifecycle.
- Production `FMOUNT` dynamically creates an absent `DNx:` after a successful
  candidate mount and geometry build.
- Direct initial DD and HD `FMOUNT` both work with no static MountLists
  installed; first normal filesystem access starts the handler naturally.
- Dynamic nodes use the public SDK `fujinet_disk_serialize_dos_envec()` ABI.
- `nio-core-apps` and `nio-apps` consume the public Amiga DiskDevice SDK rather
  than driver-private headers or source files.
- The complete current Amiberry suite is green.

### Selected and Production-Integrated

- Dynamic `DN0:`-`DN7:` creation and update from `FMOUNT`.
- Persistent session-lifetime dynamic DOS nodes.
- Separate same-geometry and geometry-changing replacement paths.
- Classification on the Amiga side from authoritative NIO capacity facts.
- Static MountLists are no longer the universal user-facing configuration; the
  eight files remain explicit DD compatibility/bootstrap assets only.

### Future or Unproven

- Full boot-block checksum, root-block, and filesystem validation.
- Nonstandard whole-volume geometries, including 1680-sector media.
- Whole-partition HDF metadata handling.
- RDB discovery, partition parsing, and partition-relative I/O.
- Embedded RDB filesystem binaries and collision policy.
- Large-media and 64-bit I/O behavior.
- Production geometry-changing replacement failure/recovery policy.
- A public destructor/ownership release path for the `MakeDosNode()`
  allocation graph. The selected persistent-node model does not require
  repeated node removal and recreation.

## ADF Media and Authoritative NIO Facts

An ADF is normally a flat sequence of 512-byte sectors containing one floppy
filesystem. It has no partition table. The standard profiles are:

| Profile | Size | Sectors | Logical geometry |
| --- | ---: | ---: | --- |
| DD ADF | 880 KiB | 1760 | 80 cylinders x 2 surfaces x 11 blocks/track |
| HD ADF | 1760 KiB | 3520 | 80 cylinders x 2 surfaces x 22 blocks/track |

The committed NIO `fn_disk_info_t` contract currently supplies:

- mounted, read-only, dirty, and changed flags;
- catalogue slot;
- coarse media type;
- `sector_size`;
- `sector_count`; and
- `last_error`.

It does not supply heads/surfaces, sectors per track, cylinders, DosEnvec
geometry, filesystem type, RDB metadata, geometry confidence, or optional
logical geometry. Those fields must not be attributed to NIO in this design.

`sector_size` and `sector_count` are authoritative block-capacity facts. A
profile or catalogue hint must not override a successfully reported media
descriptor. Range checks and I/O use the per-unit descriptor rather than a
compiled-in ADF size.

An 840 KiB image contains 1680 sectors, but its intended layout is not proven
by the size alone. The first-pass policy rejects 1680-sector media as
unsupported/ambiguous. Any linear or nonstandard geometry requires filesystem
layout proof before production support.

## Limits, Policies, Contracts, and Extension Points

The following classification prevents the completed floppy implementation
from being mistaken for a permanent architecture restriction.

| Topic | Classification | Meaning beyond Phase 2 |
| --- | --- | --- |
| Raw media with 512-byte sectors and exactly 1760 or 3520 sectors | Intentional current supported-media policy | This is the production acceptance list now, not a promise that future media must use these capacities. |
| Reject 1680-sector and other unproved layouts | Intentional current supported-media policy | Add a profile only after its filesystem layout and lifecycle are validated; never infer it from a convenient fallback. |
| Accept only `DOS\0` OFS and `DOS\1` FFS boot identifiers | Current Phase 2 implementation limitation | The classifier and generated DosEnvec can be extended after handler/filesystem compatibility is defined. |
| Read only the first four boot bytes for Amiga filesystem classification | Current Phase 2 implementation limitation | Checksums, root blocks, and deeper filesystem validation are future work. |
| Amiga driver I/O requires 512-byte aligned blocks | Current Phase 2 implementation limitation | Generic NIO inspection reports a sector size; future Amiga media work must validate and deliberately support other sizes rather than silently coercing them. |
| Profile-driven DD/high-density-floppy DosEnvec | Current Phase 2 implementation limitation and future extension point | The serializer is generic classic ABI machinery; profile selection is replaceable by validated partition or whole-volume metadata. |
| `fn_disk_info_t`/Disk Inspect reports media type, sector size/count, and bounded boot bytes | Public interface contract | These are authoritative media facts and remain useful for future formats. They do not assert heads, cylinders, partitions, or Amiga filesystem identity. |
| Non-mutating inspection before live replacement | Permanent architecture contract | Candidate discovery must not alter the mounted unit or active DOS handler. |
| Versioned resident-device commands and explicit DosEnvec serialization | Public interface contract | Existing commands remain backward compatible. New partition metadata or selectors require additive/versioned structures or commands. |
| `DN0:`-`DN7:` and catalogue-driven `FMOUNT`/`FUMOUNT` | Stable user-facing contract | Future media should preserve the simple command model even if one host image requires partition selection below it. |
| Current mapping record stores only unit flags and catalogue slot | Current implementation limitation | Partitioned media needs a versioned mapping identity that can also name a partition. Version-1 floppy mappings must continue to restore unchanged. |
| 32-bit sector count/LBA and Amiga byte-offset I/O | Public interface constraint for current commands | It is not floppy-specific, but media exceeding these address ranges requires a versioned 64-bit protocol/device extension rather than overflow-prone reuse. |
| One mounted image backing one unit and one DOS node | Current implementation limitation | RDB images may need a disk object with multiple partition bindings; this is not encoded in the permanent inspection facts. |

## Media and Filesystem Classification

NIO does not select DD or HD. The proven split is:

```text
NIO fn_disk_info_t
    -> RAW + 512-byte sectors + total sector count

Amiga media-profile classifier
    512 x 1760 -> standard DD profile
    512 x 3520 -> standard HD profile
    other current sizes -> unsupported or ambiguous
```

Geometry and filesystem identity are separate decisions:

```text
fn_disk_info_t
    -> geometry classifier
    -> DD or HD media profile

media boot bytes 0..3
    -> filesystem classifier
    -> recognized DOS\0 or DOS\1 identifier
```

The first-pass filesystem policy is:

| Boot identifier | Policy |
| --- | --- |
| `DOS\0` | Supported OFS identifier |
| `DOS\1` | Supported FFS identifier |
| `DOS\2+` | Recognized DOS-family identifier, currently unsupported |
| malformed/truncated | Rejected |

A recognized boot-block DosType does not validate the complete filesystem.
Checksum validation, root-block checks, and filesystem-structure validation
remain future production work.

## Verified Classic DosEnvec Contract

The following effective environment was read from the active static `DN0:`
node in AmigaOS 3.2 under Amiberry and is reproduced by the builder:

```text
de_TableSize       = 19       # final valid index; complete entries 0..19
de_SizeBlock       = 128      # longwords, 512 bytes
de_SecOrg          = 0
de_Surfaces        = 2
de_SectorPerBlock  = 1
de_BlocksPerTrack  = 11 DD / 22 HD
de_LowCyl          = 0
de_HighCyl         = 79
de_Reserved        = 2
de_PreAlloc        = 0
de_Interleave      = 0
de_NumBuffers      = 5
de_BufMemType      = 1
de_MaxTransfer     = 0x7fffffff
de_Mask            = 0xfffffffe
de_BootPri         = 0
de_DosType         = recognized filesystem DosType
de_Baud            = 1200
de_Control         = 0
de_BootBlocks      = 0

handler stack      = 32768
handler priority   = 5
handler GlobVec    = -1
```

`de_TableSize=19` is not a count of 19. It is the final valid environment
index and therefore describes 20 entries, indices `0..19`.

The omitted MountList defaults were verified at runtime rather than inferred
from text: `PreAlloc=0`, `MaxTransfer=0x7fffffff`, `Mask=0xfffffffe`, and
`Baud=1200`.

## Dynamic DOS-Node Model

The experimentally proven classic construction is:

```text
MakeDosNode packet:
    [0]     DOS device name, e.g. "DY0"
    [1]     "fujinet-disk.device"
    [2]     unit number
    [3]     OpenDevice flags
    [4..23] DosEnvec in classic DE_* index order
```

The public fujinet_disk_dos_envec_t now follows the classic DosEnvec
field ordering. Construction still uses the explicit
fujinet_disk_serialize_dos_envec() helper rather than relying on
struct memcpy, so the MakeDosNode packet ABI remains explicit and
independent of compiler representation. It must be explicitly serialized by `DE_*` index; direct `memcpy()` is incorrect.
An earlier private representation used a different semantic field
order; that duplicate definition was removed after it caused an ABI
mismatch between SDK callers and the serializer implementation.

`MakeDosNode()` supplies different handler defaults. The verified startup
fields are therefore applied explicitly before insertion:

```text
node->dn_StackSize = 32768
node->dn_Priority  = 5
node->dn_GlobVec   = -1
```

The static node has no explicit `dn_Handler`; its handler BSTR is zero. The
dynamic node preserves that value. `ADNF_STARTPROC` is not required for the
selected model:

```text
MakeDosNode
    -> apply verified handler fields
    -> AddDosNode(..., 0, node)
    -> node remains registered and inactive, dn_Task == 0
    -> first Dir/Type access naturally starts the filesystem handler
```

## Persistent-Node Lifecycle

Dynamic nodes are selected as session-lifetime objects. The proven lifecycle
is:

```text
active handler, dn_Task != 0
    -> DoPkt(task, ACTION_DIE, ...)
registered node remains, dn_Task == 0
    -> next access
fresh handler starts, dn_Task != 0
```

In the validated Amiberry test, `ACTION_DIE` returned `-1` and `IoErr()` was
`0`. The return value alone is not treated as proof of retirement; retirement
is established by read-only DOS-list observation of `dn_Task` becoming zero.

`RemDosEntry()` and node destruction are not the normal media-transition path.
`RemDosEntry()` requires an exclusive `LDF_WRITE | LDF_DEVICES` lock and does
not free the removed memory. `FreeDosEntry()` applies to `MakeDosEntry()`
objects, not the allocation graph returned by `MakeDosNode()`. No public
destructor for that graph has been established, which reinforces the
session-lifetime design.

## Proven Variable-Geometry Transition

A single persistent dynamic node has completed this full cycle in Amiberry:

```text
DD active
    -> ACTION_DIE
DD inactive
    -> mount HD media, 512 x 3520
    -> update inactive DosEnvec, BlocksPerTrack 11 -> 22
    -> Dir/Type HD succeeds
HD active
    -> ACTION_DIE
HD inactive
    -> mount DD media, 512 x 1760
    -> update inactive DosEnvec, BlocksPerTrack 22 -> 11
    -> Dir/Type DD succeeds
DD active
```

This validates the selected variable-media mounting strategy. Production
`FMOUNT` now uses the same inspect/classify, `ACTION_DIE`, inactive-node update,
and natural-restart strategy for geometry-changing replacement.

## Same-Geometry Replacement

Same-geometry replacement is a distinct lifecycle and must not be replaced by
the `ACTION_DIE` findings:

```text
same geometry / compatible active DosEnvec
    -> Inhibit(TRUE)
    -> replace underlying media
    -> Inhibit(FALSE)
    -> existing handler rescans
```

The A -> B -> A same-geometry replacement path has been proven without
requester or handler recreation.

Geometry-changing replacement uses the persistent-node path instead:

```text
geometry or DosEnvec change
    -> ACTION_DIE
    -> observe dn_Task == 0
    -> replace/classify media
    -> update inactive DosEnvec
    -> next access starts a fresh handler
```

## FMOUNT Production Status

Production `FMOUNT` supports standard DD/HD ADF mounting and replacement.
It obtains candidate facts through the generic non-mutating NIO Disk Inspect
operation, exposed to Amiga as `INSPECT_CATALOG`, before selecting a lifecycle
path. Inspection does not change live unit state.

The intended flow separates candidate inspection from committing replacement to
the active unit. The currently available NIO mount operation is stateful: it
mounts into the same NIO slot backing an Amiga unit. It is not a valid candidate
inspection primitive while that unit has an active DOS handler.

1. Obtain candidate facts through `INSPECT_CATALOG`, backed by generic
   non-mutating NIO Disk Inspect. The candidate is not mounted into the live
   unit slot.
2. Classify the geometry and filesystem identity on the Amiga side.
3. Compare the candidate environment with the existing node's active/inactive
   environment and select the lifecycle path.
4. Never replace media underneath an uninhibited/unretired active handler.
5. For compatible same-geometry replacement, use `Inhibit(TRUE)`, commit the
   media replacement, then use `Inhibit(FALSE)`.
6. For a geometry or DosEnvec change, use `ACTION_DIE`, observe `dn_Task==0`,
   commit the media replacement, update the inactive DosEnvec, and allow the
   next access to start a fresh handler.
7. Persist the catalogue-to-unit assignment only after the selected operation
   has succeeded.

For an absent node, production uses this order:

1. Inspect and classify the candidate.
2. Commit `MOUNT_CATALOG`.
3. Build and serialize the profile-driven DosEnvec through the public SDK.
4. Create and add the persistent node.
5. Let the first normal `Dir`/`Type` access start the handler.

Both direct initial DD and direct initial HD are tested with static MountLists
removed.

Failure and recovery semantics after a successful geometry-changing media
commit remain incomplete. In particular, production does not yet roll back a
successful commit if the subsequent inactive DosEnvec update or first access
fails.

## Static MountLists

Static `DN0:`-`DN7:` MountLists are explicit DD compatibility/bootstrap assets
only. They are no longer required by the standard `FMOUNT` path: production
FMOUNT can inspect, mount, construct, and add an absent node for both DD and HD
media. They remain available for compatibility and low-level diagnostics, but
are not the universal user-facing configuration.

## HDF and RDB Architecture Boundaries

HDF/RDB support is a future media programme, not unfinished Phase 2 work. Its
active checklist is tracked in
[`backlog/amiga-hdf-rdb-support.md`](../../backlog/amiga-hdf-rdb-support.md).
It must preserve the completed DD/high-density-floppy behavior while adding a
partition-aware model. “HDF” is only a container convention; support must
distinguish two materially different layouts:

- A **raw whole-volume/whole-partition image** begins with one Amiga
  filesystem at image sector zero. It has no RDB from which to recover the
  complete DosEnvec, so required metadata must be supplied, discovered by a
  validated convention, or stored alongside the catalogue entry.
- A **whole-disk RDB image** contains an `RDSK` metadata area and zero or more
  `PART` records. Partition bounds, names, DosEnvec values, DosTypes, boot
  priorities, and possibly filesystem binaries come from validated RDB data;
  filesystem I/O is relative to each partition, not image sector zero.

### Discovery and inspection

A useful discovery contract must distinguish raw whole-volume media from an
RDB disk and describe zero or more partitions without mutating runtime state.
Its validation corpus needs valid and corrupt whole-volume HDFs, RDBs,
multiple partitions, unusual but valid bounds, and writable images.

The existing Disk Inspect request and its media type/sector size/sector count/
boot-byte result remain valid and backward compatible. They are sufficient for
floppy and simple whole-volume probing. RDB support probably needs an additive,
versioned inspection command or optional response carrying stable partition
identifiers, byte/LBA bounds, DosType, complete relevant DosEnvec values, boot
priority, and metadata provenance. Do not overload the existing boot-byte
array with RDB records.

### Validated RDB parsing and media policy

RDB discovery belongs outside mounting. `RDSK` and `PART` checksums,
linked-list termination, block sizes, cylinder/sector arithmetic, partition
bounds, overlap policy, and all offsets must be valid before a partition is
exposed. Policy must state whether an unsupported or corrupt partition rejects
the whole disk or is reported individually as unusable.

Sector size must be authoritative from inspection/RDB evidence. The current
Amiga driver supports 512-byte blocks only; retain that as the initial HDF/RDB
implementation policy if necessary, but do not bake it into the partition
metadata contract. Audit 32-bit sector counts, LBAs, Amiga byte offsets, and
multiplication before setting a maximum supported image size. Add versioned
64-bit operations if the safe range of current commands is insufficient.

### Partition binding and DOS-node ownership

The model needs an explicit binding between a mounted host image and a selected
partition. The recommended direction is one shared, inspected disk object with
one logical binding per exposed partition; each binding applies a validated
base LBA and length and owns the Amiga DOS-node identity for that partition.
This avoids mounting the same writable host image independently for every
partition.

Two user models remain possible:

1. Map one selected partition to one `DNx:` unit. This preserves the current
   eight-drive model and is the simplest compatible first delivery.
2. Map one catalogue disk to multiple DOS devices automatically. This is more
   convenient for multi-partition disks but requires device naming, unit
   allocation, partial-mount failure, and group eject semantics.

Start with explicit one-partition-to-one-`DNx:` selection unless user research
shows automatic expansion is essential. Keep the inspection model capable of
listing all partitions so automatic exposure can be added later. Partition
names from RDB must not be trusted as globally unique DOS device names; define
collision and sanitisation rules.

DosEnvec and partition bounds should be owned by the validated partition
descriptor, then serialized through the existing public classic DosEnvec
helper. Do not reconstruct RDB partitions using floppy geometry or static
MountLists. Define policy for RDB-provided DosType, boot priority, filesystem
handler selection, and embedded filesystem binaries. The safe initial policy
is to use an already available compatible AmigaOS filesystem and reject
unknown DosTypes; loading embedded filesystem code requires a separate trust,
memory-lifetime, and version-collision design.

### Read/write and lifecycle semantics

Partition-relative bounds apply to every read, write, clear, and update before
translating to the host-image LBA. Multiple writable partitions of one image
must share serialization, dirty state, flush ordering, and error reporting.
Define whether ejecting one binding leaves sibling partitions mounted and
whether replacing a disk is an atomic group operation.

Recommended semantics are disk-scoped replacement/eject with a preflight
phase: inspect and validate the complete candidate, inhibit or retire all
affected handlers, commit only when every selected binding can be recreated,
then restart them. Failure must either leave the old group intact or return a
clearly specified recoverable state. Preserve current notification, concurrent
access, timeout, failed-replacement, writable durability, and RO enforcement
for every exposed partition.

### Persistence and standard commands

`FMOUNT`, `FUMOUNT`, and `FMOUNTRESTORE` remain the user-facing workflow.
Version the current mapping record so a binding can identify at least the
catalogue slot, RO/RW mode, and a stable partition selector. A selector based
only on display name or ordinal is fragile when an RDB changes; prefer an
identity derived from validated partition metadata, with an explicit policy
for a missing or changed partition.

Version-1 DD/high-density-floppy mappings must continue to restore exactly as
they do now. Decide whether `FUMOUNT DNx:` removes one partition binding or an
entire disk group, and provide an explicit group operation if both are needed.

### Acceptance strategy

Acceptance should build in these layers:

1. Host parser tests for valid/corrupt RDB chains, checksums, bounds, overlaps,
   sector sizes, partition identity, and fuzzed malformed metadata.
2. Native driver tests for partition-relative translation, overflow rejection,
   independent bindings, shared-image locking/flush, public ABI versioning,
   and backward-compatible floppy requests.
3. Focused Amiberry tests for whole-volume HDF and one- and multi-partition RDB
   images: `Dir`/`Type`, copies to/from `DH0:`, copies between partitions,
   RO/RW enforcement, durability across eject/remount, replacement, change
   notification, concurrent access, and requester-free failure recovery.
4. A two-process `FMOUNTRESTORE` test proving versioned partition mappings and
   unchanged restoration of existing floppy mappings.

No HDF/RDB parser, partition binding, metadata contract, persistence version,
or embedded-filesystem policy is currently implemented or implied by Phase 2.

The current production boundary is standard DD/high-density-floppy ADF
whole-volume media.
Failure/recovery after a successful geometry-changing commit, nonstandard
geometry, HDF/RDB, and large-media behavior remain future work.

The intended user model remains one stable command such as:

```text
FMOUNT 12 DN0: RW
```

The media classification and lifecycle complexity should remain below that
command rather than leaking into parallel end-user workflows.
