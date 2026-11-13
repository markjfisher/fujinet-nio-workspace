# Headless Atari800 NetSIO test

This path builds the exact `mozzwald/atari800` `netsio-feb2026` revision
reported in [fujinet-nio issue 26](https://github.com/fujinet-nio/fujinet-nio/issues/26).
The source is checked out into ignored `build/`, not installed as another
workspace repository. It uses Atari800's no-video/no-sound target and never
opens a window. A tiny test-only observer in its headless main loop reads a
result marker from guest RAM; it does not change POKEY, SIO or NetSIO timing.
The no-video target uses Atari800's simplified ANTIC path, so this is not an
exact substitute for Andy's iOS build or his full game workload.

From the workspace root:

```sh
source scripts/env.sh
integration-tests/atari800/build-emulator.sh
(cd repos/fujinet-nio-lib && make atari)
(cd repos/fujinet-nio && ./build.sh -cp atari-fujibus-netsio-debug)
python3 integration-tests/atari800/run.py
```

The test needs `cl65`, `dir2atr`, autotools, a C compiler and a readable
XL/XE OS ROM (`$ATARI_OS_ROMS/REV02.ROM` by default; `--rom` overrides it).
It creates an isolated firmware data directory, boots a PicoBoot ATR via the
actual POSIX NIO disk frontend and runs 200 ClockDevice calls with a DLI active.
Each call uses the native W/P/R exchange. Guest RAM reports init status,
completed calls, errors, calls that took over 100 PAL video frames, and a
saturating DLI counter (which must be nonzero).
Temporary run logs are retained and their path is printed.

`--ack-gap-us 0` runs the same guest with the firmware gap disabled;
`--ack-gap-us 250` is the default. A passing run is useful compatibility
coverage, not proof the race is absent: host wall-clock timing can collapse
inside an emulator's receive queue. The issue's emulator-side change is needed
for an emulated-time guarantee, and Andy's full game workload remains a
separate acceptance test.
