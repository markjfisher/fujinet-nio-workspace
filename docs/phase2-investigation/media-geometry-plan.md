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
