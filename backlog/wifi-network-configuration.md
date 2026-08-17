# Wi-Fi configuration clients and platform integration

Status: `IN PROGRESS`

## Goal

Finish the client and UI adoption of the implemented versioned Wi-Fi wire
service without duplicating protocol logic or exposing stored passwords.

## Completed foundation

- [x] `fujinet-nio` provides the Wi-Fi service, status/config/set/scan
      commands, persistence/controller integration, POSIX simulation, and
      service tests.
- [x] `fujinet-nio-lib` provides public C status/config/scan types and helpers,
      write-only password handling, BBC-compatible transport code, and wire
      tests.

## Remaining work

- [ ] Confirm the service protocol and registration/capability behavior are
      documented in the owning `fujinet-nio` repository, including versioning,
      pagination, errors, persistence, and password policy.
- [ ] Add the standard portable `FWIFI`/Wi-Fi command in `nio-core-apps` with
      status, scan, get/set SSID, optional BSSID, and password operations.
- [ ] Build and test the command on the currently supported application
      targets; never echo or return credential bytes.
- [ ] Add BBC `fn-rom` constants/wrappers and the appropriate transient command
      while preserving ROM workspace and utility ABI constraints.
- [ ] Add 6502 unit and Beebium packet/output tests for paging, invalid
      responses, BSSID formatting, and hidden passwords.
- [ ] Integrate Wi-Fi status, scanning, selection, password entry, save/apply,
      and reconnect state into `nio-config` without duplicating wire codecs.
- [ ] Add platform-appropriate `nio-config` UI coverage, including BBC layout
      constraints and Linux/MS-DOS host tests where those targets remain
      supported.
- [ ] Reconcile diagnostic-console Wi-Fi behavior with the public service and
      remove any remaining duplicate platform logic.
- [ ] Run affected library, platform-build, and emulator gates and document the
      final supported client/platform matrix.

## Exit criteria

Supported platforms can inspect and configure Wi-Fi through standard commands
and `nio-config` using the shared service/library API; scan pagination and
errors are tested, credentials remain write-only, and owner-repository
documentation describes the final protocol and platform support.
