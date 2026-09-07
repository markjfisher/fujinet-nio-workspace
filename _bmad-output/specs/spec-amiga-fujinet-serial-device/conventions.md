# Conventions: names, install, tests

Owning repo: `repos/fujinet-nio-driver`. Workspace harness: `integration-tests/amiberry`. Durable hardware procedure: `repos/fujinet-nio-driver/docs/amiga/rs232-cold-warm-hardware-test.md`. Lifecycle contracts: `lifecycle.md`.

## Names

| Thing | Name |
| --- | --- |
| Paula Exec device | `fujinet-serial.device` |
| Broker | `fujinet-nio.device` |
| Select/inspect serial driver | `fujinet-nio-serial` |
| Inspect/set baud | `fujinet-nio-baud` |
| Cold/warm matrix / clock | `fujinet-nio-exchange` |
| Load/unload | `fujinet-load-resident` / `fujinet-unload-resident` |
| Stock OS serial | `serial.device` (default; never rename) |
| Serial hardware claim | `misc.resource` (`MR_SERIALPORT` then `MR_SERIALBITS`; release in reverse) |

`docs/amiga/nio-broker-architecture.md` still mentions `fujinet-nio-serial.device` in an Option-B aside. That is not this device. Do not revive that name.

## SET_SERIAL ABI

Defined in `repos/fujinet-nio-driver/amiga/include/fujinet_nio_device.h` and `fujinet_nio_serial_config.h`.

- `FUJINET_NIO_CMD_SET_SERIAL` = `CMD_NONSTD + 3`
- `FUJINET_NIO_CMD_GET_SERIAL` = `CMD_NONSTD + 4`
- Payload: little-endian `uint32` unit, then NUL-terminated Exec device name
- Name rules: 1..30 chars, printable, no space, no `:`, `/`, `\`
- SET_SERIAL closes the current serial backend so the next EXCHANGE opens the new name
- `OpenDevice` looks the name up in `DEVS:`

CLI:

```text
fujinet-nio-serial
fujinet-nio-serial fujinet-serial.device
fujinet-nio-serial serial.device
```

Exchange override (does not persist unless SET_SERIAL also ran):

```text
fujinet-nio-exchange --type clock --backend cold --baud 19200 \
    --serial-device fujinet-serial.device --trials 1
```

## Install surfaces already wired

Keep these unless the spec is updated:

- `amiga/Makefile` native target `fujinet-serial.device`
- `configs/amiga/ftp/release.txt` → `/dev/NIO/Devs/fujinet-serial.device` and `C:fujinet-nio-serial`
- `configs/amiga/release-adf.yaml`, `tools/build/nio_build/amiga_config.py` development share
- `scripts/build-amiga-test-disk --devs-file`
- Amiberry `tests.toml` case `nio-paula-serial` with `nio_broker = true` and `fujinet_serial = true`
- `docs/amiga/amiberry-testing.md` NIO: copy lines for `fujinet-serial.device`

Hardware load order:

```text
C:fujinet-load-resident DEVS:fujinet-serial.device fujinet-serial.device
C:fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device
C:fujinet-nio-serial fujinet-serial.device
```

## Tests (cheapest gate per owner)

Source `scripts/env.sh` first.

| Gate | Command | Covers |
| --- | --- | --- |
| Host | `make -C repos/fujinet-nio-driver/amiga tests` | SERPER math (9600 NTSC=371, 38400 PAL=91, 19200 PAL=183); ring; distinct hardware vs software overrun latches; SET_SERIAL encode/decode; exchange `--serial-device` plan; named lifecycle cases in `lifecycle.md` |
| Native build | `make -C repos/fujinet-nio-driver/amiga native` | `fujinet-serial.device`, `fujinet-nio.device`, `fujinet-nio-serial`, `fujinet-nio-exchange` |
| Amiberry one node | `uv run pytest --run-amiga --amiga-env wb32 --amiga-machine a1200-030 integration-tests/amiberry/test_nio_paula_serial.py::test_paula_serial_clock` | CAP-4 |
| Hardware | Cold clock one-shot in `rs232-cold-warm-hardware-test.md` | CAP-5; operator runs this; PiStorm is the sole hardware-stability gate |

Do not run the full Amiberry suite as the inner loop. Isolation: no `fujinet-disk.device`, no FLS/FHOST/FIN in another shell. Do not run no-arg `fujinet-nio-exchange` on PiStorm (that is the Amiberry isolation suite and has rebooted PiStorm after PASS).

FileDevice list used as an Amiberry completion marker must send `maxPayloadBytes` ≥ 18 (non-formatted). Size 8 returns `FN_ERR_INVALID` (status 2) and the harness waits until timeout. Size 256 is the known-good value used by `nio-paula-serial`.

## Broker subset the Paula device must satisfy

The serial backend (`fujinet_nio_serial_backend.c`) issues `OpenDevice`, `SDCMD_SETPARAMS` (8N1, `SERF_XDISABLED`, optional `SERF_RAD_BOOGIE`, `io_RBufLen` multiple of 64), `CMD_WRITE` (DoIO, often one SLIP frame), `SDCMD_QUERY`, `CMD_READ` (SendIO + timer abort), `CMD_FLUSH`. Exclusive open is required: the broker is the only opener of `fujinet-serial.device`. Hardware ownership is still via `misc.resource`.

`CMD_READ` must wait until the requested count is available. The broker already supplies timer `AbortIO`. Immediate 0-byte READ completion is rejected.

`SERF_RAD_BOOGIE` must not be treated as a FIFO or a TX/RX direction change.

SETPARAMS may accept 300–230400. The FujiNet hardware acceptance matrix remains 9600 / 19200 / 38400.
