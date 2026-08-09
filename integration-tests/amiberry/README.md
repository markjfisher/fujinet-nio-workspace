# Amiberry integration tests

This suite runs real Amiga binaries in Amiberry against a real POSIX
`fujinet-nio` instance. It is the cross-repository equivalent of the
Beebium integration suite; it is intentionally separate from the small unit
tests in `tools/amiga_emulator/tests`.

## Prerequisites

The suite needs:

- Amiberry with Unix IPC socket support;
- `socat`;
- `xdftool` (or `uvx`, which the disk builder can use to fetch it);
- the Amiga cross compiler;
- licensed, expanded AmigaOS assets configured through `AMIBERRY_OS_ROOT` and
  `AMIBERRY_WORKBENCH_ADF`.

The tests build the Amiga library, example apps, core utilities, and the
FujiNet-NIO TCP debug binary before running.

## Running

From the workspace root:

```sh
./scripts/build.sh amiga-tests
```

The suite is skipped by default when invoked directly with pytest. To run it
directly:

```sh
./scripts/run-amiga-e2e-tests -k wifi -v
```

Outputs, generated HDFs, and logs remain under `build/amiga-e2e-tests/`.
Each case also retains `amiberry-screen.png`, captured through Amiberry's IPC
socket from the guest framebuffer for human inspection; the test runner is
not headless. Protocol cases boot only the Amiga CLI, display the completed
result files with `Type`, capture the CLI framebuffer, and exit without
loading Workbench. Set `AMIGA_E2E_SCREENSHOT_DELAY` to adjust the short
post-activity evidence delay.
The runner starts its own FujiNet-NIO instance for each test case, so an
external TCP instance should not be started for this suite.

## Adding a test

1. Add or reuse an Amiga executable. Portable example/test applications belong
   in `repos/nio-apps/apps/test/`; product command coverage uses the binaries
   from `repos/nio-core-apps/apps/`.
2. Add a startup sequence under `startup/`. Each command should redirect its
   output to a distinct file in the HDF, for example:

   ```text
   C:FAPP PUT nio.e2e key value >DH0:put.result
   ```

3. Add a `[[test]]` entry to `tests.toml` with the application, startup file,
   and result files to extract.
4. Add a pytest module that calls `run_amiga_case("your-name")` and asserts
   the guest output and any required markers.

The fixture builds a fresh HDF, installs the selected app plus all core
utilities, boots it in Amiberry, waits for the configured timeout, extracts
the result files with `xdftool`, and returns their text to the test.

Keep result output deterministic and include an explicit `PASS` marker. A
test should validate observable behavior, not only that Amiberry started.
