---
title: 'Atari SpartaDOS X compatibility'
type: 'feature'
created: '2026-10-25'
status: 'in-progress'
baseline_commit: 'db1d11731a2c0d54f49ac5fd4a7f48feac60edb3'
review_loop_iteration: 0
context: ['docs/agent-test-policy.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Establish a reproducible SpartaDOS X environment and a safe lifecycle for the existing production Atari N: handler, with genuine BASIC READ, PUT and POST and return to DOS and BASIC.

## Boundaries & Constraints

**Always:** Prove unmodified SDX boots and works first. Use pinned, checksum-verified local inputs and offline deterministic builds; document provenance and licensing. Preserve existing drivers, the 3,072-byte permanent RAM ceiling, native $7F protocol, public Atari library, Epic 2 and configuration ATR boot contract. Record HATABS, MEMLO, resident integrity and memory through transitions. Exercise production NetSIO and NetworkDevice. Run MyDOS and DOS 2.5 regressions.

**Ask First:** A broad SDX driver rewrite.

**Never:** Fork the resident payload, change it without a demonstrated defect, redistribute third-party DOS binaries without permission, or expand to SpartaDOS 3.x, DOS 2.0S, hardware or unrelated firmware.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Clean boot | Verified unmodified SDX cartridge | Normal command processor and functioning commands | Report failure with evidence |
| Install | Existing drivers and SDX memory manager | N: safely registered, existing drivers preserved and permanent allocation protected | Fail safely if allocation or registration unavailable |
| BASIC networking | READ, PUT, POST fixtures | Production network operations succeed | Report exact failure |
| Transition | BASIC to command processor and back | N: remains registered and usable; resident integrity and allocation confirmed | Document demonstrated incompatibility and safe subset |
| SDX command | N: access from command environment | Characterize CIO versus native SDX integration | Report unsupported operations accurately |

</frozen-after-approval>

## Code Map

- `integration-tests/atari-sio/run_boot_acceptance.py` -- production NetworkDevice fixture and BASIC/SDX lifecycle acceptance.
- `integration-tests/atari-sio/probe_dos25_lifecycle.py` -- emulator keyboard, screenshots and memory snapshots.
- `integration-tests/atari-sio/boot-app/Makefile` -- production o65, streamed loader and BASIC fixtures.
- `integration-tests/atari-sio/DOS25.md` -- offline inputs and existing regressions.
- `repos/nio-core-apps/apps/platform/atari/resident/fnresident_o65_loader.s` -- streamed installer with SDX relocatable child and child-owned scratch buffers.
- Official SDX 4.51 project download at https://sdx.atari8.info/index.php?show=en_download_release; emulator image `SDX451_maxflash1.car` SHA-256 `e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3`. Site states all rights reserved. Local copy `/tmp/sdx451/SDX451_maxflash1.car`.
- Official programming guide https://sdx.atari8.info/sdx_files/4.51/SDX451_Programming_Guide.pdf describes SDX MALLOC and INSTALL; ordinary MEMLO changes alone do not establish permanent reservation.

## Tasks & Acceptance

**Execution:**
- [ ] `integration-tests/atari-sio/` -- establish clean and NIO-enabled SDX environments and extend existing acceptance and diagnostics, preserving offline reproducibility.
- [ ] `repos/nio-core-apps/apps/platform/atari/resident/` -- implement only the smallest SDX-specific installation adaptation justified by observed behavior.
- [ ] `integration-tests/atari-sio/` -- document source, startup, exact commands, measurements and limitations; execute targeted tests and regressions.

**Acceptance Criteria:**
- Given verified SDX media, when booted clean, then the normal command environment works.
- Given installed N:, when BASIC executes all three existing fixtures and returns to SDX and re-enters BASIC, then N: remains safely usable and measured memory and drivers are intact, or a demonstrated fundamental incompatibility and supported subset are recorded.
- Given deterministic local inputs, when builds are repeated offline, then artifacts are reproducible and source inputs unchanged.

## Verification

The final shared loader passed MyDOS READ after `source scripts/env.sh && make -C integration-tests/atari-sio/boot-app resident-o65-mydos-basic && python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1`. DOS 2.5 READ passed with `ATARI_RESIDENT_DOS=dos25 ATARI_RESIDENT_BASIC_ATR=/tmp/dos25-build-a/dos25-resident.atr python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1` in the same sourced environment. Earlier MyDOS and DOS 2.5 READ, PUT and POST regressions also passed.

The revised parent passed SDX PUT and POST with `ATARI_RESIDENT_DOS=sdx ATARI_SDX_CART=/tmp/sdx451/SDX451_maxflash1.car ATARI_RESIDENT_BASIC_ATR=/tmp/sdx-revised-determinism-a/sdx-fixture.atr ATARI_RESIDENT_BUILD_DIR=/tmp/sdx-revised-determinism-a`, using `python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-write --timeout 1` and `--resident-o65-basic-post --timeout 1` respectively.

**Commands and results:**
- `source scripts/env.sh` before builds and tests.
- `make -C integration-tests/atari-sio/boot-app test-resident-asm` — pass for existing non-SDX installer and resident controls.
- `python3 integration-tests/atari-sio/sdx-parent-child/test-allocation.py` — pass for permanent-budget limit and invalid wrapper reservations.
- With `parser="$PWD/integration-tests/atari-sio/boot-app/build/tools/basicParser-v12-0-ga877718/basicParser"`, run `make -C integration-tests/atari-sio/boot-app sdx-fixture SDX_CART=/tmp/sdx451/SDX451_maxflash1.car OUT=/tmp/sdx-revised-determinism-a TBXL_PARSER="$parser"` and again with `OUT=/tmp/sdx-revised-determinism-b`; `cmp /tmp/sdx-revised-determinism-{a,b}/sdx-fixture.atr` passed. Both revised fixture hashes are `e2e510147e017a95e2cb10f2518ac1cdd31d9cf29b8cbbc19a83a75e4a09a9f1`; cartridge unchanged.
- `ATARI_SDX_LIFECYCLE=1 ATARI_RESIDENT_DOS=sdx ATARI_SDX_CART=/tmp/sdx451/SDX451_maxflash1.car ATARI_RESIDENT_BASIC_ATR=/tmp/sdx-final-child-a/sdx-fixture.atr ATARI_RESIDENT_BUILD_DIR=/tmp/sdx-final-child-a python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1` — pass for two production READs, existing driver tables, HATABS, resident code and bounds through SDX/BASIC transitions.
- With the same SDX environment, `python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-write --timeout 1` and `python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-post --timeout 1` passed on the byte-identical parent/child fixture `/tmp/sdx-child-integrated.atr`.
- `python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py /tmp/sdx451/SDX451_maxflash1.car /tmp/sdx-child-cleaned.atr /tmp/sdx-child-noslot --case no-slot` — pass. The same probe passed `oom`, `missing-child`, `bad-magic`, `wrong-size`, and `repeat` against their corresponding fault fixtures; the exact fixture-generation commands are in `integration-tests/atari-sio/SDX.md`.
- Revised parent failure checks: for `case` in `oom` and `bad-magic`, `python3 integration-tests/atari-sio/sdx-parent-child/build.py /tmp/sdx-revised-$case.atr --resident-build /tmp/sdx-revised-determinism-a --fault $case`, then `python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py /tmp/sdx451/SDX451_maxflash1.car /tmp/sdx-revised-$case.atr /tmp/sdx-revised-$case-evidence --case $case` — pass. OOM was repeated with the console assertion and `/tmp/sdx-revised-oom-visible-evidence`; both failures visibly reported `N: INSTALL FAILED`. `python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py /tmp/sdx451/SDX451_maxflash1.car /tmp/sdx-revised-determinism-a/sdx-fixture.atr /tmp/sdx-revised-repeat-evidence --case repeat` — pass.
- `python3 integration-tests/atari-sio/sdx-parent-child/build.py /tmp/sdx-parent-child2.atr` followed by `python3 integration-tests/atari-sio/sdx-parent-child/probe.py /tmp/sdx451/SDX451_maxflash1.car /tmp/sdx-parent-child2.atr /tmp/sdx-parent-child2-evidence` — pass; 4,096-byte child allocation reclaimed while the 2,335-byte parent allocation survived BASIC/DOS transitions.
- Earlier MyDOS and DOS 2.5 READ/PUT/POST regressions passed; see `integration-tests/atari-sio/DOS25.md` for commands.

**Outstanding:** Coverage is limited to the documented SDX emulator profile; native SDX command integration with a live device remains uncharacterized. The parent/child installer is experimental and is not wired into the configuration ATR.

## Spec Change Log
