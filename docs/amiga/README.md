# Amiga workspace documentation

- [`disk-media-architecture.md`](disk-media-architecture.md) — supported
  DiskDevice media, standard user workflow, lifecycle contracts, current
  limitations, and future HDF/RDB architecture boundaries.
- [`rs232-paula-and-cia-handshake.md`](rs232-paula-and-cia-handshake.md) —
  Paula UART vs CIA-B RTS/CTS, `misc.resource` split, why seven-wire is
  not this `fujinet-serial.device` cut, and how to add it later.
- [`amiberry-testing.md`](amiberry-testing.md) — interactive and automated
  Amiberry setup, focused integration tests, retained evidence, and debugging.
- [`cli-stack-and-iorequest.md`](cli-stack-and-iorequest.md) — default Shell
  STACK 4096 (`#80000006` CHK) and never `WaitIO` an OpenDevice-only
  IORequest.

Active cross-repository work is tracked in [`../../backlog/`](../../backlog/),
and completed acceptance records are retained in
[`../../completed/`](../../completed/).
