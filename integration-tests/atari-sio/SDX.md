# SpartaDOS X investigation

The experimental SDX 4.51 fixture installs the existing Atari N: resident with
an SDX-specific parent and a relocatable child. The parent is loaded into the
SDX programming guide's `$0400–$06FF` initialization scratch area and uses
`MALLOC` to reserve the resident. The child is loaded by `U_LOAD`; its code,
48-byte header buffer, 128-byte disk buffer, and result buffer occupy its own
SDX allocation. The child installs the unchanged production o65 payload into
the parent allocation, and SDX reclaims the child when it returns. The parent
sets `INSTALL` only after the child reports a complete, current success result. A child load error may abort the parent directly; SDX reports the error and releases the parent allocation. Other installer failures print `N: INSTALL FAILED`. The child rejects a payload
whose reservation differs from the size used to build the parent.

These results cover the existing `atari-nio-config-boot.yaml` Altirra profile
(800XL, PAL, 1088K RAM), SDX 4.51 Maxflash 1M cartridge and a direct
MyDOS-format fixture disk. Other memory configurations and installed drivers
have not been validated. The configuration ATR is not modified. Startup is
manual: at the SDX prompt enter `PARENT`, then `BASIC`. The fixture is an
experiment, not a general SDX distribution or an automatic installation path. A repeat invocation allocates before checking whether N: is already installed; it can therefore fail for lack of memory even when the existing installation remains usable.

The cartridge is `SDX451_maxflash1.car`, from the [official SDX 4.51 release](https://sdx.atari8.info/index.php?show=en_download_release), SHA-256
`e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3`.
The release page says all rights reserved. Provision it locally; it is not
redistributed here. The pinned BASIC parser and provisioning procedure are in
[DOS25.md](DOS25.md). Builds below are offline and verify both inputs.

The SDX fixture requires `nio-core-apps` commit
`4856d27250add3df63345e8ecda81be1e7305c8a`. The workspace pin remains at
the previously merged commit until this change is merged in that repository.
For local reproduction, check out that commit in `repos/nio-core-apps` before
running the commands below.

The official release form produced the emulator cartridge locally with:

```sh
curl -L -o /tmp/sdx-451.zip --data-urlencode 'path=sdx_files/4.51/' --data-urlencode 'zip_filename_prefix=sdx_451_' --data-urlencode 'hardware_version[]=.car' 'https://sdx.atari8.info/index.php?show=download'
mkdir -p /tmp/sdx451
unzip /tmp/sdx-451.zip -d /tmp/sdx451
printf '%s  %s\n' e400cba0ba7e20dc62c60019ab99de04d11f4a4fa841e20cacca7c44099940a3 /tmp/sdx451/SDX451_maxflash1.car | sha256sum -c
```

```sh
source scripts/env.sh
parser="$PWD/integration-tests/atari-sio/boot-app/build/tools/basicParser-v12-0-ga877718/basicParser"
cart=/tmp/sdx451/SDX451_maxflash1.car
make -C integration-tests/atari-sio/boot-app sdx-fixture SDX_CART="$cart" OUT=/tmp/sdx-final-child-a TBXL_PARSER="$parser"
make -C integration-tests/atari-sio/boot-app sdx-fixture SDX_CART="$cart" OUT=/tmp/sdx-final-child-b TBXL_PARSER="$parser"
cmp /tmp/sdx-final-child-{a,b}/sdx-fixture.atr
sha256sum /tmp/sdx-final-child-{a,b}/sdx-fixture.atr "$cart"
python3 integration-tests/atari-sio/probe_sdx_clean.py "$cart" /tmp/sdx-final-child-a/sdx-fixture.atr /tmp/sdx-clean
export ATARI_RESIDENT_DOS=sdx ATARI_SDX_CART="$cart" ATARI_RESIDENT_BASIC_ATR=/tmp/sdx-final-child-a/sdx-fixture.atr ATARI_RESIDENT_BUILD_DIR=/tmp/sdx-final-child-a
ATARI_SDX_LIFECYCLE=1 python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic --timeout 1
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-write --timeout 1
python3 integration-tests/atari-sio/run_boot_acceptance.py --resident-o65-basic-post --timeout 1
unset ATARI_RESIDENT_DOS ATARI_SDX_CART ATARI_RESIDENT_BASIC_ATR ATARI_RESIDENT_BUILD_DIR
```

On 2026-10-25 the revised parent fixture was rebuilt offline in `/tmp/sdx-revised-determinism-a` and `/tmp/sdx-revised-determinism-b`. The images compared equal and both had SHA-256 `e2e510147e017a95e2cb10f2518ac1cdd31d9cf29b8cbbc19a83a75e4a09a9f1`; the cartridge hash remained unchanged. The clean SDX boot reached D1:,
ran `DIR`, listed the fixture files and returned to the prompt. The READ, PUT,
and POST fixtures passed against production NetSIO and NetworkDevice. The READ
lifecycle run checked the initial operation, returned to DOS, re-entered
BASIC, and completed a second READ. HATABS, existing 12-byte driver dispatch
tables, resident code and memory bounds were checked during transitions. On
the tested profile the resident occupied `$1004–$1922`; BASIC MEMLO was
`$1BB5` and DOS MEMLO was `$2757`. The 2,335-byte SDX reservation includes an
alignment byte; with the 26-byte zero-page charge the permanent budget is
2,361 bytes.

A separate ownership probe allocates 2,335 bytes in the parent, fills them,
loads a 4,096-byte position-independent child, then checks the entire parent
allocation through BASIC and DOS. The observed child MEMLO rose from `$1922`
to `$2922` and returned to `$1922` before the parent marked itself resident:

```sh
python3 integration-tests/atari-sio/sdx-parent-child/build.py /tmp/sdx-parent-child.atr
python3 integration-tests/atari-sio/sdx-parent-child/probe.py "$cart" /tmp/sdx-parent-child.atr /tmp/sdx-parent-child-evidence
python3 integration-tests/atari-sio/sdx-parent-child/test-allocation.py
```

Failure fixtures exercise real SDX allocation failure, missing child, corrupt
resident image after allocation, changed resident allocation size, full HATABS,
repeated installation, and a successful installation followed by a missing child in the same session. Each uses a disposable disk and checks MEMLO and
HATABS; repeated installation also checks every resident byte:

```sh
for case in oom missing-child bad-magic wrong-size; do
  python3 integration-tests/atari-sio/sdx-parent-child/build.py "/tmp/sdx-$case.atr" --resident-build /tmp/sdx-final-child-a --fault "$case"
  python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py "$cart" "/tmp/sdx-$case.atr" "/tmp/sdx-$case-evidence" --case "$case"
done
python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py "$cart" /tmp/sdx-final-child-a/sdx-fixture.atr /tmp/sdx-no-slot-evidence --case no-slot
python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py "$cart" /tmp/sdx-final-child-a/sdx-fixture.atr /tmp/sdx-repeat-evidence --case repeat
python3 integration-tests/atari-sio/sdx-parent-child/failure-probe.py "$cart" /tmp/sdx-final-child-a/sdx-fixture.atr /tmp/sdx-repeat-missing-evidence --case repeat-missing
```

The revised parent also passed the OOM, bad-magic, and repeat probes using
`/tmp/sdx-revised-determinism-a` as the resident build. Evidence is in
`/tmp/sdx-revised-oom-visible-evidence`, `/tmp/sdx-revised-bad-magic-evidence`,
and `/tmp/sdx-revised-repeat-evidence`; both OOM and bad-magic visibly printed
`N: INSTALL FAILED`. The same-session repeat-missing probe passed using
`/tmp/sdx-fix-review/sdx-fixture.atr`, with evidence in
`/tmp/sdx-fix-repeat-missing4`.

An earlier isolated `DIR N:` returned SDX error 138, “Device does not respond”,
with no NetSIO endpoint attached. That observation alone does not establish
whether SDX's command environment can use the CIO handler. SDX commands use
kernel devices, while this handler registers in CIO HATABS; see the [SDX programming guide](https://sdx.atari8.info/sdx_files/4.51/SDX451_Programming_Guide.pdf).
Native command integration with a live device remains unproven.
