# Wi-Fi Configuration Wire Service

## Summary

Add a dedicated `WifiService` wire device for clients to scan, inspect, and
configure FujiNet-NIO Wi-Fi. Keep it separate from the existing HTTP/TCP
`NetworkDevice` and console diagnostics.

Use the next service ID, `0xF3`, with a versioned binary protocol. Passwords
are write-only and are never returned to clients.

## Key Changes

- In `fujinet-nio`:
  - Extend `WifiConfig` with configured BSSID.
  - Extend the platform network-link abstraction with BSSID, RSSI, IP,
    subnet, gateway, DNS, and scan results.
  - Implement an ESP32-backed `WifiService` registered only when hardware
    capabilities indicate a self-managed Wi-Fi link.
  - Define commands:
    - `GET_STATUS`: link state, IP details, current BSSID, RSSI, and capability flags.
    - `GET_CONFIG`: enabled, SSID, configured BSSID, and password-present flag;
      never password bytes.
    - `SET_CONFIG`: versioned optional fields for enabled, SSID, BSSID, and
      password, with persist/reconnect flags.
    - `SCAN`: perform/cache a scan and return bounded, offset-based records
      containing SSID, BSSID, RSSI, channel, and authentication mode.
  - Return standard `StatusCode` values for malformed data, unavailable
    hardware, invalid BSSID, scan failure, and not-ready operations.
  - Reuse the existing config store and link lifecycle; do not place Wi-Fi
    state in transport/channel code.
  - Refactor the diagnostic provider to use the shared Wi-Fi service/link
    APIs, preserving console behavior without duplicated ESP32 logic.
  - Add the service ID, command IDs, payload formats, limits, versioning,
    error behavior, persistence, and password policy to a new protocol doc.
  - Update `architecture.md` to document the management service,
    platform-service dependency, registration rule, and client data flow.
  - Update relevant PlantUML source diagrams only; do not manually generate
    or edit SVG outputs.

- In `fujinet-nio-lib`:
  - Add public C types for Wi-Fi status, configuration, BSSID, scan records,
    and result/error codes.
  - Add helpers for status/config reads, configuration writes, and paginated
    scans.
  - Keep password input write-only and expose only `password_present` on reads.
  - Add wire constants and packet builders/parsers shared by all C targets.
  - Implement BBC/cc65 assembly glue where the existing C transport ABI
    cannot be used directly.
  - Document buffer ownership, string termination, maximum lengths, and scan
    pagination.

- In `fn-rom`:
  - Add protocol constants and BBC assembly wrappers for the Wi-Fi service.
  - Add `cmd_wifi.s` or equivalent transient utility for status, scan,
    configuration, password/BSSID updates, and connection status.
  - Preserve existing network-session commands and ROM memory conventions.
  - Add 6502 unit tests for packet construction, response parsing, BSSID
    formatting, scan pagination, invalid responses, and password non-display.
  - Add Beebium end-to-end tests verifying FujiBus packets and command output.

- In `nio-core-apps`:
  - Add a portable `wifi`/`fwifi` application using the new library API.
  - Support Linux, Atari, and MS-DOS builds.
  - Provide status, scan, get/set SSID, set BSSID, and set-password operations.
  - Do not echo or print credentials.
  - Add host-side behavior tests and platform builds; run MS-DOS builds after
    sourcing `~/.local/bin/add_watcom.sh`.

- In `nio-config`:
  - Add Wi-Fi state, scan-result display, SSID/BSSID selection, password entry,
    connection status, and save/apply handling.
  - Integrate platform-specific controls without duplicating wire protocol code.
  - Add BBC UI/assembly support while preserving existing layout constraints.
  - Add Linux/MS-DOS and Beebium coverage for scan, editing, apply/save,
    reconnect status, invalid input, and hidden-password behavior.
  - Regenerate template-derived sources through the existing build process;
    do not hand-edit generated assets.

## Test Plan

- `fujinet-nio`: protocol, fake-link/service, config-store persistence, scan
  pagination, invalid payload, unsupported-platform, and ESP32 integration
  tests where hardware facilities exist.
- `fujinet-nio-lib`: C wire tests for every command, boundary-length strings,
  BSSID encoding, scan paging, error/status mapping, and password write-only
  behavior.
- `fn-rom`: 6502 unit tests and Beebium FujiBus end-to-end tests.
- `nio-core-apps`: Linux/Atari/MS-DOS compile and command behavior tests,
  including Watcom builds.
- `nio-config`: platform unit tests and Beebium UI workflows.
- Workspace validation: run affected platform workflows and existing emulator
  suites, recording commands and submodule commits in the handoff.

## Assumptions

- The new wire device is `0xF3`, following the existing NIO service IDs.
- Registration is conditional on
  `HardwareCapabilities.network.managesItsOwnLink`.
- `SET_CONFIG` supports atomic updates and explicit persist/reconnect flags.
- Scan responses are offset/limit based so 8-bit clients never require an
  oversized single frame.
- POSIX/Linux clients receive a defined unsupported/not-managed result unless
  a managed Wi-Fi backend is later added.
- The current `nio-core-apps` and `nio-config` working trees contain broad
  deletion markers; implementation must preserve or restore those user-owned
  changes before editing.
