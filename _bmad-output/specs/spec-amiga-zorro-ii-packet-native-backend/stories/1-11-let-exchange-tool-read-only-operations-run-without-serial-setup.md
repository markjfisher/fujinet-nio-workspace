---
title: '1-11 Let exchange-tool read-only operations run without serial setup'
type: feature
created: '2026-09-17'
status: done
baseline_commit: 0b264b35bbc75a7b482ab74d45ede86cd341000f
owner_baseline_commit: d7d65934cf0dec1f1610f9b37c245ea0df3f4abb
review_loop_iteration: 0
spec_checkpoint: false
done_checkpoint: false
context:
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/docs/amiga/cli-stack-and-iorequest.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
---

<frozen-after-approval reason="approved Story 1.11; routine checkpoints disabled by execution-gates.md">

## Intent

**Problem:** The exchange tool's cold lifecycle uses serial controls to reset the backend. Native installations need explicit clock/file-list operation planning without those controls.

**Approach:** Add caller-declared `--installed-backend serial|native` (default serial), preserving `--backend cold|warm` as lifecycle. Native warm performs ordinary clock/file-list exchanges; incompatible options fail before I/O.

## Boundaries & Constraints

**Always:** Preserve existing valid serial invocations and trial fields. Context declares the installed backend; it neither discovers nor switches hardware. Native cold is unsupported because no generic reset exists. Keep public device ABI, broker and library unchanged. Use the actual tool in Amiberry.

**Ask First:** Public ABI, retry/service changes, or hardware selection.

**Never:** Simulate native reset with SET_BAUD; serial fallback; ordinary native disk support (1.12); test harness code in production sources; WaitIO an OpenDevice-only request.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected behavior | Errors |
|---|---|---|---|
| Native clock/list | native + warm, valid operation arguments | WARMUP and MEASURE use EXCHANGE only; real service succeeds | Existing error separation |
| Native cold | native + cold | Reject before OpenDevice | Explain unsupported reset |
| Serial controls on native | baud, serial-device or serial-unit | Reject before I/O, regardless option order | Usage error |
| Other incompatible native options | disk/provocation, host-get, slot/LBA including explicit zero | Reject before I/O | Usage error |
| Malformed options | missing/unknown values, bad numeric input, incomplete file-list | Reject before I/O | Usage error |
| Serial compatibility | omitted context or explicit serial; existing cold/warm invocations | Existing control ordering, warmup and trial output retained | Existing failure policy |
| Bounded planner | too-small step array or invalid native option struct | Fail without executable serial plan | Planner error |

</frozen-after-approval>

## Code Map

Paths are workspace-relative. Own only the files below and this story; accommodate concurrent edits without reverting them.

- `repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.h` and `.c`: parser:51, planner:158, trial formatter:238. Type/backend required. Cold plans SET_BAUD; warm without baud already plans only WARMUP+MEASURE. Add separate installation context and track explicit disk options where zero currently hides presence. Validate both parsed and directly supplied native structs. Preserve old trial formatter contract.
- `repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c`: usage:597, run_set_baud:613, run_matrix:892. Parse/plan/build packets before OpenDevice. SET_BAUD with omitted baud first GET_BAUDs, then reopens at same rate. Add clear context/lifecycle output and errors; native path must not issue optional serial diagnostics. Read-only run_disk_provocation:724 and isolation suite.
- `repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_opts.c`: existing serial/parser/request/planner tests; retain all and extend matrix including native insufficient capacity and explicit `--lba 0`.
- `repos/fujinet-nio-driver/amiga/README.md`: document examples and context versus lifecycle.
- `integration-tests/amiberry/tests.toml`: existing nio-native-test:887 demonstrates `nio_broker=true`, `nio_native_test=true`, `completion_mode=host_file`. Add separate case for actual exchange tool.
- `integration-tests/amiberry/startup/nio-native-exchange.sequence` (new), `integration-tests/amiberry/test_nio_native_test.py`: add `test_native_exchange_tool_read_only`. Run invalid native combinations before loading broker to prove early rejection, then actual native warm clock and file-list with at least two trials. Seed a disposable known file under `NATIVE:host-fs/`; use `host:/` URI and size128. Record every RC; completion marker only after result files written. Assert successful trial counts and context, errors, no serial setup failures, and valid request/response evidence. Preserve 1.10 probe test.
- `integration-tests/amiberry/conftest.py`: read-only existing case support. It installs the native broker, launches real host runner and exposes `NATIVE:`. Avoid changing harness unless a demonstrated missing facility requires it.
- Public `amiga/include/fujinet_nio_device.h` and directory backend are read-only. No generic reset/backend query exists. Host endpoint registers Clock/File only; native host-get is outside this story.

## Tasks & Acceptance

**Execution:**
- [x] Options header/implementation — add context, pre-I/O validation and bounded native plan; preserve serial behavior.
- [x] Actual exchange tool and README — explain native warm usage and reject unsupported combinations clearly.
- [x] Native option tests — cover every planning/error matrix row and serial regressions.
- [x] Workspace case/startup/pytest — prove actual guest clock/list operations and early rejection.
- [x] Run owner and guest checks; record evidence and review findings.

**Acceptance Criteria:**
- Given the native installation, when valid clock/file-list commands execute, then they reach real handlers through EXCHANGE without any serial control request.
- Given malformed or incompatible native options, when invoked even before a broker is loaded, then usage validation rejects them before I/O.
- Given existing serial invocations, when parsed/planned and exercised by existing guest coverage, then behavior remains compatible and declared installation context is distinct from cold/warm lifecycle.

## Spec Change Log

- 2026-09-17: Used the Code Map's conditional harness allowance: the existing
  native runner path omitted CMake's `tests/` output subdirectory. Both native
  guest cases failed before launch despite a successful build. Corrected only
  that path in `conftest.py`; no backend, protocol or service scope changed.

## Verification

Source workspace `scripts/env.sh` before every build/test. From workspace root:

- `make -C repos/fujinet-nio-driver/amiga/tests build/test_fujinet_nio_exchange_opts && repos/fujinet-nio-driver/amiga/tests/build/test_fujinet_nio_exchange_opts`
- `make -C repos/fujinet-nio-driver/amiga ../build/amiga/fujinet-nio-exchange`
- `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_read_only test_nio_native_test.py::test_native_test_clock_exchange test_nio_broker.py::test_isolated_exchange`

Expected: focused native tests, cross-build and all three guest nodes pass. No firmware/lib edits or full Amiberry suite required. Inspect source/plan to establish absence of native serial controls; native broker rejects them rather than hiding success. Record exact guest evidence directory.


### Implementation evidence (2026-09-17)

- Sourced `scripts/env.sh` before each build/test invocation.
- Focused options build and executable passed after final source changes:
  `make -C repos/fujinet-nio-driver/amiga/tests build/test_fujinet_nio_exchange_opts && repos/fujinet-nio-driver/amiga/tests/build/test_fujinet_nio_exchange_opts`.
- Actual tool cross-build passed:
  `make -C repos/fujinet-nio-driver/amiga ../build/amiga/fujinet-nio-exchange`.
- The specified three-node guest command was run. Serial
  `test_nio_broker.py::test_isolated_exchange` passed; native cases initially
  exposed the runner-path defect described above. Evidence:
  `test-evidence/amiberry-20260917-102538/nio-broker-isolated/`.
- After the harness fix, native probe
  `test_nio_native_test.py::test_native_test_clock_exchange` passed. Evidence:
  `test-evidence/amiberry-20260917-102612/nio-native-test/`.
- The actual exchange case initially exposed the Amiga 30-character filename
  limit in new result names, then a missing U8 status parameter in the test's
  response-length expectation. Shortened result filenames and corrected the
  independent response shape (6-byte header + U8 status + service payload).
- Final focused command passed:
  `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_read_only`.
  Evidence: `test-evidence/amiberry-20260917-102716/nio-native-exchange/`.
  Thirteen invalid invocations before resident loading return usage RC=10;
  clock and list each produce two successful measured trials. Host log decoding
  verifies all eight real exchanges (six clocks including four warmups and two
  lists), service status zero, current host timestamps, and the disposable
  `native-exchange.txt` entry with size 5. Clock/list raw response sizes are
  19/54 bytes respectively.
- Native planning returns only WARMUP then MEASURE; both submit EXCHANGE.
  Invalid directly supplied native structs and insufficient plan capacity fail
  without modifying the steps buffer. Native execution gates optional serial
  diagnostics. The old trial formatter and isolation suite are unchanged.
- No firmware, library, broker or public ABI sources changed. No hardware acceptance claim is made.


### Review follow-up evidence (2026-09-17)

- Restored `strtoul`'s pre-existing acceptance of positive `+2` and leading
  whitespace numeric syntax for serial compatibility, while retaining ERANGE
  overflow rejection. Added explicit serial regression cases. Added direct
  native-struct rejection tests for trials 100001 and inactive size/list-flags
  fields holding nonzero values. The focused native test command and actual
  tool cross-build above both passed after these final changes.
- Guest RC assertions now match whole lines. Source inspection confirms the
  argument parser returns `RETURN_ERROR` (10) before CreatePort/OpenDevice;
  an OpenDevice failure returns `RETURN_FAIL` (20). The thirteen pre-load
  failures assert exact `RC=10`, establishing usage rejection. Removed the
  misleading stdout-only `Cannot open` absence assertion: that diagnostic and
  usage are printed on stderr, which the startup stdout redirection does not
  capture.
- Ran final changed-path guest coverage using an existing serial matrix case:
  `scripts/amiga-tests --amiga-env wb32 --amiga-machine a1200-030 test_nio_native_test.py::test_native_exchange_tool_read_only test_nio_paula_serial.py`.
  **2 passed in 9.35s.** Evidence root:
  `test-evidence/amiberry-20260917-103203/`; cases `nio-native-exchange/` and
  `nio-paula-serial/`. The existing serial case executes the actual matrix
  with omitted installation context, cold lifecycle, baud 19200 and
  `fujinet-serial.device`; the recorded trial is request 6 / response 19,
  result/cause/native/status all zero, `installed_backend=serial lifecycle=cold`,
  and exact `TOOL RC=0`.
- Limitation: native measured-failure execution was not fault-injected in a
  guest. The native guards around optional serial error diagnostics were
  source-reviewed; successful native trials alone do not exercise those error
  branches. No new packet relay/fault infrastructure was added for this small
  diagnostic guard change. Existing serial failure/isolation coverage remains
  recorded above; no claim of native failure-path execution is made.
- `git diff --check` passed in the workspace and driver repository.

## Review outcome

Three independent review lenses completed. Fixed numeric compatibility, exact return-code assertions, and missing direct-struct checks. Added execution of the existing serial matrix case. Native failure-output verification remains limited to source inspection as recorded above. No unresolved implementation blocker.

Owner implementation commit: `c7f1fbd382724b34b5f83ec8f99baf8df4ea1fcb`.

## Suggested Review Order

- Follow context validation before device access.
  [fujinet-nio-exchange.c:897](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet-nio-exchange.c#L897)

- Inspect native restrictions and EXCHANGE-only planning.
  [fujinet_nio_exchange_opts.c:49](../../../../repos/fujinet-nio-driver/amiga/tools/fujinet_nio_exchange_opts.c#L49)

- Read context versus lifecycle usage.
  [README.md:152](../../../../repos/fujinet-nio-driver/amiga/README.md#L152)

- Check parser compatibility and invalid native structures.
  [test_fujinet_nio_exchange_opts.c:707](../../../../repos/fujinet-nio-driver/amiga/tests/test_fujinet_nio_exchange_opts.c#L707)

- Check real service payloads and exact guest results.
  [test_nio_native_test.py:31](../../../../integration-tests/amiberry/test_nio_native_test.py#L31)

- Follow invalid commands before broker loading, then successful operations.
  [nio-native-exchange.sequence:1](../../../../integration-tests/amiberry/startup/nio-native-exchange.sequence#L1)

- Inspect case registration and corrected host runner path.
  [tests.toml:924](../../../../integration-tests/amiberry/tests.toml#L924)

- Locate the CMake-built native test endpoint.
  [conftest.py:413](../../../../integration-tests/amiberry/conftest.py#L413)

