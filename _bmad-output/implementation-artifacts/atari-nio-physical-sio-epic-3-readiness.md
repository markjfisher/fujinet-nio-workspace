# Atari physical SIO: Epic 3 readiness

**Status: investigation complete; physical deployment is not yet accepted.**
This record covers Epic 3 stories 3.1–3.3 in
`_bmad-output/planning-artifacts/epics-atari-nio-physical-sio.md`, not the
unrelated generic Epic 3. Baseline: workspace
`1d896db8be1ec4bf732b522e29ccca262cd09bc3`, `fujinet-nio`
`2d584912c47602629b83160c33eb5019d9574cb5`. The legacy comparison is the
local `fujinet-firmware` checkout at
`ac25a355271e4c4ba17967d6494161fe2df35a12` (origin
`github.com/markjfisher/fujinet-firmware`); its two untracked local files are
not used as evidence. It is a reference, not a new dependency.

## Source-verified reuse and gaps

| Component | Evidence and role |
| --- | --- |
| Legacy board mapping | `include/pinmap/atariv1.h`, `atari-common.h`, `common.h`: CMD GPIO39, MTR 36, INT 26, PROC 22, CKI 27, CKO 32, UART2 RX 33/TX 21, SD SPI 23/19/18/5. NIO's `src/platform/esp32/pinmap.cpp` matches these and identifies v1.6 and later. Verify the actual board revision. |
| Legacy physical SIO | `lib/bus/sio/sio.cpp`, `sio.h`, `lib/hardware/ESP32UARTChannel.cpp`: established GPIO setup, standard 19,200 baud, command assertion and deassertion handling, UART I/O, checksums and response sequencing. `DELAY_T4` is 850 us and `DELAY_T5` 250 us in that source; these are implementation references, not measured requirements. Reuse the pin/electrical knowledge and adapt the necessary sequencing, not legacy device semantics or protocol. |
| NIO already wired | `src/app/main_esp32.cpp` constructs `AtariSioIngress` with the actual `DiskService` and core routing manager. `src/lib/atari_sio_ingress_router.cpp` routes `$31–$38` through `AtariSioDiskFrontend` and `$7F` through `AtariSioNioFrontend`; the latter implements native Q/W/P/R, a 512-byte limit and polling. Virtual acceptance is evidence for these services, not ESP32 signal timing. |
| ESP32 ingress | `src/platform/esp32/atari_sio_ingress.cpp`, `uart_channel.cpp`: configures input CMD/MTR/CKO and released open-drain INT/PROC/CKI and TX; default SIO is 19,200 8N1 without flow control. **NIO actually selects UART1**, mapped through the GPIO matrix to RX33/TX21; the legacy source uses UART2. NIO uses a 2,048-byte RX driver buffer, 64-event queue, FIFO threshold 32, blocking TX, and explicit flush. UART selection is not determined by the pin names. |

Confirmed source gaps and integration work:

1. COMMAND any-edge ISR records only a coalescing Boolean; `poll()` resets
   command collection when it consumes it, without capturing the level or
   ordering the edge against queued UART bytes. It neither gates collection
   on asserted COMMAND nor waits for deassertion before replying. Edges can
   coalesce, and an edge during draining may be associated with the wrong
   bytes. Legacy `sio.cpp` instead waits for deassertion after collecting the
   frame. Add and host-test an ordered, level-aware COMMAND/UART transaction
   path in the **existing** ingress; preserve write-data phases and recovery.
2. The router sends the disk frontend's NAK for every device ID outside
   `$31–$38` and `$7F`; this can interfere with unrelated SIO peripherals.
   Ignore unowned IDs on the physical bus and test shared-bus isolation.
   Do not conflate unsupported commands for an owned ID with an unowned ID.
3. `send()` writes each frontend reply as one vector; ACK, COMPLETE and data
   have no SIO-specific phase scheduling or COMMAND-release wait. Establish
   the needed phase timing using legacy behavior and physical traces, then
   implement only the necessary timing in this ingress. UART pacing options
   alone are not evidence that command-phase deadlines are satisfied.
4. `AtariSioNioFrontend` advertises feature flags zero and ingress leaves PROC
   released: polling is implemented; physical PROC notifications are not.
   POSIX NetSIO has an explicit `reset_device()`/`reset_host()` path; this
   ESP32 ingress has no corresponding physical host-reset detection. Measure
   and implement the required physical reset/session recovery and optional
   PROC behavior before claiming Epic 3 acceptance. Do not infer an Atari
   RESET signal exists on SIO from a virtual reset event.
5. GPIO interrupt setup failures and UART initialization failure are not
   propagated as ingress construction failure; confirm actionable diagnostics
   and boot/mount/slot, native capability and memory visibility against Story
   3.1. `gpio_install_isr_service(0)` is not an IRAM-service guarantee merely
   because the handler has `IRAM_ATTR`.

The configuration ATR remains the existing boot-selection environment; the
user DOS owns resident N: installation. There is no new protocol or SIO HAL.

## Target and reproducible build/flash preparation

Official profile: `atari-nio-fujibus-sio-gpio-fujinet-v1-16mb`, original
ESP32, ESP-IDF via PlatformIO `espressif32@6.10.0`, 240 MHz, 40 MHz DIO flash,
quad 40 MHz PSRAM with startup test. The 16 MB partition CSV has two 6 MiB
app slots (`0x10000`, `0x610000`) and LittleFS at `0xC10000`, size `0x3F0000`.
It requires working PSRAM. An 8 MB profile exists for custom boards; its two
2 MiB app slots are materially smaller and it is not the Epic 3 official
16 MB acceptance target. Verify flash and PSRAM on the actual board.

On 2026-10-25, after sourcing `scripts/env.sh`, the existing local 16 MB
profile built with `cd repos/fujinet-nio && ./build.sh -b`: **pass**, 44,248
of 327,680 bytes reported static RAM, 2,111,383 of 6,291,456 bytes application
flash; generated `firmware.bin` is 2,111,792 bytes. Debug build with
`FN_DEBUG` and `consoleuart`; these are build-time figures, not peak runtime
heap, PSRAM or real-time timing. No image was flashed. The local
`platformio.local.ini` currently selects `boot_images = amiga/wb32`, so this
build is **not** an Atari-ready storage image. It must be changed for Atari.

For a fresh local profile, `./build.sh -s atari-nio-fujibus-sio-gpio-fujinet-v1-16mb`
generates/overwrites local PlatformIO and SDK defaults; select `consoleuart`
and the actual USB serial port, not the common default `/dev/ttyACM0` by
assumption. Generate the workspace Atari boot disk using the existing boot
disk build (`scripts/build.sh boot-disks`) and verify
`repos/fujinet-nio/distfiles/esp32-data/boot/atari/autorun.atr`. Select
`boot_images = atari` in `[fujinet]` and set config mode and the correct
flash URI, `flash:/boot/atari/autorun.atr`, in the actual deployed configuration.
Build with `./build.sh -b`; `./build.sh -u` uploads firmware and
`./build.sh -f` uploads the selected filesystem. These are separate operations;
`-f` rewrites the storage image, so back up existing configuration and files.
The script uses 460800 upload and 115200 monitor baud. Verify image/partition
offsets in that build and configure Wi-Fi and disk mappings before testing;
do not assume the legacy firmware's stored configuration is compatible.

## First hardware acceptance, in order

This is a **procedure to run after the ingress fixes**, not an assertion that
they or any physical result already passed. Record firmware and ATR hashes,
board revision/flash/PSRAM, Atari model, OS, supply, cable and all peripherals;
use a logic analyzer and preferably an oscilloscope.

1. With the Atari and only the target FujiNet connected, confirm wiring,
   voltage levels and released idle/non-contention on the actual board, then
   flash firmware and selected LittleFS image and check UART logs, PSRAM,
   boot mode and D1 mount. Capture CMD, Atari-to-device and device-to-Atari
   data, PROC and ground. Check that INT, MTR, CKI and CKO remain benign.
2. Cold boot the configuration ATR as D1. Capture `$31 $53` STATUS and
   `$31 $52` sector 1 (then boot sectors 2–3); compare control bytes,
   128-byte data and checksums against the literal disk/boot fixtures under
   `integration-tests/atari-sio/fixtures/`, and verify the config program
   actually launches. Record COMMAND assertion/deassertion to ACK, COMPLETE,
   data and checksum, UART rate and polarity. Repeat with an unrelated SIO
   peripheral and verify no response to its address or bus contention.
3. Run the existing public-API `FNACCEPT.XEX` from the configuration ATR:
   first a Clock exchange, observing native `$7F` Q if requested, W, P and
   exact-length R and checksums; then the existing Network/File/Disk fixture
   rows when their services and media are configured. Capture traces and
   application results, not merely an ACK. Default to polling; test PROC only
   after implemented and advertised. Record aborts, timeouts and recovery;
   do not automatically retry uncertain writes.
4. Expand to normal-mode persisted mappings, supported user DOS/BASIC N:
   READ/PUT/POST, warm start and real host-reset/session behavior only after
   the initial disk and native exchanges work. Document topology, failures,
   electrical levels, response timing and all limitations.

**Measurements still required:** actual transceiver/inversion and pull-ups,
voltage and idle release on every supported board revision, signal edges,
UART tolerance, phase timing under Wi-Fi/flash load, contention, interrupt
latency and reset behavior. Source pin modes do not prove electrical safety.

**Smallest next implementation task:** repair and host-test the existing
ESP32 ingress's COMMAND/byte ordering and unowned-address silence, with
focused tests covering both edges, queued bytes, write data and unrelated
devices. Then add only the measured SIO reply timing required for the first
isolated physical D1 STATUS/READ probe. Do not replace DiskService or the
native `$7F` service path.

## Verification of this record

Source comparison and the targeted 16 MB profile build above were performed
against the stated revisions. `source scripts/env.sh && python3 -m unittest
discover -s integration-tests/atari-sio/tests -q` passed 69 tests. No firmware
source, board, device, or production configuration was changed; no flash,
physical measurement, or emulator acceptance run was performed.
