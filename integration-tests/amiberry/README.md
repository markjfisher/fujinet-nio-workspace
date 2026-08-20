# Amiberry integration tests

This suite runs real Amiga binaries in Amiberry against a real POSIX
`fujinet-nio` instance.

## Prerequisites

- Amiberry with Unix IPC socket support
- `socat`
- `xdftool` (or `uvx`, which the disk builder uses to fetch it)
- The Amiga cross compiler (`m68k-amigaos-gcc`)
- A built AmigaOS environment — see `docs/amiga/environment-setup.md`

## Running tests

### Full build + test (recommended)

Builds all Amiga libraries, apps, core utilities, and the POSIX NIO binary,
then runs the suite. Pass `--amiga-env` and `--amiga-machine` to select the
OS environment and emulated machine:

```sh
./scripts/build.sh amiga-tests --amiga-env wb32 --amiga-machine a1200-030
./scripts/build.sh amiga-tests --amiga-env wb31 --amiga-machine a1200-030
```

### Direct test run (when binaries are already built)

`scripts/amiga-tests` is a thin pytest wrapper that sources `local/amiga.env`
and forwards all arguments to pytest:

```sh
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030
scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 -k test_fmount -v
scripts/amiga-tests --amiga-env wb31 --amiga-machine a500-030 -x -v
```

`--amiga-env` is required. Without it every test skips with a message
directing you to build the environment first.

### Building an environment

If you haven't built the environment yet:

```sh
scripts/amiga-env build wb32 --machine a1200-030
scripts/amiga-env build wb31
scripts/amiga-env status
```

See `docs/amiga/environment-setup.md` for full details.

## Evidence

Each run creates `test-evidence/amiberry-YYYYMMDD-HHMMSS/`. Every case keeps
its generated HDF, component logs, extracted result files, and an
`amiberry-screen.png` framebuffer capture (via Amiberry IPC). Evidence is
gitignored and retained for manual review and cleanup.

Set `AMIGA_E2E_EVIDENCE_ROOT` to choose an explicit directory.
Set `AMIGA_E2E_SCREENSHOT_DELAY` to adjust the post-activity capture delay.

Cases with continuous background protocol activity can set `completion_log`
in `tests.toml` and emit a unique final NIO operation from their startup
sequence — the harness captures and quits on that marker instead of waiting
for the safety timeout.

## Adding a test

1. Add or reuse an Amiga executable. Test applications belong in
   `repos/nio-apps/apps/test/`; product command binaries come from
   `repos/nio-core-apps/apps/`.

2. Add a startup sequence under `startup/`. Each command should redirect its
   output to a distinct file on the HDF:

   ```text
   C:FAPP PUT nio.e2e key value >DH0:put.result
   ```

3. Add a `[[test]]` entry to `tests.toml` with the application, startup file,
   and result files to extract.

4. Add a pytest module that calls `run_amiga_case("your-name")` and asserts
   the guest output and any required markers.

Keep result output deterministic and include an explicit `PASS` marker. A
test should validate observable behaviour, not only that Amiberry started.
