# Amiga DiskDevice Phase 2 Handoff

## Current State

Phase 2 remains in progress, but the previous writable-DN2 runtime incident is
closed. Do not resume broad runtime archaeology unless a normal-mode regression
reproduces.

The root cause was a resident-device Exec lifecycle defect: requests deferred
through the private FIFO bypassed Exec `PutMsg()` and were not explicitly
transitioned to `NT_MESSAGE` before later `ReplyMsg()`. This caused intermittent
AmigaOS requester failures under real OFS workloads.

Evidence:

- Pre-fix driver `53716d3c`: 3 failures in 5 normal foreground runs.
- First relevant fix `6c9bf6af`: 3 passes in 3 normal foreground runs.
- Current production driver: 5 passes in 5 default-timeout foreground runs.
- The dedicated native regression is
  `repos/fujinet-nio-driver/amiga/tests/test_fujinet_exec_boundary.c`.

The normal foreground `diskdevice-adf` case now proves all of these in one
workflow: writable Copy, `CMD_UPDATE`/Flush, writable remount, DOS remount,
persisted `PERSIST.TXT`, malformed replacement rejection, and eject/status
checks. Use it as the regression baseline, with no debugger environment flags
or timeout overrides.

## Do Not Repeat

- Do not re-investigate Copy completion, `CMD_WRITE`, Flush, retained change
  requests, stale DN2 handler selection, or OFS metadata persistence unless the
  normal foreground test fails again.
- Do not use debugger controllers, CPU slowdown, packet tracing, task
  snapshots, or an extended timeout as routine pass criteria.
- Do not reintroduce `fujinet-mount` as an end-user mounting requirement. It is
  still a useful diagnostic/baseline tool while standard-tool coverage is
  completed.
- Do not infer a failing state from historical evidence alone. Reproduce using
  the normal default-timeout harness first.

## Priority 1: Standard Tool Ownership

Complete the user-facing `FMOUNT`/`FUMOUNT` path so it owns the same media
state transitions already proven with the diagnostic mount utility.

1. Inspect the current Amiga `FMOUNT` and `FUMOUNT` implementations in
   `repos/nio-core-apps` and their platform interface to
   `fujinet-disk.device`.
2. Add or extend an Amiberry case that mounts a writable catalogue slot with
   `FMOUNT`, accesses it through `DNx:`, updates/remounts it safely, verifies
   persistence, ejects with `FUMOUNT`, and verifies persisted mapping state.
3. Prove the standard tools cannot desynchronise driver media state, change
   count, protection state, flush behavior, or replacement behavior.
4. Keep the guest startup sequence minimal and use redirected checkpoint files
   for assertions.

Success criterion: standard tools perform the complete catalogue-to-DNx
workflow without requiring a user to run `fujinet-mount`.

## Priority 2: Handler-Safe Replacement

The known safe baseline is explicit `Assign DNx: DISMOUNT`, followed by a new
mount and `Mount DNx: FROM DEVS:DNx`. The earlier nested single-command
replacement attempt was rejected by emulator evidence.

1. Decide whether `FMOUNT`/`FUMOUNT` should orchestrate this explicit handler
   lifecycle or expose a documented two-step user operation.
2. Test replacement while the previous volume was accessed, including stale
   handler retirement and clean volume rescan.
3. Reject requester-producing flows (`You MUST replace volume`, `Not a DOS
   disk`, invalid-block requester) rather than masking them with timeouts.

Success criterion: replacement is deterministic through the standard tools and
does not leave an old DOS handler owning the device name.

## Priority 3: Variable Geometry and Media Families

The driver now stores NIO-reported geometry per unit, but the Phase 2 user
story is not complete while static DD MountLists remain universal.

1. Define supported whole-volume profiles first: DD ADF (1760 sectors), HD ADF
   (3520 sectors), then explicitly decide the 1680-sector and whole-partition
   HDF cases.
2. Determine how `FMOUNT` provides matching DosEnvec geometry to AmigaDOS:
   known profiles, dynamically constructed DOS nodes, or a proven logical
   geometry model.
3. Keep RDB whole-disk images separate from whole-volume images. Do not mount
   an RDB HDF as one filesystem without scanning partitions.
4. Add host/native tests for Info-derived sector count and independent geometry
   on all units; add Amiberry DD/HD standard-tool coverage.

Success criterion: no hidden 1760-sector fallback and no static MountList is
presented as a universal media solution.

## Useful Commands

Normal writable baseline:

```sh
pytest integration-tests/amiberry/test_diskdevice_adf.py \
  -q --run-amiga -k test_standard_adf
```

Standard-tool baseline:

```sh
pytest integration-tests/amiberry/test_diskdevice_fmount.py \
  -q --run-amiga
```

Build driver and native contracts:

```sh
source "$NIO_WORKSPACE/scripts/env.sh"
make -C repos/fujinet-nio-driver amiga
```

Read evidence HDF checkpoints with the harness-supported tool:

```sh
uvx --from amitools xdftool \
  test-evidence/amiberry-YYYYMMDD-HHMMSS/diskdevice-adf/amiga-diskdevice-adf.hdf \
  read disk-persist.result /tmp/disk-persist.result
```

## Debugging Escalation

Only if a normal-mode regression recurs:

1. Preserve the failure evidence directory and identify its first missing
   checkpoint.
2. Re-run once normally to confirm reproducibility.
3. Use the concrete controller examples in `docs/amiberry-testing.md`.
4. Resolve live vectors through `tools/amiga_emulator/device_debug.py`; never
   break on a link-time resident address.
5. Return to a normal controller-free regression before accepting a fix.
