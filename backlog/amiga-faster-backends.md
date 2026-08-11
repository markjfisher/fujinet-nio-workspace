# Faster Amiga FujiBus backends

Status: `TODO`

## Goal

Add packet-native and faster physical transports without changing the
DiskDevice, Slot Catalog, mapping, driver-unit, or application contracts
validated over RS-232.

## Dependencies

- Stage 8 and Amiga DiskDevice Phase 2 are complete and reviewed.
- The Amiga `nio-config` port is complete enough to configure and exercise the
  platform without depending on a faster transport.

## Work

- [ ] Define channel capabilities and packet envelope requirements for the
      Pico/native link.
- [ ] Develop the Pico/native packet backend.
- [ ] Develop additional faster-channel backends behind the shared session
      interface where hardware warrants them.
- [ ] Prove backend parity with the RS-232 protocol and multi-drive suites.
- [ ] Add integrity, recovery, capability, throughput, and latency tests.
- [ ] Document hardware, installation, fallback, and compatibility behavior.

## Exit criteria

At least one faster backend passes the same configuration, catalogue mapping,
multi-drive, writable-media, and change-notification behavior as RS-232, with
recorded performance and recovery results.
