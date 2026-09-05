# Amiga RS-232 38400 reliability

Status: `IN PROGRESS`

## Goal

Make FujiBus over Amiga RS-232 usable at 38400 for disk and large replies
without silent data corruption. Line baud stays 38400; ESP→host TX may be
paced. Paula RBF overrun is the failure mode, not CIA TX→RX.

Research:
[`_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md`](../_bmad-output/planning-artifacts/research/technical-amiga-rs-232-disk-operation-failures-abo-2026-09-03/research.md)

Evidence:
[`repos/fujinet-nio-driver/docs/amiga/rs232-38400-pacing-evidence.md`](../repos/fujinet-nio-driver/docs/amiga/rs232-38400-pacing-evidence.md)

## Done (research ranks 1–2)

- [x] Cold/warm + size diagnostic (`fujinet-nio-exchange`).
- [x] ESP configurable inter-byte and chunk pacing; product default
      `tx_chunk_size=16`, `tx_chunk_gap_us=2000`, `tx_byte_gap_us=0`.
- [x] After `cause=7`, drain RX until idle then close so the next EXCHANGE
      is not sticky `cause=3`. Hardware: no `cause=3` after `cause=7`.

Rank 2 is **not** “zero overruns”. 16/2000 soak still had 1/500 on cold
LIST 512; later 50-trial clusters were higher. Stream is recoverable;
the failed packet still returns `FN_ERR_TRANSPORT` with length 0.

## Remaining (disk-safe packet recovery)

A disk block must not complete OK with a truncated body (already fail-closed)
and must not leave the volume needing a human requester because one RBF miss
dropped a sector command.

- [x] NIO-layer retry of **idempotent** DiskDevice commands after
      `FN_ERR_TRANSPORT` / `FN_ERR_TIMEOUT`, only after stream drain+reopen.
      READ is idempotent. WRITE of the same 512-byte ADF sector is replay-safe.
      Do not retry non-idempotent FujiBus commands without request IDs.
- [ ] Prove on hardware: inject or wait for a `cause=7` during `CMD_READ` /
      `CMD_WRITE` and show the block completes `io_Error=0` with a full
      `io_Actual`, or a persistent error after bounded retries — never a
      short successful read.
- [ ] Optional later (research rank 3): seven-wire RTS/CTS with
      `SERF_7WIRE` before `OpenDevice()`, only with analyzer capture.
- [ ] Do not start 57600, READY/GO, or a custom `serial.device` unless
      retry+pacing cannot meet disk reliability.

## Dependencies

- DiskDevice Phase 2 and broker Stage 3/4 are complete; do not reopen them.
- Pacing defaults live in `repos/fujinet-nio` `UartConfig`; Atari SIO clears
  them.
