# The problem statement

We are starting the Media geometry section of backlog/amiga-diskdevice-phase-2.md.

Do not make production changes yet. This segment is for evidence gathering and choosing the mounting model.

The relevant backlog items are:

- Specify which image families can be presented as an Amiga filesystem in
  a whole-disk device, beginning with standard DD and HD ADF profiles and
  separating those from partitioned RDB/HDF media.


- Treat NIO's mounted-media sector size and sector count as authoritative;
  hints may assist raw-image probing but must not override successfully
  inferred geometry.


- Define how AmigaDOS receives matching DosEnvec geometry. Do not assume
  that TD_GETGEOMETRY rewrites Surfaces, BlocksPerTrack, LowCyl, or HighCyl
  from a static MountList.


- Choose and test the mounting strategy for variable media: known geometry
  profiles, dynamically constructed DOS device nodes, or a verified linear
  logical geometry. The choice must preserve existing filesystem layout and
  allocation semantics.

We have already removed the driver's unconditional 1760-sector validation
and fixed TD_GETGEOMETRY; do not reopen that work unless current evidence
shows an actual defect.

1. Establish the current NIO geometry contract

Trace the current mounted-media Info path from NIO service through the
Amiga driver and report exactly which authoritative fields are currently
available per unit:

sector size
sector count
writable/protected state
any media/image type hint
any heads/surfaces/tracks/cylinders metadata

Show the relevant structs/functions and state clearly which values come from
actual mounted-media inference versus defaults/hints.

Specifically establish what NIO currently reports for:

standard DD ADF
standard HD ADF
raw HDF/RDB-style image, if currently detectable
malformed/non-standard raw image

Do not infer values that the existing code does not actually provide.

2. Document the existing Amiga side

Inspect the current DN0–DN7 MountLists and the driver implementation of
TD_GETGEOMETRY.

Report the current DD values for:

Surfaces
BlocksPerTrack
LowCyl
HighCyl
BlockSize
Reserved
PreAlloc
Interleave
Buffers
BufMemType
MaxTransfer
Mask
DosType

Then identify which of those fields are filesystem-layout significant and
which are merely device/IO configuration.

Confirm from the classic Amiga implementation/API behaviour whether mounting
a device from a static MountList causes AmigaDOS to use that DosEnvec
independently of TD_GETGEOMETRY.

Do not assume TD_GETGEOMETRY can repair a mismatched MountList.

3. Define supported media families

Produce a proposed first-pass support matrix, at minimum:

media                    whole-disk DNx filesystem?   expected handling
DD ADF (880 KiB)
HD ADF (1760 KiB)
non-standard ADF/raw OFS/FFS
partitioned RDB/HDF
unpartitioned/raw HDF
malformed/ambiguous image

Separate:

what we can support now from sector-size/count alone;
what needs additional metadata/probing;
what must be explicitly rejected.

Do not treat sector_count == 1760 as meaning DD ADF in the generic design.

4. Evaluate the three mounting strategies

Compare these options:

A. Known geometry profiles

e.g. DD and HD MountLists/profile definitions selected from authoritative
media geometry.

B. Dynamically constructed DOS device nodes

Build the appropriate DosEnvec/device node at runtime from mounted-media
geometry before starting the filesystem handler.

C. Verified linear logical geometry

Present media using a deliberately chosen logical geometry derived from
total block count, only if this is demonstrably safe for OFS/FFS allocation
and existing on-disk layout.

For each give:

feasibility on classic m68k AmigaOS
APIs required
whether handler restart/recreation is required
compatibility with FMOUNT live replacement
DD -> HD -> DD behaviour
risk to existing OFS/FFS layout
interaction with static DN0-DN7 MountLists
implementation complexity

Do not choose based only on implementation convenience.

5. Do one bounded black-box experiment if it resolves the design

If needed, create test-only fixtures for one DD ADF and one HD ADF and answer
this specific question:

Can the same already-created DOS handler/device node correctly consume both
geometries merely because TD_GETGEOMETRY changes, or does its startup
DosEnvec remain authoritative?

It is acceptable and expected for this experiment to prove that the static
DD MountList cannot consume HD media.

Do not change production lifecycle behaviour to force the experiment to pass.

Deliverable

Return:

current NIO geometry contract;
current DD MountList/DosEnvec contract;
supported-media matrix;
mounting-strategy comparison;
any bounded experimental result;
your recommended strategy and why;
the smallest next implementation step if we accept that strategy.

Be explicit about conclusions. If the evidence indicates one strategy is
clearly preferable, say so rather than only presenting a neutral table.

No production changes in this segment.

---

# The result

**Conclusion**

The evidence clearly favors **B. Dynamically constructed DOS device nodes**, with known DD/HD profiles as the first implementation scope. `TD_GETGEOMETRY` is useful for block-device inquiry, but it cannot be treated as a mechanism for changing the `DosEnvec` used by an already-created AmigaDOS filesystem handler.

No production changes or test fixtures were created.

## A. Current NIO Geometry Contract

### Wire/API structure

The shared descriptor is `fn_disk_info_t` in:

`repos/fujinet-nio-lib/include/fujinet-nio.h:367-375`

```c
typedef struct {
    uint8_t flags;
    uint8_t slot;
    uint8_t type;
    uint16_t sector_size;
    uint32_t sector_count;
    uint8_t last_error;
} fn_disk_info_t;
```

Available fields:

| Field | Meaning |
|---|---|
| `flags & FN_DISK_FLAG_MOUNTED` | Media is mounted |
| `flags & FN_DISK_FLAG_READONLY` | Media is protected/read-only |
| `flags & FN_DISK_FLAG_DIRTY` | NIO reports dirty state |
| `flags & FN_DISK_FLAG_CHANGED` | NIO reports changed state |
| `slot` | DiskDevice catalogue slot |
| `type` | NIO media type enum |
| `sector_size` | Sector size in bytes |
| `sector_count` | Total number of sectors |
| `last_error` | Optional protocol error field |

The media type enum currently contains:

```c
FN_DISK_TYPE_AUTO = 0
FN_DISK_TYPE_ATR  = 1
FN_DISK_TYPE_SSD  = 2
FN_DISK_TYPE_DSD  = 3
FN_DISK_TYPE_RAW  = 4
```

There are **no fields for**:

- heads/surfaces;
- sectors per track;
- cylinders;
- low/high cylinders;
- reserved blocks;
- filesystem type;
- OFS/FFS;
- RDB or partition metadata;
- geometry confidence;
- logical geometry.

Info parsing is implemented in:

`repos/fujinet-nio-lib/src/common/fn_disk.c:75-97`

It accepts a 12-byte response ending at `sector_count`, or a 13-byte response with `last_error`. The response supplies only the fields listed above.

The Amiga transport forwards the result without adding geometry:

`repos/fujinet-nio-driver/amiga/channels/rs232/fujinet_nio_client.c:26-50`

### Driver mount path

The Amiga driver passes a 512-byte hint and `FN_DISK_TYPE_AUTO`:

`repos/fujinet-nio-driver/amiga/common/fujinet_disk_driver.c:127-129`

```c
driver->client->mount(
    ...,
    FN_DISK_TYPE_AUTO,
    FUJINET_DISK_BLOCK_SIZE,
    &driver->media);
```

The hint is an input to NIO. It is not the authoritative result.

The driver then validates the returned Info response:

`fujinet_disk_driver.c:55-69`

Current validation requires:

- mounted flag;
- matching slot;
- raw media type;
- 512-byte sectors;
- sector count equal to 1760 or 3520;
- writable mount must not receive read-only media.

The successful Info result is retained independently in each `fujinet_disk_driver_t`:

```c
fn_disk_info_t media;
uint8_t mounted;
uint8_t writable;
```

The device uses that retained media descriptor for range checking. For example:

`repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:504-516`

and:

```c
media_bytes = sector_count * sector_size;
```

Thus the current block I/O path is already per-unit and sector-count-based.

### What is actually known for each image family

| Image | What current code actually reports or accepts |
|---|---|
| Standard DD ADF | NIO returns, and the Amiga driver accepts, `type=RAW`, `sector_size=512`, `sector_count=1760`. DD interpretation is supplied by the driver’s fixed profile logic, not by a NIO CHS field. |
| Standard HD ADF | NIO can return, and the Amiga driver accepts, `type=RAW`, `sector_size=512`, `sector_count=3520`. HD interpretation is inferred locally from the count in `TD_GETGEOMETRY`; NIO does not report heads/tracks/cylinders. |
| Raw HDF/RDB-style image | There is no current Amiga-side support. The current driver rejects any count other than 1760 or 3520. The `RAW` type only identifies a raw block representation; it does not establish HDF, whole-partition, RDB, or filesystem semantics. No RDB detection is present in the inspected Amiga path. |
| Malformed/non-standard raw image | If NIO successfully mounts it and reports valid geometry, the current Amiga driver rejects it unless the result happens to be exactly 512 bytes × 1760 or 3520 sectors. There is no current Amiga-side malformed-image or ambiguity classifier. |

The current NIO contract therefore provides authoritative **capacity and sector size**, plus state and a coarse type hint. It does not provide authoritative AmigaDOS mounting geometry.

## B. Current DD MountList and DosEnvec Contract

`DN0` through `DN7` are structurally identical apart from name and unit number. Example:

`repos/fujinet-nio-driver/amiga/config/DN0`

```text
DN0:
    Device = fujinet-disk.device
    Unit = 0
    Flags = 0
    Surfaces = 2
    BlocksPerTrack = 11
    Reserved = 2
    Interleave = 0
    LowCyl = 0
    HighCyl = 79
    Buffers = 5
    BufMemType = 1
    DosType = 0x444F5300
    StackSize = 32768
    Priority = 5
    GlobVec = -1
```

The repository also contains `config/DN0HD`, which changes only:

```text
BlocksPerTrack = 22
```

It is not currently integrated as the universal dynamic selection mechanism.

### Requested DD values

| Field | Current DD value | Status |
|---|---:|---|
| `Surfaces` | 2 | Explicit |
| `BlocksPerTrack` | 11 | Explicit |
| `LowCyl` | 0 | Explicit |
| `HighCyl` | 79 | Explicit |
| `BlockSize` | Not present | No explicit value in the file inspected |
| `Reserved` | 2 | Explicit |
| `PreAlloc` | Not present | No explicit value in the file inspected |
| `Interleave` | 0 | Explicit |
| `Buffers` | 5 | Explicit |
| `BufMemType` | 1 | Explicit |
| `MaxTransfer` | Not present | No explicit value in the file inspected |
| `Mask` | Not present | No explicit value in the file inspected |
| `DosType` | `0x444F5300` | Explicit, OFS-style DOS type |

`StackSize`, `Priority`, and `GlobVec` are also present. `StackSize=32768` is significant operationally for the filesystem handler but is not disk layout geometry.

### Layout-significant fields

These describe the filesystem’s logical block layout and therefore must match the image’s filesystem assumptions:

- `Surfaces`;
- `BlocksPerTrack`;
- `LowCyl`;
- `HighCyl`;
- `Reserved`;
- `DosType`;
- `BlockSize`, if supplied;
- `PreAlloc`, if supplied;
- related partition/filesystem geometry fields.

`Interleave` can affect allocation/access ordering and should not be changed casually, although the current value is zero.

For the DD profile:

```text
2 surfaces × 11 blocks/track × 80 cylinders = 1760 blocks
```

For the HD profile:

```text
2 surfaces × 22 blocks/track × 80 cylinders = 3520 blocks
```

### Device and handler configuration fields

These do not define the on-disk block layout:

- `Device`;
- `Unit`;
- `Flags`;
- `Buffers`;
- `BufMemType`;
- `MaxTransfer`;
- `Mask`;
- `StackSize`;
- `Priority`;
- `GlobVec`.

`Buffers` and memory/transfer settings can affect performance, DMA compatibility, or handler operation, but they do not replace the filesystem’s `DosEnvec` geometry.

### `TD_GETGEOMETRY` behavior

The current implementation is:

`repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c:630-655`

It reports:

- sector size: always 512;
- total sectors: retained NIO `sector_count`;
- cylinders: always 80;
- heads: always 2;
- track sectors: 22 for 3520 sectors, otherwise 11;
- cylinder sectors: 44 for 3520 sectors, otherwise 22;
- public memory;
- direct-access device;
- removable flag.

The current implementation therefore supports the known DD/HD profiles for the block-device query, but it does not construct or modify a `DosEnvec`.

### AmigaDOS startup semantics

Classic AmigaDOS obtains the filesystem device configuration from the DOS device node created from the MountList. The MountList supplies the `DosEnvec` used when the filesystem handler is started.

`TD_GETGEOMETRY` is a trackdisk/device inquiry command. It reports geometry to a caller; it does not rewrite an already-created DOS device node’s:

- `Surfaces`;
- `BlocksPerTrack`;
- `LowCyl`;
- `HighCyl`;
- `Reserved`;
- `DosType`;
- or other filesystem startup parameters.

Therefore:

> A static DD MountList remains a DD filesystem configuration even when the underlying device later returns HD values from `TD_GETGEOMETRY`.

The existing handler-safe replacement experiment proves that an active handler can rescan replacement media under the current workflow, but it does not prove that the handler’s startup `DosEnvec` changes between DD and HD. The current evidence does not justify relying on that behavior.

## C. Proposed Supported-Media Matrix

| Media | Whole-disk `DNx:` filesystem? | Expected handling |
|---|---|---|
| DD ADF, 880 KiB, 1760 × 512 | Yes | Recognize as the standard DD whole-volume profile. Use `2 × 11 × 80`, 512-byte blocks, reserved=2, existing OFS/FFS policy. |
| HD ADF, 1760 KiB, 3520 × 512 | Yes | Recognize as the standard HD whole-volume profile. Use `2 × 22 × 80`, 512-byte blocks, matching reserved/filesystem settings. Must use an HD DosEnvec before handler startup. |
| Non-standard ADF/raw OFS/FFS | Not generically | Sector size/count alone establishes capacity, not the intended filesystem geometry or filesystem type. Require additional profile/catalogue metadata and boot/root validation before mounting. |
| Partitioned RDB/HDF | Not as one whole-volume filesystem | Detect and parse RDB separately. Discover partition definitions, validate checksums/bounds, and create partition-specific DOS nodes with their own DosEnvec values. Do not present the whole disk as one OFS/FFS volume. |
| Unpartitioned/raw HDF | Only with explicit metadata/proof | Treat as a whole-partition image only if metadata or probing proves that sector zero is the filesystem boot block and supplies compatible block size, total geometry, reserved blocks, and DosType. |
| Malformed/ambiguous image | No | Reject before announcing insertion. Do not fall back to DD, 1760 sectors, or a guessed logical geometry. |

### What sector size/count alone can support

Sector size/count alone is sufficient for:

- block-device capacity;
- range checking;
- raw reads/writes;
- DD profile selection for exactly 512 × 1760;
- HD profile selection for exactly 512 × 3520, assuming the product requirement defines that standard profile.

It is not sufficient to establish:

- OFS versus FFS;
- RDB versus whole-partition HDF;
- partition boundaries;
- reserved blocks;
- filesystem type;
- non-standard CHS layout;
- whether a non-standard-size raw image is a valid filesystem.

The generic design must not equate `sector_count == 1760` with “DD ADF.” That interpretation is valid only when the media-class/profile policy explicitly recognizes the standard DD profile.

## D. Mounting Strategy Comparison

| Criterion | A. Known geometry profiles | B. Dynamic DOS device nodes | C. Verified linear geometry |
|---|---|---|---|
| Classic m68k feasibility | Feasible | Feasible, and aligns with AmigaDOS’s existing MountList model | Technically feasible but requires filesystem-layout proof |
| APIs required | Existing MountList/Mount flow, profile selection | `MakeDosNode()`/equivalent DOS node construction, `AddDosNode()`, handler startup/control, `Inhibit()` for replacement | Same dynamic node APIs plus probing/validation and a proof that logical geometry is safe |
| Handler restart/recreation | Required when geometry changes unless a handler-specific rescan contract is proven | Required for geometry changes; node must be built before handler startup | Required for geometry changes |
| FMOUNT live replacement | Existing same-geometry inhibit path can remain useful | FMOUNT must inhibit old handler, replace node/configuration, then restart or recreate handler for changed geometry | Same, plus possible layout-dependent transition failures |
| DD → HD → DD | Separate DD/HD profile selection works | Correctly creates the corresponding node each time | Only safe if the selected linear layout matches all existing images |
| OFS/FFS layout risk | Low for known standard profiles | Low if the generated `DosEnvec` exactly matches the selected profile | High until experimentally proven for non-standard layouts |
| Interaction with static MountLists | Static files can remain DD compatibility profiles | Static files become bootstrap/legacy only | Static files cannot safely express arbitrary derived geometry |
| Complexity | Low initially, grows poorly for HDF/RDB | Moderate, but is the correct general mechanism | High validation burden and unresolved filesystem semantics |
| Long-term extensibility | Poor for RDB and arbitrary partitions | Strong: one node per whole volume or partition | Poor for RDB and partitioned media |

### A. Known geometry profiles

This is the safest initial scope for DD and HD ADFs. It preserves the existing filesystem layout because each profile has known, standard geometry.

Its limitation is that profile selection alone cannot solve:

- non-standard ADFs;
- whole-partition HDFs;
- RDB partition discovery;
- arbitrary filesystem DosEnvec values.

It is best treated as the first implementation layer, not the final mounting architecture.

### B. Dynamically constructed DOS device nodes

This is the correct permanent model.

The flow should be:

1. Resolve the catalogue slot.
2. Mount the media in the NIO-backed device.
3. Obtain the authoritative Info descriptor.
4. Classify the media.
5. Select or construct the matching `DosEnvec`.
6. Construct/update the DOS device node.
7. Start or recreate the filesystem handler.
8. Persist the mapping only after successful activation.

For DD and HD ADFs, the generated geometry is deterministic. For future RDB media, the same model naturally extends to one DOS node per validated partition.

This model also makes the geometry boundary explicit: the NIO device owns block capacity, while AmigaDOS receives a matching filesystem configuration before handler startup.

### C. Verified linear logical geometry

This should not be selected as the general solution.

A linear geometry derived from total block count might be mathematically valid for block addressing, but that does not establish compatibility with an existing OFS/FFS layout. The on-disk filesystem may depend on:

- root block placement;
- reserved blocks;
- cylinder boundaries;
- allocation bitmap organization;
- filesystem type;
- boot block assumptions;
- partition-relative geometry.

The architecture document correctly identifies this as a later, experimentally validated option for selected non-standard whole-volume images, not as a substitute for known profiles or RDB metadata.

## E. Bounded Experiment

A new black-box experiment was not run.

It was not necessary to establish the design recommendation because:

1. The static `DN0` MountList is explicitly DD-shaped.
2. The separate `DN0HD` file confirms that HD requires a different `BlocksPerTrack` value.
3. `TD_GETGEOMETRY` only writes a `DriveGeometry` result supplied to the caller.
4. The AmigaOS Trackdisk documentation describes `TD_GETGEOMETRY` as a device inquiry and does not describe it as mutating DOS device nodes or handler startup state.
5. The existing code contains no API call that updates the active handler’s `DosEnvec`.

The existing handler-safe replacement evidence demonstrates same-handler media rescan behavior, but it should not be generalized to a DD-to-HD geometry transition. A targeted DD-to-HD experiment would be useful as a confirmation test, but it should be performed only after a test-only dynamic-node harness exists. It must not modify production lifecycle behavior merely to accommodate the test.

Expected result:

> A handler started from the static DD node will retain DD startup geometry. Changing `TD_GETGEOMETRY` to report HD sectors cannot be assumed to make that handler an HD filesystem handler.

## F. Recommendation

Choose **B: dynamically constructed DOS device nodes**, initially driven by **A: explicit known DD/HD profiles**.

Recommended policy:

- Keep `sector_size` and `sector_count` authoritative for block capacity.
- Treat `type` as a media-class hint, not as complete Amiga filesystem metadata.
- Recognize standard DD and HD ADF profiles explicitly.
- Construct a matching `DosEnvec` before starting the filesystem handler.
- Treat static `DN0`–`DN7` MountLists as DD compatibility/bootstrap profiles only.
- Require handler recreation or a deliberately verified node replacement when geometry changes.
- Do not use a linear geometry for arbitrary images until OFS/FFS layout preservation is demonstrated.
- Keep partitioned RDB/HDF as a separate media family requiring RDB parsing and partition DOS nodes.
- Reject ambiguous media instead of applying DD defaults.

This preserves current DD filesystem semantics, provides a correct HD path, and gives the architecture a viable extension point for whole-partition HDF and RDB media.

## G. Smallest Next Implementation Step

The smallest useful implementation step is:

> Add a testable Amiga-side media-profile classifier and DosEnvec builder for exactly two profiles: standard DD ADF and standard HD ADF.

It should consume the committed per-unit descriptor:

```text
sector_size
sector_count
type
flags
```

and produce a profile descriptor containing at least:

```text
block size
surfaces
blocks per track
low cylinder
high cylinder
reserved blocks
interleave
DosType
```

The first focused tests should verify:

- `512 × 1760` selects DD;
- `512 × 3520` selects HD;
- `512 × 1680` is rejected as ambiguous;
- non-512 sectors are rejected for the ADF profile path;
- raw media with large or unrecognized counts is not silently classified as DD;
- DD and HD profiles produce different `BlocksPerTrack` values;
- each of the eight units retains its own selected profile.

This step does not need to change production handler lifecycle yet. It establishes the classification and exact `DosEnvec` contract that the later dynamic-node/FMOUNT integration must consume.

# The Ask

Proceed with only the smallest implementation step from the geometry report.

Add a testable Amiga-side media-profile classifier and DosEnvec builder for exactly:

- standard DD ADF: 512 × 1760
- standard HD ADF: 512 × 3520

No production handler lifecycle changes yet.

The classifier must consume the retained per-unit fn_disk_info_t and produce an explicit profile containing at least:

block size
surfaces
blocks per track
low cylinder
high cylinder
reserved blocks
interleave
DosType

Required behavior:

512 × 1760 -> DD profile
512 × 3520 -> HD profile
512 × 1680 -> reject as ambiguous/unsupported
non-512 sector size -> reject for ADF profile path
large/unrecognized RAW media -> do not silently classify as DD

Add focused unit tests proving DD and HD produce different BlocksPerTrack, and that classification state is independent per unit.

Keep sector_size and sector_count authoritative.

Do not infer OFS/FFS, RDB, partition metadata, or arbitrary geometry from sector count alone.

Do not modify FMOUNT, Mount, handler restart behavior, or static MountLists in this segment.

Return:

1. the new profile/classifier API;
2. the exact DD and HD profile values;
3. test results;
4. where this output will later feed dynamic DOS-node construction.

# The implementation

Implemented the focused DD/HD media-profile classifier without changing mount lifecycle behavior, `FMOUNT`, static MountLists, or handler restart logic.

**1. Profile/classifier API**

Added to `amiga/include/fujinet_disk_driver.h`:

```c
typedef enum fujinet_disk_media_profile_kind {
    FUJINET_DISK_MEDIA_PROFILE_DD_ADF = 1,
    FUJINET_DISK_MEDIA_PROFILE_HD_ADF = 2
} fujinet_disk_media_profile_kind_t;

typedef struct fujinet_disk_media_profile {
    fujinet_disk_media_profile_kind_t kind;
    uint32_t block_size;
    uint32_t surfaces;
    uint32_t blocks_per_track;
    uint32_t low_cylinder;
    uint32_t high_cylinder;
    uint32_t reserved_blocks;
    uint32_t interleave;
    uint32_t dos_type;
} fujinet_disk_media_profile_t;
```

Classifier API:

```c
uint8_t fujinet_disk_classify_media_profile(
    const fn_disk_info_t *info,
    fujinet_disk_media_profile_t *profile);
```

Implementation:

`repos/fujinet-nio-driver/amiga/common/fujinet_disk_media_profile.c`

The classifier requires:

- `FN_DISK_FLAG_MOUNTED`;
- `FN_DISK_TYPE_RAW`;
- `sector_size == 512`;
- exact DD or HD sector count.

All other media return `FN_ERR_INVALID`.

**2. Exact profile values**

DD ADF, `512 × 1760`:

| Field | Value |
|---|---:|
| `kind` | `FUJINET_DISK_MEDIA_PROFILE_DD_ADF` |
| `block_size` | 512 |
| `surfaces` | 2 |
| `blocks_per_track` | 11 |
| `low_cylinder` | 0 |
| `high_cylinder` | 79 |
| `reserved_blocks` | 2 |
| `interleave` | 0 |
| `dos_type` | `0x444F5300` |

HD ADF, `512 × 3520`:

| Field | Value |
|---|---:|
| `kind` | `FUJINET_DISK_MEDIA_PROFILE_HD_ADF` |
| `block_size` | 512 |
| `surfaces` | 2 |
| `blocks_per_track` | 22 |
| `low_cylinder` | 0 |
| `high_cylinder` | 79 |
| `reserved_blocks` | 2 |
| `interleave` | 0 |
| `dos_type` | `0x444F5300` |

The classifier does not infer OFS/FFS, RDB, partition metadata, or arbitrary geometry.

**3. Tests**

Added focused tests covering:

- DD profile selection;
- HD profile selection;
- distinct DD/HD `BlocksPerTrack`;
- exact profile field values;
- rejection of 1680-sector media;
- rejection of large/unrecognized raw media;
- rejection of non-512-byte media;
- independent DD and HD classification for separate unit media descriptors.

Validation passed:

```text
make -C repos/fujinet-nio-driver/amiga/tests test
```

Results:

```text
All Amiga driver contract tests passed
All Amiga FIFO policy tests passed
All Amiga Exec boundary contract tests passed
```

`git diff --check` also passed.

**4. Later dynamic DOS-node integration**

The generated `fujinet_disk_media_profile_t` is intended to become the input to the later dynamic DOS-node construction path:

1. Mount media through NIO.
2. Read retained per-unit `fn_disk_info_t`.
3. Classify into DD or HD profile.
4. Convert the profile fields into a `DosEnvec`.
5. Construct the corresponding DOS device node before starting the filesystem handler.

No lifecycle integration has been added in this segment.

# Corrections

Before proceeding to dynamic DOS-node construction, correct the media-profile model so geometry classification does not implicitly infer filesystem type.

The current DD and HD profiles both populate:

dos_type = 0x444F5300

but DD/HD image size alone does not establish OFS versus FFS. Therefore the statement that the classifier “does not infer OFS/FFS” is inconsistent with its output.

Keep this segment small:

1. Make the DD/HD classifier describe geometry only.
2. Remove dos_type from the geometry profile, or represent it explicitly as unknown/unresolved rather than defaulting to DOS\0.
3. Do not add boot-block probing yet unless it is required to keep the API clean.
4. Preserve all existing DD/HD geometry tests and rejection tests.
5. Add a test proving DD/HD geometry classification does not claim a filesystem DosType.

Also document the units of block_size explicitly as bytes.

Add a note for the future DosEnvec builder that:

profile.block_size = 512 bytes
DosEnvec.de_SizeBlock = 128 longwords

Do not change FMOUNT, lifecycle behavior, MountLists, or dynamic-node handling in this correction.

Return the revised API and test results only.

# Implementation 2

**Revised API**

`fujinet_disk_media_profile_t` now describes geometry only:

```c
typedef struct fujinet_disk_media_profile {
    fujinet_disk_media_profile_kind_t kind;
    uint32_t block_size; /* bytes */
    uint32_t surfaces;
    uint32_t blocks_per_track;
    uint32_t low_cylinder;
    uint32_t high_cylinder;
    uint32_t reserved_blocks;
    uint32_t interleave;
} fujinet_disk_media_profile_t;
```

Classifier:

```c
uint8_t fujinet_disk_classify_media_profile(
    const fn_disk_info_t *info,
    fujinet_disk_media_profile_t *profile);
```

`dos_type` has been removed. The classifier no longer claims OFS, FFS, or any other filesystem type.

The profile implementation still accepts only:

- mounted `FN_DISK_TYPE_RAW` media;
- `sector_size == 512`;
- `sector_count == 1760` or `3520`.

All other geometry remains rejected.

Future `DosEnvec` construction must convert:

```text
profile.block_size = 512 bytes
DosEnvec.de_SizeBlock = 128 longwords
```

No boot-block probing or filesystem-type inference was added.

**Test Results**

Preserved and passing:

- DD profile selection for `512 × 1760`;
- HD profile selection for `512 × 3520`;
- DD `BlocksPerTrack == 11`;
- HD `BlocksPerTrack == 22`;
- rejection of 1680-sector media;
- rejection of large/unrecognized raw media;
- rejection of non-512-byte media;
- independent DD/HD classification per unit.

Added a geometry-only test confirming the profile API does not claim a filesystem `DosType`.

Validation passed:

```text
make -C repos/fujinet-nio-driver/amiga/tests test
```

Results:

```text
All Amiga driver contract tests passed
All Amiga FIFO policy tests passed
All Amiga Exec boundary contract tests passed
```

Commit: 881a7a3e in fujinet-nio-driver

# Second part ask

Proceed to the next Media Geometry segment.

The DD/HD geometry classifier is complete and must remain geometry-only.

The next task is to establish and implement a small, testable Amiga filesystem/DosType classifier for standard ADF media, so the later dynamic DosEnvec builder has two independent inputs:

fn_disk_info_t
    ↓
geometry classifier
    ↓
DD / HD geometry profile


media contents
    ↓
filesystem classifier
    ↓
validated DosType

Do not construct dynamic DOS nodes yet.

Do not modify FMOUNT or handler lifecycle yet.

1. Establish the source of filesystem identity

Inspect the classic Amiga filesystem/boot-block format and our existing DD/HD ADF fixtures.

Establish exactly how an OFS/FFS-family whole-volume ADF identifies its filesystem DosType on disk.

Report:

where the value is stored
how many bytes are required to identify it
which DosType values our existing test fixtures actually contain
what validation is required before trusting it

Do not infer filesystem type from DD/HD geometry.

2. Add a pure/testable classifier

Add a small API which consumes the minimum media bytes required and returns either:

validated DosType
unsupported/invalid

Keep this separate from fujinet_disk_media_profile_t.

At minimum test:

- existing standard DD fixture;
- existing standard HD fixture if available;
- OFS and FFS fixtures if both already exist or can be safely generated test-only;
- invalid boot signature;
- unsupported DosType;
- truncated input.

Do not silently default invalid/unknown media to DOS\0.

3. Define the future combined contract

Show how the later DosEnvec builder will consume:

fujinet_disk_media_profile_t geometry
+
validated filesystem DosType

and produce the exact DD/HD DosEnvec.

Remember that:

profile.block_size = 512 bytes
de_SizeBlock = 128 longwords

Do not implement MakeDosNode() / AddDosNode() yet.

Deliverable

Return:

a. filesystem-identification evidence;
b. classifier API;
c. supported/rejected DosType policy;
d. tests and results;
e. exact proposed input contract for the subsequent DosEnvec builder.

Keep this segment bounded. No production lifecycle changes.

# Implementation part 2

## A. Filesystem Identification Evidence

An Amiga whole-volume boot block stores the filesystem identity in its first four bytes as a big-endian `DosType` longword:

```text
offset 0..3: DosType
```

Examples:

```text
"DOS\x00" -> 0x444F5300 -> OFS
"DOS\x01" -> 0x444F5301 -> FFS
```

The existing fixture generator in `integration-tests/amiberry/conftest.py` creates both DD and HD images with `xdftool` and installs a boot block. The existing standard fixtures are OFS-family images and therefore contain:

```text
DOS\x00
```

The existing HD fixture uses the same boot installation path and is also expected to contain `DOS\x00`.

No existing FFS fixture was found. The FFS test vector is a test-only four-byte boot-block fixture using:

```text
DOS\x01
```

The classifier requires only the first four bytes to identify the candidate `DosType`. Full boot-block trust for mounting would additionally require later validation, including boot-block checksum and filesystem/root-block consistency. That validation is intentionally not implemented in this bounded segment.

## B. Classifier API

Added:

`amiga/include/fujinet_disk_filesystem.h`

```c
#define FUJINET_AMIGA_DOS_OFS 0x444F5300UL
#define FUJINET_AMIGA_DOS_FFS 0x444F5301UL

#define FUJINET_AMIGA_BOOT_DOSTYPE_BYTES 4U

uint8_t fujinet_disk_classify_filesystem(
    const uint8_t *boot_block,
    size_t boot_block_length,
    uint32_t *dos_type);
```

Implementation:

`amiga/common/fujinet_disk_filesystem.c`

The classifier:

- requires at least four bytes;
- reads the DosType as big-endian;
- requires the `DOS` signature;
- accepts only `DOS\x00` and `DOS\x01`;
- returns the validated DosType through `dos_type`;
- returns `FN_ERR_INVALID` for null, truncated, malformed, or unsupported input;
- does not default unknown media to `DOS\0`.

## C. Supported Policy

| Boot DosType | Policy |
|---|---|
| `0x444F5300` (`DOS\x00`) | Accepted as OFS |
| `0x444F5301` (`DOS\x01`) | Accepted as FFS |
| `0x444F5302` and above | Rejected by this first-pass policy |
| Invalid signature | Rejected |
| Fewer than four bytes | Rejected |

The filesystem classifier is separate from `fujinet_disk_media_profile_t`. Geometry classification still consumes authoritative `fn_disk_info_t` sector size/count and does not infer filesystem type.

## D. Tests

Added tests for:

- standard DD boot identity as OFS;
- standard HD boot identity as OFS;
- test-only FFS boot identity;
- invalid boot signature;
- unsupported DosType;
- truncated boot-block input.

The prior geometry tests remain unchanged and continue to cover:

- DD and HD geometry;
- different `BlocksPerTrack`;
- independent per-unit classification;
- 1680-sector rejection;
- large/unrecognized raw-media rejection;
- non-512-byte rejection.

Validation passed:

```text
make -C repos/fujinet-nio-driver/amiga/tests test
```

Results:

```text
All Amiga driver contract tests passed
All Amiga FIFO policy tests passed
All Amiga Exec boundary contract tests passed
```

`git diff --check` passed.

## E. Future DosEnvec Input Contract

The later DosEnvec builder should receive two independent validated inputs:

```text
fn_disk_info_t
    -> fujinet_disk_media_profile_t
       geometry fields only

boot-block bytes
    -> validated uint32_t dos_type
       filesystem identity only
```

For the subsequent DD/HD builder:

```text
profile.block_size       = 512 bytes
DosEnvec.de_SizeBlock    = 128 longwords
profile.surfaces         = 2
profile.blocks_per_track = 11 or 22
profile.low_cylinder     = 0
profile.high_cylinder    = 79
profile.reserved_blocks  = 2
profile.interleave       = 0
dos_type                 = validated filesystem result
```

`MakeDosNode()`, `AddDosNode()`, `FMOUNT`, and handler lifecycle behavior were not changed.

# Corrections to part 2

Before moving on to the DosEnvec builder, I want to close out three concerns from the filesystem-classifier segment.

Do not start any new Media Geometry implementation work in this turn.

1. API contract language

The current report says the classifier returns a “validated DosType”.

That wording is too strong for what the implementation currently proves.

Reading the first four boot-block bytes and recognizing:

DOS\0
DOS\1

establishes that the boot block claims a recognized/supported DosType.

It does not establish that the whole filesystem is valid.

Full filesystem validation would require later checks such as:

boot-block checksum
root-block consistency
filesystem structural consistency

Please review the code comments, header documentation, tests, and any backlog/findings wording added in this segment.

Adjust terminology so the contract is explicitly:

recognize/classify a supported boot-block DosType

rather than:

validate the filesystem / validated DosType

The API name fujinet_disk_classify_filesystem() may remain if you think it still accurately describes the narrow operation, but its documented contract must make the limitation explicit.

Report the exact wording used after correction.

2. DOS\2 and above

The first-pass implementation accepts:

DOS\0 -> OFS
DOS\1 -> FFS

and rejects DOS\2 and above.

I want the policy and terminology checked carefully here.

DOS\2+ should be treated as:

recognized Amiga DOS-family identifiers that are unsupported by the current first-pass policy

rather than:

inherently malformed/corrupt input

If the current low-level API still maps both malformed and unsupported inputs to FN_ERR_INVALID, that is acceptable for now if the surrounding code does not yet need a distinct error code.

However, the documentation/tests must preserve the conceptual distinction:

malformed boot signature
recognized but unsupported DosType
supported DosType

Review and correct the implementation comments/tests/report wording as needed.

Explicitly state whether the current API can distinguish malformed from unsupported at runtime, and whether that distinction is intentionally deferred.

3. Verify the actual generated DD/HD fixtures

The previous report said:

the existing HD fixture uses the same boot installation path and is also expected to contain DOS\0

I do not want this left as an assumption.

Verify the actual generated DD and HD ADF fixtures used by the Amiberry integration tests.

Inspect the first four bytes of each generated image and report them explicitly, e.g.:

DD fixture: 44 4F 53 00 -> DOS\0
HD fixture: 44 4F 53 00 -> DOS\0

If either fixture differs, report the actual value and explain why.

Also confirm whether the current DD/HD classifier tests consume bytes from those real/generated fixtures or only synthetic four-byte test vectors.

Do not change fixture generation unless the verification exposes a genuine mismatch.

Deliverable

Return only:

a. final API-contract wording;
b. final policy for DOS\2+ and malformed inputs;
c. actual first four bytes of the generated DD and HD fixtures;
d. whether the tests use real fixture bytes or synthetic vectors;
e. any small corrections made to close these points.

Do not proceed to the DosEnvec builder yet.

# Implementing corrections

a. **Final API-contract wording**

The classifier contract is now:

> `fujinet_disk_classify_filesystem()` recognizes and classifies a supported boot-block `DosType` from the first four bytes of an Amiga boot block. A successful result means that the boot block claims a supported OFS or FFS-family identifier. It does not validate the complete filesystem. Full validation would additionally require boot-block checksum verification, root-block consistency checks, and filesystem structural validation.

The header comment uses the equivalent wording:

> “Returns a recognized supported `DosType` from the boot-block identifier. This does not by itself establish that the complete filesystem is valid.”

The implementation and tests do not describe the result as a validated filesystem or validated `DosType`.

b. **Final DOS\2+ and malformed-input policy**

| Input | Conceptual classification | Current result |
|---|---|---|
| `DOS\0` | Supported boot-block DosType, OFS | `FN_OK`, returns `0x444F5300` |
| `DOS\1` | Supported boot-block DosType, FFS | `FN_OK`, returns `0x444F5301` |
| `DOS\2+` | Recognized Amiga DOS-family identifier, unsupported by this first-pass policy | `FN_ERR_INVALID` |
| Non-`DOS` signature | Malformed/unrecognized boot-block identifier | `FN_ERR_INVALID` |
| Fewer than four bytes | Truncated input | `FN_ERR_INVALID` |

The current API cannot distinguish malformed, truncated, and recognized-but-unsupported inputs at runtime because all map to `FN_ERR_INVALID`. That distinction is intentionally deferred until the surrounding classifier API needs separate error reporting. The tests preserve the conceptual distinction with separate cases and descriptions.

c. **Actual generated DD/HD fixture bytes**

Generated using the existing `create_standard_adf()` and `create_hd_adf()` helpers without changing fixture generation:

```text
DD fixture: 44 4F 53 00 -> DOS\0
HD fixture: 44 4F 53 00 -> DOS\0
```

Observed generated sizes:

```text
DD: 901120 bytes = 1760 × 512
HD: 1802240 bytes = 3520 × 512
```

d. **Test fixture source**

The current filesystem-classifier unit tests use synthetic four-byte vectors:

```c
{'D', 'O', 'S', 0}  // OFS
{'D', 'O', 'S', 1}  // FFS
```

They do not consume bytes directly from the generated DD/HD image files.

The generated DD and HD fixtures were independently inspected and both contain `DOS\0` at offset zero. No fixture-generation changes were made.

e. **Corrections made**

Only the API contract wording was reviewed and clarified. No DosEnvec, geometry, lifecycle, FMOUNT, MountList, or fixture-generation changes were made.

Commit e0697c09 in repos/fujinet-nio-driver

# Part 3

Proceed to the next bounded Media Geometry step: implement a pure/testable DosEnvec builder from the already-separated geometry profile and recognized boot-block DosType.

Inputs:

const fujinet_disk_media_profile_t *profile
uint32_t dos_type

Output:

an AmigaDOS environment/DosEnvec representation suitable for later dynamic DOS-node construction

Do not call MakeDosNode() or AddDosNode() yet.
Do not modify FMOUNT, static MountLists, or handler lifecycle.

The builder must map the profile into exact AmigaDOS values and must explicitly handle representation units.

In particular:

profile.block_size = 512 bytes
de_SizeBlock       = 128 longwords

Required field mapping for the current DD/HD scope:

Surfaces       = 2
BlocksPerTrack = 11 for DD, 22 for HD
LowCyl         = 0
HighCyl        = 79
Reserved       = 2
Interleave     = 0
DosType        = supplied supported DosType

Also preserve the operational values currently required by the existing DN0-DN7 MountLists where applicable, such as buffers, memory type, stack size, priority, and any other fields needed for a correct future DOS node.

Before hard-coding those operational values, inspect the existing MountLists and classic DosEnvec structure and distinguish:

filesystem/layout fields
handler/device operational fields
values that are omitted and therefore use OS defaults

Do not invent values for fields that the existing MountLists intentionally omit unless the API requires an explicit value.

Required tests:

DD + DOS\0
DD + DOS\1
HD + DOS\0
HD + DOS\1

Verify every produced field, especially:

de_SizeBlock
de_Surfaces
de_BlocksPerTrack
de_LowCyl
de_HighCyl
de_Reserved
de_Interleave
de_DosType

Ensure unsupported DosTypes cannot enter the builder silently. Either reject them directly or make the precondition explicit and test that contract.

Also verify that DD and HD produce identical fields except where the geometry genuinely differs.

Return:

1. builder API;
2. exact field mapping;
3. treatment of omitted/default MountList fields;
4. tests and results;
5. the exact structure/output that the later MakeDosNode() integration will consume.

Do not proceed to dynamic DOS-node creation in this turn.

# Implementation for part 3

Implemented the pure/testable DosEnvec builder. No `MakeDosNode()`, `AddDosNode()`, `FMOUNT`, MountList, or handler lifecycle changes were made.

## 1. Builder API

Added:

`amiga/include/fujinet_disk_dos_envec.h`

```c
typedef struct fujinet_disk_dos_envec {
    uint32_t de_SizeBlock;
    uint32_t de_Surfaces;
    uint32_t de_BlocksPerTrack;
    uint32_t de_LowCyl;
    uint32_t de_HighCyl;
    uint32_t de_Reserved;
    uint32_t de_PreAlloc;
    uint32_t de_Interleave;
    uint32_t de_NumBuffers;
    uint32_t de_BufMemType;
    uint32_t de_MaxTransfer;
    uint32_t de_Mask;
    uint32_t de_DosType;
    int32_t handler_stack_size;
    int32_t handler_priority;
    int32_t handler_glob_vec;
} fujinet_disk_dos_envec_t;
```

```c
uint8_t fujinet_disk_build_dos_envec(
    const fujinet_disk_media_profile_t *profile,
    uint32_t dos_type,
    fujinet_disk_dos_envec_t *envec);
```

The output is a host-testable representation of the DosEnvec and handler configuration fields required by the later dynamic-node path.

## 2. Exact Field Mapping

For both DD and HD:

| Output field | Value |
|---|---:|
| `de_SizeBlock` | `128` longwords |
| `de_Surfaces` | `2` |
| `de_LowCyl` | `0` |
| `de_HighCyl` | `79` |
| `de_Reserved` | `2` |
| `de_Interleave` | `0` |
| `de_NumBuffers` | `5` |
| `de_BufMemType` | `1` |
| `handler_stack_size` | `32768` |
| `handler_priority` | `5` |
| `handler_glob_vec` | `-1` |

`de_SizeBlock` is explicitly converted from bytes to longwords:

```text
profile.block_size = 512 bytes
de_SizeBlock = 512 / 4 = 128 longwords
```

Geometry-specific values:

| Profile | `de_BlocksPerTrack` |
|---|---:|
| DD | 11 |
| HD | 22 |

Filesystem-specific value:

```text
de_DosType = supplied DOS\0 or DOS\1
```

## 3. Omitted MountList Fields

The existing MountLists explicitly provide:

- `Surfaces`;
- `BlocksPerTrack`;
- `Reserved`;
- `Interleave`;
- `LowCyl`;
- `HighCyl`;
- `Buffers`;
- `BufMemType`;
- `StackSize`;
- `Priority`;
- `GlobVec`.

They omit:

- `PreAlloc`;
- `MaxTransfer`;
- `Mask`.

The builder leaves omitted fields at zero:

```text
de_PreAlloc   = 0
de_MaxTransfer = 0
de_Mask       = 0
```

No values were invented for omitted MountList fields.

## 4. Validation and Tests

The builder rejects:

- null profile;
- null output;
- unsupported profile kind;
- non-512-byte profiles;
- unsupported DosTypes, including `DOS\2` and above.

Tests cover all required combinations:

- DD + `DOS\0`;
- DD + `DOS\1`;
- HD + `DOS\0`;
- HD + `DOS\1`.

They verify:

- `de_SizeBlock`;
- surfaces;
- blocks per track;
- cylinder bounds;
- reserved blocks;
- interleave;
- DosType;
- operational MountList values;
- omitted fields remain zero;
- DD and HD differ only in genuine geometry fields when the DosType is held constant;
- unsupported DosTypes cannot enter the builder.

Validation passed:

```text
make -C repos/fujinet-nio-driver/amiga/tests test
```

Results:

```text
All Amiga driver contract tests passed
All Amiga FIFO policy tests passed
All Amiga Exec boundary contract tests passed
```

`git diff --check` passed.

## 5. Later Integration Input

The future dynamic-node path will consume:

```text
fujinet_disk_media_profile_t geometry
+
recognized boot-block DosType
+
fujinet_disk_dos_envec_t output
```

The resulting structure is ready to be translated into the classic Amiga `DosEnvec` representation when dynamic DOS-node construction is implemented.

# Part 3 Correction

Before moving to dynamic DOS-node creation, verify that fujinet_disk_dos_envec_t represents the effective DosEnvec produced by the current static DNx MountLists, not merely the keywords textually present in the files.

Do not start MakeDosNode() integration yet.

There are two specific concerns to resolve.

1. Omitted MountList fields versus effective defaults

The current report says:

PreAlloc = 0
MaxTransfer = 0
Mask = 0

because those keywords are absent from the MountLists.

Verify this against actual classic AmigaDOS behavior.

Omitted MountList keywords may receive defaults rather than becoming zero. In particular investigate the effective values of:

PreAlloc
MaxTransfer
Mask

Do not infer these from the MountList text alone.

Preferably verify the actual mounted DN0: environment at runtime using an AmigaOS API/tool such as MOUNTINFO ... DEBUG, DOS-list inspection, or an equivalent test helper that reads the active FileSysStartupMsg / DosEnvec.

Report both:

MountList keyword
effective runtime DosEnvec value

for all relevant fields.

If the runtime effective values differ from the current builder output, correct the builder and tests.

2. Complete DosEnvec shape required by MakeDosNode

Review the classic DosEnvec / MakeDosNode() environment layout and identify every field the later dynamic-node packet must provide.

In particular verify whether the current abstraction needs to represent:

de_TableSize
de_SecOrg
de_SectorPerBlock
de_BootPri

and any other fields currently omitted.

Do not add fields merely because they exist historically; add them if they are required to faithfully reproduce the existing DNx mount behavior or required by the MakeDosNode() environment format.

Explicitly verify the expected values for our device, including:

de_SizeBlock       = 128 longwords
de_SecOrg          = 0
de_SectorPerBlock  = 1
Deliverable

Return:

a. the effective runtime DosEnvec for the current static DN0: mount;
b. differences, if any, from the existing builder;
c. the corrected builder representation if required;
d. exact tests added/changed;
e. confirmation that the resulting abstraction contains everything required for later MakeDosNode() construction.

Do not proceed to dynamic-node creation yet.

# Part 4

Proceed to the next Media Geometry segment: test-only dynamic DOS-node construction.

The geometry classifier, boot-block DosType classifier, and complete DosEnvec builder are now signed off.

Do not modify production FMOUNT lifecycle yet.
Do not remove or repurpose the static DN0–DN7 MountLists yet.

Goal

Prove that classic AmigaOS can dynamically construct and activate a DNx: device node from the generated fujinet_disk_dos_envec_t, reproducing the current static MountList behavior.

Start with DD only.

1. Establish exact classic API mapping

Implement a test helper that translates:

fujinet_disk_dos_envec_t

into the exact structures expected by classic:

MakeDosNode()
AddDosNode()

and whatever startup structure is required for:

Device = fujinet-disk.device
Unit   = 0

Use the complete verified environment values from the builder.

Note explicitly that:

de_TableSize = 19

represents the complete environment entries 0..19; do not reinterpret it as an entry count of 20.

2. DD proof only

Using a new test-only DOS device name so the existing static DN0: does not interfere, dynamically construct a DD device node for unit 0.

Prefer something unmistakably diagnostic such as:

DY0:

or another unused name.

Then start/mount the filesystem handler through the normal classic AmigaDOS mechanism.

The test must prove:

dynamic node exists
handler starts
Dir succeeds
Type KNOWN.TXT succeeds
correct expected DD fixture contents are read

Also use doslistdiag or equivalent to inspect the dynamically created node and verify its effective runtime DosEnvec matches the builder output.

3. Cleanup/lifetime

Establish and report:

ownership/lifetime of MakeDosNode allocations
ownership after AddDosNode
how the test removes/retires the node
what happens to the handler task
whether explicit DOS-list removal is required

Do not guess at ownership semantics. Verify them against the classic API behavior and/or the running test.

Cleanup must leave the existing static DN devices unaffected.

4. Failure behavior

Exercise at least one bounded failure case, such as:

invalid/unsupported DosEnvec input
duplicate device-node name
failed handler startup

Ensure the helper does not leave a stale DOS-list entry behind.

Scope boundary

Do not:

- integrate this into FMOUNT;
- implement DD→HD replacement;
- modify handler-safe Inhibit() logic;
- remove static MountLists;
- add RDB/HDF handling.

This segment answers only:

Can we faithfully replace the static DD MountList with a dynamically constructed classic DOS node?

Deliverable

Return:

a. exact MakeDosNode/AddDosNode construction path;
b. dynamic node name and startup sequence;
c. runtime DosEnvec comparison against the builder;
d. Dir/Type evidence;
e. node/handler ownership and cleanup findings;
f. failure-case result;
g. focused Amiberry test result.

If the DD proof succeeds, stop there. Do not proceed to HD in this turn.

# Implementation 4

The DD dynamic-node segment is not proven yet. I stopped before any HD work or production lifecycle changes.

**Implemented**

- Added test-only `dynamicdosnode` helper in `repos/nio-apps/apps/test/dynamicdosnode.c`.
- Uses the classic packet layout:
  - packet word 0: handler name, `L:FastFileSystem`
  - packet word 1: Exec device, `fujinet-disk.device`
  - packet word 2: unit `0`
  - packet word 3: OpenDevice flags `0`
  - words 4 through 23: the complete `fujinet_disk_dos_envec_t` environment
- Uses `de_TableSize = 19` as the final populated index for entries `0..19`.
- Uses diagnostic DOS name `DY0`.
- Calls:
  - `MakeDosNode(packet)`
  - sets the returned node name to the BCPL string `DY0`
  - `AddDosNode(0, ADNF_STARTPROC, node)`
- Adds a duplicate-name attempt.
- Adds a cleanup helper using `RemDosEntry()`.
- Added a focused startup sequence and pytest case:
  - `integration-tests/amiberry/startup/diskdevice-dynamic-dd.sequence`
  - `integration-tests/amiberry/test_diskdevice_adf.py`
  - `integration-tests/amiberry/tests.toml`

The helper and native Amiga application build successfully.

**Runtime Result**

The focused Amiberry case reaches:

```text
dynamic-node.result
```

That confirms the helper reached the `MakeDosNode()` and `AddDosNode()` path far enough to produce its result file.

However, the next operation, DOS-list inspection of the dynamic node, does not complete:

```text
last checkpoint present: dynamic-node.result
first checkpoint missing: dynamic-doslist.result
```

The case then times out before `Dir DY0:`. Therefore:

- dynamic node activation is not yet demonstrated;
- handler startup is not yet demonstrated;
- `Dir` and `Type` have not passed;
- runtime DosEnvec comparison for `DY0` has not passed;
- cleanup behavior has not been validated;
- the duplicate-name result has not been accepted as a valid proof.

The likely fault is in the constructed node/startup representation, not in the Amiberry harness or compiler. The next debugging step is to inspect the newly created `DeviceNode` directly before calling DOS-list traversal, especially the returned node’s `dn_Name`, `dn_Startup`, `dn_Handler`, and the BPTR chain to `FileSysStartupMsg`. The test currently stops rather than hiding that failure.

**Validation**

Passed:

```text
make -C repos/nio-apps amiga
```

The existing native driver contract tests also pass during the focused harness setup:

```text
All Amiga driver contract tests passed
All Amiga FIFO policy tests passed
All Amiga Exec boundary contract tests passed
```

Failed:

```text
pytest integration-tests/amiberry/test_diskdevice_adf.py::test_dynamic_dd_dos_node --run-amiga -q
```

Failure occurs after `dynamic-node.result` and before dynamic DOS-list inspection.

No `FMOUNT` lifecycle code, static `DN0`–`DN7` MountLists, HD logic, RDB/HDF logic, or handler-safe `Inhibit()` logic was modified.

# 4. Corrections, and next moves

We now have the actual dynamicdosnode.c, and there is a concrete issue in the MakeDosNode() packet construction that must be corrected before any further debugging.

Do not make production, FMOUNT, HD, geometry, or harness changes.

Do not investigate handler startup yet.

1. Correct the MakeDosNode() packet

The current code contains:

static const char dos_name[] = "DY0";
static const unsigned char dos_name_bstr[] = { 3, 'D', 'Y', '0', 0 };
static const char exec_name[] = "fujinet-disk.device";
static const char handler_name[] = "L:FastFileSystem";


...


packet[0] = (ULONG)handler_name;
packet[1] = (ULONG)exec_name;
packet[2] = 0;
packet[3] = 0;

This is wrong for the classic MakeDosNode() packet.

Packet word 0 must be the DOS device name, not the filesystem handler name.

Correct the construction to use:

packet[0] = "DY0"
packet[1] = "fujinet-disk.device"
packet[2] = unit 0
packet[3] = OpenDevice flags 0
packet[4..23] = complete DosEnvec

Establish from the classic API whether packet word 0 is expected to point to a normal C string for MakeDosNode(), and implement it exactly as required.

L:FastFileSystem must not be substituted for the DOS device name. If a filesystem handler path is needed anywhere else in this API path, identify the correct field/API for it rather than putting it into packet word 0.

2. Stop rewriting dn_Name

Remove this manual patch:

node->dn_Name = MKBADDR(dos_name_bstr);

MakeDosNode() should construct the DeviceNode name from packet word 0.

After MakeDosNode() returns, inspect and report:

dn_Name BPTR
decoded dn_Name
dn_Startup BPTR
dn_Handler
dn_StackSize
dn_Priority
dn_GlobVec

The decoded name must already be:

DY0

before AddDosNode() is called.

If it is not, stop and report the actual structure instead of patching it manually.

3. Isolate DOS-list insertion from handler startup

For this diagnostic run, do not use:

ADNF_STARTPROC

Add the correctly constructed node using:

AddDosNode(source.de_BootPri, 0, node);

The purpose of this run is only to prove:

MakeDosNode
    -> valid DY0 DeviceNode
AddDosNode
    -> valid DOS-list entry
doslistdiag
    -> safely enumerates and decodes DY0

Do not invoke Dir DY0: or Type DY0: in this first corrected run.

4. Remove unrelated duplicate/cleanup testing temporarily

Do not perform the second MakeDosNode() duplicate-name attempt in this isolation run.

Do not exercise removal/cleanup yet.

Those tests can be restored after a single correctly constructed DY0 can be inserted and enumerated safely.

This removes extra DOS-list mutation while establishing the basic structure.

5. Inspect the complete generated startup structure

Immediately after MakeDosNode() and after insertion, decode:

DeviceNode
  dn_Name
  dn_Startup
  dn_Handler
  dn_StackSize
  dn_Priority
  dn_GlobVec


dn_Startup
  -> FileSysStartupMsg
     fssm_Unit
     fssm_Device
     fssm_Environ
     fssm_Flags


fssm_Environ
  -> complete DosEnvec

Compare those values with the known-good static DN0 node already exposed by doslistdiag.

6. Minimal startup sequence

Temporarily reduce the focused case to approximately:

LoadModule DEVS:fujinet-disk.device
mount the standard ADF in the NIO device


Echo "=== BEFORE DYNAMIC NODE ==="
dynamicdosnode
Echo "=== AFTER DYNAMIC NODE RC=$RC ==="


Echo "=== BEFORE DOSLIST ==="
doslistdiag
Echo "=== AFTER DOSLIST RC=$RC ==="

Retain both file results and visible CLI output/screenshots.

Do not attempt Dir DY0: yet.

Deliverable

Report:

a. corrected packet contents;
b. decoded DeviceNode immediately after MakeDosNode();
c. whether dn_Name is already DY0 without manual mutation;
d. decoded FileSysStartupMsg;
e. generated DosEnvec;
f. whether doslistdiag can enumerate DY0 after AddDosNode(..., 0, ...);
g. comparison with static DN0.

If DOS-list enumeration succeeds, stop there. The following segment will test natural handler startup via Dir DY0:.

## 4. fix result

Corrected and verified the isolated `MakeDosNode()` packet path. No production, FMOUNT, HD, geometry, or harness changes were made. No handler startup, `Dir`, `Type`, duplicate-name, or cleanup testing was performed.

**a. Corrected Packet**

The packet now uses:

```text
packet[0]  = "DY0"
packet[1]  = "fujinet-disk.device"
packet[2]  = 0
packet[3]  = 0
packet[4]  = de_TableSize through packet[23] = de_BootBlocks
```

`MakeDosNode()` receives normal null-terminated C strings for the first two packet entries. `L:FastFileSystem` is no longer used or substituted into packet word 0.

The environment is now serialized explicitly by classic `DosEnvec` index constants rather than copied with `memcpy()`. This was required because `fujinet_disk_dos_envec_t` uses a semantically grouped field order that differs from the classic in-memory order.

The explicit mapping includes:

```text
DE_TABLESIZE      <- de_TableSize
DE_SIZEBLOCK      <- de_SizeBlock
DE_SECORG         <- de_SecOrg
DE_NUMHEADS       <- de_Surfaces
DE_SECSPERBLK     <- de_SectorPerBlock
DE_BLKSPERTRACK   <- de_BlocksPerTrack
DE_RESERVEDBLKS   <- de_Reserved
DE_PREFAC         <- de_PreAlloc
DE_INTERLEAVE     <- de_Interleave
DE_LOWCYL         <- de_LowCyl
DE_UPPERCYL       <- de_HighCyl
DE_NUMBUFFERS     <- de_NumBuffers
DE_BUFMEMTYPE     <- de_BufMemType
DE_MAXTRANSFER    <- de_MaxTransfer
DE_MASK           <- de_Mask
DE_BOOTPRI        <- de_BootPri
DE_DOSTYPE        <- de_DosType
DE_BAUD           <- de_Baud
DE_CONTROL        <- de_Control
DE_BOOTBLOCKS     <- de_BootBlocks
```

`de_TableSize=19` remains the final populated index, representing complete entries `0..19`.

**b. DeviceNode Immediately After MakeDosNode()**

Runtime output before insertion:

```text
BEFORE_ADD DEVICE
dn_Name      = 0x00302e64
dn_Startup   = 0x0030365a
dn_Handler   = 0x00000000
dn_StackSize = 1024
dn_Priority  = 10
dn_GlobVec   = 0x00000000

dn_Name_decoded = DY0
dn_Handler_decoded =
```

**c. Manual Name Mutation Removed**

The previous manual mutation was removed:

```c
node->dn_Name = MKBADDR(dos_name_bstr);
```

`MakeDosNode()` populated the name correctly from packet word 0. The decoded name was already:

```text
DY0
```

before `AddDosNode()`.

**d. FileSysStartupMsg**

Runtime output before insertion:

```text
BEFORE_ADD STARTUP
fssm_Unit           = 0
fssm_Device         = 0x00303672
fssm_Environ        = 0x0030a3b8
fssm_Flags          = 0

fssm_Device_decoded = fujinet-disk.device
```

**e. Generated DosEnvec**

After correcting the explicit packet ordering, the generated environment was:

```text
de_TableSize       = 19
de_SizeBlock       = 128
de_SecOrg          = 0
de_Surfaces        = 2
de_SectorPerBlock  = 1
de_BlocksPerTrack  = 11
de_Reserved        = 2
de_PreAlloc        = 0
de_Interleave      = 0
de_LowCyl          = 0
de_HighCyl         = 79
de_NumBuffers      = 5
de_BufMemType      = 1
de_MaxTransfer     = 0x7fffffff
de_Mask            = 0xfffffffe
de_BootPri         = 0
de_DosType         = 0x444f5300
de_Baud            = 1200
de_Control         = 0
de_BootBlocks      = 0
```

The generated environment matched the builder values and the static `DN0:` environment.

One difference is in handler fields produced by `MakeDosNode()`:

```text
dynamic MakeDosNode node:
dn_StackSize = 1024
dn_Priority  = 10
dn_GlobVec   = 0

static DN0:
StackSize    = 32768
Priority     = 5
GlobVec      = -1
```

Those are `DeviceNode` handler defaults, not DosEnvec fields. They are not copied from the `fujinet_disk_dos_envec_t` environment by `MakeDosNode()`.

**f. AddDosNode and DOS-List Enumeration**

Insertion now uses:

```c
AddDosNode(source.de_BootPri, 0, node);
```

`ADNF_STARTPROC` is not used.

After insertion, the node remains:

```text
AFTER_ADD DEVICE
dn_Name_decoded = DY0
dn_Startup      = unchanged
```

`doslistdiag` successfully enumerated the dynamically inserted `DY0` entry and decoded its runtime environment:

```text
DY0 type=0 task=00000000
```

The dynamic DOS-list environment matched the generated packet:

```text
ENV name=DY0
table=19
sizeBlock=128
secOrg=0
surfaces=2
sectorPerBlock=1
blocksPerTrack=11
reserved=2
preAlloc=0
interleave=0
lowCyl=0
highCyl=79
buffers=5
bufMemType=1
maxTransfer=7fffffff
mask=fffffffe
bootPri=0
dosType=444f5300
baud=1200
control=0
bootBlocks=0
stack=1024
priority=10
globVec=00000000
```

**g. Focused Test**

Passed:

```text
pytest integration-tests/amiberry/test_diskdevice_adf.py::test_dynamic_dd_dos_node --run-amiga -q

1 passed
```

The test now proves only:

```text
MakeDosNode()
-> DeviceNode already named DY0
-> complete FileSysStartupMsg exists
-> complete DosEnvec is generated in classic memory order
AddDosNode(..., 0, ...)
-> DOS-list insertion succeeds
doslistdiag
-> safely enumerates and decodes DY0
```

The test intentionally does not attempt `Dir DY0:`, `Type DY0:`, handler startup, duplicate insertion, or cleanup. Those remain the next separate segment.

## 4. fix request #2

The corrected dynamic-node construction and DOS-list insertion are now proven. Before attempting Dir DY0: and starting the handler, close the remaining DeviceNode startup-field discrepancy.

Do not make production, FMOUNT, HD, geometry, cleanup, or duplicate-node changes.

1. Compare the complete DeviceNode startup fields

Extend the existing diagnostic comparison so the known-good static DN0 and dynamic DY0 report, at minimum:

dn_Name
dn_Handler, including decoded value if non-zero
dn_StackSize
dn_Priority
dn_GlobVec
dn_Startup
dn_Task

We already know:

static DN0:
    StackSize = 32768
    Priority  = 5
    GlobVec   = -1


dynamic DY0 from MakeDosNode defaults:
    StackSize = 1024
    Priority  = 10
    GlobVec   = 0

Establish the static DN0 value of dn_Handler as well.

Do not assume it should be L:FastFileSystem.

2. Reproduce the static handler settings

After MakeDosNode() and before AddDosNode(), explicitly apply the already-built handler configuration:

node->dn_StackSize = source.handler_stack_size;
node->dn_Priority  = source.handler_priority;
node->dn_GlobVec   = source.handler_glob_vec;

Handle dn_Handler only according to the result of the static DN0 comparison:

- if static DN0 has no explicit handler, preserve zero;
- if it has a handler value, establish exactly where that value comes from and reproduce it correctly.

Do not introduce L:FastFileSystem merely because the earlier broken helper contained that string.

3. Re-run insertion/inspection only

Repeat the existing isolated test:

MakeDosNode
-> apply handler startup fields
-> AddDosNode(..., 0, ...)
-> doslistdiag

Still do not execute Dir DY0: in this run.

The target is for DY0 to match static DN0 in all fields relevant to startup, except:

name: DY0 vs DN0
task: both should still be zero before first access
4. Deliverable

Report:

a. static DN0 dn_Handler value and decoded meaning;
b. corrected dynamic DeviceNode fields;
c. exact static-vs-dynamic comparison;
d. focused test result.

If the startup structures now match, stop there. The following segment will perform the first natural handler-start test with Dir DY0:.

# Part 5 

Proceed to the next isolated dynamic-node segment: natural filesystem-handler startup for the already-validated DD DY0: node.

Do not change production FMOUNT, HD handling, geometry classification, cleanup/removal, duplicate-node behavior, or static MountLists.

The dynamic node construction and pre-start startup fields are now signed off.

Goal

Prove that AmigaDOS can naturally start the filesystem handler for dynamically created DY0: on first access, and that the handler can read the mounted DD ADF correctly.

Test sequence

Keep the existing construction path:

LoadModule fujinet-disk.device
mount standard DD ADF in NIO
MakeDosNode("DY0", "fujinet-disk.device", unit 0, ...)
apply verified handler startup fields
AddDosNode(..., 0, ...)

Before first access, use doslistdiag to prove:

DY0 exists
dn_Task = 0
startup/DosEnvec still match expected DD values

Then visibly execute:

Echo "=== BEFORE DIR DY0 ==="
Dir DY0:
Echo "=== AFTER DIR DY0 RC=$RC ==="

Record both screen-visible output and machine-readable result files.

Immediately inspect DY0 again with doslistdiag.

Required result:

dn_Task was 0 before first access
dn_Task is nonzero after successful Dir

Then run:

Echo "=== BEFORE TYPE DY0 ==="
Type DY0:KNOWN.TXT
Echo "=== AFTER TYPE DY0 RC=$RC ==="

Required content:

FUJINET ADF READ PASSED
Diagnostics

Retain:

pre-start doslist result
Dir output and RC
post-Dir doslist result
Type output and RC
screenshot
fujinet-nio.log

If the handler does not start or the test stalls, stop there and report:

last visible CLI boundary
pre/post dn_Task
requester text if any
final FujiNet operations

Do not attempt cleanup or duplicate-node tests in the same run.

pytest assertions should be explicit rather than relying on files existing, i.e. something like:

assert "task=00000000" in results["dynamic-prestart.result"]
assert "DYNAMIC DIR RC=0" in results["dynamic-dir-rc.result"]
assert "KNOWN.TXT" in results["dynamic-dir.result"].upper()
assert "DYNAMIC TYPE RC=0" in results["dynamic-type-rc.result"]
assert "FUJINET ADF READ PASSED" in results["dynamic-type.result"]

Deliverable

Report:

1. DY0 state before first access;
2. Dir DY0: result;
3. DY0 state after Dir;
4. Type DY0:KNOWN.TXT result;
5. any requester or stall;
6. focused Amiberry test result.

If this succeeds, stop there. Cleanup/lifetime should be the following separate segment.

# Report on implementation

Natural DD filesystem-handler startup is proven for the dynamically created `DY0:` node.

**1. Pre-Start State**

Before the first `Dir DY0:` access:

```text
DY0 type=0 task=00000000
```

The pre-start DOS-list inspection also confirmed:

```text
DEVICE_FIELDS name=DY0
handler=00000000
stack=32768
priority=5
globVec=ffffffff
```

The startup structure and DD DosEnvec remained valid and matched the verified static `DN0:` values.

**2. `Dir DY0:` Result**

The sequence executed:

```text
=== BEFORE DIR DY0 ===
Dir DY0:
=== AFTER DIR DY0 RC=0 ===
```

Machine-readable assertions passed:

```text
DYNAMIC DIR RC=0
KNOWN.TXT
```

**3. Post-Dir State**

Immediately after the successful `Dir DY0:`, `doslistdiag` confirmed that `DY0` still existed and its task pointer was no longer zero:

```text
DY0 type=0 task=<nonzero>
```

The test explicitly asserts:

```python
assert "DY0 type=0 task=" in results["dynamic-post-dir.result"]
assert "DY0 type=0 task=00000000" not in results["dynamic-post-dir.result"]
```

This proves that AmigaDOS naturally started the filesystem handler on first access.

**4. `Type DY0:KNOWN.TXT` Result**

The sequence then executed:

```text
=== BEFORE TYPE DY0 ===
Type DY0:KNOWN.TXT
=== AFTER TYPE DY0 RC=0 ===
```

Assertions passed:

```text
DYNAMIC TYPE RC=0
FUJINET ADF READ PASSED
```

**5. Requester or Stall**

No requester appeared and no stall occurred.

The run completed through:

- dynamic node construction;
- pre-start DOS-list inspection;
- first natural handler startup;
- successful `Dir DY0:`;
- post-`Dir` task inspection;
- successful `Type DY0:KNOWN.TXT`;
- completion marker.

The existing Amiberry evidence retained the result files, screenshots, and `fujinet-nio.log`.

**6. Focused Test Result**

```text
pytest integration-tests/amiberry/test_diskdevice_adf.py::test_dynamic_dd_dos_node --run-amiga -q

1 passed
```

The run emitted existing Pillow deprecation warnings only.

No cleanup, removal, duplicate-node, HD, FMOUNT, geometry, or static MountList behavior was changed or exercised beyond mounting static `DN0:` for the established startup-field comparison.

# 5. next isolated dynamic-node segment

Proceed to the next isolated dynamic-node segment: cleanup and lifetime of an active dynamically created DD DY0: node.

Do not start HD work yet.
Do not modify production FMOUNT, static MountLists, geometry classification, or handler-safe Inhibit() behavior.

The following are now signed off:

MakeDosNode packet construction
complete DosEnvec serialization
AddDosNode insertion
natural handler startup
Dir DY0:
Type DY0:KNOWN.TXT
Goal

Establish the correct classic AmigaDOS lifecycle for retiring a dynamically created node after its filesystem handler has started.

We need to know:

how to stop/retire the running handler safely
when RemDosEntry() is legal
who owns/frees the DeviceNode and startup allocations
whether MakeDosNode allocations must be explicitly freed
whether removing the node while dn_Task != 0 is safe or forbidden
1. Inspect API/ownership semantics first

Review the classic APIs actually available in this m68k environment and establish the required sequence for an active dynamically added node.

Do not assume the existing:

RemDosEntry(entry);

is sufficient.

In particular, inspect whether:

Inhibit()
ACTION_DIE
RemDosEntry()
RemDosNode()/equivalent
FreeDosEntry()/FreeDosObject()/FreeVec()

or another mechanism applies.

Use only APIs actually present in the installed classic NDK.

2. Fix the current evidence problem

The old helper printed:

CLEANUP removed=1 handler_task_retired=1 static_dn_unaffected=1

without actually proving all three conditions.

Do not use declarative success strings like that unless each condition is measured.

The test must separately prove:

DY0 existed with nonzero task before cleanup
cleanup operation succeeded
DY0 no longer appears in LDF_DEVICES
its handler task is no longer referenced/running as appropriate
static DN0 remains present and unchanged
3. Locking/pointer lifetime

Review the current helper pattern where a DosList * pointer is obtained under:

LockDosList(...)

and then returned/used after unlocking.

Do not rely on that pattern unless the API explicitly permits it.

If removal requires a write lock or a different lookup/removal flow, implement the correct pattern.

4. Focused runtime test

Use the already-working sequence to:

create DY0
Dir DY0:
Type DY0:KNOWN.TXT

Confirm DY0 task != 0.

Then perform only the cleanup operation being tested.

Afterward run doslistdiag and assert:

DY0 absent
DN0 still present

Retain visible CLI breadcrumbs and screenshots.

Do not add duplicate-node testing in this same segment unless cleanup semantics require it.

5. Failure safety

If the correct cleanup sequence cannot be established safely, stop and report the exact blocker rather than forcing RemDosEntry().

Do not leave a test that removes an active handler node by assumption.

Deliverable

Return:

1. correct ownership/lifetime semantics for MakeDosNode/AddDosNode;
2. correct active-handler retirement sequence;
3. exact locking/removal pattern;
4. before/after DOS-list evidence;
5. proof that static DN0 is unaffected;
6. focused Amiberry test result.

If cleanup is proven, stop there. Duplicate insertion can be tested afterward, and HD should remain a separate subsequent segment.

## Rectification

Cleanup remains unresolved. Do not restore the experimental removal path yet.

Do not start HD, FMOUNT integration, duplicate-node testing, or production lifecycle work.

We need to answer two precise questions before another removal experiment.

1. Verify the exact DOS-list locking requirements

Inspect the installed classic NDK/autodocs for:

LockDosList
RemDosEntry
AddDosEntry/AddDosNode

Report the exact required locking mode for RemDosEntry().

In particular, determine whether removal requires:

LockDosList(LDF_WRITE | LDF_DEVICES)

rather than the LDF_READ lock used by doslistdiag.

Show the exact lock flags used by the previous failed experiment.

Do not rerun anything until this is answered.

2. Establish the correct active-handler retirement protocol

Inspect the classic NDK/autodocs and existing system behavior for:

ACTION_DIE
Inhibit
handler task lifetime
DeviceNode dn_Task
RemDosEntry

We need to establish whether the intended lifecycle is actually:

ACTION_DIE
wait for handler termination
remove DOS entry

or whether additional coordination is required.

Do not infer success merely because DoPkt(ACTION_DIE) returns.

Specifically determine:

- what ACTION_DIE return value means;
- whether the handler replies before or after its task actually terminates;
- how the caller can safely determine that dn_Task is no longer live;
- whether the DeviceNode is expected to remain on the DOS list while the handler dies;
- whether RemDosEntry() is legal while dn_Task is still nonzero.

3. Determine MakeDosNode allocation ownership

The current evidence suggests MakeDosNode() allocates:

DeviceNode
FileSysStartupMsg
DosEnvec
strings

but no matching FreeDosNode() exists in the installed API.

Establish from the classic API documentation or implementation contract:

who owns those allocations after successful AddDosNode();
whether they are intentionally system-lifetime allocations;
whether the caller is expected to free them after removal;
and if so, by what documented mechanism.

Do not use FreeDosEntry() or FreeDosObject() unless the documentation explicitly says they apply to MakeDosNode() output.

4. Inspect the preserved failed-run evidence

Before another experiment, report:

ACTION_DIE return value / IoErr
dn_Task before ACTION_DIE
exact DOS-list lock flags used for RemDosEntry
RemDosEntry return value
last visible CLI boundary
whether any requester appeared

If the existing helper did not record one of these, state that explicitly.

Deliverable

Return only:

a. required RemDosEntry lock mode;
b. exact semantics of ACTION_DIE relevant to this handler;
c. safe testable retirement sequence, if one can be established;
d. MakeDosNode allocation ownership;
e. what was wrong or still unknown in the failed experiment.

Do not implement or rerun cleanup yet.

## Response

**a. Required `RemDosEntry()` lock mode**

The installed NDK defines:

```c
#define LDF_READ  (1L << 0)
#define LDF_WRITE (1L << 1)
```

`LockDosList()` requires exactly one access mode plus the node type:

```c
LockDosList(LDF_READ | LDF_DEVICES)
LockDosList(LDF_WRITE | LDF_DEVICES)
```

The classic `RemDosEntry()` autodoc states that the DOS list must be locked before removal. The required mode for mutation is the exclusive write mode:

```c
LockDosList(LDF_WRITE | LDF_DEVICES)
RemDosEntry(entry)
UnLockDosList(LDF_WRITE | LDF_DEVICES)
```

`AddDosEntry()` differs: its autodoc explicitly says the DOS list does not have to be locked when calling it. If a caller does lock it, an exclusive write lock is the appropriate mutation lock.

The failed experiment used the wrong mode:

```c
list = LockDosList(LDF_READ | LDF_DEVICES);
entry = FindDosEntry(list, "DY0", LDF_DEVICES);
...
RemDosEntry(entry);
```

It also used an entry pointer after releasing the read lock in the earlier helper pattern. That is not a valid removal pattern.

The NDK/autodoc also warns that a handler should avoid blocking `LockDosList(LDF_WRITE | ...)` because of deadlock risk. A handler should use `AttemptLockDosList(LDF_WRITE | ...)` and retry while continuing to service its own messages. The test helper is a normal process, not the filesystem handler, so the documented write-lock path is applicable to a future experiment.

**b. `ACTION_DIE` semantics**

The installed NDK provides:

```c
#define ACTION_DIE 5
#define ACTION_INHIBIT 31
```

`DoPkt()` sends an action packet to a handler task’s message port and waits for the handler’s packet reply. `ACTION_DIE` is therefore a handler request, not a task-management primitive.

The important conclusions are:

- A successful `DoPkt(..., ACTION_DIE, ...)` result is only the handler’s packet result.
- It does not by itself prove that the handler task has terminated.
- The available APIs do not provide a general “wait until this arbitrary handler task exits” call.
- `dn_Task != NULL` means DOS has an active handler process port recorded in the node.
- A nonzero `dn_Task` pointer by itself is not proof that the task is still executing after an `ACTION_DIE` reply.
- `Inhibit()` only sends `ACTION_INHIBIT`; it stops filesystem activity while inhibited and is not a termination or removal operation.
- `RemDosEntry()` only unlinks the DOS-list entry. It neither sends `ACTION_DIE` nor waits for handler termination.

A safe sequence cannot therefore be established merely as:

```text
ACTION_DIE
RemDosEntry()
```

The missing coordination is an explicit, testable handler-termination confirmation. The current available evidence does not establish whether the particular handler replies to `ACTION_DIE` before or after its process has fully exited, nor whether this driver’s handler has a completion signal that can be observed externally.

The DOS-list entry is expected to remain available while the handler is active because the handler’s task port and startup state are stored in that entry. Removal must be performed only after the handler’s retirement protocol is known, under an exclusive DOS-list lock.

**c. Safe testable retirement sequence**

The only defensible sequence identified so far is:

```text
1. Obtain the DY0 entry under a read lock.
2. Record its nonzero dn_Task message port.
3. Use the handler-specific retirement protocol to request termination.
4. Independently confirm that the handler has terminated.
5. Acquire LDF_WRITE | LDF_DEVICES.
6. Re-find DY0 while holding the write lock.
7. Call RemDosEntry(entry).
8. Keep the write lock while verifying DY0 is absent and DN0 remains present.
9. Unlock with LDF_WRITE | LDF_DEVICES.
```

Step 4 is not currently established for this handler. Consequently, no safe runtime removal experiment should be run yet.

`ACTION_DIE` can be part of step 3, but its return value cannot serve as step 4.

**d. `MakeDosNode()` allocation ownership**

The `MakeDosNode()` autodoc states that it allocates and links:

- `DeviceNode`;
- `FileSysStartupMsg`;
- `DosEnvec`;
- up to two null-terminated BCPL strings.

The installed classic API has no `FreeDosNode()` or equivalent.

The documented `FreeDosEntry()` contract applies specifically to entries created by:

```c
MakeDosEntry()
```

It does not apply to the `DeviceNode *` returned by `MakeDosNode()`.

Likewise:

- `FreeDosObject()` is for objects allocated by `AllocDosObject()`;
- it is not documented for `MakeDosNode()` output;
- `FreeVec()` is not documented as a valid way to free the entire linked allocation graph returned by `MakeDosNode()`.

`RemDosEntry()` explicitly does not free the memory associated with the removed entry.

Therefore, ownership after `MakeDosNode()`/`AddDosNode()` is unresolved for a removable dynamic node using only the installed public APIs. The documented APIs support creation and list insertion, but do not expose a matching destructor for the allocation graph. It may be intended as system-lifetime storage, or it may require retaining and individually freeing implementation-specific allocations, but the installed API contract does not establish a safe caller-side release mechanism.

**e. Failed experiment: known and unknown**

Known:

- The helper captured a nonzero `dn_Task` before attempting cleanup.
- The attempted handler request was `DoPkt(task, ACTION_DIE, 0, 0, 0, 0, 0)`.
- The attempted DOS-list lookup/removal used the wrong read lock:
  ```c
  LockDosList(LDF_READ | LDF_DEVICES)
  ```
- The helper then attempted `RemDosEntry()` under that read-lock path.
- The last visible/runtime checkpoint was the cleanup result.
- The subsequent post-cleanup DOS-list inspection did not complete.
- No requester was detected by the Amiberry harness.
- No `Dir`, `Type`, HD, duplicate-node, or production lifecycle work was performed as part of the failed cleanup attempt.

Not recorded in preserved machine-readable evidence:

- the exact `ACTION_DIE` return value;
- `IoErr()` immediately after `DoPkt()`;
- the `RemDosEntry()` return value;
- an independently confirmed handler-task termination state;
- proof that `DY0` was absent after removal;
- proof that `DN0` remained unaffected after removal.

The cleanup experiment has therefore been disabled and must not be restored until the write-lock requirement, handler termination confirmation, and `MakeDosNode()` allocation ownership are resolved sufficiently to make removal safe.

## ... next iteration

Do not attempt RemDosEntry() or free any MakeDosNode() allocation in this segment.

The previous removal experiment is invalid as evidence because RemDosEntry() was attempted under an LDF_READ lock. Do not repeat it yet.

Instead investigate whether an active dynamically created node can be returned to its inactive but still registered state.

Goal

Answer only:

After ACTION_DIE is sent to a naturally started DY0: filesystem handler, does AmigaDOS/the handler leave the existing DeviceNode safely registered with dn_Task == 0?

Test

Use the already-proven dynamic DD path:

create DY0
AddDosNode
Dir DY0:
Type DY0:KNOWN.TXT

Confirm before retirement:

DY0 present
dn_Task != 0
Dir RC=0
Type RC=0

Then:

1. obtain dn_Task under a read lock;
2. release the lock;
3. send only:

DoPkt(task, ACTION_DIE, 0, 0, 0, 0, 0)

4. record the exact DoPkt() return value and IoErr();
5. do not call RemDosEntry();
6. do not alter dn_Task manually;
7. inspect DY0 again using normal read-only DOS-list access.

If necessary, poll the entry for a short bounded period and record:

DY0 present?
dn_Task value

Do not add arbitrary sleeps as a fix; a short polling diagnostic is acceptable to establish lifecycle behavior.

Also confirm DN0 remains readable/present.

Important

If post-ACTION_DIE DOS-list inspection itself hangs even though no DOS-list mutation occurred, stop and report that. That would tell us the problem is in the handler retirement path rather than RemDosEntry().

If dn_Task naturally becomes zero, then perform a second bounded experiment:

Dir DY0:

without recreating or removing the node.

Establish whether AmigaDOS starts a fresh handler again from the existing dn_Startup/DosEnvec.

If that succeeds:

task != 0
ACTION_DIE
task == 0
Dir DY0:
task != 0 again

we have proven that the dynamic node can be persistent while its handler is retired/restarted.

Do not modify the DosEnvec yet.
Do not attempt HD yet.
Do not call RemDosEntry().

Deliverable

Report:

1. pre-DIE task;
2. ACTION_DIE return and IoErr;
3. post-DIE node presence and task;
4. whether read-only DOS-list inspection remains healthy;
5. whether Dir DY0: can restart the handler;
6. task after restart;
7. any requester/stall.

## answer...
The read-only `ACTION_DIE` lifecycle probe succeeded. No `RemDosEntry()` call, DOS-list mutation, or allocation free was performed.

**1. Pre-DIE Task**

Before retirement:

```text
DIE pre_present=1 pre_task=00c3805c
```

This confirms:

- `DY0` was present;
- `dn_Task` was nonzero;
- the task pointer was obtained under:
  ```c
  LockDosList(LDF_READ | LDF_DEVICES)
  ```
- the lock was released before sending `ACTION_DIE`.

The preceding `Dir DY0:` and `Type DY0:KNOWN.TXT` both succeeded.

**2. `ACTION_DIE` Result**

Exact runtime result:

```text
DIE action_result=-1 ioerr=0
```

The handler returned `-1`, with `IoErr() == 0`.

The test does not interpret this return value as proof of task termination. It separately polls the DOS-list entry.

**3. Post-DIE State**

The first bounded read-only poll reported:

```text
DIE poll=0 present=1 task=00000000
```

This establishes that:

- the `DY0` DeviceNode remained registered;
- the handler task pointer naturally became zero;
- no manual mutation of `dn_Task` occurred;
- no DOS-list removal occurred.

A subsequent read-only DOS-list inspection remained healthy and showed:

```text
DY0 type=0 task=00000000
DN0 type=0 task=...
```

`DN0` remained present.

**4. Handler Restart**

Without recreating or removing `DY0`, the test then executed:

```text
Dir DY0:
```

The result was:

```text
DYNAMIC RESTART DIR RC=0
```

The subsequent DOS-list inspection showed:

```text
DY0 type=0 task=<nonzero>
DN0 type=0 task=...
```

Therefore the dynamic node supports the lifecycle:

```text
dn_Task != 0
ACTION_DIE
dn_Task == 0
Dir DY0:
dn_Task != 0 again
```

AmigaDOS retained the DeviceNode and its startup environment, then naturally started a fresh handler from the existing `dn_Startup`/DosEnvec on the next access.

**5. Requester or Stall**

No requester appeared. No stall occurred.

The full read-only DOS-list inspection after `ACTION_DIE` completed successfully. The existing screenshot and `fujinet-nio.log` evidence were retained by the focused Amiberry harness.

**6. Focused Test**

```text
pytest integration-tests/amiberry/test_diskdevice_adf.py::test_dynamic_dd_dos_node --run-amiga -q

1 passed, 112 warnings
```

The warnings are existing Pillow deprecation warnings from the Amiberry harness.

No `RemDosEntry()`, `FreeDosEntry()`, `FreeDosObject()`, `FreeVec()`, duplicate-node, HD, FMOUNT, geometry, or static MountList changes were made.

## ... next ask

Proceed to the next Media Geometry experiment: DD → HD transition on the same persistent dynamic DY0 DeviceNode.

Do not integrate this into production FMOUNT yet.
Do not remove/recreate DY0.
Do not call RemDosEntry() or attempt to free the MakeDosNode() allocation graph.

The following lifecycle is now proven and should be preserved:

DY0 active
ACTION_DIE
DY0 remains registered
dn_Task becomes 0
Dir DY0:
fresh handler starts
Goal

Prove that an inactive persistent dynamic node can have its startup DosEnvec changed from the validated DD profile to the validated HD profile, then successfully restart against HD media.

1. Prepare real HD evidence

Use the existing generated standard HD ADF fixture.

Ensure it contains a distinctive file/content different from the DD fixture so the test proves the handler is reading the replacement HD media, not stale DD state.

Keep the currently recognized DOS\0 filesystem identity unless the fixture already uses something else.

2. Establish DD baseline

Start with the already-proven dynamic DD node:

DY0 DosEnvec:
    SizeBlock       = 128
    Surfaces        = 2
    BlocksPerTrack  = 11
    LowCyl          = 0
    HighCyl         = 79
    DosType         = DOS\0


underlying NIO media:
    512 × 1760

Prove:

Dir DY0: succeeds
Type DD-specific file succeeds
dn_Task != 0
3. Retire the DD handler

Use the now-proven path:

ACTION_DIE

Assert:

DY0 remains present
dn_Task == 0

Do not continue unless the handler is demonstrably inactive.

4. Replace the underlying media with HD

Mount the existing standard HD ADF through the same validated NIO/device path.

Verify the retained media descriptor reports:

sector_size  = 512
sector_count = 3520
5. Update the inactive node's environment

Using the already-tested HD geometry classifier and DosEnvec builder, update the existing DY0 startup environment to the HD values:

de_SizeBlock       = 128
de_Surfaces        = 2
de_BlocksPerTrack  = 22
de_LowCyl          = 0
de_HighCyl         = 79
de_DosType         = recognized HD fixture DosType

Do not hand-code an unrelated second set of constants if the existing classifier/builder can provide them.

Before restarting the handler, inspect DY0 with doslistdiag and assert:

dn_Task == 0
BlocksPerTrack == 22
complete DosEnvec matches the expected HD profile
6. Restart naturally

Then visibly run:

Echo "=== BEFORE HD DIR ==="
Dir DY0:
Echo "=== AFTER HD DIR RC=$RC ==="

Required:

RC=0
HD-specific file visible
dn_Task becomes nonzero

Then:

Type DY0:<HD-specific-file>

and assert the expected HD-specific contents.

7. No reverse transition yet

Stop after proving DD → HD.

Do not perform HD → DD in this turn.

Do not integrate with FMOUNT.

Diagnostics

Retain:

DD pre-retirement DosEnvec/task
ACTION_DIE result
inactive task state
NIO HD status/geometry
HD DosEnvec before restart
HD Dir/Type output
post-restart task
screenshot
fujinet-nio.log
Deliverable

Report:

a. DD baseline;
b. retirement result;
c. HD NIO geometry;
d. exact DosEnvec changes made while inactive;
e. pre-restart DY0 state;
f. HD Dir result;
g. HD Type result;
h. post-restart task state;
i. focused Amiberry result.

If DD → HD succeeds, stop there.

## ... good response:

The isolated DD → HD transition succeeded on the same persistent dynamic `DY0` DeviceNode. No node removal, recreation, cleanup, duplicate-node, FMOUNT, or production changes were made.

**a. DD Baseline**

The test first established the existing DD path:

```text
DosEnvec:
SizeBlock       = 128
Surfaces        = 2
BlocksPerTrack  = 11
LowCyl          = 0
HighCyl         = 79
DosType         = 0x444f5300
```

The underlying NIO media was the DD fixture:

```text
sector_size  = 512
sector_count = 1760
```

The baseline passed:

```text
Dir DY0:                 RC=0
Type DY0:KNOWN.TXT       RC=0
FUJINET ADF READ PASSED
dn_Task != 0
```

**b. DD Handler Retirement**

The already-proven read-only retirement path was used:

```text
DIE pre_present=1 pre_task=00c3805c
DIE action_result=-1 ioerr=0
DIE poll=0 present=1 task=00000000
```

The node remained registered and became inactive:

```text
DY0 present = yes
dn_Task     = 0
```

No `RemDosEntry()` call was made.

**c. HD NIO Geometry**

The existing HD fixture was mounted through the same NIO/device path. The retained media descriptor reported:

```text
sector_size  = 512
sector_count = 3520
```

The HD fixture uses the recognized `DOS\0` filesystem identity and contains the distinct HD file/content.

**d. Inactive Node Environment Update**

While `DY0` had `dn_Task == 0`, the existing node’s startup environment was updated in place:

```text
de_SizeBlock       = 128
de_Surfaces        = 2
de_SectorPerBlock  = 1
de_BlocksPerTrack  = 22
de_LowCyl          = 0
de_HighCyl         = 79
de_DosType         = 0x444f5300
```

The helper verified the inactive state while applying the update:

```text
HD_UPDATE inactive=1 task=00000000
```

The complete pre-restart HD environment inspection confirmed `BlocksPerTrack=22` and the expected remaining environment values.

**e. Pre-Restart State**

Before restarting the handler:

```text
DY0 type=0 task=00000000
```

The node remained registered with its existing `dn_Startup`; only the inactive environment values were changed.

**f. HD `Dir DY0:` Result**

The existing node was accessed without recreation:

```text
Dir DY0:
DYNAMIC HD DIR RC=0
```

The directory contained the distinct HD fixture file:

```text
HD.TXT
```

**g. HD `Type DY0:HD.TXT` Result**

The HD-specific file was read successfully:

```text
DYNAMIC HD TYPE RC=0
FUJINET HD ADF READ PASSED
```

**h. Post-Restart Task State**

After the HD `Dir DY0:` access, the subsequent DOS-list inspection showed:

```text
DY0 type=0 task=<nonzero>
```

The test explicitly verified that:

```text
DY0 type=0 task=00000000
```

was absent after restart. `DN0` remained present.

The proven lifecycle is now:

```text
DD DY0 active
ACTION_DIE
DY0 remains registered, dn_Task=0
HD media mounted
inactive DY0 DosEnvec changed to HD geometry
Dir DY0:
fresh handler starts
HD directory read succeeds
HD Type succeeds
dn_Task becomes nonzero
```

**i. Focused Amiberry Result**

```text
pytest integration-tests/amiberry/test_diskdevice_adf.py::test_dynamic_dd_dos_node --run-amiga -q

1 passed, 130 warnings
```

The warnings are existing Pillow deprecation warnings from the Amiberry harness.

The test stopped after DD → HD. No HD → DD transition was attempted.

## ... more tweaks

Proceed with one final symmetry test for the dynamic-node geometry architecture:

HD → DD transition on the same persistent DY0 DeviceNode.

Do not make production FMOUNT changes yet.
Do not remove/recreate DY0.
Do not call RemDosEntry().
Do not add any new lifecycle mechanism.

Reuse exactly the now-proven flow:

current DY0 = active HD handler
ACTION_DIE
verify DY0 remains present and dn_Task == 0


remount standard DD media through the same NIO/device path
verify retained NIO geometry:
    sector_size  = 512
    sector_count = 1760


rebuild/apply the DD DosEnvec using the existing classifier/builder:
    de_SizeBlock       = 128
    de_Surfaces        = 2
    de_BlocksPerTrack  = 11
    de_LowCyl          = 0
    de_HighCyl         = 79
    de_DosType         = recognized DD DosType


inspect DY0 before restart:
    dn_Task == 0
    BlocksPerTrack == 11


Dir DY0:
    RC=0
    KNOWN.TXT visible


Type DY0:KNOWN.TXT
    RC=0
    FUJINET ADF READ PASSED


inspect DY0 after restart:
    dn_Task != 0

Keep visible screen breadcrumbs and machine-readable assertions.

The test should prove the full cycle:

DD -> HD -> DD

on one persistent dynamic node.

Do not modify production code in this turn.

If the reverse transition passes, stop there and report:

1. retirement result;
2. DD NIO geometry;
3. exact environment changes back to DD;
4. pre-restart task/environment;
5. DD Dir result;
6. DD Type result;
7. post-restart task;
8. focused test result.

Do not proceed to FMOUNT integration in the same turn.

## tweaks resolution

The HD → DD symmetry test passed on the same persistent dynamic `DY0` DeviceNode. No node removal, recreation, `RemDosEntry()`, allocation freeing, duplicate-node testing, or production changes were made.

**1. HD Retirement Result**

The test started from the active HD state, then used the proven retirement path:

```text
DIE pre_present=1 pre_task=<nonzero>
DIE action_result=-1 ioerr=0
DIE poll=0 present=1 task=00000000
```

`DY0` remained registered and became inactive before the DD environment was changed.

**2. DD NIO Geometry**

The existing DD fixture was mounted through the same NIO/device path:

```text
sector_size  = 512
sector_count = 1760
```

**3. Environment Changes Back to DD**

While the existing `DY0` node had `dn_Task == 0`, its retained startup environment was updated to:

```text
de_SizeBlock       = 128
de_Surfaces        = 2
de_SectorPerBlock  = 1
de_BlocksPerTrack  = 11
de_LowCyl          = 0
de_HighCyl         = 79
de_DosType         = 0x444f5300
```

The helper reported:

```text
DD_UPDATE inactive=1 task=00000000
```

The pre-restart DOS-list inspection confirmed the DD geometry, including:

```text
blocksPerTrack=11
```

The rest of the verified environment remained unchanged.

**4. Pre-Restart State**

Before restarting the DD handler:

```text
DY0 type=0 task=00000000
```

`DY0` remained registered with its existing `DeviceNode`, `FileSysStartupMsg`, and updated DD DosEnvec.

**5. DD `Dir DY0:` Result**

The existing persistent node was accessed without recreation:

```text
Dir DY0:
DYNAMIC DD RESTART DIR RC=0
```

The directory contained:

```text
KNOWN.TXT
```

**6. DD `Type DY0:KNOWN.TXT` Result**

The DD-specific file read succeeded:

```text
DYNAMIC DD RESTART TYPE RC=0
FUJINET ADF READ PASSED
```

**7. Post-Restart Task State**

After the DD `Dir DY0:` access, the final DOS-list inspection confirmed:

```text
DY0 type=0 task=<nonzero>
```

The test asserts that:

```text
DY0 type=0 task=00000000
```

is absent after restart.

`DN0` remained present throughout the transition.

**8. Focused Test Result**

```text
pytest integration-tests/amiberry/test_diskdevice_adf.py::test_dynamic_dd_dos_node --run-amiga -q

1 passed, 168 warnings
```

The warnings are existing Pillow deprecation warnings from the Amiberry harness.

The complete persistent-node cycle is now proven:

```text
DD active
ACTION_DIE
DD inactive
switch to HD
HD active
ACTION_DIE
HD inactive
switch back to DD
DD active again
```

No FMOUNT integration was started.

