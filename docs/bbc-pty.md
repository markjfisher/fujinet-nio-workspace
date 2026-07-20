# BBC/Master PTY FujiNet-NIO Workflow

This is the quick local path for running a BBC or Master/B2 emulator against a
POSIX `fujinet-nio` instance over a pseudo terminal.

## Commands

From the workspace root:

```sh
./scripts/build.sh bbc-pty
```

This target:

- builds `repos/fn-rom/build/FN-UTLS.ssd` for `BUILD_MACHINE=BBC`
- installs it as the BBC boot disk at:
  - `repos/fujinet-nio/distfiles/boot/bbc/autorun.ssd`
  - `repos/fujinet-nio/distfiles/esp32-data/boot/bbc/autorun.ssd`
- builds `repos/fujinet-nio/build/fujibus-pty-debug`
- writes `repos/fujinet-nio/build/fujibus-pty-debug/fujinet-data/fujinet.yaml`
- runs `repos/fujinet-nio/build/fujibus-pty-debug/run-fujinet-nio`

For Master/B2:

```sh
./scripts/build.sh master-pty
```

This target:

- builds `repos/fn-rom/build/FN-UTLS-M.ssd` for `BUILD_MACHINE=MASTER`
- installs it as the BBC boot disk at:
  - `repos/fujinet-nio/distfiles/boot/bbc/autorun.ssd`
  - `repos/fujinet-nio/distfiles/esp32-data/boot/bbc/autorun.ssd`
- builds `repos/fujinet-nio/build/fujibus-pty-debug`
- writes `repos/fujinet-nio/build/fujibus-pty-debug/fujinet-data/fujinet.yaml`
- runs `repos/fujinet-nio/build/fujibus-pty-debug/run-fujinet-nio`

Connect B2 to:

```text
/tmp/fujinet-pty
```

The PTY is created by `fujinet-nio`; the configured path is a symlink to the
actual slave device.

Both targets install to the same `fujinet-nio` BBC boot-disk path because the
device currently exposes one `persist:/boot/bbc/autorun.ssd`. The target run
last chooses which machine-specific utility disk is present there.

## Generated Config

The generated config is intentionally minimal:

```yaml
fujinet:
  device_name: fuji-nio
boot:
  mode: config
  config_uri: persist:/boot/bbc/autorun.ssd
  readonly: true
channel:
  pty_path: /tmp/fujinet-pty
```

The boot URI resolves against the build directory's local `fujinet-data`
folder. The POSIX build copies `distfiles/boot` there after compile, and the
workspace target installs the fn-rom utility disk before building/running.

## Overrides

Use a different PTY path:

```sh
BBC_PTY_PATH=/tmp/my-bbc-pty ./scripts/build.sh bbc-pty
MASTER_PTY_PATH=/tmp/my-master-pty ./scripts/build.sh master-pty
```

Use a different boot URI:

```sh
BBC_BOOT_URI=persist:/boot/bbc/other.ssd ./scripts/build.sh bbc-pty
MASTER_BOOT_URI=persist:/boot/bbc/other-master.ssd ./scripts/build.sh master-pty
```

## Why FN-UTLS

For the DISK+NET ROM profile, commands such as `*FLS` and `*FDRIVE` are
transient utilities loaded from disk. The correct boot disk is therefore
fn-rom's machine-specific utility disk, copied as `autorun.ssd`, not the
nio-apps BBC app disk.

- BBC uses `FN-UTLS.ssd`, with transient utilities load/exec at `$1900`.
- Master uses `FN-UTLS-M.ssd`, with transient utilities load/exec at `$0E00`.
- The workspace Master utility disk also includes `CONFNIO`, built from
  `repos/nio-apps/build/bbc/bin/config-nio` and staged as `$.CONFNIO`. The BBC
  `$1900` build of `CONFNIO` does not fit yet, so the BBC utility disk omits it
  until the BBC UI is reduced further.

The fn-rom `*FLS` utility requests formatted FileDevice directory lines from
FujiNet (`sort | formatted`, flag `$06`) and prints those strings directly on
the BBC side.
