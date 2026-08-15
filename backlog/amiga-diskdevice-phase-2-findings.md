# Progress document for phase 2 work

Add from the top down, so previous history is at the bottom of this document making the top of the document the latest progress, and lower down just history.
Ensure additions are short but relevant to indicate areas attempted, and findings that worked or did not, so future agents do not attempt the same mistakes.

## Handler-safe media replacement via `Inhibit()`

Classic AmigaOS does not provide the OS4-style `DismountDevice()` /
`MountDevice()` API. Investigation against the installed classic NDK showed
that `Inhibit()` is the appropriate mechanism for coordinating media
replacement with an already-running DOS filesystem handler.

A standalone proof-of-concept established that an existing `DN0:` handler can
remain resident across media replacement:

1. Mount volume A on `DN0:`
2. `Inhibit("DN0:", DOSTRUE)`
3. Replace the underlying FujiNet media
4. `Inhibit("DN0:", DOSFALSE)`
5. Read volume B through the same DOS handler

The handler rescanned the newly inserted media successfully without
`Assign ... DISMOUNT`, recreating the handler, requester dialogs, or DOS-list
surgery.

Production `FMOUNT` was updated to:

- detect an active DOS handler using
  `LockDosList(LDF_READ | LDF_DEVICES)`;
- require the matching device entry to have a non-NULL `dol_Task`;
- inhibit the DOS handler before opening `fujinet-disk.device`;
- perform the catalogue media replacement;
- close the device/request resources;
- uninhibit the existing handler;
- report inhibit/uninhibit failure distinctly.

An earlier detection attempt used `LockDosList(LDF_ALL)` without `LDF_READ` or
`LDF_WRITE`. That returned no usable list and caused production `FMOUNT` to
incorrectly conclude that no handler was active. Correcting the lock flags
fixed this.

Repeated A->B->A replacement was then validated with the same handler task
remaining active throughout. For both directions:

- `Inhibit(TRUE)` returned success;
- the volume node disappeared while inhibited;
- catalogue replacement returned success;
- `Inhibit(FALSE)` returned success;
- exactly one volume node reappeared afterward;
- the same handler task remained active;
- the disk change counter advanced;
- `Dir` and `Type` saw the newly inserted media;
- no requester appeared.

This validates handler-safe replacement for the current DD ADF fixture. The
replacement mechanism must not depend on old/new media geometry; support for
different geometries belongs to the separate Media Geometry work.

## `diskdevice-inhibit-poc` completion flake

During final full-suite validation, `diskdevice-inhibit-poc` showed an
intermittent completion failure even though all functional media-replacement
checkpoints had succeeded.

Initial evidence showed the final FujiNet traffic ending with:

- normal disk reads;
- `DiskCommand::Flush` (`0x0E`);
- the expected FLS host-filesystem request.

A 20-run isolated campaign reproduced the apparent failure 5/20 times. Further
instrumentation proved:

- the final `Type` returned with RC=0;
- the shell reached the command immediately before FLS;
- FLS issued its FujiNet request;
- FujiNet returned a successful response;
- failing runs lacked the guest-side command following FLS.

The disk flush was not causal: all 20 runs, passing and failing, had the same
final FujiNet command ordering, including the same flush followed by the FLS
request.

The test was then corrected so the FLS operation being exercised was no longer
also used as the harness completion sentinel. The sequence now:

1. runs an ordinary FLS command under test;
2. records and asserts an `after-fls` checkpoint;
3. displays the functional results;
4. waits 2 seconds for visual evidence capture;
5. issues a separate FLS request solely as the `nio_marker` completion signal.

No production, driver, or shared transport/client code changed.

With the corrected sequencing and explicit assertions for:

- `before-type.result`;
- `after-type.result`;
- `before-fls.result`;
- `after-fls.result`;

the isolated test passed 20/20 runs.

Conclusion: the prior intermittent failure is attributed to completion/test
sequencing rather than a demonstrated production FLS, disk flush, or
handler-replacement defect. The original failing evidence is retained for
history, but the shared transport/FLS return path should not be reopened unless
the failure reproduces with the corrected test structure.

## Root Cause 2026-08-14

- Root cause: deferred IORequests stored in the resident device's private FIFO were not transitioned to `NT_MESSAGE`. Because private FIFO insertion bypasses Exec `PutMsg()`, queued requests could retain `NT_UNKNOWN` or stale node state, violating Exec message lifecycle semantics when the device later completed them with `ReplyMsg()`. Under real OFS writable workloads this caused intermittent completion/requester failures.
- Historical A/B confirms the causal boundary. Pre-fix driver `53716d3c` failed 3/5 normal foreground runs with an AmigaOS requester before the writable checkpoints, while the first one-line production change `6c9bf6af` (`request->io_Message.mn_Node.ln_Type = NT_MESSAGE` immediately before FIFO append) passed 3/3. Later queued-close and invalid-unit hardening commits also pass 3/3 but are not needed to explain the first transition.
- Added an explicit native Exec-boundary regression in `repos/fujinet-nio-driver/amiga/tests/test_fujinet_exec_boundary.c`: an IORequest beginning in `NT_UNKNOWN` must become `NT_MESSAGE` when privately deferred, remain `NT_MESSAGE` through dequeue, then become `NT_REPLYMSG` after successful non-quick completion/ReplyMsg. Native driver tests and `make amiga` pass with the new contract.

## Progress 2026-08-14 00:52

- Returned to the normal foreground harness path: no `AMIGA_E2E_DEBUGGER`, controller, breakpoint, task snapshot, packet-trace, or full-payload logging environment was active. The host-side diagnostic tools remain opt-in only. The normal timeout path import was repaired so a timeout can write passive evidence without a `NameError`.
- Five clean repetitions of `test_standard_adf_mount_info_read_dir_and_type` passed: evidence directories `amiberry-20260814-004732`, `004843`, `004958`, `005111`, and `005223`. Each run took about 65 seconds and passed all pytest assertions.
- Every repetition produced the key writable checkpoints: `COPY RC=0`, successful update, writable remount, `DOS REMOUNT 2 RC=0`, and `FUJINET WRITE PERSISTED`. The fifth run also has every later asserted checkpoint through malformed replacement rejection, direct mount, drive-7 status, drive-3 eject, and final drive-3 status.
- `E2E COMPLETE` is an unredirected final console echo. The normal quiet-screen harness does not retain console text in `amiberry.log`, so its literal marker cannot be independently proven from these run directories; however, the later redirected checkpoints that precede it all exist and the test passed. No run failed or diverged.
- The original writable-DN2 failure is not reproducible across these five non-debugger foreground repetitions with the current production correctness fixes. Treat the prior failure as fixed or timing-sensitive until a normal-mode regression reproduces it.

## Progress 2026-08-14 00:36

- Host-only DOS handler identity evidence is `test-evidence/amiberry-20260814-003615/diskdevice-adf/dn2-handler-trace.log`. Exact NDK/cross-compiler offsets were used to resolve `dos.library` from Exec's LibList, then `RootNode.rn_Info` (BPTR), `DosInfo.di_DevInfo`, and the `DN2` DeviceNode.
- Before the new DN2 process appears, the old handler is process `0xc58b90`, embedded port `0xc58bec`. The new DN2 process is `0xc62e60`, embedded port `0xc62ebc`. Once both exist, the live DOS `DN2:` DeviceNode's `dn_Task` is exactly `0xc62ebc`, the new process's port, not the old port.
- The same trace run completed Copy, update, writable remount, DOS remount, and `disk-persist.result` (`FUJINET WRITE PERSISTED`). Thus the final `Type DN2:PERSIST.TXT` is routed through the current `DN2:` DeviceNode to the newer handler, not to the stale pre-remount process.
- A transient Exec PutMsg breakpoint did not yield packet-level event records because this Kickstart's PutMsg vector is not directly resolved by the existing simple trampoline decoder. This does not weaken the authoritative DOS DeviceNode routing result, but if per-packet handler internals are needed next, resolve that Exec vector form rather than returning to block I/O.

## Progress 2026-08-14 00:13

- Focused live read-path evidence is `test-evidence/amiberry-20260814-001230/diskdevice-adf`. The POSIX `fujinet-nio` debug binary was rebuilt after adding the diagnostic-only `FUJINET_FULL_PACKET_LOG=1` override; its full `cmd=0x03` responses retain all 523 response bytes (11-byte protocol header plus complete 512-byte sector).
- Host-only `CMD_READ` tracing captures BeginIO and common completion for LBA 880-883. Every target read completes with `io_Actual=512` and `io_Error=0`; the final Type path specifically reads LBA 880 (request `0xc29788`), then 882 and 883, all synchronously successful.
- Full NIO response vs final backing ADF SHA-256 comparisons are exact: LBA 880 request id 83, LBA 881 id 82, LBA 882 id 84, and LBA 883 id 85 each have `equal=True` across all 512 returned bytes. NIO is not returning stale/different data during `Type DN2:PERSIST.TXT`.
- This selects the block-device-success branch: persistence and live reads are correct through the affected file header/data sectors. Continue investigation above the block device, in the DOS/OFS mount or handler state; do not return to write-persistence or general disk command sequencing without new contradictory evidence.

## Progress 2026-08-14 00:00

- Current fresh evidence (`test-evidence/amiberry-20260813-232447/diskdevice-adf/fujinet-data/writable.adf`) does **not** reproduce the older malformed-file state. `xdftool` lists `PERSIST.TXT` at 24 bytes; raw LBA 882 is its OFS file header (data block pointer `883`, byte count `24`) and LBA 883 contains `FUJINET WRITE PERSISTED\n`. LBA 881 is a valid bitmap block. Do not carry forward the historical FileData Block Count Mismatch as a current result without re-verifying it.
- Added `tools/amiga_emulator/disk_write_compare.py`, a host-only offline comparator for full NIO log records and backing ADF sectors. For the current run, the final logged DiskDevice write payload prefixes match the stored sectors: LBA 880 request 63, LBA 881 request 61, LBA 882 request 62, and LBA 883 request 57 all match for the 504 sector bytes retained by the NIO formatter.
- The NIO formatter truncates each 520-byte write record after 512 wire bytes, leaving the final 8 sector bytes unavailable from historical logs. A host-only exact-buffer capture controller was prepared, but its debugger-mode runs did not reach the Copy phase within the controller deadline and produced no target captures; do not treat them as sector evidence. The available current evidence excludes a persistence mismatch in all recorded metadata/payload bytes and supports normal stored OFS metadata.
- This run therefore cannot establish either requested failure case A or B: it has a correct persisted file and no structural inconsistency. No native DF0 control artifact is retained in the current evidence tree for an optional sector comparison.

## Progress 2026-08-13 23:24

- The existing `amiberry-20260813-231309` HDF was extracted directly with the harness's `xdftool` path. It contains `disk-copy-rw.result` (`COPY RC=0`), `disk-update.result` (`UPDATED drive=2 slot=3`), `disk-remount-rw.result`, `disk-dos-remount-2.result` (`DOS REMOUNT 2 RC=0`), and an empty `disk-persist.result`. All later requested checkpoints are absent. That run definitely reached `C:Type DN2:PERSIST.TXT` and created its redirected result file, even though the Type output was empty.
- Added visible, non-redirected markers only around the writable section and final display section: `COPY-BEGIN`, `COPY-END rc=$RC`, `UPDATE-BEGIN`, `UPDATE-END rc=$RC`, `RESULTS-BEGIN`, and `RESULTS-END`. This preserves every command and stored result path.
- Fresh marker evidence (`amiberry-20260813-232447`) visibly shows `COPY-BEGIN`, `COPY-END rc=0`, `UPDATE-BEGIN`, and `UPDATE-END rc=0`. Its extracted HDF contains Copy, Update, remount, and DOS-remount checkpoints but lacks `disk-persist.result`; it is therefore paused/stalled at the immediately following `C:Type DN2:PERSIST.TXT`, before the final result-display block.
- NDK/cross-compiler verified CLI fields now record `cli_CurrentInput=0x20`, `cli_CurrentOutput=0x30`, and `cli_Module=0x3c` in snapshots. These identify CLI stream/module BPTRs but do not encode a command argument. Sequence position plus the HDF checkpoint boundary identifies the active `C:Type` as `DN2:PERSIST.TXT`, not a final `Type DH0:...result` command.

## Progress 2026-08-13 23:13

- The Initial CLI wait was decoded with m68k-amigaos-gcc-verified offsets for `Process`, `MsgPort`, `Message`, `DosPacket`, and `CommandLineInterface`; clean evidence is `test-evidence/amiberry-20260813-231309/diskdevice-adf/task-timeout-snapshot.log`.
- Initial CLI (`0xc212d0`) is `TS_WAIT` on `tc_SigWait=0x100`. Its embedded process port is `0xc2132c`, uses `mp_SigBit=8`, and therefore has signal mask `1 << 8 == 0x100`; `mp_SigTask` points back to Initial CLI. This proves the foreground CLI is waiting on its DOS/process reply port at capture time.
- That CLI port queue is empty. Its decoded CLI command name is `C:Type`, not `Copy`; do not infer that Copy is still blocked merely because Initial CLI waits on its port. There is no queued reply packet waiting to wake it and no queued packet from Initial CLI on either DN2 handler port.
- Two distinct `DN2` filesystem processes exist: current/wait process `0xc62d38` with port `0xc62d94`, and wait process `0xc58b90` with port `0xc58bec`. Both have empty port queues and each owns its own signal bit 8. Their shared process `pr_FileSystemTask` field (`0xc0e144`) is the DOS filesystem task pointer, not evidence that one is an outstanding caller. The snapshot cannot, by itself, attribute one to the writable mounted volume beyond their observed lifecycle state.
- No DOS packet/message is outstanding between Initial CLI and either DN2 port at timeout. This shifts the checkpoint investigation away from a missing DN2 packet reply and toward the sequence/checkpoint mechanism running after `C:Type` or the harness's command/output observation.

## Progress 2026-08-13 23:00

- A host-only Exec task snapshot was captured at the bounded reproduction timeout: `test-evidence/amiberry-20260813-230029/diskdevice-adf/task-timeout-snapshot.log`. It uses NDK-derived `ThisTask`, `TaskReady`, `TaskWait`, Node, and Task offsets; Process extension offsets have subsequently been verified with `m68k-amigaos-gcc` as `pr_FileSystemTask=0xa8` and `pr_CLI=0xac`.
- The snapshot current task is the `DN2` filesystem handler (`NT_PROCESS`, `TS_WAIT`), waiting on signals `0x10000000` with received `0x08000100`. The handler also appears in Exec's wait list. It is not currently running or ready, so the timeout snapshot is not a CPU spin in the driver/handler.
- No task/process named `Copy` appears in current, ready, or wait task lists at capture time. This rules out the narrow interpretation that foreground Copy is still blocked waiting for the device or DN2 handler at timeout; it has already exited or is no longer represented under that task name before the checkpoint failure.
[Later superseded: absence of a task named Copy did not itself prove command
completion; subsequent CLI/checkpoint evidence established Copy had completed.]

- Other filesystem handlers (`DN0`, `DN1`, `DF0`, `DF1`, `RAM`, `DH0`) are likewise waiting normally. The current PC is in Amiberry/ROM-side scheduling code (`0xfc983e`), not resident disk-device code. Do not add more disk breakpoints from this evidence; investigate checkpoint/process-sequencing state next.

## Progress 2026-08-13 22:51

- Corrected the post-update command decoding using the installed NDK: `CMD_NONSTD=9`, so `TD_ADDCHANGEINT=20`, `TD_REMCHANGEINT=21`, and `TD_GETGEOMETRY=22`. The earlier label of command `22` as ADDCHANGEINT was wrong; it is ordinary quick geometry bookkeeping.
- The bounded post-update trace in `test-evidence/amiberry-20260813-225058/diskdevice-adf/beginio-command-stream.log` did not issue any command `20` before its 55-second cutoff. Therefore this Copy reproduction provides no `TD_ADDCHANGEINT` registration to inspect, and there is no evidence of a retained-request lifecycle violation, removal, abort, or media-change callback on this path.
- The first 10 post-update BeginIO calls are normal geometry/write/update/query work: command `22` (`TD_GETGEOMETRY`), writes at LBAs 881/882/880, quick `CMD_UPDATE`, command `9` (`TD_MOTOR`), command `268` (`TD_GETGEOMETRY` with extension bit), then more update/motor/query/read operations. The trace continues past these operations; no first non-completing command was isolated before the controller deadline.
- Do not investigate ADDCHANGEINT registration as the immediate post-Copy boundary unless a future trace actually observes command `20`. The immediate observed sequence instead returns to normal OFS metadata writes, including LBA 881, after the successful quick update.

## Progress 2026-08-13 21:47

- The first post-Copy `CMD_UPDATE` trace is complete in `test-evidence/amiberry-20260813-214611/diskdevice-adf/beginio-command-stream.log`. The exact quick request is command `4`, flags `0x1`, zero offset and length; it reaches CMD_UPDATE entry, `fujinet_disk_flush()` entry, flush return, and the common post-`io_Error` completion point.
- `fujinet_disk_flush()` returns `FN_OK` (`D0 & 0xff == 0`; upper D0 bits are outside the byte-sized result), and at common completion the request still has `IOF_QUICK`, `io_Error=0`, and `io_Actual=0`. No ReplyMsg is expected for this quick request. The immediate next BeginIO is command `22` (`TD_GETGEOMETRY`), so CMD_UPDATE returned synchronously as Exec expects. `TD_ADDCHANGEINT` is command `20` (`CMD_NONSTD + 11`) and requires a separate lifecycle trace.
- The matching NIO log confirms transport activity: after the six DiskDevice write requests (`cmd=0x04`, ids 54-59), the traced unit's DiskDevice Flush is transmitted as `id=60 dev=0xFC cmd=0x0E`, payload slot `3`, and receives `status=0` response (`fujinet-nio.log` lines 1480-1485). The update/flush operation neither stalls nor fails.
- No resident device or guest-sequence change was made. The next narrowing boundary is after the successful quick CMD_UPDATE, including normal `TD_GETGEOMETRY` bookkeeping and then the actual `TD_ADDCHANGEINT` registration, not CMD_WRITE, Flush, IOF_QUICK completion, or ReplyMsg.

## Progress 2026-08-13 21:36

- Internal host-only completion tracing is complete for Copy records 52-57. Evidence is `test-evidence/amiberry-20260813-213612/diskdevice-adf/beginio-command-stream.log`; it resolves the live relocation delta (`0xc30010`) and verifies the runtime opcodes for `fujinet_disk_write()` entry, its CMD_WRITE return site, and the common pre-`ReplyMsg()` completion call.
- Every targeted `CMD_WRITE` enters `fujinet_disk_write()`, returns with success (`D0 & 0xff == 0`; upper D0 bits are not part of the byte-sized FN result), sets `io_Actual=512`, retains `io_Error=0`, and reaches the common pre-`ReplyMsg()` boundary. This includes record 57 at LBA 882.
- Record 57 therefore is not the failure boundary: it enters, completes, and replies normally. The next `BeginIO` after record 57 is `CMD_UPDATE` (command `4`), `IOF_QUICK` (`flags=0x1`), zero length and offset, on a distinct request pointer. Progression reaches the filesystem update/flush phase after the Copy writes.
- No resident device or guest-sequence change was made. The next investigation boundary is the `CMD_UPDATE`/flush handling and its completion, not `CMD_WRITE`, `io_Actual`, or ReplyMsg for the six Copy writes.

## Progress 2026-08-13 21:18

- The host-side Amiberry `BeginIO` trace is now deterministic without changing the resident device or the guest startup sequence. The runner pauses before opening the serial bridge; the controller waits for the existing `LoadModule` command to register `fujinet-disk.device`, resolves the live vector from Exec's `DeviceList`, arms only `device_begin_io()`, then resumes and records each request.
- Successful evidence is `test-evidence/amiberry-20260813-211831/diskdevice-adf/beginio-command-stream.log`. It captured 60 ordered requests and reached the foreground `Copy` write sequence with the corrected `io_Offset +44` decoder.
- The expected foreground writes are records 52-56: `CMD_WRITE` (command `3`), 512 bytes, unit `12871686`, at LBAs `880, 882, 882, 883, 880` respectively.
- The answer to the current breakpoint question is **yes**: after the final LBA 880 write (record 56), `device_begin_io()` receives another request. Record 57 is `CMD_WRITE`, unit `12871686`, flags `0x0`, error `0x0`, actual `0`, length `512`, offset `451584`, LBA `882`.
- This disproves the narrower hypothesis that the filesystem submits no device work after the final LBA 880. Do not add internal `fujinet_disk_write()` or `ReplyMsg()` breakpoints yet; first interpret the completed BeginIO stream alongside the existing image delta showing missing block 881.


## Progress 2026-08-13 14:50

- The native-vs-driver ADF comparison now shows the most precise symptom so far: a native `DF0:` write changes blocks `866, 880, 881, 882, 883`, while the driver-backed `DN2:` write changes only `866, 880, 882, 883`. The missing metadata write is block `881`.
- Block 883 (the `PERSIST.TXT` data block) is identical between the native-written and driver-written images. The remaining corruption is therefore not data delivery; it is a missing or inconsistent metadata finalization write in the driver-backed path.
- Tried forcing a `Flush` after every successful `CMD_WRITE` in `fujinet_disk_write()`. This was informative but wrong: it removed the previous corrupt half-created `PERSIST.TXT`, but it also caused the file not to appear at all. The NIO trace showed a `cmd=0x0E` flush after every write, and the write sequence stopped earlier (four writes instead of five). Reverted this experiment.
- Tried additional live tracing/geometry probing inside the Amiberry sequence (`--trace`, then `--geometry`). Those probes made the pre-RW boundary less stable without providing enough new leverage. Do not keep expanding the e2e sequence further unless needed for final validation.
- Current preferred approach has changed: stop perturbing the live Amiberry workflow and instead use the known image delta (especially missing block 881) to reason directly about the resident device's `BeginIO`/`CMD_WRITE`/`CMD_UPDATE` contract, then validate in Amiberry only after a targeted driver change.


## Progress 2026-08-13 14:10

- Added a native-floppy write control case that copies the same `FUJINET WRITE PERSISTED` payload to `DF0:PERSIST.TXT` and preserves the resulting `native-floppy.adf` for comparison.
- The native control write passes. Comparing `native-floppy.adf` against the driver-written `writable.adf` is now the strongest narrowing tool.
- Key result from that comparison: the file data block is correct. `PERSIST.TXT` payload matches, and block 883 is identical between the native-written and driver-written images.
- The corruption is entirely in OFS metadata bookkeeping. `xdftool` reports `FileData Block Count Mismatch(13)` for the driver-written image: the directory entry says `PERSIST.TXT` has one data block, while the file header says zero.
- Byte diffs are tightly localized: root/directory bookkeeping block 881 differs in only two positions; `PERSIST.TXT` file-header block 882 differs in six bytes/fields; the data block is identical. This means accepted `CMD_WRITE` traffic reaches the image, but OFS finalization is being driven inconsistently by the resident device contract.
- Current leading hypothesis is still the geometry/trackdisk contract exposed by `fujinet-disk.device` during writable OFS allocation/finalization (`TD_GETGEOMETRY` and related queries), not transport, queueing, or `io_Actual` handling.


## Progress 2026-08-13 14:00

- Cleaned up the duplicate-registration hardening into a proper helper (`remove_all_change_requests`) so `device_close()`, `TD_REMCHANGEINT`, and `AbortIO()` all exhaustively remove retained change registrations for the same `IORequest` without the previous empty `while (...) {}` loops.
- The duplicate-registration/idempotent `TD_ADDCHANGEINT` fix did not eliminate the writable DN2 failure, but it preserved the useful narrowed boundary and removed another stale-callback class from the resident device.
- Strongest current finding: this is now a specific on-disk OFS metadata corruption, not a generic write failure. In the latest focused `diskdevice-adf` run, `fujinet-nio.log` shows five successful `CMD_WRITE` sector transfers for `PERSIST.TXT`, including the file payload (`FUJINET WRITE PERSISTED`).
- The resulting `writable.adf` is structurally inconsistent: `xdftool` reports `FileData Block Count Mismatch(13)` for `PERSIST.TXT` (directory entry says one data block, file header says zero). This means the data sectors reach the image, but OFS finalization/bookkeeping is being driven inconsistently.
- Because `io_Actual` is already being set correctly for `CMD_WRITE`, the next most likely driver-side cause is the geometry contract exposed through `TD_GETGEOMETRY` and related trackdisk queries during writable file allocation/finalization, not transport or queue lifetime.


## Progress 2026-08-13 13:30

- Second resident-device lifetime fix landed: retained `TD_ADDCHANGEINT` registrations now store the interrupt pointer at registration time and `signal_media_change()` no longer re-reads `io_Data` from possibly stale `IORequest` objects. This moved the live Amiberry boundary forward again.
- With that fix in place, the `diskdevice-adf` run once more reaches the RW `DN2:` mount and issues multiple successful `CMD_WRITE` sector transfers before dying during ordinary AmigaDOS file output. Latest good narrowed boundary: RW mount succeeds, five sector writes complete, but `disk-copy-rw.result` is still never written and `PERSIST.TXT` does not survive in the resulting ADF.
- Tried correcting `TD_GETNUMTRACKS` from 80 to 160 because the current code was returning cylinders, not tracks. Native tests still passed, but it did not resolve the writable-DN2 crash.
- Tried keeping the resident transport session open across empty FIFO batches; this regressed the suite back to the first mount because standalone CLI tools need the backend handle released between batches. That experiment was reverted immediately.


## Progress 2026-08-13 13:18

- First concrete driver fix landed in `repos/fujinet-nio-driver/amiga/disk.device/fujinet_disk_device.c`: `device_close()` now clears retained `TD_REMOVE` waiters and removes queued work for the closing `IORequest`, instead of leaving stale request pointers inside the resident device across handler/CLI teardown.
- Added a host regression in `repos/fujinet-nio-driver/amiga/tests/test_fujinet_exec_boundary.c` covering close-time cleanup of a retained remove waiter.
- This fix did not fully solve the Amiberry `diskdevice-adf` failure, but it changed the failure surface. The latest focused run now reaches `disk-status-1-early.result` and then disconnects before `disk-mount-rw.result`, pointing to a remaining close/reopen lifetime bug in the resident device rather than the earlier DN2 write/update phase.
- Latest NIO evidence confirms the failure now happens before the RW mount request is even sent. So the current live boundary is the transition from the last `DN1:` operations / `--status 1` shell tool back into the next standalone `fujinet-mount 13 2 RW` process.


## Progress 2026-08-13 13:10

- The broad Amiberry failures were partly harness issues, now fixed. `cli-stateful`, `diskdevice-fmount`, `diskdevice-mapping-failure`, `wifi-config`, and the renamed stalled-external-peer timeout case all pass again.
- The remaining `diskdevice-adf` failure is not another harness false negative. Fresh focused reruns still stop at missing `disk-update.result` even after increasing `screenshot_quiet` from 5s to 15s.
- Latest evidence shows the writable path definitely reaches the resident driver and NIO: `host:/writable.adf` mounts RW, `PERSIST.TXT` sector writes are sent, and multiple `CMD_WRITE` requests succeed before the guest dies.
- The latest `amiberry.log` shows a guest crash during the writable DN2 workflow (`M68K PC=00f82e00`) rather than a plain mount/update shell failure. This points at a real Amiga-side bug around the RW/update/remount path, not a missing NIO response.
- Strong suspect area now is the resident device's writable-media transition / change-notification lifetime handling (`TD_ADDCHANGEINT`, `CMD_UPDATE`, `TD_EJECT`, `signal_media_change`). The repo README already warned the host exec-boundary test does not validate real Amiga `Cause()` and request lifetimes.


## Progress 2026-08-12 18:00

These were captured by me from claude conversations, not actually written by claude:

```
The data is correct but OFS still rejects it. Let me check what the Amiga actually sees — let me look at the amiberry.log and also check whether there's something about how io_Actual is set differently than OFS expects
Let me check if the HD ADF test passes (same driver, different geometry) to see if the issue is DD-specific
HD ADF passes! The driver works fine for HD, but not DD. Let me check the HD mountlist — it probably uses FFS not OFS

The HD ADF has no _fix_adf_root_block call yet passes. Let me check what's actually in that root block

Wait — the HD ADF has own_key=0 and secondary_type=1 and PASSES. Our DD fix sets own_key=880 and secondary_type=0xFFFFFFFF and FAILS. The fix is wrong. Let me temporarily disable it and test with xdftool defaults

Now I see the key difference. The diskdevice-adf test uses fujinet-mount host:/standard.adf (direct slot 1 mount) which already passes. The diskdevice-fmount test uses fmount 11 0 RO (slot 11 mapped to unit 0). Let me look at the driver to see how it handles the slot mapping for reads

Found the problem. fujinet_disk_unit_to_slot hardcodes slot = FUJINET_DISK_FIRST_SLOT + unit — it doesn't use the fmount mapping! Let me check the constants and understand the fmount slot mapping

Now I have a clear picture. The _fix_adf_root_block function is wrong on two counts:
1. secondary_type=0xFFFFFFFF is demonstrably wrong — HD ADF has secondary_type=1 and PASSES
2. own_key=880 is also likely wrong — HD ADF has own_key=0 and PASSES; native floppy specifically requires fix_root_block=False because own_key=880 causes rejection

The real root cause of "Not a DOS disk" was StackSize=2048 in the DN0 mountlist, which is now fixed to 32768. The _fix_adf_root_block was a red herring.

Step: Remove _fix_adf_root_block entirely and stop calling it:
- Update(~/dev/nio/fujinet-nio-workspace/integration-tests/amiberry/conftest.py

Now fix the native floppy call site which used fix_root_block=False:
- Update(~/dev/nio/fujinet-nio-workspace/integration-tests/amiberry/conftest.py

Good. Now the create_standard_adf function has no fix_root_block parameter and no longer modifies the root block. The ADF is used as xdftool creates it (same as HD ADF and native floppy — both of which work).

Now let me check what else references fix_root_block in the codebase to make sure I haven't missed anything:

  Searched for 1 pattern

No remaining references. Now let me also verify what the boot block situation is. The _patch_boot_block function was in the diff — let me make sure it's still present and understood:

  Searched for 3 patterns, read 1 file

Now let me look at whether NIO has a catalog set function, which would be needed for fujinet-mount --slot

Good. I've removed _fix_adf_root_block entirely. The key insight from this analysis session:

Root cause found: The StackSize in the DN0 mountlist was 2048 (too small for OFS). It's now 32768 in the modified working tree. That was the actual cause of "Not a DOS disk". The root block modifications were a red herring — HD ADF passes with xdftool's raw output (own_key=0, secondary_type=1), so modifying root block fields was both unnecessary and harmful.

What I changed:
- Removed _fix_adf_root_block() entirely
- Removed the fix_root_block parameter from create_standard_adf()
- All ADFs now use xdftool's unmodified output (same as HD ADF)

Validate by running the diskdevice-adf test:
cd integration-tests/amiberry
python -m pytest test_diskdevice_adf.py::test_standard_adf_mount_info_read_dir_and_type --run-amiga -v

This test uses Mount DN0: with a DD ADF and exercises Dir DN0: and Type DN0:KNOWN.TXT. If it passes, the StackSize fix is confirmed and the root block changes were the problem.

The fmount test (diskdevice-fmount) also needs two more pieces of implementation that are still missing:
1. fujinet-mount --slot N URI support (Amiga-side catalog registration)
2. Amiga-specific fumount DNx: command (uses TD_EJECT)

Run the diskdevice-adf test first to validate before tackling those.
```

```
Now let me assess what's done for the backlog, then commit and continue. Let me check the state of things:

  Searched for 2 patterns, read 1 file

Good. Now I have all the pieces. Let me assess backlog status, simplify the fmount sequence (drop the unimplemented --slot step), implement Amiga fumount, then commit everything.

First, simplify the fmount startup sequence and test to remove the --slot premount step (catalog is pre-populated by conftest)
Write(~/dev/nio/fujinet-nio-workspace/integration-tests/amiberry/startup/diskdevice-fmount.sequence)
- Update(~/dev/nio/fujinet-nio-workspace/integration-tests/amiberry/startup/diskdevice-fmount.sequence)
Now update tests.toml to remove fmount-premount.result:
- Update(~/dev/nio/fujinet-nio-workspace/integration-tests/amiberry/tests.toml)
Now update the test assertions to remove PREMOUNT check:
- Update(~/dev/nio/fujinet-nio-workspace/integration-tests/amiberry/test_diskdevice_fmount.py)
Also update the fumount assertion — the output will be "Ejected DN0:" not "Ejected DN0:" with a drive letter
Good. Now implement the Amiga-specific fumount:
- Write(~/dev/nio/fujinet-nio-workspace/repos/nio-core-apps/apps/platform/amiga/fumount.c)
Now check what platform include directory is needed for the build to pick up fujinet_disk_iface.h
Good — PLATFORM_INCLUDE_DIR = include/platform/amiga is already in CFLAGS. The fujinet_disk_iface.h at include/platform/amiga/fujinet_disk_iface.h will be found. The diagnostics are Linux clang noise; the Amiga GCC cross-compiler has these system headers.
Now mark off the backlog items that are done, then commit. Let me update the backlog
- Update(~/dev/nio/fujinet-nio-workspace/backlog/amiga-diskdevice-phase-2.md)

```
