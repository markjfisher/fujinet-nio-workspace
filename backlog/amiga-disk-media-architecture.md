# Amiga disk-media architecture direction

This document records the intended progression from the standard-ADF
DiskDevice foundation to general floppy and hard-disk media. It separates
image layout, block-device capacity, and AmigaDOS filesystem geometry so that
temporary implementation limits do not become permanent user interfaces.

## ADF: normally one floppy filesystem

An ADF is normally a flat sequence of 512-byte sectors containing one floppy
filesystem. It has no partition table.

The standard profiles are:

| Profile | Size | Sectors | Logical geometry |
| --- | ---: | ---: | --- |
| DD ADF | 880 KiB | 1760 | 80 cylinders × 2 heads × 11 sectors |
| HD ADF | 1760 KiB | 3520 | 80 cylinders × 2 heads × 22 sectors |

The Amiga's standard DD floppy has 11 usable 512-byte sectors per track.
`TD_GETGEOMETRY` can describe media by total sectors,
cylinders/sectors-per-cylinder, or full cylinder/head/track geometry; total
sectors is the most reliable representation. See the
[AmigaOS Trackdisk documentation](https://wiki.amigaos.net/wiki/Trackdisk_Device).

An 840 KiB image contains 1680 512-byte sectors. That size does not uniquely
identify its intended geometry. One possible factorisation is:

```text
84 cylinders × 2 heads × 10 sectors = 1680 sectors
```

The file size alone does not prove that this was how the image was formatted.
Profiles or hints therefore remain relevant.

The governing rule is:

> Inferred facts beat hints; hints fill in facts that cannot be inferred.

For example:

- NIO can infer `512 × 1760` from a standard ADF and confidently select DD.
- NIO can infer `512 × 3520` and select HD.
- NIO can infer that an 840 KiB file contains 1680 sectors, but may need a
  profile or catalogue metadata to identify its intended CHS layout.
- A hint must never force 1760 sectors onto a file that demonstrably contains
  1680 or 3520.

## HDF: an ambiguous name

HDF generally means a raw hard-disk image, but it does not guarantee what
begins at sector zero. Two forms must be distinguished.

### Whole-partition HDF

The image contains one Amiga filesystem directly, like a large ADF:

```text
sector 0
┌──────────────────────────┐
│ Boot block / filesystem  │
│ filesystem blocks        │
│ ...                      │
└──────────────────────────┘
```

It has no embedded partition description. AmigaDOS must receive the correct
DosEnvec externally: block size, total geometry, reserved blocks, filesystem
type, and related settings. This is comparable to a nonstandard ADF, although
potentially much larger.

### Whole-disk RDB HDF

This represents an entire Amiga hard disk:

```text
sector 0
┌──────────────────────────┐
│ RDB metadata area        │
│ PART: DH0 definition     │
│ PART: DH1 definition     │
│ optional filesystem code │
├──────────────────────────┤
│ DH0 partition data       │
├──────────────────────────┤
│ DH1 partition data       │
└──────────────────────────┘
```

RDB means Rigid Disk Block. It is Amiga's native hard-disk partitioning
format, analogous in purpose to MBR or GPT but structurally different. It can
record:

- disk block size and logical disk geometry;
- a linked list of partitions;
- each partition's low/high cylinders and DosEnvec;
- partition names such as `DH0`;
- filesystem type and boot priority; and
- optionally, filesystem binaries and boot code.

The RDB is normally found by scanning the first 16 blocks for a valid `RDSK`
block. Partition definitions, rather than nominal physical geometry in the
RDB header, supply the values used to mount each filesystem. See the
[AmigaOS RDB documentation](https://wiki.amigaos.net/wiki/RDB) and
[AmigaOS SCSI/RDB driver documentation](https://wiki.amigaos.net/wiki/SCSI_Device).

RDB is preferable for network hard disks because the image carries its
partition layout.

## Implementation direction

### Separate media capacity from filesystem mounting geometry

After NIO mounts an image, it should provide a media descriptor containing:

```text
sector size
sector count
image/media class
read-only state
geometry confidence
optional logical geometry
```

Sector size and sector count are the minimum authoritative facts. The driver
stores them independently for every unit. Consequently:

- range checking uses `sectorCount`, never a compiled-in ADF size;
- `TD_GETGEOMETRY` reports the mounted unit's media;
- reads and writes work identically for 1680, 1760, 3520, or millions of
  sectors; and
- floppy and hard-disk images do not require separate block-I/O paths.

Their difference is primarily how AmigaDOS constructs filesystems on top.

### Classify the mounted image

```text
Mount image
    │
    ├── Known floppy/whole-volume profile
    │      └── create one DNx: filesystem node
    │
    ├── RDB whole-disk image
    │      └── scan RDB and create one DOS node per partition
    │
    ├── Whole-partition hard-disk image with supplied metadata
    │      └── create one filesystem node from that metadata
    │
    └── Ambiguous or unsupported
           └── leave unannounced and report a useful error
```

NIO can perform file-format probing, while the Amiga side remains responsible
for the AmigaDOS consequences.

### Dynamically construct the DOS device entry

The permanent solution must not depend on fixed `DN0`–`DN7` MountLists. For a
floppy-like whole-volume image, `FMOUNT` will:

1. Resolve the catalogue slot.
2. Ask `fujinet-disk.device` to mount it on unit N.
3. Obtain the committed media descriptor.
4. Select or validate its filesystem geometry.
5. Create or update the AmigaDOS device node for `DNn:`.
6. Start the filesystem handler.
7. Persist the catalogue-to-unit assignment.

Known profiles are direct:

```text
1760 sectors → DD profile
3520 sectors → HD profile
```

For 1680 sectors, a logical factorisation can be derived, but emulator tests
must establish whether OFS/FFS requires only the correct total block count or
the original formatting geometry. RDB practice supports logical rather than
physical geometry, but that behavior must be proved for whole-volume images.

Static MountLists may remain as bootstrapping or explicit DD-ADF compatibility
profiles. They no longer define what the driver can handle.

## Intended user experience

The command remains the same regardless of image size:

```text
FMOUNT 12 DN0: RW
```

For an 880 KiB ADF:

```text
catalogue slot 12
→ DiskDevice unit 0
→ 1760-sector DD profile
→ one volume on DN0:
```

For a 1.76 MiB ADF:

```text
catalogue slot 12
→ DiskDevice unit 0
→ 3520-sector HD profile
→ one volume on DN0:
```

For a supported 840 KiB filesystem image:

```text
catalogue slot 12
→ DiskDevice unit 0
→ 1680 sectors
→ validated logical/profile geometry
→ one volume on DN0:
```

For an RDB hard-disk image:

```text
catalogue slot 12
→ DiskDevice unit 0
→ scan RDB
→ discover DH0 and DH1 partitions
→ mount those partition devices
```

In the RDB case, `DN0` identifies the underlying FujiNet disk unit while the
image may contain partition names such as `DH0` and `Work`. Phase 2 must define
a collision policy rather than silently replacing existing DOS devices. Safe
embedded names or generated names such as `DN0P0:` and `DN0P1:` are candidate
policies.

## Hard-disk work beyond geometry

Large media require more than removing the 1760-sector check:

- RDB and PartitionBlock parsing with checksum and bounds validation;
- partition-relative reads and writes;
- DOS-node creation for multiple partitions on one unit;
- filesystem selection from the partition DosType;
- a safe policy for filesystem binaries embedded in an RDB;
- device and partition name collision handling;
- 64-bit I/O commands beyond classic 32-bit byte-offset limits;
- sensible network caching and flush performance; and
- preservation of the existing write/update/eject durability rules.

## Delivery progression

1. Dynamic DD and HD ADF profiles.
2. Nonstandard whole-volume images with validated logical geometry.
3. Whole-partition HDF with explicit catalogue metadata.
4. Whole-disk RDB HDF with automatic partition discovery.
5. Large-media/64-bit I/O and performance work.

This progression preserves one stable user model—`FMOUNT slot drive`—while
teaching the driver progressively richer media classes. Complexity remains
below the command rather than leaking into parallel tools or user workflows.
