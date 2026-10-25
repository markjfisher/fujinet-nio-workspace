# Atari NIO wire and acceptance contract

## SIO ingress planes

```text
Atari OS boot / mounted applications
  -> standard SIO D1:–D8: disk frontend
  -> DiskService -> ATR slots

Atari NIO application
  -> public fujinet-nio-lib API
  -> packet-native FujiBus
  -> SIO device 0x7F: Q / W / P / R
  -> internal FujiBus transport -> FujinetCore -> existing services

Atari BASIC
  -> relocatable CA65 CIO N: handler installed by user DOS startup
  -> native packet protocol
  -> SIO device 0x7F -> NetworkService URI + handle operations
```

The planes share physical SIO, board configuration, disk-slot state, and core DiskDevice. They do not share framing or dispatch. The disk frontend is a narrowly scoped standard Atari disk adapter, not `LegacyTransport` and not a legacy FujiNet compatibility path.

The CIO `N:` handler is a native Atari-side adapter using the existing NetworkService contract, not an SIO network-device alias. The user's DOS startup installs the relocatable CA65 module below adjusted `MEMLO` and registers `HATABS`; MyDOS 4.53/4 is the first verified environment. The transient configuration ATR retains its existing configuration and boot-selection contract and is not the DOS startup disk. Installation initializes state, rolls back on failure, is idempotent for the same handler, and reports a foreign `N:` collision without replacement. IOCBs own returned service handles; read/write/update map to GET/PUT/POST with `BODY_UNKNOWN` on output. Bounded 128-byte caches preserve ordered I/O and partial acknowledgements; output flushes and commits exactly once with a zero-length write before first STATUS, read or CLOSE. Uncertain side effects are never automatically replayed. The total permanent allocation, including zero page and retained workspace, must not exceed 3,072 bytes. The handler must not address `0x71`–`0x78`, translate legacy `O/C/R/W/S` frames, or invoke `LegacyTransport`.

A genuine OS warm start must leave the installed driver usable while abandoning open sessions and reclaiming their remote resources without flushing or committing incomplete output. NetSIO host-reset resource reclamation is verified; genuine OS warm-start persistence and physical SIO reset detection are not. Stale handles must fail safely, release local ownership and allow a subsequent OPEN without affecting other clients. Atari DOS 2.0S/2.5, SpartaDOS and SpartaDOS X are follow-on compatibility targets for the same resident module with DOS-appropriate installation. Embedded-adapter BASIC acceptance remains outstanding. A possible future `config://` means of accessing files from the original configuration/boot disk after selecting a DOS is deferred and is not a current protocol or feature.

## NIO application-channel contract

| Concern | Contract |
| --- | --- |
| Address | SIO device `0x7F` is permanently the NIO application-channel address. It is unrelated to FujiBus `WireDeviceId` values such as Clock, Disk, Network, and File. |
| Capability query | `Q` is an optional, direct fixed-size query. The client/fixture uses AUX `0` and DCB receive length `4`; at `P=idle`, the device returns ACK, COMPLETE, then four bytes: wire revision `1`, little-endian advertised maximum payload (at least 512 for v1), and feature flags. Bit 0 advertises advisory PROC readiness notification; all other bits are zero and ignored by v1 clients. The device validates AUX and state—not DCB length, which is not observable on the SIO wire—and rejects nonzero AUX or `Q` while pending/ready with `NAK`. `Q` neither creates nor consumes a `W`/`P`/`R` transaction. |
| Request | The client/fixture uses matching AUX and DCB byte counts for `W`; it carries exactly one packet-native FujiBus request plus its standard SIO checksum. It is valid only at `P=idle`; a `W` while pending or ready is rejected with `NAK`. Valid receipt returns ACK then COMPLETE. |
| Poll | The client/fixture uses `P` AUX `0` and DCB receive length `3`; the device returns ACK, COMPLETE, then exactly three bytes: state `0=idle`, `1=pending`, or `2=ready`, then a little-endian queued-response size which is nonzero only for `ready`. |
| Response | After `P=ready`, the client/fixture uses `R` AUX and DCB byte counts equal to the reported size and the device returns exactly one packet-native FujiBus response plus the SIO checksum. A wrong observable `R` AUX length or bad command frame is rejected with `NAK` and retains the response. Once a valid `R` is accepted, its response slot is consumed and the next `P` is idle even if the data transfer is interrupted at the client. No zero padding is used. |
| Capacity | One shared named compile-time constant initially limits a `W` or `R` payload to 512 bytes. Builds may tune it together for measured compatibility/performance. A v1 device must support this full baseline. A client that elects to query uses the lesser of its compiled capacity and the advertised `Q` maximum; a client that does not query uses the 512-byte v1 baseline. A lower-capacity profile requires a new wire revision and matching fixtures. A larger packet fails with the defined NIO message-too-large transport error; no implicit segmentation exists. |
| Errors | `NAK` means malformed/rejected SIO transaction only: bad command/checksum, invalid length, bad state, or another transport rejection. It never means pending. Every valid request, including a service or transport error, yields a normal FujiBus response; `P` carries no fault or request flags. |
| Recovery | Only one NIO request may be outstanding. A local client timeout does not cancel or forget an accepted request: later traffic first observes its state with `P`, and a valid terminal `R` attempt clears its queued response. A malformed or rejected `W` does not create a transaction; device reset clears one. The library never retries automatically after timeout; application retry remains safe only where the operation semantics permit it. Client retry delay and total deadline are configurable policy, not wire constants. |

### PROC readiness notification

The default backend polls `P`. An application that owns or chains the Atari PROC (`VPRCED`) handler may opt in to notification:

- FujiNet sends a bounded, rate-limited open-drain PROC pulse when the NIO response queue transitions to ready, including a ready error response.
- The application handler may call the library's ISR-safe constant-time notification hook, which only latches a flag.
- Outside IRQ context, the client issues `P` before `R`; PROC conveys neither source, request ID, response length, nor reason on the shared SIO bus.
- False or missed pulses are harmless because the response remains queued and the polling path is complete.

## Disk bootstrap and configured drives

- Standard Atari disk device IDs `D1:`–`D8:` select the corresponding runtime DiskService slots.
- The frontend handles only the standard Atari disk commands and sector/status semantics required for ATR-backed boot and mounted-media operation. It composes DiskService directly and maps its results to standard SIO replies; `DiskDevice` remains the separate FujiBus wrapper.
- In config mode, `boot.config_uri` identifies the flashed configuration ATR prepared for the active boot slot (`D1:`). In normal mode, restored user URI-backed slots determine which disk responds.
- The configuration ATR supplies the cc65 XEX configuration and acceptance programs. It is the supported bootstrap medium; loading must not require legacy FujiNet services.

## Physical profile and measurements

- Production profile: `FN_BUILD_ATARI_FUJIBUS_SIO` on official Atari FujiNet v1 16 MB hardware.
- Standard-speed SIO is 19,200 baud. CMD gates command-frame recognition; UART data input/output carry command replies and data frames.
- Board-driven DATA OUT and PROC are open-drain and released while idle. INT, MTR, CKI, and CKO have no NIO protocol role and remain electrically benign.
- The physical fixture records board revision, Atari model, cable/peripheral topology, firmware/client commits, logic levels, idle release/no contention, command-to-ACK/COMPLETE timing, data/checksum timing, abort/reset recovery, and PROC opt-in versus polling-only behavior.

## Acceptance matrix

| Level | Required evidence | Does not prove |
| --- | --- | --- |
| Literal vectors and host tests | `0x7F` `W`/`P`/`R`, exact lengths, malformed input, recovery, and D1–D8 sector/status mappings | Atari client ABI or electrical behavior |
| Atari library build/tests | Public API, polling fallback, opt-in ISR hook, and bounded buffers | Firmware channel correctness |
| AltirraSDL | NIO command-level integration, disk boot, and guest XEX | ESP32 signals or physical timing |
| NetSIO | SIO envelope, scheduling, and regression parity | Physical SIO electronics |
| ESP32 profile build | Board configuration compiles | Real-bus interoperability |
| Real Atari + official v1 | Config ATR boot as D1, URI drive mapping, physical NIO, and recovery | Broad legacy FujiNet compatibility |

## Required guest acceptance

The cc65 XEX loaded from the configuration ATR must use the public library API and demonstrate items 1–5. Separately, a genuine BASIC program running under the user DOS must demonstrate item 6:

1. Clock request/response.
2. Network open/write/read/close, including delayed readiness through `P` and, where available, the application-owned PROC path.
3. File persistent write/read.
4. Disk read/write against a mounted supported image.
5. Rejected `W`, malformed-length `R`, interrupted terminal `R`, and reset recovery followed by a successful exchange.
6. A native Atari BASIC `N1:` URI open, stream I/O/status, and close using the installed CIO handler and NetworkService.

The operator procedure documents flash, boot-mode choice, ATR/URI mapping, launch, diagnostics, and the physical evidence record.
