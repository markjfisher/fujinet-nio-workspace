# Amiga NIO broker Stage 3 — cut-over

Status: `ACCEPTED` (2026-08-22)

## Goal

Stop Amiga `fn_transport` from opening `serial.device`. Clients open
`fujinet-nio.device`; the broker serial backend is the sole production FujiNet
NIO serial owner.

## Acceptance

Parent gate `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-3.md`
is `done` only because both children are `done` and their named Verification
commands ran:

- 3A — lib transport cut-over (`spec-amiga-nio-broker-stage-3a.md`)
- 3B — guest bootstrap and DiskDevice/FLS race proof (`spec-amiga-nio-broker-stage-3b.md`)

`--load-driver` on `scripts/build-amiga-test-disk` requires `--load-nio`.
Isolated broker images still do not auto-prepend disk LoadResident.

## Durable contract

`docs/amiga/nio-broker-architecture.md`

Remaining work stays in `backlog/nio-broker.md`: Stage 4 idle-close removal,
Stage 5 extra backends. Do not reopen Stage 3 unless a regression is found.
