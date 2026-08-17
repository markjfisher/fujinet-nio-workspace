# Faster Amiga FujiBus backends

Status: `TODO`

## Goal

Add packet-native and faster physical transports without changing the
DiskDevice, Slot Catalog, mapping, driver-unit, or application contracts
validated over RS-232.

## Dependencies

- Stage 8 and Amiga DiskDevice Phase 2 are complete and reviewed.
- The existing `serial.device` FujiBus/SLIP implementation remains the
  compatibility baseline; faster channels must not fork service payloads or
  application APIs.

The Amiga `nio-config` port is useful for end-user configuration but is not a
transport prerequisite: standard commands and the existing integration
harness can validate a backend independently.

## Work

- [ ] Define channel capabilities and packet envelope requirements for the
      first selected packet-native hardware link.
- [ ] Select the first target hardware and develop its packet-native backend.
- [ ] Develop additional faster-channel backends behind the shared session
      interface where hardware warrants them.
- [ ] Prove backend parity with the RS-232 protocol and multi-drive suites.
- [ ] Add integrity, recovery, capability, throughput, and latency tests.
- [ ] Document hardware, installation, fallback, and compatibility behavior.

## Exit criteria

At least one faster backend passes the same configuration, catalogue mapping,
multi-drive, writable-media, and change-notification behavior as RS-232, with
recorded performance and recovery results.
