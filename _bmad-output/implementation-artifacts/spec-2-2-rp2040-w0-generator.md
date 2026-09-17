---
title: 'Story 2.2 first slice: RP2040 W0 stimulus generator'
type: feature
created: 2026-09-17
status: done
baseline_commit: fdf7ba3d0193a2b0c58f21edbd034dcef1ed014f
firmware_baseline_commit: eceaa5447d922c65ccb258b72514206e9f1fe135
review_loop_iteration: 0
context:
  - docs/agent-test-policy.md
---

<frozen-after-approval reason="User explicitly requests generator implementation; existing story has no routine approval checkpoint">

## Intent

**Problem:** W0 is wired and the USB analyzer is detected, but there is no RP2040 stimulus firmware to validate with it. Implement the generator before touching RP2350 firmware.

**Approach:** Extend the Story 2.1 bridge with an isolated RP2040 lab target, shared APIO-authored instructions tested under epio, explicit USB run/stop control, a bounded slow pattern and copy/paste capture instructions. Build and verify software now; identify the correct board before any load. Hardware observations must be distinguished from test/build results.

## Boundaries & Constraints

**Always:** Work in the existing bridge. GP2–5 carry D0–3; GP6 is /AS. Physical analyzer CH1–4 observe data and CH8 observes /AS (sigrok D0–3/D7). Pins are inputs before explicit run; at stop return /AS high then release pins. Use APIO encoding, no RP2350 MMIO on RP2040. Tests precede waveform implementation. Finite runs and timeout/disconnect cleanup. Keep current RP2350 and host presets working. Preserve pinned dependencies and policy guard. No writes outside the identified generator. Report actual checks and remaining physical evidence.

**Ask First:** Resolve USB identity before replacing existing device firmware; exact unknown clone flash configuration must not be assumed. Routine implementation is already authorized.

**Never:** ESP project, FujiBus/link protocol, final mailbox ABI, .pio files, RP2350 firmware changes, autonomous output on boot, unbounded signal run, hardware timing claims from epio.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
| --- | --- | --- | --- |
| Idle | Boot or USB enumeration | GP2–6 released; status/help available | No automatic run |
| Burst | Explicit valid run | Known ascending four-bit sequence, setup before /AS low, hold through low, deassert between samples, bounded completion | Report generated count and nominal clock timing |
| Stop | Explicit stop while active | /AS high before release, bounded stop latency | No stuck waveform |
| Fault | USB disconnect or deadline | Stop and release, reset run state | Report aborted status when console returns |
| Invalid | Unknown/oversized command or run while busy | No new waveform | Bounded parser, explicit error |
</frozen-after-approval>

## Code Map

- `repos/fujinet-nio/bridges/rp2350-zorro/CMakeLists.txt`, `CMakePresets.json`, `cmake/host.cmake`, `scripts/bootstrap.py`: existing isolated modes/locked SDK/apio/epio; add stimulus mode with separate cache.
- `.deps/apio/include/apio.h`: instruction encoders are usable independently; hardware macros use RP2350 registers and must not initialize RP2040.
- `.deps/epio/include/epio.h`, `tests/test_capture.c`: native harness style, checks active in Release, emulator GPIO observations; source bridge dependencies stay unmodified.
- `src/capture_program.{c,h}`: read-only existing DUT fixture; no DUT work in this slice.
- `tools/build/nio_build/tasks.py`, `tools/build/tests/test_rp2350_tasks.py`: reusable compiler discovery/bootstrap/preset pattern.
- `docs/story-2-2-experiment-plan.md`: preserve broader staged gates; this slice partially delivers E0–E3 only.

## Tasks & Acceptance

**Execution:**
- [x] Firmware owner: `lab/rp2040/` shared instruction builder and RP2040 SDK loader/USB executable; explicit finite run, status/help/stop and bounded parser/state machine. Select conservative clone-compatible configuration without asserting unknown flash identity; RAM firmware is acceptable for this first test.
- [x] Firmware owner: `tests/feasibility/` native epio waveform tests and portable command/state tests; record red then green, output values/timing/setup/hold, stop/rearm and invalid commands.
- [x] Firmware owner: CMake/bootstrap integration and tooling coverage, host Debug/Release and separate stimulus ELF/UF2, existing RP2350 firmware regression build.
- [x] Workspace owner (root agent): add discoverable `rp2040-stimulus` build command and focused tests; build never loads/starts devices.
- [x] Firmware owner: `docs/rp2040-generator.md` and README link, exact build/load/USB/capture commands, expected analyzer pattern, finite run timing and known limits. No requirement to implement a two-board runner yet.
- [x] Root agent: identify USB target before load; retain observed hardware results if available, otherwise exact user load/run procedure and named blocker. Update experiment progress and implementation record without closing Story 2.2.

Owners are working concurrently. Firmware implementer owns only bridge files; root owns workspace task code, spec and physical device interaction. Do not revert other edits; do not commit until root coordinates acceptance.

**Acceptance Criteria:**
- Given clean dependencies, when host presets and stimulus build run, then behavioral tests and RP2040 ELF/UF2 succeed with no first-party text PIO and no DUT source change.
- Given an identified RP2040 and explicit run, when flashed/loaded and captured, then the documented independent waveform oracle can validate data and /AS; if physical execution awaits user action, record it as unverified, never a timing pass.
- Given workspace listing/help, when requested, then the generator build and artifact locations are discoverable without affecting default workflows.

## Spec Change Log

## Design Notes

Prefer a slow finite 0..15 pattern (a single 16-assertion burst suffices), with distinct setup/low/hold intervals and idle high /AS. PIO clocks edges; USB never paces them. The native test consumes exactly the emitted words used by the SDK loader. No assertion of upstream RP2040 apio initialization support. Scope is generator bring-up, not all future parameter sweeps or DUT capture. Candidate seven-word program: SET X15; MOV pins,!X delay9; SET /AS0 delay9; SET /AS1 delay8; JMP X-- to MOV; IRQ0; parking JMP. OUT_BASE2/COUNT4 and SET_BASE6/COUNT1 at 100 kHz yield 100us setup/low/hold, to be verified by tests. Configure RAM-only RP2040 UF2 if clone flash identity remains unknown.

## Verification

Source `scripts/env.sh` first. Firmware: bootstrap host; configure/build/test both host presets; configure/build stimulus-rp2040 and firmware with local ARM toolchain; `python3 scripts/check_pio_policy.py`. Workspace: `PYTHONPATH=tools/build:tools python3 -m unittest discover -s tools/build/tests -v`; `scripts/build.sh rp2040-stimulus`; `scripts/build.sh --explain rp2040-stimulus`. Both owners: `git diff --check`. Physical: identify generator, load only it, query status, arm a bounded waveform and capture fx2lafw D0–3/D7 at an adequate sample rate; otherwise record pending steps.


## Implementation verification record

Workspace tests were added first: generator action/listing tests failed for the
missing `rp2040-stimulus` task, then passed with the implementation. Final
`PYTHONPATH=tools/build:tools python3 -m unittest discover -s tools/build/tests -v`
after `source scripts/env.sh`: 20/20 passed. Actual
`scripts/build.sh rp2040-stimulus` and `--explain rp2040-stimulus` passed; build
performs no hardware operation.

Firmware native Debug and Release each passed all four CTest registrations:
capture, stimulus, tooling and PIO policy. Both RP2040 stimulus and existing
RP2350 firmware configure/build succeeded with locked dependencies and ARM GNU
14.2.Rel1. RP2350 capture sources remain unchanged. Source-collector execution
with output paths redirected to temporary files confirmed the bridge remains
excluded; pre-existing checked-in generator drift was not changed.

Test-first stimulus started with missing implementation symbols (red). A temporary
shortened /AS delay then failed the independent waveform assertion; restored
source passed. Review mutations to shared output-pin configuration and to
flush-after-greeting ordering also failed behavioral checks, then unmodified
Debug/Release tests passed. Epio rearm recreates the model because its public
API lacks SM restart; this models initialization but does not claim to execute
the SDK reset implementation or prove electrical release.

Three review layers found and resolved configuration drift and USB session
coverage gaps. Shared register construction now feeds firmware and emulator;
TinyUSB session epochs, atomic bounded console iterations and fake-queue tests
cover reconnect races, ready-greeting order and full transmit buffers. Added
boundary-time and repeated-cleanup tests. Re-review found both original gaps
resolved without a concrete new regression. GPIO high impedance and numerical
abort latency remain physical limitations, not fake native passes. Corrected
stale USB address examples and restored transport constraints in the epic cache.

Hardware: two initial 1 MHz captures passed an independent trace checker, each
with 16 values 0–15, 100us low/setup/hold and 300us assertion spacing. These captures
predate the final USB hardening and are explicitly identified by artifact hash in
the owning evidence report. The checker also rejected injected wrong-data and
short-pulse trace mutations. Final image SHA-256:
`3ce6a0f7f5962e0fad13b73bffd9b8b43bb4611bd841de1d656d9c5c2c6fb1a4`.
Final-image physical checks passed: two full bursts; partial command across DTR reconnect plus malformed commands produced no assertions; scripted stop ended after four samples; following run restarted at zero. See the owning evidence report for hashes and trace limitations. One analyzer-busy capture attempt was excluded and recorded. Raw USB transcripts were normalized from CRLF to LF to satisfy whitespace checks.


## Suggested Review Order

- Start with the user procedure and observed waveform contract.
  [rp2040-generator.md:1](../../repos/fujinet-nio/bridges/rp2350-zorro/docs/rp2040-generator.md#L1)
- Inspect shared PIO instructions/configuration and bounded USB session handling.
  [stimulus_program.c:1](../../repos/fujinet-nio/bridges/rp2350-zorro/lab/rp2040/stimulus_program.c#L1)
  [stimulus_control.c:1](../../repos/fujinet-nio/bridges/rp2350-zorro/lab/rp2040/stimulus_control.c#L1)
- Compare physical evidence with native coverage and explicit measurement limits.
  [report.md:1](../../repos/fujinet-nio/bridges/rp2350-zorro/docs/feasibility/results/2026-09-17-generator/report.md#L1)
  [test_stimulus.c:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/test_stimulus.c#L1)
- Check discoverability without implicit flashing or signal generation.
  [tasks.py:115](../../tools/build/nio_build/tasks.py#L115)
