---
title: Machine-local generator bench enrollment
type: feature
created: 2026-09-17
status: done
review_loop_iteration: 1
baseline_commit: b64f5ec60ea27c098dd25c3df7d488606baf7439
context: [docs/agent-test-policy.md]
---

## Intent

User asks whether USB IDs differ on another PC, which assumptions are hardcoded,
and wants another person to set up a compatible bench without editing source.
Separate universal RP2040 USB mode IDs from per-board flash identity and optional
analyzer selection. Keep experiment waveform/wiring requirements fixed. Current
runner is Linux-specific; do not claim Windows/macOS support or arbitrary boards.
Implement within existing generator runner/setup, not a new project. No routine
approval checkpoint and no live USB activity in this implementation turn.

## Boundaries

Always retain intended-board verification before RAM load, ambiguous-device refusal,
physical USB path re-enumeration and matching session checks. Never use EEEE RAM
serial as identity, select first arbitrary device, alter USB class IDs to accept
RP2350, write flash, auto-install permissions, invoke sudo, change waveform/pins,
or falsely claim cross-platform hardware validation. Local board config is
ignored and persistent outside build outputs; checked-in manifest has no personal
flash ID. Fresh clone must have no inherited private board selection.

## Code Map and ownership

Worker owns bridge tests/feasibility/experiment.py, test_experiment.py,
generator-check/experiment.json and run.sh if needed, plus any supporting profile
module/test. Root owns README/docs, .gitignore, this spec and current user's local
profile migration. You are not alone; preserve others' edits. No commits or live
hardware commands; use external-boundary fixtures only.

Known symbols: main stages doctor/build/load/run/analyse/all; validate_info checks
picotool RP2040 type plus 16hex flashID; load validates RAM artifact then selects
2e8a:0003, reads picotool info, RAMloads then follows physicalport 2e8a:000a.
validate_session binds flashID/ELFhash/bootID/deviceinstance. doctor reads sysfs,
serial, fx2lafw scan. parse analyzer allows fx2lafw[:conn=BUS.ADDRESS]. GPIO2..5data,
GPIO6strobe, analyzerD0..3/D7 and 1MHz are fixed waveform assumptions, not user
profile knobs. Current main uses expected_flash_id in manifest; tests have literal
benchfixtures. source_identity includes manifest but currently board identity
belongs there; separate physical config so build/offlineanalyse need no enrollment.
Generator localprofile desired at bridge .bench/generator-check.json; profile path
selectable --bench FILE. Session stays build/feasibility/generator-check/session.json.

## Tasks and acceptance

- [x] Remove personal flash ID from shared manifest; add versioned strict local
  profile schema with generator_flash_id (normalized 16hex), analyzer driver (`fx2lafw` only for now); no persisted USB bus address/tty/path.
  Optional --usb-path is transient selection only. --analyzer overrides profile
  for one run; don't persist a scan-derived address silently. Profile atomically
  saved and existing profile not overwritten without explicit interactive choice.
- [x] Add configure stage to generator starter. Requires built pinned USBpicotool
  (actionable build instruction if absent); bounded BOOTSEL discovery, correct
  RP2040 type + readable non-placeholder flash ID, refuse ambiguous devices unless
  --usb-path selected. Print discovered identity/physicalpath and userconfirms
  enrollment interactively before saving. Reads info only, never loads/runs outputs.
  Prefer reuse discovery/info helpers with load to avoid divergent checks.
- [x] Default all after softwarebuild/doctor: if no profile, guide configuration
  while in BOOTSEL, save only on confirmation, then load that same identifiedboard
  with normal revalidation. Explicit load/run without profile fails with concrete
  configure instruction (no implicit arbitrary identity). Offline build/analyse/help
  and dry-run work without profile. doctor displays configured identity or missing
  profile guidance, USB type IDs meaning and current detectedpaths. Invalid profile
  fails before hardware/load; no silently accepting personal manifest identity.
- [x] Profile identity used by load/run and retained with physical evidence; sessions
  bound to selected profile identity. Changing profile board invalidates oldsession;
  moving USB port or machine requires reload. Preserve hardware provenance separated
  from build identity; no cross-board confusion when profile changes duringprompt.
- [x] Tests real configure orchestration fakeexternal boundaries: success, wrongtype,
  missing/placeholderID, ambiguous, cancellation/nooverwrite, re-enumeration during
  confirmation, malformedprofile/noeffects, differentprofiles/sessionmismatch,
  missingprofileofflinebuild/help/analyse, defaultall initial enrollment ordering.
  Keep all current load/run and optimized acceptance tests. No test uses realUSB.
- [x] Root docs: concise first-clone Linux setup flow, software/USBpermissions/board
  enrollment distinction, portability table (VIDPID stable bymode, flashID perboard,
  addresses dynamic, fixedpins/waveform, analyzerfamily, native tools vs optional
  Linuxx86 compiler installer, Linux/sysfs/termios + systemdseat rule restrictions).
  Keep standalone CLI/rule installation as already documented; no system install.

Given new compatible Linuxhost, initial run builds and prompts for its own RP2040
without editing tracked files. Given existing valid profile, sameworkflowverifies
that board. Given unsupported host/hardware, diagnostics/docs make supportlimits
clear, not automatic broad claims. Given user currentboard profilemigration, root
may seedignoredprofile from established prior verified flashidentity without any
hardware action; clearly record this as migration, not fresh enrollment evidence.

## Verification

After source scripts/env.sh: Python runner tests normal/-O, native Debug/Release
CTest via generator-check/run.sh build (unchanged RAMfirmware, loader plus newhost
regressions), shellsyntax and help/dryrun from /tmp withno localprofile, doclinks,
manifest hasnopersonalID, profileignored, gitdiffchecks. No live configuration,
load or capture. Record exact commands/results; commit bothowners, neverpush.


## Review and verification results

Profile enrollment now uses a separate flock lock for final compare/publication,
atomic creation/replacement, temporary-file cleanup covering write/fsync failures,
and directory fsync after publication. An error after publication reports failure
without claiming rollback; the new complete profile may already exist. Offline
build/analyse ignore unrelated profiles, while physical stages reject invalid
profiles before hardware operations and provide concrete recovery guidance.
Enrollment requires an interactive terminal early, quotes path-containing commands,
and previews resolved bench/identity/analyzer/USB selection in dry-run output.

Follow-up reviews found the identity mismatch test and edge cases resolved. Tests
include a different valid RP2040 ID (not merely a rejected placeholder), confirmed
replacement/old-session refusal, two simultaneous writers, and publication errors.
All verification followed `source scripts/env.sh`:

- `python3 repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/test_experiment.py`:
  50 passed; same command with `python3 -O`: 50 passed.
- `repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/generator-check/run.sh build`:
  Debug/Release CTest 7/7 each, RAM firmware and USB picotool built successfully.
- Shell syntax, absolute starter `--help` and `--dry-run` from `/tmp` with an absent
  custom `--bench`, analyzer selector and USB path: passed, no enrollment required.
- Actual saved `w0-final-001.sr` analysed from `/tmp` while `--bench` points at
  malformed JSON: passed. Offline analysis is independent of physical selection.
- Python workspace checks: shared manifest has no personal board ID, migrated
  local profile matches established board identity, all portability/setup links
  resolve. `git check-ignore` confirms `.bench/generator-check.json` is ignored.
- `git diff --check` and `git -C repos/fujinet-nio diff --check`: passed.

Current user's local profile was seeded from the existing successful load session's
RP2040 `picotool_info` and flash ID, not from newly observed hardware. Existing
session/evidence was not rewritten. No live configure, load or capture was run;
first-run enrollment is verified with controlled external-boundary fixtures.
Permissions files were not installed/changed. Linux-only host support, supported
analyzer family and fixed waveform/wiring constraints are documented explicitly.

## Suggested Review Order

- Understand portable identifiers, initial setup and supported hardware/hosts.
  [bench-setup.md:1](../../repos/fujinet-nio/bridges/rp2350-zorro/docs/bench-setup.md#L1)

- Inspect enrollment, atomic profile publication and intended-board enforcement.
  [experiment.py:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/experiment.py#L1)

- Shared experiment expectations no longer select one person’s board.
  [experiment.json:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/generator-check/experiment.json#L1)

- Verify rejection, recovery and first-run orchestration independently of USB.
  [test_experiment.py:1](../../repos/fujinet-nio/bridges/rp2350-zorro/tests/feasibility/test_experiment.py#L1)
