# Atari Emulator Profiles

Atari emulator runs are described with a neutral YAML profile and rendered by
`scripts/atari-run`.

The goal is to keep application Makefiles free of emulator-specific flags. A
profile describes the machine, startup program, boot disks, and any
emulator-specific extras. The runner translates that profile to an Altirra or
atari800 command line.

## Commands

Dry-run the default Altirra profile:

```sh
./scripts/atari-run altirra --dry-run
```

Run the default Atari application build under Altirra:

```sh
./scripts/build.sh atari-run
```

Override the program under test:

```sh
./scripts/build.sh atari-run -- \
  altirra \
  --program repos/nio-apps/build/atari/bin/fls.xex
```

Select atari800 command rendering:

```sh
./scripts/atari-run \
  atari800 \
  --dry-run \
  --profile configs/atari/profiles/atari800-pal-800xl.yaml
```

The command modules live under `tools/atari_emulator/`. Adding a new emulator,
such as Fujisan, should be a new module with `register_subcommands()` rather
than another branch inside the Altirra or atari800 code.

## Environment

- `ALTIRRA_BIN` overrides the Altirra/AltirraSDL executable. Default:
  `AltirraSDL`.
- `ATARI800_BIN` overrides the atari800 executable. Default: `atari800`.
- `ATARI_OS_ROMS` supplies the `__OS_ROMS__` replacement for AltirraSDL
  settings templates unless `altirra.rom_roots.os` is set in the profile.
- `ATARI_BASIC_ROMS` supplies the `__BASIC_ROMS__` replacement for AltirraSDL
  settings templates unless `altirra.rom_roots.basic` is set in the profile.
- `NIO_APPS_ATARI_BIN` points at Atari app outputs. Default:
  `repos/nio-apps/build/atari/bin`.

## Profile Shape

```yaml
machine:
  system: 800xl
  video: pal
  ram_kb: 64
  kernel: xl
  basic: false
  sio_patch: false
  accurate_disk: true
  rom:
    os: ~/8bit/atari/images/os/REV04.ROM

startup:
  program: ${NIO_APPS_ATARI_BIN}/fhost.xex
  disks:
    - ~/atari/disks/spartados.atr

altirra:
  settings_template: configs/atari/settings/altirraSDL-settings.ini
  rom_roots:
    os: ${ATARI_OS_ROMS}
    basic: ${ATARI_BASIC_ROMS}
  profile: null
  portable: false
  debug: true
  devices:
    - type: custom
      params:
        hotreload: false
        path: ~/dev/atari/fujinet-emulator-bridge/altirra-custom-device/netsio.atdevice
        allowunsafe: false
  debug_commands:
    - bp _main
```

For AltirraSDL, the runner copies `altirra.settings_template` to a temporary
`XDG_CONFIG_HOME/altirra/settings.ini`, replacing `__OS_ROMS__` and
`__BASIC_ROMS__`. The temporary config directory is passed only to the launched
process. Device entries render as repeated `--adddevice` arguments.

The Altirra command currently translates these `machine` keys:

- `system` -> `--hardware`
- `video` -> `--pal`, `--ntsc`, `--secam`, `--ntsc50`, or `--pal60`
- `ram_kb` -> `--memsize <n>K`
- `kernel`, `kernel_ref`, `basic_ref`
- `basic`, `stereo`, `vsync`, `fastboot`, `accurate_disk`, `burst_io`
- `sio_patch`: `true`, `false`, `safe`, `on`, or `off`
- `artifact`, `axlon_memsize`, `high_banks`, `diskemu`

Classic Altirra/Wine profiles are still supported through `altirra.profile`,
`altirra.portable`, and `ALTIRRA_BIN='wine /path/to/Altirra64.exe'`.

The atari800 backend is intentionally conservative for now. It renders the basic
machine/video/ROM/program/disk command line, but richer cfg generation should be
added once we choose the canonical atari800 cfg layout.
