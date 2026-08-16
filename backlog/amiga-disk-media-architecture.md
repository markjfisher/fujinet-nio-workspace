# Amiga Disk-Media Architecture Direction

This document records the architecture established by the Phase 2 media
geometry investigation. It distinguishes behavior proven in the Amiberry
end-to-end tests from the selected production design and from future work.

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

### Selected, Not Yet Production-Integrated

- Dynamic `DN0:`-`DN7:` creation and update from `FMOUNT`.
- Persistent session-lifetime dynamic DOS nodes.
- Separate same-geometry and geometry-changing replacement paths.
- Classification on the Amiga side from authoritative NIO capacity facts.
- Retirement of static MountLists as the universal user-facing configuration.

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

The semantic `fujinet_disk_dos_envec_t` field order is not the classic memory
order. It must be explicitly serialized by `DE_*` index; direct `memcpy()` is
incorrect.

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

This validates the selected variable-media mounting strategy. It remains a
test-only architecture result; production `FMOUNT` integration is outstanding.

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

Production integration is not complete. `FMOUNT` does not yet claim to create
dynamic nodes as the production/user-facing path.

The intended flow is:

1. Resolve the catalogue slot and mount it on the NIO unit.
2. Read the committed `fn_disk_info_t` descriptor.
3. Classify the geometry on the Amiga side.
4. Classify the boot-block filesystem identity separately.
5. Compare the new environment with the existing node's active/inactive
   environment.
6. Use `Inhibit()` for compatible same-geometry replacement.
7. Use `ACTION_DIE`, `dn_Task==0`, environment update, and natural restart for
   geometry-changing replacement.
8. Persist the catalogue-to-unit assignment only after the selected operation
   has succeeded.

Failure and recovery semantics for geometry-changing production replacement
remain to be designed and tested. In particular, production must define what
happens when media mounting succeeds but classification, handler retirement,
environment update, or first access fails.

## Static MountLists

Static `DN0:`-`DN7:` MountLists remain part of the installed DD compatibility
and bootstrap story. They are not the universal architecture.

Dynamic persistent nodes are the proven long-term mechanism, but replacing the
static files in the production/user-facing path remains outstanding. The
static files must remain available until the production FMOUNT path owns node
creation, transition, failure recovery, and compatibility behavior.

## HDF and RDB Future Work

The current proven classifier supports only standard DD/HD ADF whole-volume
profiles. HDF and RDB support remains future work.

Two HDF forms remain architecturally distinct:

### Whole-partition HDF

The image contains one filesystem directly from sector zero, like a larger
whole-volume ADF. It requires externally supplied or separately validated
DosEnvec geometry and filesystem identity.

### Whole-disk RDB HDF

The image contains an RDB metadata area followed by one or more partitions.
RDB metadata can describe disk geometry, partition cylinder ranges, partition
names, DosEnvec values, filesystem types, boot priority, and optionally
filesystem code.

RDB support must still provide:

- RDSK/PART checksum and bounds validation;
- partition-relative reads and writes;
- one DOS node per selected partition;
- partition DosType and embedded-filesystem policy;
- device and partition name collision handling;
- large-media and 64-bit I/O handling; and
- preservation of write/update/eject durability rules.

No RDB parsing, partition discovery, whole-partition metadata contract, or
embedded filesystem handling is currently proven.

## Delivery Progression

1. Production-integrated dynamic DD and HD ADF profiles.
2. Production failure/recovery semantics for geometry-changing replacement.
3. Nonstandard whole-volume images with validated logical geometry.
4. Whole-partition HDF with explicit metadata.
5. Whole-disk RDB HDF with automatic partition discovery.
6. Large-media/64-bit I/O and performance work.

The intended user model remains one stable command such as:

```text
FMOUNT 12 DN0: RW
```

The media classification and lifecycle complexity should remain below that
command rather than leaking into parallel end-user workflows.
