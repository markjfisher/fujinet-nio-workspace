---
title: 'Repeatable and inspectable Story 2.2 experiments'
created: 2026-09-17
status: done
type: feature
baseline_commit: 80bac1ce511800f8ae1de1ada90a643c32a19fcb
review_loop_iteration: 1
context: [docs/agent-test-policy.md]
---

## Intent

User requires actual repository changes making hardware work independently runnable,
inspectable and controlled from a shell. Prior generator validation was bring-up,
not C1 completion. Repackage it before adding any DUT behavior. Implementation is
explicitly authorized; no routine confirmation checkpoint. Story 2.2 stays open.

## Boundaries

Preserve shared APIO/epio source, pinned builds, RP2350 source and existing firmware
behavior. No .pio, ESP, final ABI, unattended physical runs this turn, fabricated
matrix completion or sudo inside experiment stages. Keep RAM loading for this
slice; flash installation is authorized but unnecessary. Explicit user-directed
setup may install documented permissions separately; never install system policy
as a side effect of running an experiment. Build/test/analyse should work without
hardware. Load/run stages identify only the intended generator and explain their
operations. Never identify RAM firmware by the nonunique EEEE serial alone.

## Ownership and Code Map

Firmware worker owns ONLY `repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/`
runner Python/shell/tests and `cmake/host.cmake` test registration. Root owns docs,
C0-C10 manifests/readmes/starters, generator manifest/source relocation/CMake source
references, workspace records. You are not alone: preserve others' changes.
Existing `lab/rp2040/main.c`, `stimulus_control.c`, `stimulus.h` supply shared target
and USB commands run/stop/status/help. `stimulus_program.c` currently supplies
seven-instruction0..15waveform; root will move it to
`tests/feasibility/generator-check/src/stimulus_program.c` and update build sources.
`docs/feasibility/results/2026-09-17-generator/check_trace.py` and *.sr provide the
independent oracle and recorded captures; runner should own a reusable robust
oracle, not import evidence code by ad hoc absolute path. Inspect existing
CMakeLists, presets/bootstrap and source tests. Local USB-enabled picotool can be
built from `.deps/picotool` separately from build-only picotool. Workspace
`scripts/build.sh rp2040-stimulus` already builds target; native tests task exists.

## Interface and tasks

- [x] Root: generator-check/experiment.json, README, source; C0-idle through
  C10-real-bus folders with experiment.json/README/run.sh clearly unimplemented,
  preserving each matrix case and prerequisites. Root docs update story contract.
- [x] Worker: common `tests/feasibility/experiment.py`, generator-check/run.sh,
  meaningful offline `test_experiment.py`, CTest registration.
- [x] Worker: starter usable from any cwd, full interactive workflow by default;
  subcommands `doctor`, `build`, `load`, `run`, `analyse`, `all`. `--help` explains
  no side effects; `--dry-run` prints actions without devices/build/writes.
  `--output` is a fresh results directory for a physical run, `analyse` accepts
  an existing .sr. Use stdlib or pinned pyserial dependency, never mystery temp code.
- [x] Worker: doctor checks tools, pinned source requirements, USB/serial access
  and analyser contention with actionable diagnostics. Build uses bridge presets,
  host tests and pinned USB picotool; no firmware/source duplication. Load prints
  BOOTSEL instructions, waits boundedly for selected RP2040 flash identity, verifies
  picotool info before RAMload and verifies target type/ID, handles re-enumeration
  by physical USB path, saves identity+artifact hash session record. Do not reuse
  stale bus addresses or open arbitrary serial ports. Separate run uses persisted
  identity+physical path plus current firmware hash session record, requires
  explicit validated identity if no matching session, no standalone EEEE guessing.
- [x] Worker: run names intended pins, requires explicit Enter before outputs
  in interactive all/run, starts analyser first, checks acquisition failure before
  run command, handles disconnect/timeout/Ctrl-C with stop and child cleanup,
  retains failed outputs. Fresh-result/error accounting, strict waveform oracle
  with finite result, capture metadata/sample rate/channels validated, no Python
  assert for acceptance (must work under -O). Logs/JSON report distinguish transport,
  acquisition and waveform errors, never accept cached greeting as fresh completion.
- [x] Root: README/existing generator guide/Story2.2/epic/spec log link new canonical
  interface; record source maps and one-time permissions setup, no surprise sudo.

Manifests root supplies: id, title, status (implemented or planned), stage,
preset (`stimulus-rp2040`), target (`feasibility_stimulus`), expected_flash_id
(`754765170F445253`), data_gpio [2,3,4,5], strobe_gpio6, analyzer channels
D0,D1,D2,D3,D7, expected_values0..15, samplerate_hz1000000, pulse_us100,
period_us300, setup_hold_us100. Worker coordinate necessary schema additions.
C0-C10 starters call commonrunner with their manifest and fail explicitly before
any side effect when status planned. No fake sources for unimplemented experiments.

## Acceptance and edge cases

Given generator-check starter, `--help`, `doctor`, `build` and historical-capture
analyse are independently usable. Full run gives visible stages and waits for
BOOTSEL/explicit run with bounded cancellation. Given wrong board, ambiguous USB,
permission failure, busy analyzer, stale session, missing burst, wrong data/pulses,
unknown capture rate or aborted acquisition, fail accurately and retain evidence;
never flash DUT or claim pass. Given C0-C10, explain unimplemented requirements,
do no hardware/build work and return nonzero. Source is inspectable in each
implemented experiment, and shared sources are linked explicitly.

## Verification

Source scripts/env.sh. Firmware owner: native Debug/Release CMake+CTest including
new runner tests; actual `scripts/build.sh rp2040-stimulus` preserves build; analyse
both recorded final .sr captures and negative corrupt/truncated/metadata fixtures;
Python -O acceptance tests; shell syntax; policy and diff checks. Workspace docs
links, manifest coverage C0-C10, unchanged DUT source; no full unrelated builds.
Do not operate connected boards this turn: user asked to gain control of running
experiments. Explicitly report live starter orchestration as not hardware-tested.


## Results and review

Implemented the generator-check workflow and C0–C10 planned entry points. The
original capture remains generator equipment validation, not C1. No matrix case
or overall Story 2.2 is marked complete. No live hardware was operated in this
slice; new live orchestration still needs its first user-run bench validation.
The existing APIO waveform was relocated byte-for-byte and shared firmware is
unchanged. System permission rules are documented and validated, not installed.

Review corrections cover repeated DTR sessions, identity revalidation after Enter,
relative session paths, immutable loaded artifacts with build-time provenance,
attempted-command/partial-output logging, late acquisition errors, detailed
waveform failure evidence, offline report retention and prerequisite ordering.
Tests now exercise load/run orchestration with fake external boundaries, not
only helper parsers. Follow-up reviews cleared the original boundary findings;
the relative-session finding gained an explicit regression test.

Commands run after sourcing `scripts/env.sh`:

- `repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/generator-check/run.sh build`
  passed: native Debug/Release, RAM firmware and USB-enabled pinned picotool.
- In the bridge, `ctest --preset host --output-on-failure` and
  `ctest --preset host-release --output-on-failure`: 6/6 each, including 28 runner
  tests in normal Python and optimized `-O` mode, epio tests and policy checks.
- `scripts/build.sh rp2040-stimulus`: passed for the relocated source.
- Starter `analyse --capture` against both retained `w0-final-001.sr` and
  `w0-final-002.sr`: passed, 16 expected assertions each. Negative/malformed,
  incorrect-data and incorrect-timing cases pass rejection tests.
- `udevadm verify repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/69-nio-feasibility.rules`:
  one success, zero failures. `bash -n` for all twelve starters passed.
- Workspace Python checks: all eleven planned starters refuse from `/tmp`, local
  experiment README links resolve, CAP/story identities and dispatch checkpoints
  are preserved, relocated APIO is byte-identical, DUT/shared main are unchanged.
- Source collector `scripts/update_cmake_sources.py` exercised by importing and
  invoking `main()` with both output paths redirected into a temporary directory:
  bridge remains excluded. Avoided changing pre-existing generated-template drift.
- `git diff --check` and `git -C repos/fujinet-nio diff --check`: passed.

No unrelated firmware preset, product-wide suite or hardware pass is implied.
`code` is unavailable; review links below provide the navigation entry point.

## Suggested Review Order

**User control**

- Start with the staged, user-run procedure and expected measured result.
  [README.md:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/generator-check/README.md#L1)

**Matrix scope**

- Distinguish equipment bring-up from the eleven planned DUT experiments.
  [README.md:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/README.md#L1)

**Loading and acquisition**

- Inspect target verification, artifact identity and retained failures.
  [experiment.py:255](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/experiment.py#L255)

**Inspectable APIO**

- The existing waveform remains shared by firmware and epio.
  [stimulus_program.c:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/generator-check/src/stimulus_program.c#L1)

**Regression checks**

- Exercise actual orchestration through controlled external boundaries.
  [test_experiment.py:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/test_experiment.py#L1)

**Permission setup**

- Optional one-time access replaces ephemeral per-device ACL commands.
  [69-nio-feasibility.rules:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/69-nio-feasibility.rules#L1)
