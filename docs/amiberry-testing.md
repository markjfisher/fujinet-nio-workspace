# AmigaOS testing with Amiberry

The workspace can build a licensed AmigaOS 3.2 test HDF, boot it in Amiberry,
and connect its emulated `serial.device` to a POSIX FujiNet NIO instance.
The HDF is local Amiberry storage; FujiNet NIO remains the network/device
service and does not need Amiga disk support for this workflow.

## Prerequisites

Install `amiberry`, `socat`, `nc`, and the `m68k-amigaos` toolchain. Set the
Amiga asset root if it is not the default:

```sh
export AMIBERRY_ASSET_ROOT="$HOME/dev/amiga/amigaOS3.2"
```

The root must contain `ROM/kickCDTVa1000a500a2000a600.rom`,
`ADF/Workbench3.2.adf`, and `L/FastFileSystem`. These are user-supplied
licensed assets and are not stored in the workspace.

## Build and run

Build the Amiga example applications and a bootable HDF containing
`wifitest`:

```sh
./scripts/build.sh amiga-e2e --timeout 15
```

The runner starts FujiNet NIO, Amiberry, and a small `socat` bridge. Both NIO
and Amiberry expose TCP listeners, so the bridge is required. Logs are written
under `build/amiga-e2e/`.

To run a core utility instead:

```sh
AMIGA_TEST_PROJECT=core AMIGA_TEST_APP=fhost \
  ./scripts/build.sh amiga-e2e --timeout 15
```

The generated HDF is under `build/images/`. The builder imports
`Devs/serial.device` from the licensed Workbench ADF and installs the app in
the `C:` path. The startup command can be overridden with
`AMIGA_TEST_COMMAND` when an app needs arguments.

## What this validates

`wifitest` exercises `fn_init()` and the Wi-Fi status/configuration/scan wire
operations. `fhost` exercises the host-device protocol. With Wi-Fi disabled
in the generated NIO configuration, network operations are expected to return
an NIO I/O error; the NIO log still confirms the request and response frames.

This keeps the architecture split clean: Amiga code uses the platform
transport in `fujinet-nio-lib`, Amiberry supplies the guest serial device, and
POSIX `fujinet-nio` owns the device services. Future FujiNet disk-image support
can be added independently; it is not required to boot or test these apps.
