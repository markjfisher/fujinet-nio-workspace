---
title: 'Reproducible Atari DOS 2.5 test media'
type: 'feature'
created: '2026-10-25'
status: 'done'
baseline_commit: '48e440eb378fbf14c29b300420c99d6ab9feb56d'
review_loop_iteration: 0
context: ['docs/agent-test-policy.md', 'integration-tests/atari-sio/DOS25.md']
---

<frozen-after-approval reason="User-specified scope">

## Intent

Replace the legacy FujiNet-modified source with a provenance-documented standard DOS 2.5 distribution and offline reproducible clean and NIO acceptance ATRs. Verify real BASIC networking and baseline memory.

## Boundaries & Constraints

**Always:** Use pinned local inputs for normal builds; clearly distinguish verified facts, provenance limitations and redistribution status. Provision copyright-uncertain DOS media locally and checksum it. Build twice independently and compare both image hashes. Preserve the existing DUP incompatibility finding.

**Never:** Change production handler, firmware, native protocol, configuration ATR, or attempt a DUP fix. Do not silently download during build or commit third-party binary without verified rights.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected behavior |
| --- | --- | --- |
| Missing or changed media | Absent or wrong hash | Build fails without network access or modifying input |
| Clean build | Verified local standard distribution | Deterministic clean ATR boots to BASIC READY |
| Acceptance | Clean image plus production artifacts | Deterministic ATR passes real READ/PUT/POST over production NetSIO |
| Baseline | Clean and earlier legacy-derived DOS | Measure and document MEMLO |

</frozen-after-approval>

## Code Map

- `integration-tests/atari-sio/boot-app/Makefile` and `make-dos25-atr.py`: legacy image build, replace source and unmanaged ATR tool; MyDOS builds with dir2atr and checked-in MyPicoDOS.
- `integration-tests/atari-sio/probe_dos25_lifecycle.py`: clean boot and memory evidence.
- `integration-tests/atari-sio/run_boot_acceptance.py`: existing NetSIO BASIC fixture and assertions.
- `integration-tests/atari-sio/DOS25.md`: preserve DUP findings, replace legacy baseline and document provenance and commands.
- `repos/nio-core-apps/makefiles/boot-disk.mk`: separate config ATR, read only.
- Candidate local distribution `/tmp/atari-archive-dos25.atr`, SHA-256 `c154f4d55330b2a5e197f21db07123835c877d5b8fae10694be811c3dd8bfa64`, from https://archive.org/download/a8b_DOS_v2.5_1984_Atari/DOS_v2.5_1984_Atari.atr. Its six-file listing matches the Atari manual, but it is a single-density copy and archive does not establish acquisition chain or bit-exact original master; do not overclaim. AtariWiki https://atariwiki.org/wiki/Wiki.jsp?page=Atari+DOS+2.5+Source+Code reproduces a restrictive copyright notice; no redistribution permission established. A separate atrcopy enhanced-density image shares boot sectors and utilities but configured DOS.SYS/DUP.SYS differ; document this limitation.
- Existing `dir2atr` supports DOS 2.5 but is not workspace pinned; prefer a small repository-owned ATR manipulation implementation or a genuinely pinned managed tool. No unmanaged PATH dependency or hidden download.

## Tasks & Acceptance

**Execution:**
- [x] Implement deterministic offline clean and NIO image targets using checksum-verified local media and managed tools; test malformed or missing inputs and source preservation.
- [x] Record source, version, file/boot checksums, licensing conclusion, exact provisioning/build commands and output hashes; maintain prior DUP findings.
- [x] Test two independent builds, clean BASIC boot and MEMLO comparison, plus READ/PUT/POST via NetSIO and focused MyDOS regression.

**Acceptance Criteria:**
- Given verified local media, when two independent builds run offline, then corresponding output hashes match and source is unchanged.
- Given clean image, when booted with BASIC, then READY and MEMLO are recorded.
- Given acceptance image, when READ/PUT/POST BASIC fixtures execute, then existing production NetworkDevice and resident integrity assertions pass.

## Verification

- `source scripts/env.sh && python3 -m unittest discover -s integration-tests/atari-sio/tests -q`
- `source scripts/env.sh && make -C integration-tests/atari-sio/boot-app test-resident-asm resident-o65-mydos-basic`
- Record and run exact offline media build, two independent hash comparisons, clean boot probe and three NetSIO acceptance commands in `integration-tests/atari-sio/DOS25.md`; run focused MyDOS READ regression.

Final validation: independent builds produced clean `c154f4d55330b2a5e197f21db07123835c877d5b8fae10694be811c3dd8bfa64` and resident `7c41036296015fc193d2dcf9c97d074a4fc3db2034b8b5922320da32f50e25e8`. Clean BASIC reached READY at MEMLO `$1CFC`; the previous legacy-derived image used `$1F8C`. READ, PUT, POST and MyDOS READ passed, as did 69 Python tests and the resident assembly controls. The distribution candidate's original master provenance and redistribution permission remain unverified, as documented in DOS25.md.

## Suggested Review Order

**Media and provenance**

- Review source provenance, licensing limits, hashes and reproduction.
  [DOS25.md:1](../../integration-tests/atari-sio/DOS25.md#L1)
- Inspect offline targets and input protection.
  [Makefile:228](../../integration-tests/atari-sio/boot-app/Makefile#L228)
- Inspect the bounded DOS sector writer and checksum validation.
  [make-dos25-atr.py:1](../../integration-tests/atari-sio/boot-app/make-dos25-atr.py#L1)

**Verification**

- Review deterministic output and failure-case tests.
  [test_dos25_media.py:1](../../integration-tests/atari-sio/tests/test_dos25_media.py#L1)
