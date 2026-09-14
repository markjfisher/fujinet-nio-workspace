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

Story 1.6 software contract acceptance is **held** (2026-09-14). The
[decision and evidence record](../_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#technical-decision-record--2026-09-14)
maps Stories 1.1–1.5 to exact revisions and passing tests; the
[native packet contract](../repos/fujinet-nio/docs/native-packet-contract.md)
describes the verified software behavior and limits. Missing pre-send,
post-delivery and post-effect evidence through both actual retry paths,
including transmission/effect counts and late-response isolation across
close/open, blocks acceptance. Historical 1.5 completion is preserved.
Independent review confirms the published hold. The revised contract is at
firmware revision `059cf18cf6ee39f3a65cc7a4e01ee77815507057`; the workspace
commit containing the linked decision records its publication. There is no
accepted revision for downstream consumers yet. The current execution gates
also block direct 1.5 dependents 1-8/1-10 until the missing evidence is closed.

Story 2.4 requires accepted 1.6, positive relevant 2.2/2.3 feasibility evidence
and explicit ABI approval. Setup/feasibility may proceed independently;
physical implementation also requires accepted 1.14. None of this audit's
software checks establishes hardware readiness or closes the exit criteria.

## Work

- [ ] Driver owner (`repos/fujinet-nio-driver`): complete the
      [scoped retry-containment follow-up](../_bmad-output/specs/spec-amiga-zorro-ii-packet-native-backend/stories/1-6-accept-the-canonical-software-packet-contract-for-bridge-design.md#scoped-follow-up-for-parentuser-decision).
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
