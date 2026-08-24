---
title: 'Amiga NIO broker Stage 2 — parent completion gate'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 0
context:
  - docs/amiga/nio-broker-architecture.md
  - docs/agent-test-policy.md
  - backlog/nio-broker.md
  - _bmad-output/specs/spec-amiga-nio-broker/stages.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2a.md
  - _bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2b.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Stage 1 shipped the public ABI, but Stage 2 (`fujinet-nio.device` + serial backend + isolated proof) is still undelivered. A single implementation spec for all of that exceeded the BMAD size limit.

**Approach:** Keep **one** Stage 2 delivery checkpoint. Implement through two sequenced specs only: **2A** Exec core (host/native tests), then **2B** serial backend and isolated guest. Parent Stage 2 is complete only when both are accepted. 2A passing does **not** complete Stage 2. This is not two independent checkpoints and does not drop any Stage 2 backlog scope.

## Boundaries & Constraints

**Always:**
- Sequence: finish and accept 2A, then implement 2B. Do not start 2B implementation before 2A verification commands have run and passed.
- Check `backlog/nio-broker.md` Stage 2 boxes only after **both** 2A and 2B Verification commands have actually run and passed.
- Follow `docs/agent-test-policy.md`: named commands in the child specs must be executed; do not substitute the full Amiberry suite or DiskDevice pytest as the Stage 2 gate.
- Isolation for 2B: never load the new broker beside the old serial-direct shim; no FLS; no `fujinet-disk.device` in the isolated guest image.

**Ask First:**
- Changing public `FujiNetNIORequest` or `FUJINET_NIO_CMD_EXCHANGE`.
- Installing the broker on any existing Amiberry case that still uses the serial-direct shim.

**Never:**
- Treat 2A or 2B as a separately shippable Stage 2.
- Defer any Stage 2 backlog deliverable out of 2A+2B.
- Create epics or `stories.yaml` for this split.
- Edit `fn_transport.c` (Stage 3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 2A accepted only | Host broker tests + lib check pass; no serial guest | Parent Stage 2 remains **open** | Do not check Stage 2 backlog boxes |
| 2A and 2B accepted | 2A commands passed; `make native` + isolated pytest passed | Parent Stage 2 **complete** | Environment blocker reported, not skipped |

</frozen-after-approval>

## Code Map

- `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2a.md` — Exec device, BeginIO/AbortIO/FIFO/expunge, `fn_slip.h`, NDK stub alignment, host `make tests`.
- `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2b.md` — §11 serial backend, `make native`, isolated `test_nio_broker.py::test_isolated_exchange`.
- `backlog/nio-broker.md` — single Stage 2 section and broker test suite table; still the checkpoint tracker.
- `docs/agent-test-policy.md` — cheapest owner gates; child specs name the exact commands.

## Tasks & Acceptance

**Execution:**
- [ ] Accept and implement `spec-amiga-nio-broker-stage-2a.md` first -- context-sized Exec core
- [ ] Accept and implement `spec-amiga-nio-broker-stage-2b.md` after 2A verification -- serial + isolated guest
- [ ] `backlog/nio-broker.md` -- mark Stage 2 only when both child specs are `done` and their commands were run

**Acceptance Criteria:**
- Given 2A verification has passed and 2B has not, when someone asks if Stage 2 is done, then the answer is no.
- Given both child specs are `done` and every named Verification command in 2A and 2B was run, when the parent is closed, then Stage 2 backlog deliverables are complete without leftover scope.

## Spec Change Log

- 2026-08-22: Split from a combined Stage 2 implementation spec for token budget. Scope stays 2A+2B under this parent gate.

## Verification

Parent complete only if **both** child Verification sections were executed.

**Commands:**
- Entire Verification list in `spec-amiga-nio-broker-stage-2a.md` -- expected: all 2A commands run and passed
- Entire Verification list in `spec-amiga-nio-broker-stage-2b.md` -- expected: all 2B commands run and passed
