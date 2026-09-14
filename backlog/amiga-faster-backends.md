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

## Software contract gate

Story 1.6 software contract acceptance is **accepted** (2026-09-15). The
[decision and evidence record](../_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#technical-acceptance-record--2026-09-15)
maps Stories 1.1–1.5 and the reviewed retry-containment follow-up to exact
revisions and passing tests; the
[native packet contract](../repos/fujinet-nio/docs/native-packet-contract.md)
describes the verified software behavior and limits. F1–F3 are closed:
both actual retry callers establish pre-send, post-delivery and post-effect
containment with independent transmission/effect counts and late-response
isolation across close/open. Historical 1.5 completion is preserved.
The reviewed driver is `e6f9686797f6bae256342d362795c4b3fc5b3da1`; the
accepted firmware contract is `cf2ab541c95d8769e67cb41541ca627db455e541`.
Pin the workspace commit containing the linked acceptance decision as well.
This satisfies the 1.5/1.6 software prerequisites; every other story prerequisite
still applies. Known-completion application replay remains documented existing
policy; physical quiescence is not proven by these software tests.

Story 2.4 requires accepted 1.6, positive relevant 2.2/2.3 feasibility evidence
and explicit ABI approval. Setup/feasibility may proceed independently;
physical implementation also requires accepted 1.14. None of this audit's
software checks establishes hardware readiness or closes the exit criteria.

## Work

- [x] Driver owner (`repos/fujinet-nio-driver`): complete the
      [scoped retry-containment follow-up](../_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/retry-containment-follow-up.md).
      Exit: resolve F1–F3 with both actual retry paths proving backend-enforced
      containment, transmission/effect counts and late-response isolation
      across close/open until independently established software quiescence.
- [ ] Define channel capabilities and packet envelope requirements for the
      first selected packet-native hardware link.
- [ ] Select the first target hardware and develop its packet-native backend.
- [ ] Develop additional faster-channel backends behind the shared session
      interface where hardware warrants them.
- [ ] Prove backend parity with the RS-232 protocol and multi-drive suites.
- [ ] Add integrity, recovery, capability, throughput, and latency tests.
- [ ] Document hardware, installation, recovery, and compatibility behavior
      for a Zorro-only deployment without fallback or automatic failover.

## Exit criteria

At least one faster backend passes the same configuration, catalogue mapping,
multi-drive, writable-media, and change-notification behavior as RS-232, with
recorded performance and recovery results.
