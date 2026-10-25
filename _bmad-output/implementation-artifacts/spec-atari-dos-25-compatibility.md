---
title: 'Atari DOS 2.5 compatibility'
type: 'feature'
created: '2026-10-25'
status: 'done'
baseline_commit: '404b31e64250afd4e930479ecff09bf4a5e37ebd'
review_loop_iteration: 0
context: ['docs/agent-test-policy.md']
---

<frozen-after-approval reason="User-specified scope">

## Intent

Establish reproducible Atari DOS 2.5 BASIC compatibility with the existing production CA65 N: handler, and measure its actual DUP.SYS and RESET lifecycle.

## Boundaries & Constraints

**Always:** Preserve native $7F, MyDOS acceptance, public library, resident safety and the 3,072-byte permanent RAM limit. Preserve media provenance and prove normal BASIC boot before adding N:.

**Never:** Fork the handler, alter the configuration ATR, redesign DOS or relocate arbitrary OS structures to force compatibility. Fix only small demonstrated packaging or installer issues.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected behavior |
| --- | --- | --- |
| Boot | Clean DOS 2.5 | Normal BASIC READY before installation |
| Startup | AUTORUN.SYS and NIO.O65 | Safe installation, HATABS and MEMLO reservation, intact resident code |
| BASIC | READ, PUT, POST | Existing production NetSIO fixture assertions pass |
| DUP | Enter menu and return to BASIC | Measure registration, memory and N: behavior; document any conflict |
| RESET | Emulator reset | Record observed path and resulting resident state without assuming warm persistence |

</frozen-after-approval>

## Code Map

- `integration-tests/atari-sio/boot-app/Makefile` -- existing MyDOS ATR, production streamed loader and tokenized BASIC fixtures.
- `integration-tests/atari-sio/run_boot_acceptance.py` -- real BASIC driver, retained memory and production NetworkDevice assertions.
- `repos/nio-core-apps/apps/platform/atari/resident/fnresident_o65_loader.s` -- production streamed loader; checks HATABS and allocates from MEMLO.
- `repos/nio-core-apps/apps/platform/atari/resident/README.md` -- production handler and 2,360-byte footprint.
- Atari DOS 2.5 owner manual documents AUTORUN.SYS before BASIC or DUP.SYS: https://www.atarimania.com/8bit/files/Atari_DOS_2.5%20_1050_Disk_Drive_Owners_Manual.pdf

## Tasks & Acceptance

**Execution:**
- [x] Establish a provenance-recorded DOS 2.5 ATR and prove clean boot.
- [x] Package the existing loader and module on a reproducible installation ATR.
- [x] Reuse BASIC NetSIO acceptance for READ/PUT/POST and inspect DUP entry, BASIC return, resident integrity and RESET.
- [x] Record commands, observations and limitations; run focused MyDOS regression and commit verified changes.

**Acceptance Criteria:**
- Given clean DOS 2.5 media, when booted with BASIC, then BASIC reaches READY.
- Given the installation ATR, when booted, then N: is registered safely and real BASIC READ/PUT/POST succeeds through production NetSIO.
- Given installed N:, when entering DUP and returning to BASIC, then measured behavior and any exact conflict are reported.

## Verification

- `source scripts/env.sh && make -C integration-tests/atari-sio/boot-app test-resident-asm resident-o65-mydos-basic`
- `source scripts/env.sh && python3 -m unittest discover -s integration-tests/atari-sio/tests -q`
- Run DOS 2.5 clean boot, BASIC READ/PUT/POST, DUP and RESET using the recorded acceptance commands, plus focused MyDOS BASIC regression.

Observed DUP corruption and post-DUP OPEN failure are documented in `../../integration-tests/atari-sio/DOS25.md`; the user explicitly accepts a verified limitation. The post-hang reset probe returned nonzero in the final run after entering the Atari memory test. All three BASIC NetSIO cases and the MyDOS READ control passed; clean boot, normal RESET, assembly and 65 Python tests passed. No submodule changes were required.

## Suggested Review Order

**Media and compatibility**

- Review provenance, observed lifecycle and reproduction commands.
  [DOS25.md:1](../../integration-tests/atari-sio/DOS25.md#L1)
- Derive installation media without modifying the source image.
  [make-dos25-atr.py:1](../../integration-tests/atari-sio/boot-app/make-dos25-atr.py#L1)

**Verification**

- Inspect the measured DUP and RESET lifecycle.
  [probe_dos25_lifecycle.py:1](../../integration-tests/atari-sio/probe_dos25_lifecycle.py#L1)
- Reuse BASIC and NetSIO acceptance with explicit DOS selection.
  [run_boot_acceptance.py:1365](../../integration-tests/atari-sio/run_boot_acceptance.py#L1365)
