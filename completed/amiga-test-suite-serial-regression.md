# Amiga test-suite serial regression — completed 2026-09-16

The stock `serial.device` open path overwrote the broker's requested serial
parameters. A September 7 initialization change had moved the assignments to
before `OpenDevice`, so the subsequent `SDCMD_SETPARAMS` enabled default
XON/XOFF handling and consumed binary `0x11`/`0x13` bytes. Debugger capture
proved the overwritten fields and the missing byte in the rejected mount
reply. See the [driver diagnosis and captured evidence](../repos/fujinet-nio-driver/docs/amiga/serial-open-parameters-regression.md).

The broker now reapplies its requested parameters after open, retaining the
pre-open setup required by the custom Paula serial device. This adds no I/O
operation, retry, or mount recovery. The inherited session skip, 16-byte
inspect request, cached catalogue URI, and persistence workaround were removed;
the library and core-apps repositories are unchanged from their incoming HEADs.
FHOST, the original FFS fixture and its assertions were restored.

The wrapper now accepts a suite-relative pytest node and uses the complete
suite by default. Two stale tests were aligned with the existing September 3
FUMOUNT behavior: a low-level media remount must recreate its removed DOS node,
and successful FUMOUNT must leave the node absent. Persistence, mapping-error,
busy-handler refusal and unload/reload assertions remain covered. Failed FFS
mounts and failed DOS remounts do not trigger filesystem requester dialogs.

## Verification

Commands below run from the workspace after `source scripts/env.sh`.

| Check | Result |
|---|---|
| `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_amiga_fin_ffs_adf.py::test_fin_mounts_and_reads_ffs_adf` | Passed, 11.97s |
| Final focused FFS + corrected DD remount cases | 2 passed, 25.82s |
| `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030` | **65 passed, 364.42s; no skips** |
| `make -C repos/fujinet-nio-driver/amiga/tests test` | Passed |
| `make -C repos/nio-core-apps TARGET=amiga` | Passed |
| `PATH="$CC65_HOME/bin:/opt/watcom/binl64:/opt/watcom/binl:$PATH" WATCOM=/opt/watcom make -C repos/fujinet-nio-lib check` | All configured targets and host checks passed |
| Wrapper collection / shell syntax | Exact node: 1; default suite: 65; `bash -n` passed |

The initial library invocation could not find cl65. Both cc65 and Watcom were
already installed; adding their executable directories resolved it. No targets
were skipped. The serial backend's behavior is exercised in Amiberry; the
native driver suite does not compile that backend.

Final full-run evidence is in `test-evidence/amiberry-20260916-233252/`, including
`pytest.log`, build/check logs, per-case HDFs, screenshots and firmware logs.
Final focused evidence is in `test-evidence/amiberry-20260916-233208/`.
The original isolated pass is in `test-evidence/amiberry-20260916-232333/`.
All acceptance runs use normal execution, without debugger or timeout overrides.
The earlier discovery run had 63 passes and the two stale lifecycle failures;
its evidence remains under `test-evidence/amiberry-20260916-232356/`.

[Completed specification and review order](../_bmad-output/completed-specs/amiga-suite-serial-regression/spec.md).
