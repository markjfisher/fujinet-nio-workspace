# Atari public-library size measurement

From the workspace root:

```sh
export NIO_WORKSPACE="$PWD"
source "$NIO_WORKSPACE/scripts/env.sh"
python3 integration-tests/atari-sio/library-size/measure.py \
  --archive repos/fujinet-nio-lib/build/fujinet-nio-atari.lib \
  --output test-evidence/atari-library-size-current
```

Use a new or empty output directory for each measurement. Nonempty output
directories are rejected so failed or stale results cannot be mistaken for a
fresh run. The selected archive is copied to `selected-archive.lib` in the output
directory before linking, and all clients link that preserved copy.
The script recompiles the unchanged production `fnaccept.c`, a minimal Clock
client, and an empty C control with the same `-Osir -O` flags and Atari linker
configuration. All start at `$0D00`. It retains objects, XEX, maps, labels and
`measurement.json`, including toolchain revision/version, archive and XEX SHA-256,
each repository's HEAD, dirty status and tracked-diff digest. The input hash
manifest covers the client sources, public/internal headers, library sources and
build rules, linker configuration, measurement helpers, compiler/linker binaries
and Atari C runtime archive. HEAD alone does not identify an uncommitted build;
the saved archive digest identifies exactly what was linked, while source hashes
record the working-tree inputs observed at measurement time.
It rejects a map whose module attribution does not sum to its segment totals.

`linked_code_data_bytes` is CODE + RODATA + DATA. `main_footprint_bytes` includes
STARTUP, ONCE, CODE, RODATA, DATA and BSS. `total_ram_bytes` additionally includes
the linked zero page, the unchanged 2 KiB C stack reservation, and fnaccept's
384-byte fixed result/Disk buffer region `$0B00–$0C7F`. The Atari OS hardware
stack, screen, DOS and OS workspace are shared environment costs, not additional
library reservations. The linker exposes 126 bytes of ZP allocation space;
the original programs allocate 26 bytes (compact allocations are listed below). Stack reservation is a bound, not
measured high-water usage. Live acceptance verifies its runtime floor `$941F`.

Library cost is the sum of **linked library archive member** segments, reported
separately from application and cc65 runtime members. The Clock-versus-empty
comparison also isolates runtime dependencies introduced by this minimal client.
For fnaccept, extra runtime versus empty includes both application and library
demands and must not be attributed entirely to NIO. A change in the exact linked
library members remains an unambiguous incremental library measurement.

## Original baseline (2026-10-25)

Workspace `a25fc1ee9c33e2acdbbd5274a7fd4680ce3af024`, library
`86431220c78ffbdb40cbf1596f2b394fef3e8801`, applications
`5721eff1df32470046994550629f305bb8196ff9`. Original archive and all measured
artifacts: `test-evidence/atari-library-size-baseline/`.

| Bytes | Empty C | Minimal Clock | fnaccept |
| --- | ---: | ---: | ---: |
| XEX | 264 | 3,521 | 18,584 |
| CODE | 100 | 3,334 | 18,242 |
| RODATA | 0 | 16 | 170 |
| DATA | 41 | 48 | 49 |
| BSS | 5 | 1,120 | 1,315 |
| Zero page | 26 | 26 | 26 |
| STARTUP + ONCE | 111 | 111 | 111 |
| Main occupied span | 257 | 4,629 | 19,887 |
| Stack reservation | 2,048 | 2,048 | 2,048 |
| Fixed app workspace | 0 | 0 | 384 |
| Total RAM | 2,331 | 6,703 | 22,345 |
| Linked NIO members, all segments | 0 | 3,973 | 13,126 |
| Linked runtime, all segments | 279 | 644 | 1,153 |
| Linked application, all segments | 4 | 38 | 5,634 |

Main occupied half-open ranges are `$0D00–$0E01`, `$0D00–$1F15` and
`$0D00–$5AAF`, respectively. Minimal Clock adds 4,372 bytes of total RAM over
empty C: 3,973 library bytes, 365 additional runtime bytes and 34 application
bytes. fnaccept links 11,984 library CODE bytes, 16 RODATA, 8 DATA and 1,118 BSS.
Its largest library CODE members are Disk (2,708), read/write (1,505), packet
read/write builders (927), open packet builder (734), and open (726).
The already-assembly native SIO transport contributes 585 CODE, 17 BSS and 6 DATA.

## Live acceptance commands

After rebuilding the selected production Atari archive and `fnaccept.xex`:

```sh
make -C repos/nio-core-apps -f makefiles/build.mk TARGET=atari fnaccept
python3 integration-tests/atari-sio/run_boot_acceptance.py \
  --public-api-clock --write-evidence --json
python3 integration-tests/atari-sio/run_boot_acceptance.py \
  --public-api-clock-altirra-embedded --write-evidence --json
```

Run each remaining scenario separately with `--public-api-rejected-w-recovery`,
`--public-api-malformed-r-recovery`, `--public-api-interrupted-r-recovery` and
`--public-api-reset-recovery`, then repeat those four with `-altirra-embedded`
appended to the option. Each run independently validates live guest state,
actual native wire traffic, core dispatch counts and backing-store effects.

## Baseline live verification

All ten baseline runs passed with `ADP!` on 2026-10-25. Normal runs used the
original production XEX before implementation changes. Recovery runs executed
the unchanged runner with only `PUBLIC_API_CLOCK_XEX` redirected in memory to
the saved baseline XEX (and its sibling map); no runner or guest behavior was
changed. Exact logs, commands and evidence paths are retained in
`test-evidence/atari-library-size-baseline/{run_baseline_recovery.py,acceptance-summary.json}`.

| Adapter | Normal | Rejected W | Malformed R | Interrupted R | Reset |
| --- | --- | --- | --- | --- | --- |
| Production NetSIO | pass | pass | pass | pass | pass |
| Embedded AltirraSDL | pass | pass | pass | pass | pass |

## Compact result (2026-10-25)

Same source, compiler, flags and linker configuration as the baseline.
Negative changes mean bytes saved. RAM includes code, static storage, zero page
and the unchanged reservations described above.

| Client / metric | Original bytes | Compact bytes | Change bytes | Change |
| --- | ---: | ---: | ---: | ---: |
| Minimal Clock: XEX | 3,521 | 2,318 | -1,203 | -34.2% |
| Minimal Clock: CODE + RODATA + DATA | 3,398 | 2,195 | -1,203 | -35.4% |
| Minimal Clock: total RAM | 6,703 | 5,524 | -1,179 | -17.6% |
| Minimal Clock: linked NIO members | 3,973 | 2,954 | -1,019 | -25.6% |
| fnaccept: XEX | 18,584 | 16,114 | -2,470 | -13.3% |
| fnaccept: CODE + RODATA + DATA | 18,461 | 15,991 | -2,470 | -13.4% |
| fnaccept: total RAM | 22,345 | 19,933 | -2,412 | -10.8% |
| fnaccept: linked NIO members | 13,126 | 10,713 | -2,413 | -18.4% |

| Segment / reservation | Clock original → compact | fnaccept original → compact |
| --- | ---: | ---: |
| CODE | 3,334 → 2,131 | 18,242 → 15,772 |
| RODATA | 16 → 16 | 170 → 170 |
| DATA | 48 → 48 | 49 → 49 |
| BSS | 1,120 → 1,138 | 1,315 → 1,361 |
| ZEROPAGE | 26 → 32 | 26 → 38 |
| C stack reservation | 2,048 → 2,048 | 2,048 → 2,048 |
| fixed app workspace | 0 → 0 | 384 → 384 |

Compact occupied main ranges (half-open): clock `$0D00–$1A74`, fnaccept `$0D00–$5137`.
Zero-page allocations grow from 26 to 38 bytes; BSS also grows slightly for explicit
assembly scratch/parameter blocks. The reported RAM reduction comes from code
savings, not from hiding those reservations. The two 512-byte packet buffers
remain unchanged.

The final measurement artifacts are in `test-evidence/atari-library-size-final/`.
Fresh measurements with saved archives and full working-tree provenance are in
`test-evidence/atari-library-size-{original,compact}-provenance/`. The selectable
original backend reproduces all three saved baseline XEX files byte for byte;
the compact provenance run reproduces all three final XEX files byte for byte.
Archive SHA-256 for that compact run is
`435fc39a9c86a630938c946f573594272edec287741a8b79829c861a25137d3c`.
The original backend is reproducible using
`make -C repos/fujinet-nio-lib atari ATARI_BACKEND=original`; select
`ATARI_BACKEND=compact` to restore the default.
Implementation details and the runtime-free assembly parameter-block ABI are in
`repos/fujinet-nio-lib/docs/atari/compact-library.md`.

## Acceptance and regression evidence

The original baseline and compact build each pass all five scenarios on both
production NetSIO and embedded AltirraSDL. Every final row reports `ADP!`,
continued execution, valid memory bounds and the expected independently
observed wire traffic, core dispatches and persistent File/Disk effects.
Q remains maximum 512, flags zero and PROC not advertised.

Evidence directories below are relative to `test-evidence/`.

| Adapter | Scenario | Final compact evidence |
| --- | --- | --- |
| netsio | clock | `atari-sio-public-api-clock-20261025-122826-6ndfxow1/public-api-clock` |
| netsio | rejected-w-recovery | `atari-sio-public-api-rejected-w-recovery-20261025-122834-k8sdfktc/public-api-clock` |
| netsio | malformed-r-recovery | `atari-sio-public-api-malformed-r-recovery-20261025-122844-5vt3z9vw/public-api-clock` |
| netsio | interrupted-r-recovery | `atari-sio-public-api-interrupted-r-recovery-20261025-122853-z5fm509a/public-api-clock` |
| netsio | reset-recovery | `atari-sio-public-api-reset-recovery-20261025-122902-4rbe8a0q/public-api-clock` |
| embedded | clock | `atari-sio-public-api-clock-altirra-embedded-20261025-122911-p95vketg/public-api-clock-embedded` |
| embedded | rejected-w-recovery | `atari-sio-public-api-rejected-w-recovery-altirra-embedded-20261025-122919-4cnksk0u/public-api-clock-embedded` |
| embedded | malformed-r-recovery | `atari-sio-public-api-malformed-r-recovery-altirra-embedded-20261025-122928-6piosasi/public-api-clock-embedded` |
| embedded | interrupted-r-recovery | `atari-sio-public-api-interrupted-r-recovery-altirra-embedded-20261025-122937-x1iztis9/public-api-clock-embedded` |
| embedded | reset-recovery | `atari-sio-public-api-reset-recovery-altirra-embedded-20261025-122945-ula9_g9q/public-api-clock-embedded` |

Baseline results and exact saved archive: `test-evidence/atari-library-size-baseline/`.
Fresh measurements with full input provenance and retained archives:
`test-evidence/atari-library-size-original-provenance/` and
`test-evidence/atari-library-size-compact-provenance/`. The selectable original
reproduces all three saved baseline XEX files byte-for-byte. The compact
provenance rerun reproduces all three final measured XEX files byte-for-byte.

The committed library measurement is retained at
`test-evidence/atari-library-size-committed/`; all three XEX images remain
byte-identical to final acceptance. Its archive SHA-256 is
`f870033afa39b9170ddb12deb9931f660f7e2ca3068d63e3ac14f182cbadac26`.
The earlier provenance archive predates review-only layout assertions; its
archive hash differs while its linked client images are identical.

Final regression checks: complete library `make check` passed for all configured
targets; the compact suite passed 13,137 differential 6502 checks, runtime-free
assembly execution, and 128 transport/recovery/capability checks. The workspace
fixture/runner suite passed 65 tests. An ar65/od65 export audit found all 103
original `fn_*` exports in the compact archive. Review fixes also verify that
compact tests preserve an explicitly selected original canonical archive.
