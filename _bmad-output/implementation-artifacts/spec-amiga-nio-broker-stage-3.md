---
title: 'Amiga NIO broker Stage 3 — parent cut-over gate'
type: 'feature'
created: '2026-08-22'
status: 'draft'
review_loop_iteration: 0
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - backlog/nio-broker.md
  - _bmad-output/specs/spec-amiga-nio-broker/stages.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3a.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3b.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Stage 2 delivered an isolated `fujinet-nio.device`, but normal Amiga clients still `OpenDevice("serial.device")`, so DiskDevice and CLI can contend as competing serial owners.

**Approach:** Keep **one** Stage 3 delivery checkpoint. Implement through two sequenced specs only: **3A** lib transport cut-over and host tests, then **3B** Amiberry bootstrap plus broker-backed DiskDevice/FLS regression. Parent Stage 3 is complete only when both are accepted. 3A passing does **not** complete Stage 3.

## Boundaries & Constraints

**Always:**
- Sequence: finish and accept 3A, then implement 3B. Do not start 3B implementation before 3A Verification commands have run and passed.
- After 3A+3B, production Amiga FujiNet NIO `OpenDevice("serial.device")` exists only in the broker serial backend.
- Check `backlog/nio-broker.md` Stage 3 boxes only after **both** 3A and 3B Verification commands have actually run and passed.
- Follow `docs/agent-test-policy.md`. Do not treat compile-only as Stage 3 complete.

**Ask First:**
- Changing public `FujiNetNIORequest`, `FUJINET_NIO_CMD_EXCHANGE`, or public `fn_transport_*` signatures.
- Starting Stage 4 idle-close removal.

**Never:**
- Treat 3A or 3B as a separately shippable Stage 3.
- Defer any Stage 3 backlog deliverable out of 3A+3B.
- Create epics or `stories.yaml` for this split.
- Start Stage 4 or Stage 5 backends.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 3A accepted only | Lib host tests + `make check` pass; no broker-backed DiskDevice/FLS guest | Parent Stage 3 remains **open** | Do not check Stage 3 backlog boxes |
| 3A and 3B accepted | 3A commands passed; bootstrap + inspect-catalog guest passed | Parent Stage 3 **complete**; serial-direct shim is gone from the normal path | Environment blocker reported, not skipped |

</frozen-after-approval>

## Code Map

- `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3a.md` — Amiga `fn_transport` broker client, per-context Amiga resources, lib host tests, lib README/building sentences.
- `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3b.md` — Amiberry load-before-NIO bootstrap, disk.device via cut-over lib (no semantics redesign), DiskDevice/FLS guest, classified serial/`OpenDevice` source search.
- `backlog/nio-broker.md` — Stage 3 section; still the checkpoint tracker.
- `docs/amiga/nio-broker-architecture.md` §3, §4, §8 — ownership, disk-as-lib-client, load ordering.
- `docs/agent-test-policy.md` — cheapest owner gates; child specs name the exact commands.

## Tasks & Acceptance

**Execution:**
- [ ] Accept and implement `spec-amiga-nio-broker-stage-3a.md` first -- context-sized lib cut-over
- [ ] Accept and implement `spec-amiga-nio-broker-stage-3b.md` after 3A verification -- bootstrap + guest race proof
- [ ] `backlog/nio-broker.md` -- mark Stage 3 only when both child specs are `done` and their commands were run

**Acceptance Criteria:**
- Given 3A verification has passed and 3B has not, when someone asks if Stage 3 is done, then the answer is no.
- Given both child specs are `done` and every named Verification command in 3A and 3B was run, when the parent is closed, then Stage 3 backlog deliverables are complete without leftover scope.

## Spec Change Log

- 2026-08-22: Split from a combined Stage 3 implementation spec for token budget. Scope stays 3A+3B under this parent gate.
- 2026-08-22: Human edit — 3A request-init/close precondition and 3B classified source search; no scope expansion.

## Verification

Parent complete only if **both** child Verification sections were executed. Compile-only is not sufficient.

**Commands:**
- Entire Verification list in `spec-amiga-nio-broker-stage-3a.md` -- expected: all 3A commands run and passed
- Entire Verification list in `spec-amiga-nio-broker-stage-3b.md` -- expected: all 3B commands run and passed
