# Amiga CLI stack and IORequest close

Two application bugs looked like serial-device crashes on PiStorm
(2026-09-07 CAP-5). The clock through `fujinet-serial.device` was fine
(`result=0` / `status=0`, Shell returned). The failures were in
`fujinet-nio-exchange`.

## Default Shell STACK is 4096

Guru `#80000006` is a 68k CHK. clib2 uses that for a blown stack. The
default Shell `STACK` is 4096 bytes.

`--help` is not a free path. If `main()` or `run_*()` allocates large
packet buffers, isolation-suite locals, or both *before* parsing argv,
`--help` still takes that frame and can Guru with no `OpenDevice`.

Do not nest a 2 KB matrix frame on top of unused isolation locals.
Parse argv / print usage in a thin `main`. Put kilobyte buffers in BSS
or `AllocMem`. clib2 programs that still need a deep frame can declare
`long __stack = 16384;` so the CRT requests more than 4096.

## AbortIO/WaitIO only on a submitted request

Keep an `OpenDevice` IORequest and a command IORequest separate if you
want; that is normal.

`AbortIO` + `WaitIO` apply only when `CheckIO` says **that** request is
still outstanding after `SendIO` / `BeginIO`. After `DoIO`, `WaitIO` has
already run. A second `WaitIO` can hang or steal the next message on the
port.

Never `WaitIO` an IORequest used only for `OpenDevice`. Exec does not
`ReplyMsg` that request. `CheckIO` can look pending (`ln_Type` still
`NT_MESSAGE`), and `WaitIO` waits forever: the CLI freezes with no Guru.
Just `CloseDevice` it.

The public header used to say “CloseDevice requires AbortIO/WaitIO first
on this IORequest” without that distinction. That wording caused the
post-`[D]` hang.
