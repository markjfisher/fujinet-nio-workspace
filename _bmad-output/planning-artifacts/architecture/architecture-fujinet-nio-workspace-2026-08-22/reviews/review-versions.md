# Review: versions / named-tech / brownfield reality-check

- **Content:** `_bmad-output/planning-artifacts/architecture/architecture-fujinet-nio-workspace-2026-08-22/ARCHITECTURE-SPINE.md`
- **Lens:** Every committed decision must be reality-checked against this workspace, not asserted from training data or copied from the parent architecture without opening the files it names. Named tech must exist and fit this brownfield tree.
- **Checked:** spine ADs, Stack, Structural Seed, Deploy; `docs/amiga/environment-setup.md`; `scripts/env.sh`; `repos/fujinet-nio-lib/include/fujinet-nio.h`; `repos/fujinet-nio-lib/include/fn_protocol.h`; `docs/amiga/nio-broker-architecture.md`; `backlog/nio-broker.md`; Amiga transport, disk device, NDK `exec/errors.h`, driver README.
- **Date:** 2026-08-22
- **Verdict:** **CHANGES REQUIRED**

The spine correctly ratifies most Amiga names, Exec symbols, staged cut-over, and the unused `0x13` error slot. Two committed pins were not checked against the files that actually define them: FujiBus packet size on Amiga is 1024, not 512; device residency in this workspace is `C:fujinet-load-resident` / `InitResident`, not a generic load or a `LoadResident` command.

---

## Method

Opened the spine, then the files the spine and this brief name. For each ADOPTED rule and Stack row: locate the symbol or path in-tree (or in the installed toolchain), confirm it exists, and confirm the numeric/path/version claim matches Amiga (amiga-gcc, not cc65). Future Stage 1–2 artifacts (`fujinet_nio_device.h`, `nio.device/`) were allowed as seed only if labeled as not-yet-built.

Did not treat `docs/amiga/nio-broker-architecture.md` as evidence of current code. Where the spine copied that doc, the copy was re-checked against headers and sources.

---

## Decision-by-decision

| Claim | Evidence | Result |
| --- | --- | --- |
| Device `fujinet-nio.device`, command `FUJINET_NIO_CMD_EXCHANGE`, struct `FujiNetNIORequest` | Named in architecture + backlog Stage 1; header not in tree yet (`amiga/include/` currently has disk headers only). Correct as seed. | Pass (future) |
| Device `fujinet-disk.device` | `amiga/include/fujinet_disk_device.h`: `FUJINET_DISK_DEVICE_NAME "fujinet-disk.device"`. Implementation is `amiga/disk.device/`, not `amiga/` as the paradigm box implies. | Pass name; path imprecise |
| Clients call lib; only Amiga `fn_transport` opens physical serial today | `src/platform/amiga/fn_transport.c` `OpenDevice` on serial unit 0; disk device uses lib + `fn_transport_close` idle-close. | Pass |
| `fn_request_data` / `fn_response_data` opaque | Proposed ABI in architecture §2; not in tree. Fits the existing lib (service code already builds FujiBus frames). | Pass (future ABI) |
| `io_Error` Exec-only; `IOERR_ABORTED`, `IOERR_NOCMD`, `IOERR_BADLENGTH`, `IOERR_OPENFAIL` | Installed NDK `/opt/amiga/m68k-amigaos/ndk-include/exec/errors.h` (`$VER: errors.h 47.1`): `IOERR_OPENFAIL -1`, `IOERR_ABORTED -2`, `IOERR_NOCMD -3`, `IOERR_BADLENGTH -4`. | Pass |
| `FN_ERR_ABORTED` `0x13` unused; not `FN_ERR_UNKNOWN` `0xFF` | `fujinet-nio.h`: `FN_ERR_NOT_FOUND 0x01` … `FN_ERR_UNSUPPORTED 0x08`, `FN_ERR_TRANSPORT 0x10` … `FN_ERR_NO_HANDLES 0x12`, `FN_ERR_UNKNOWN 0xFF`. No `0x13`. | Pass |
| `OpenDevice` fail → `FN_ERR_NOT_FOUND` | Current serial `OpenDevice` failure already returns `FN_ERR_NOT_FOUND`. `FN_ERR_NOT_FOUND` is `0x01` in the C header (Atari `fn_protocol.inc` numbering differs; Amiga uses the C header). | Pass |
| `FN_MAX_PACKET_SIZE` = 512; UWORD lengths while bound is 512 | **`fn_protocol.h` (not `fujinet-nio.h`):** 512 only if `__CC65__`, else **1024**. Amiga is `m68k-amigaos-gcc` / `__amigaos__`. `fn_transport.c` sizes the wire buffer from `FN_MAX_PACKET_SIZE`. `FN_DISK_CONTEXT_PACKET_SIZE` is 1024. Parent architecture comment `≤ 512` is the same error; spine pinned it into Stack. | **Fail** |
| WB 3.1 and 3.2 guests | `docs/amiga/environment-setup.md`: WB3.1 / WB3.2 recipes (`wb31`, `wb32`). | Pass |
| exec / serial.device / timer.device | Current Amiga transport opens serial and `TIMERNAME` / `UNIT_MICROHZ`. | Pass |
| amiga-gcc + NDK via `scripts/env.sh` | `env.sh` adds `AMIGA_TOOLCHAIN_BIN` default `/opt/amiga/bin`. Compiler makefile: `m68k-amigaos-gcc` (bebbo amiga-gcc). NDK headers exist under `/opt/amiga/m68k-amigaos/ndk-include/`. `env.sh` does not name or version NDK. | Pass fit; version pin is “as installed”, not a product version |
| `fn_session.c` includes `fn_internal.h`; drop before Stage 2 | Confirmed include at line 4. File uses `fn_session.h`, `fujinet-nio.h`, `fn_protocol.h`, `fn_slip_decode`; no `_fn_*` globals. `fn_slip.c` already includes only `fn_protocol.h`. | Pass |
| Idle-close in disk worker | `amiga/disk.device/fujinet_disk_device.c` `device_worker_entry`: `fn_transport_close()` when FIFO empty. | Pass |
| Stage 1–5 order | Matches `backlog/nio-broker.md`. | Pass |
| `nio.device/` directory | Not present; Stage 2 seed. | Pass (future) |
| `CMD_NONSTD + 0` for broker EXCHANGE | Disk device documents that `CMD_NONSTD` is `TD_MOTOR` **on trackdisk**. Broker is not trackdisk; first private command as `CMD_NONSTD + 0` is the normal Exec pattern. | Pass |
| Environment loads broker; lib does not autoload | Lib must not `LoadSeg` the device. This workspace does **not** rely on stock `OpenDevice` DEVS: autoload for FujiNet devices: `amiga/README.md` requires `C:fujinet-load-resident DEVS:fujinet-disk.device …` (`LoadSeg` + `InitResident`), injected into `S:Startup-Sequence`. Spine Deploy names Startup-Sequence / User-Startup / Amiberry but not that tool. Parent architecture’s user-typed `LoadResident` is not a WB 3.1/3.2 command and is not in this tree. | **Fail (loader name / brownfield)** |
| FLS as an Amiga client | `docs/amiga/amiberry-testing.md` and backlog Stage 2 isolation mention FLS as an Amiga NIO client. | Pass |
| Zorro as future backend | Real Amiga bus; Option A packaging is backlog Stage 5. Not present in code. | Pass (deferred) |
| Capability map: public ABI governed by AD-12 | AD-12 is the `fn_session.c` include cut, not the public ABI. | Inconsistency (not a version pin) |

---

## Findings

### 1. Stack and conventions pin `FN_MAX_PACKET_SIZE` at 512; Amiga is 1024

**Location:** Consistency Conventions (Data & formats); Stack row “FujiBus frame bound”; inherits architecture §2 (`fn_request_length` bounded `≤ 512`, prose “currently 512 bytes”).

**What was not opened:** `repos/fujinet-nio-lib/include/fn_protocol.h`. `fujinet-nio.h` has `FN_MAX_CHUNK_SIZE 512` and `FN_DISK_CONTEXT_PACKET_SIZE 1024` but **does not define** `FN_MAX_PACKET_SIZE`.

**Reality:**

```c
#ifndef FN_MAX_PACKET_SIZE
#ifdef __CC65__
#define FN_MAX_PACKET_SIZE   512
#else
#define FN_MAX_PACKET_SIZE   1024
#endif
#endif
```

Amiga builds do not set `__CC65__`. The live Amiga transport already does `#define FN_TRANSPORT_WIRE_BUF_SIZE ((FN_MAX_PACKET_SIZE * 2) + 2)`. Disk inspect/catalog paths use 1024-byte context packets. If Stage 2 BeginIO rejects `fn_request_length > 512` as the spine’s bound, valid Amiga frames (inspect boot + header, Wi-Fi scan pages, disk context) fail.

UWORD lengths remain valid at 1024 (still ≪ 65535). The defect is the **512 pin**, not the integer width.

**Guard:** Pin “Amiga / non-cc65: `FN_MAX_PACKET_SIZE` 1024 (`fn_protocol.h`); cc65 512. Broker oversize check uses the Amiga compile-time value, not 512.” Do not cite `fujinet-nio.h` as the source of this macro.

### 2. AD-13 / Deploy omit the workspace’s real resident loader

**Location:** AD-13; Deploy / env.

**Reality:** `repos/fujinet-nio-driver/amiga/README.md` — `C:fujinet-load-resident DEVS:fujinet-disk.device fujinet-disk.device` using OS 1.3-compatible `LoadSeg()` / `InitResident()`, validated on WB 3.1; disk builder appends that line to `S:Startup-Sequence`. Integration tests assert `Resident loaded: fujinet-disk.device`.

**Named tech that does not exist here:** the parent architecture’s shell command `LoadResident DEVS:fujinet-nio.device`. Spine text is vaguer (“environment loads”) so it does not repeat that string, but it also never names `fujinet-load-resident`. Two implementers can diverge: fake `LoadResident`, assume stock `OpenDevice` DEVS: autoload, or copy the proven loader.

**Guard:** AD-13 should name `fujinet-load-resident` (or an equivalent `InitResident` path) for `DEVS:fujinet-nio.device`, matching the disk-device bootstrap, Amiberry `--with-driver` / test bootstrap, and User-Startup.

### 3. Structural seed path for the disk device is the `amiga/` tree, not `disk.device/`

**Location:** Design Paradigm path box; Capability map “Disk device idle-close removal”.

**Reality:** Resident disk code lives in `repos/fujinet-nio-driver/amiga/disk.device/` (`fujinet_disk_device.c`, `device_worker_entry`). `amiga/include/` is shared headers. Calling the whole `amiga/` directory `fujinet-disk.device` will send Stage 4 edits to the wrong place once `nio.device/` exists beside it.

**Guard:** Seed `disk.device/` and `nio.device/` as sibling directories under `amiga/`.

### 4. Stack “NDK via `scripts/env.sh`” is a toolchain fact, not an env.sh export

**Location:** Stack.

**Reality:** `scripts/env.sh` exports `AMIGA_TOOLCHAIN_BIN` (default `/opt/amiga/bin`) only. NDK headers are the bebbo tree at `/opt/amiga/m68k-amigaos/ndk-include/` (errors.h VER 47.1). Fit is real; the version row over-attributes NDK to `env.sh`.

**Guard:** “amiga-gcc (`m68k-amigaos-gcc`) from `AMIGA_TOOLCHAIN_BIN`; NDK includes from that install (`ndk-include/exec/errors.h`).”

### 5. Capability map mis-binds AD-12 to the public ABI

**Location:** Capability → Architecture Map, first row.

**Reality:** AD-12 is the `fn_session.c` / `fn_internal.h` cycle cut. Public ABI is AD-3 / AD-4 / AD-9.

**Guard:** Move AD-12 to the broker serial-backend / framing row.

---

## What was correctly reality-checked

- `FN_ERR_*` values in `fujinet-nio.h` for the abort pair and `FN_ERR_NOT_FOUND` mapping.
- Guest OS 3.1 / 3.2 from `environment-setup.md`, not a guessed AmigaOS version.
- Current serial race (`OpenDevice("serial.device")` in lib + idle-close in the disk worker).
- `fn_internal.h` leftover in `fn_session.c` before compiling framing into a broker.
- Exec `IOERR_*` symbols exist in the installed NDK and must stay symbolic.
- Staged migration matches `backlog/nio-broker.md`.
- Future files `fujinet_nio_device.h` and `amiga/nio.device/` are labeled as Stage 1–2 work, not claimed as present.

---

## Verdict

**CHANGES REQUIRED.** Re-pin `FN_MAX_PACKET_SIZE` from `fn_protocol.h` (Amiga 1024). Name `fujinet-load-resident` in AD-13/Deploy. Fix the disk-device seed path. Optional: tighten the NDK stack row and AD-12 map.

Do not treat the parent architecture’s “currently 512” or `LoadResident` as verified; both failed this workspace check.
