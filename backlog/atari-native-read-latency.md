# Atari native-endpoint read latency: the remaining savings

Status: `DONE` - options 1 to 3 implemented and measured: a 256-byte read is 46.5 ms at index 0 (from 55 ms at index 1; 246 ms at 19200 before this work)

## Context

A 256-byte native read at high speed (index 1) takes 55 ms, down from 246 ms at 19200. The evidence and
the per-step breakdown are in `repos/fujinet-nio/docs/atari/hsio-report.md`. The wire time of the response
is 25.3 ms of the 55; the rest is the Atari's own processing (about 14 ms after the response arrives),
the request transaction `W` (9.3 ms) and the poll `P` (4.6 ms).

These are the changes still on the table, with the saving per 256-byte read and what each costs in design.
Together the first three are about 10 ms (18 percent); the fourth is a protocol-format change and is not
recommended.

## Options

### 1. Index 0 instead of 1 (about 3 ms) - configuration only - DONE (works; the index stays the user's choice)

`sio.hsio 0` (or `atari_sio.hsio_index: 0`), then the T page. 124,017 baud against 108,800. Disk boot at
index 0 measured about 30 ms a sector against 33. The risk is the Atari receive loop in
`fujinet-nio-lib/src/platform/atari/fn_hsio.s`, which crosses a page and so costs cycles it cannot spare at
that rate; the run shows whether `hs errors` stay at zero. No code change needed to try it.

### 2. Optimistic read: skip the poll `P` (about 4.6 ms) - DONE (measured: no `P` for sector reads, about 5.5 ms saved together with option 3)

Today a call is `W` (request), `P` (state and response length), `R` (exactly that length). `P` exists only to
learn the length, and the firmware's handler runs inside the `W` (`complete_write`), so the response is
already ready when `W` completes.

Design, with no new command and no change to the packet format:

- The firmware accepts `R` with a length greater than or equal to the response length (up to the
  capacity) and pads the rest with zeros (a shorter `R` is still refused; it was decided against accepting
  prefixes, to keep the retained-response contract and its integration tests unchanged). The Q reply's flag
  bit 0 advertises it. The FujiBus header already carries the
  packet length, so a client that reads more bytes than the packet needs still parses it correctly.
- A client that knows the size of the response (a sector read: 7 + 11 + sector size) issues `R` straight
  after `W`. If the firmware NAKs (an older firmware, or the response is not ready), it falls back to `P`
  and the exact `R`. A new client on an old firmware therefore still works, and an old client on a new
  firmware is unchanged.
- Calls that do not know the size keep using `P`.
- Cost to the design: one length rule in `AtariSioNioFrontend::begin` (and its tests, the protocol
  document, and the Python client's parser if it reads `R`), and a size hint in the library's raw call for
  the calls that have one (`fn_disk_read_sector`, and read for network when the size is requested).
- Tests: host tests for an `R` with extra length (padded, checksum over what is sent), a too-short `R`
  (NAK, state kept), an `R` before the response is ready (NAK); a soft65c02 test that the hinted call
  makes two SIO calls, not three.

### 3. Skip the second copy of the response (about 2.4 ms) - library only - DONE (profile: 14,000 to 9,850 cycles after the response)

The response is copied twice: response buffer to the disk reply buffer (`fn_raw_call`), then to the
caller's buffer (`memcpy` in `fn_disk_read_sector`). A raw-call variant that returns a pointer and length
into the response buffer lets the disk read validate its 11-byte header in place and copy the payload
once. The cycle profile (`fujinet-nio-lib/tests/atari_read_profile_soft65c02.*`) measures it exactly; the
test's ceiling can be lowered when it is done. Applies to every call that copies a reply.

### 4. A shorter response header (about 1.7 ms) - not recommended

19 of the 275 response bytes are FujiBus and disk framing. Removing them means a second response format.
Not worth the extra design.

## Done in this work (for reference)

Library checksum 90 to 10 cycles a byte, response copy 62 to 16 cycles a byte, CMD glitch filter during
writes, data gap 0 by default, `atari_sio` settings in `fujinet.yaml`, `sio.tune`, `sio.save`.

## Open, not about latency

- About 10 ACK timeouts per 600 calls remain; cause unknown.
- U1MB: resolved. Ultimate BIOS 4.20 (the released one) never polls non-disk devices; 4.33 sends `3F` to
  every device and speeds up `$7F` with no library driver (`docs/atari/hsio-report.md`, "The U1MB's own
  handler"). To do: flash the firmware with the "command frames lost" counter (`sio.status`) and run the T
  page both ways (index 0, `H` off, then `sio.reset` and `H` on, one boot). The library driver counted 12
  timeouts in 1,400 transactions (log 023), each a command frame the firmware never decoded; the U1MB
  handler's retries are not visible any other way.
- AltirraSDL / NetSIO answering `3F` so an emulated HSIO driver is exercised.
