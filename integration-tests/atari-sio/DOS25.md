# DOS 2.5 resident experiment

The source is the enhanced-density ATR downloaded from
<https://apps.irata.online/Atari_8-bit/DOS/Atari%20DOS%202.5.atr>,
SHA-256 `6b90fcfc9ca1765bb9d6eb2d27b174287a5c2d619d910b4d60057db708fbcb2e`.
Retrieved 2026-10-25 from Irata Online; the original publisher and distribution rights were not independently verified. It contains FujiNet utilities and a pre-existing AUTORUN.SYS. The build copies
this exact image, removes only that AUTORUN from the clean-start baseline, and
adds the production streamed loader as AUTORUN.SYS, NIO.O65 and the three BASIC
fixtures to a second copy. It does not modify the downloaded source or the
configuration ATR. The image is not presented as an untouched Atari release.

The DOS 2.5-capable `atr` disk utility must be installed separately on PATH;
it was `/home/markf/.local/bin/atr` in these runs. The workspace environment
setup does not install it.
Each probe needs a new evidence directory and operates on a disposable ATR copy.
The lifecycle probe may exit nonzero after recording `reset-failed` when RESET
does not recover from the deliberately hung post-DUP OPEN. This is a recorded
limitation, not a passing reset assertion.

```sh
source scripts/env.sh
make -C integration-tests/atari-sio/boot-app resident-dos25-basic DOS25_SOURCE=/path/to/Atari-DOS-2.5.atr
python3 integration-tests/atari-sio/probe_dos25_lifecycle.py integration-tests/atari-sio/boot-app/build/dos25-clean.atr /tmp/dos25-clean --clean
python3 integration-tests/atari-sio/probe_dos25_lifecycle.py integration-tests/atari-sio/boot-app/build/dos25-resident.atr /tmp/dos25-lifecycle
python3 integration-tests/atari-sio/probe_dos25_lifecycle.py integration-tests/atari-sio/boot-app/build/dos25-resident.atr /tmp/dos25-normal-reset --reset-only
export ATARI_RESIDENT_DOS=dos25
export ATARI_RESIDENT_BASIC_ATR="$PWD/integration-tests/atari-sio/boot-app/build/dos25-resident.atr"
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-write --timeout 1
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-post --timeout 1
unset ATARI_RESIDENT_BASIC_ATR ATARI_RESIDENT_DOS
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1
```

The baseline reached BASIC READY with MEMLO `$1F8C`. Installed at
`$1F8C–$28A9`, the handler used 2,360 permanent bytes including zero page;
READ, PUT and POST passed the existing production NetSIO assertions, with
code and registration intact. The focused MyDOS READ regression also passed.

**Do not use N: after entering DUP.** DOS 2.5 loads DUP.SYS over
`$1F0C–$3305`, overlapping the handler. The observed resident allocation
changed on entering DUP while HATABS still pointed to `$255F` and MEMLO stayed
`$28AA`. Option B returned to BASIC READY but left the same corruption and
stale N: registration. In a separate reset directly from installed BASIC, warm RESET restored MEMLO
`$1F8C` and removed N: from HATABS; resident bytes remained but the handler
was no longer registered. A cold boot is the
safe way to reinstall it. These observations do not establish safe N: use
after DUP, and no DOS or OS structures are relocated to mask this conflict.

In an isolated local-disk run, entering `OPEN #1,4,0,"N:TEST"` after
returning from DUP produced no new READY or error on the screen within 600
frames; the sampled CPU PC was `$0056`. This is an observed hang, not a
network-service result (the isolated run had no NetSIO device). The earlier
READY remains visible on screen, so its presence alone does not prove the
OPEN returned. An earlier warm RESET after the hung OPEN returned to BASIC; a later run entered
Atari memory test instead and did not reach READY within 3,600 frames. This
path is not reliably recovered by warm RESET.

The reviewed runs retained clean boot evidence in `/tmp/dos25-review-clean`,
normal reset evidence in `/tmp/dos25-review-reset`, and DUP/OPEN evidence in
`/tmp/dos25-review-lifecycle-final`, including `reset-failed.json`, PNG and
resident byte dumps. An earlier failure screenshot is `/tmp/reset-now.png`. These temporary paths are local evidence,
not permanent artifacts.
