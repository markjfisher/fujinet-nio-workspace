- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-1.md`
  summary: Checked-in Amiga GCC compile of a TU that only includes `fujinet_nio_device.h`
  evidence: Header self-sufficiency was verified once off-tree; `make check` / `make amiga-driver` would not catch a later incomplete header.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-1.md`
  summary: Host test that `fn_error_string(FN_ERR_ABORTED)` returns `"Aborted"`
  evidence: `make check` never calls `fn_error_string`; dropping the case still passes session/link tests.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-1.md`
  summary: Shared `fn_slip.h` (or equivalent) instead of a local `fn_slip_decode` prototype in `fn_session.c`
  evidence: Removing `fn_internal.h` required a duplicate prototype; Stage 2 path-compiling session into the broker will need a stable declaration.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-1.md`
  summary: Align host `amiga/tests/stubs/exec/errors.h` IOERR_NOCMD/BADLENGTH numerics with NDK 47.1
  evidence: Stub swaps those two values relative to NDK; Stage 2 tests must use symbols, not stub numbers.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-1.md`
  summary: Stage 2 BeginIO policy for NULL+zero length, overlapping malformations, and `fn_response_capacity` vs `FN_MAX_PACKET_SIZE`
  evidence: Architecture matrix only specifies NULL+nonzero and request oversize; not caused by the Stage 1 header itself.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2.md`
  summary: Stage 2B serial backend and isolated guest is a sequenced implementation spec under the same Stage 2 parent gate (not dropped scope, not a second checkpoint)
  evidence: Combined Stage 2 implementation spec exceeded the 1600-token budget; user chose S and forbade splitting Stage 2 into independent deliveries or deferring Stage 2 backlog items.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2a.md`
  summary: Wire `nio.device` into the Amiga native `Makefile` so `make native` produces a loadable `fujinet-nio.device`
  evidence: 2A verification is host `make tests` with an injectable backend; `amiga/Makefile` still builds only `fujinet-disk.device`.

- source_spec: `_bmad-output/implementation-artifacts/spec-amiga-nio-broker-stage-2a.md`
  summary: Allocate the worker signal on the worker task and name/type the `struct Task` instead of copying disk.device's init-task `AllocSignal`/`AddTask` setup
  evidence: Host tests never run `AddTask`/`Wait`/`Signal`; the disk resident uses the same pattern and is out of 2A scope.
