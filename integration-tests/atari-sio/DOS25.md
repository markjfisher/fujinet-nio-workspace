# DOS 2.5 resident experiment

The local source is the single-density DOS 2.5 image retrieved on 2026-10-25 from [Internet Archive](https://archive.org/download/a8b_DOS_v2.5_1984_Atari/DOS_v2.5_1984_Atari.atr). Its six files match the Atari manual's distribution listing. This is a copy; its acquisition chain and identity with an original master are not established. A separate atrcopy enhanced-density image has the same boot sectors and utility files, but different configured DOS.SYS and DUP.SYS. The [AtariWiki source page](https://atariwiki.org/wiki/Wiki.jsp?page=Atari+DOS+2.5+Source+Code) reproduces a restrictive copyright notice; redistribution permission has not been established. Provision the ATR locally; do not commit it.

The clean image is an exact copy. The acceptance image adds AUTORUN.SYS, NIO.O65 and three tokenized BASIC fixtures with the repository-owned DOS 2 single-density sector writer. Neither the source nor the configuration ATR is modified. The build validates the source and the provisioned pinned BASIC parser before building, and never downloads either. The parser's release archive is checksum-verified by the provisioning script; its extracted executable is also verified at build time. Build output depends on the current production artifacts and toolchain.

SHA-256 of the source ATR: `c154f4d55330b2a5e197f21db07123835c877d5b8fae10694be811c3dd8bfa64`; boot sectors 1–3: `2711e0a94e6d23907ae43229c0486335ecc3cf216341830103b2d0149671b5be`. File content hashes (DOS sector links excluded):

| File | SHA-256 |
| --- | --- |
| DOS.SYS | `df65788b85204cf9a885b5aedc8617f05f6a0a3d506a63fd3072178c5c7b3b73` |
| DUP.SYS | `c2229629cd75c6ae3a39c7c9821ff3b76155d1079f0cbbcaf4e9d77553812b86` |
| RAMDISK.COM | `60703e93da9f565dc363621c7fa4c428914fcb63176fbeb7c5b13cea3dac0f8a` |
| SETUP.COM | `25c09a13527ef158b6d9c3742f358b209ac012291c9dbcc5df9bdc3cb2636ffa` |
| COPY32.COM | `5fd5b615248a5f34bef50d81bf9f723c9cc09e17dde97eecbfe38ad1a568cf07` |
| DISKFIX.COM | `99bca12ac60ca80d8cb6a38af4436b9f6681c35cf9a20595afddf019fcd7edac` |

Provision once with network access, then build offline. Choose unused output and evidence directories; probes write disposable copies.

```sh
source scripts/env.sh
curl -L 'https://archive.org/download/a8b_DOS_v2.5_1984_Atari/DOS_v2.5_1984_Atari.atr' -o /tmp/atari-archive-dos25.atr
printf '%s  %s\n' c154f4d55330b2a5e197f21db07123835c877d5b8fae10694be811c3dd8bfa64 /tmp/atari-archive-dos25.atr | sha256sum -c
python3 integration-tests/atari-sio/fetch_tbxl_parser.py --output "$PWD/integration-tests/atari-sio/boot-app/build/tools/basicParser-v12-0-ga877718/basicParser"
parser="$PWD/integration-tests/atari-sio/boot-app/build/tools/basicParser-v12-0-ga877718/basicParser"
# The clean target requires only the verified source; the resident target also builds fixtures.
make -C integration-tests/atari-sio/boot-app clean-dos25 DOS25_SOURCE=/tmp/atari-archive-dos25.atr OUT=/tmp/dos25-build-a
make -C integration-tests/atari-sio/boot-app clean-dos25 DOS25_SOURCE=/tmp/atari-archive-dos25.atr OUT=/tmp/dos25-build-b
make -C integration-tests/atari-sio/boot-app resident-dos25-basic DOS25_SOURCE=/tmp/atari-archive-dos25.atr OUT=/tmp/dos25-build-a TBXL_PARSER="$parser"
make -C integration-tests/atari-sio/boot-app resident-dos25-basic DOS25_SOURCE=/tmp/atari-archive-dos25.atr OUT=/tmp/dos25-build-b TBXL_PARSER="$parser"
sha256sum /tmp/dos25-build-{a,b}/dos25-{clean,resident}.atr /tmp/atari-archive-dos25.atr
cmp /tmp/dos25-build-{a,b}/dos25-clean.atr
cmp /tmp/dos25-build-{a,b}/dos25-resident.atr
python3 integration-tests/atari-sio/probe_dos25_lifecycle.py /tmp/dos25-build-a/dos25-clean.atr /tmp/dos25-standard-clean --clean
export ATARI_RESIDENT_DOS=dos25 ATARI_RESIDENT_BASIC_ATR=/tmp/dos25-build-a/dos25-resident.atr
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-write --timeout 1
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-post --timeout 1
unset ATARI_RESIDENT_BASIC_ATR ATARI_RESIDENT_DOS
make -C integration-tests/atari-sio/boot-app resident-o65-mydos-basic
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1
```

The two independent runs produced clean SHA-256 `c154f4d55330b2a5e197f21db07123835c877d5b8fae10694be811c3dd8bfa64` and resident SHA-256 `7c41036296015fc193d2dcf9c97d074a4fc3db2034b8b5922320da32f50e25e8`. The source hash remained unchanged. Clean BASIC reached READY with MEMLO `$1CFC`, compared with `$1F8C` for the previous FujiNet-modified enhanced-density image (a difference of 656 bytes). The prior image came from Irata Online, SHA-256 `6b90fcfc9ca1765bb9d6eb2d27b174287a5c2d619d910b4d60057db708fbcb2e`; its original publisher and rights were not independently verified.

With the standard image, the installed handler occupied `$1CFC–$2619`, MEMLO became `$261A`, and the READ, PUT and POST fixtures exercised production NetSIO with resident integrity assertions. The MyDOS READ regression also passed.

The following DUP findings are from that earlier FujiNet-modified image, not a fresh test of the standard image. The lifecycle probe may exit nonzero after recording `reset-failed` when RESET does not recover from the deliberately hung post-DUP OPEN.

**Do not use N: after entering DUP.** The previous image loaded its DUP.SYS over
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
