# Handoff: Amiga RS-232 receive overrun at 57,600 baud

## Scope

This is a live real-hardware investigation. Do not broaden it into FujiBus,
FHOST/FLS, DiskDevice, ESP application, or Workbench work. The active BMad
spec is `spec-amiga-rs232-response-diagnostics.md` in this directory.

## Hardware and observed behaviour

- Real Amiga connected to an ESP32-S3 FujiBus RS-232 endpoint.
- The user sets `fujinet-nio-baud 57600` in User-Startup, so the driver is
  configured after every reboot; the ESP endpoint is also set to 57,600.
- Normal `fhost tnfs://192.168.1.101/amiga` and `fls` fail at 57,600 with raw
  transport error 16, although ESP logs show the requests and valid replies.
- At 19,200 and 38,400, `fujinet-nio-exchange` ends with
  `PASS isolated-exchange` and FHOST/FLS work normally.

## Diagnostic implementation already present

The Amiga resident driver has request-local diagnostics only; it has no trace
buffer or broker print logging.

- `fn_pad[0]`: completion stage; `2` means exchange backend reached.
- `fn_pad[1]`: broker/public result.
- `fn_pad[2]`: detailed cause:
  - `0` none/success
  - `1` backend-open failure
  - `2` generic serial I/O fallback
  - `3` stream/SLIP session I/O
  - `4` timeout
  - `5` serial `CMD_WRITE`
  - `6` serial `SDCMD_QUERY`
  - `7` serial `CMD_READ`
  - `8` timer `TR_ADDREQUEST`
- On exchange replies, `fn_flags` was input-zero/reserved. It now returns
  diagnostic output: low byte = native serial.device error; high byte = high
  byte of `IOExtSer.io_Status`. This preserves the request layout.
- The public library also exposes
  `fn_amiga_transport_last_broker_cause(uint8_t *cause)`; existing public
  success/error values are unchanged.
- `amiga/tools/fujinet-nio-exchange.c` prints the diagnostics and is now
  allowed to run with `fujinet-disk.device` resident. It must not run while a
  separate legacy FLS task owns serial.device.

## Conclusive evidence

At 57,600, the tool’s first clock request has repeatedly reported:

```text
EXCHANGE io=0 nio=16 len=0 stage=2 result=16 cause=7 native=6 status-hi=1
```

Interpretation:

1. `io=0`: the broker completed/replied normally at Exec level.
2. `stage=2`: serial backend executed the exchange.
3. `nio/result=16`: normal public `FN_ERR_TRANSPORT` mapping.
4. `cause=7`: the failure occurred in `serial.device` `CMD_READ`.
5. `native=6`: Amiga `SerErr_LineErr`.
6. `status-hi=1`: `io_Status == 0x0100` in the relevant bit range,
   `IO_STATF_OVERRUN`; the UART receive buffer overran.
7. The immediate retry (`REUSE`) succeeds, demonstrating the fault is not a
   persistent FujiBus framing/packet incompatibility.

The proven chain is:

```text
ESP emits valid response
  -> Amiga serial.device CMD_READ
  -> UART receive overrun
  -> SerErr_LineErr
  -> broker maps to FN_ERR_TRANSPORT
```

The ESP warning for raw `c0 99 c0` during a run is expected: the diagnostic
tool deliberately sends that malformed request to verify timeout/reset
recovery. It is unrelated to the first-response overrun.

## Relevant current code

- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_serial_backend.c`
  - uses a 1 ms `SDCMD_QUERY`/timer poll loop before `CMD_READ`.
  - `FN_SERIAL_BACKEND_WIRE_BUF_SIZE` is `(FN_MAX_PACKET_SIZE * 2) + 2` and
    is passed as `IOExtSer.io_RBufLen`.
  - the direct post-query drain buffer is 128 bytes.
  - configures 8 data bits, 1 stop bit and `SERF_XDISABLED`.
- `repos/fujinet-nio-driver/amiga/nio.device/fujinet_nio_device.c`
  transports the diagnostic values through the completed request.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c` is the field
  probe; wait for it to exit before running normal FHOST/FLS.

## Safest next work

Study the Amiga serial.device receive/high-speed contract and exact `IOExtSer`
initialization. Determine why a short first response overruns at 57,600 with
the current 1 ms poll pattern and configured receive buffer.

Do not yet:

- lower the product baud default or declare 38,400 the ceiling;
- modify FujiBus/SLIP framing, generic retries, FHOST/FLS, or ESP firmware;
- infer that serial baud is mismatched—the User-Startup configuration removes
  the reboot-default explanation;
- run broad emulator/firmware suites.

Potential areas to validate, not yet fixes: explicit high-speed serial flags,
serial receive buffer semantics/placement, querying/draining timing around the
initial response, physical cable/electrical quality, and UART clock accuracy.

## Stage completed after the initial handoff: receive-buffer contract

The installed NDK `serial.device/SDCMD_SETPARAMS` autodoc supplies a concrete
constraint: `io_RBufLen` must be at least 64 bytes **and a multiple of 64**.
The prior backend incorrectly used the SLIP wire-buffer size directly:

```c
FN_SERIAL_BACKEND_WIRE_BUF_SIZE = (FN_MAX_PACKET_SIZE * 2) + 2
```

For the active 1024-byte packet configuration that is 2050 bytes, not a
multiple of 64. The backend now keeps its 2050-byte SLIP codec buffer but
rounds the serial.device receive allocation upward to 2112 bytes before
`SDCMD_SETPARAMS`.

This is a documented serial.device contract correction, not a timing or
protocol change. It is the first production change justified by the receive
overrun evidence. Do not enable `SERF_RAD_BOOGIE` yet: the NDK says it skips
break/parity and other checks, so test the valid buffer configuration first.

### Real-hardware result: buffer correction did not resolve the overrun

The user rebuilt, copied the updated `fujinet-nio.device`, restarted the
Amiga, and confirmed the User-Startup baud setup. At 57,600 the first
exchange remains:

```text
0 16 0 2 16 7 6 1
```

That is unchanged: `FN_ERR_TRANSPORT`, `CMD_READ`, `SerErr_LineErr`, receive
overrun. Normal FLS still fails. Therefore the invalid 2050-byte allocation
was a real documented configuration defect worth retaining, but it was not
the cause of this short-first-response overrun.

The next session should not repeat the buffer-size experiment. Its narrow
question is whether the current 1 ms poll/reply timing or missing explicit
high-speed serial-device mode makes the first response burst vulnerable. Read
the `RAD_BOOGIE` and receive-path portions of the serial.device autodoc, then
compare a minimal pending `CMD_READ` strategy against the existing
`SDCMD_QUERY`/timer loop. Preserve the successful 19,200/38,400 behaviour and
do not hide the error merely by disabling line-status checks.

## Verification completed

After each diagnostic change:

```sh
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga tests
source scripts/env.sh && make -C repos/fujinet-nio-driver/amiga native
```

Both pass. Earlier, after the public library diagnostic accessor was added:

```sh
cd repos/fujinet-nio-lib && source ../../scripts/env.sh && make check
```

also passed.
