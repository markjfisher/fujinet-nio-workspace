# Adversarial review — Architecture Spine (Amiga NIO broker)

**Content:** `_bmad-output/planning-artifacts/architecture/architecture-fujinet-nio-workspace-2026-08-22/ARCHITECTURE-SPINE.md`  
**Lens:** adversarial (two implementers, one level down; every pair is a hole)  
**Also consider:** broker cut-over (Stages 1–4), brownfield `fn_transport` / disk idle-close  
**Stance:** do not invent a replacement architecture. Flag where the spine’s ADs fail to prevent incompatible-but-legal implementations of the *existing* cut-over.  
**Verdict:** **FAIL** — thirteen ADs do not pin the shared ABI shape, the shim’s wire bytes, context ownership under the current `void` transport API, or the Stage 3–4 close/session mutation. Two units can obey every AD to the letter and still miss each other on the wire.

Authoritative prose in `docs/amiga/nio-broker-architecture.md` already closes several of these. The spine explicitly says not to treat itself as a second design, then hands implementers *only* the AD box. Units one level down (Stage 1 ABI, Stage 2 broker, Stage 3 shim, Stage 4 disk idle-close) will bind the ADs, not the prose appendix. That gap is the attack surface.

---

## Method

Construct two units that:

1. cite every adopted AD as satisfied,
2. never add serial/Zorro fields to the public `IORequest`,
3. never parse DiskService inside the broker,
4. still ship incompatible shared data, dual ownership, or two mutation paths for one entity.

Pairs below are holes to close with a new or tightened AD (or by lifting a locked clause from the architecture doc into an AD). Deferred rows that allow divergence are holes, not polite postponements.

---

## Two-unit constructions

### Pair 1 — `FujiNetNIORequest` layout (clashing shared-data shape)

**Unit A — Stage 1, driver header.** Owns `amiga/include/fujinet_nio_device.h`. Base type `struct IORequest`; `FUJINET_NIO_CMD_EXCHANGE = CMD_NONSTD + 0`; field order as in architecture §2; `fn_pad[3]`; `fn_struct_size = sizeof(struct FujiNetNIORequest)`.

**Unit B — Stage 3, lib shim.** AD-1 forbids a link dependency on the driver. AD-3 only names the struct and forbids hardware fields. B redeclares a “compatible” `FujiNetNIORequest` locally, using `IOStdReq` so `io_Data`/`io_Length` can carry buffers (normal Amiga device style), or inserts `fn_nio_error` before the pointer fields for alignment. Exact-match `fn_struct_size` (Consistency Conventions) then either rejects every `DoIO` (`IOERR_BADLENGTH`) or, if sizes coincide, silently mis-parses pointers.

**ADs obeyed:** AD-1 (shim names the device string only), AD-3 (one command, no baud/SLIP on the struct), AD-12 (unrelated).  
**Hole:** no AD owns a single canonical layout, base type (`IORequest` not `IOStdReq`), command numeric, packing, or which repo’s header is included by the shim.

### Pair 2 — EXCHANGE payload: FujiBus vs SLIP (clashing shared-data shape)

**Unit A — Stage 3 shim.** Today `fn_transport.c` SLIP-encodes before `serial.device`. AD-2 binds the *broker worker and public ABI*, not the shim. A keeps SLIP in the shim and submits SLIP bytes as `fn_request_data`.

**Unit B — Stage 2 serial backend.** AD-2 + architecture §11: `backend_exchange` SLIP-encodes opaque FujiBus. B SLIP-encodes again (or treats input as already framed and never finds `END`).

**ADs obeyed:** AD-2 (broker does not parse service IDs; bytes are opaque *to the broker*), AD-3 (no SLIP fields on the `IORequest`), AD-12 (framing compiled into the backend).  
**Hole:** payload *meaning* of `fn_request_data` is not bound on the shim. Cut-over can ship double-SLIP or raw-UART vs FujiBus without violating any AD.

### Pair 3 — Two owners of the in-flight `IORequest`

**Unit A — lib as process-local BSS.** Implements AD-5 with the existing `fn_transport_init(void)` / `fn_transport_exchange_buffers(...)` signatures (`fn_platform.h`). One hidden `FujiNetNIORequest`. Fine for a CLI process; fatal if the same objects are linked as a shared `.library` or if two tasks in one address space call the API.

**Unit B — disk device.** AD-5 says the disk device “must use its own context.” Call sites must stay unchanged (architecture §3, not an AD). B either (1) relies on a separate static link (own BSS) — works only while the lib is not a shared library — or (2) `OpenDevice("fujinet-nio.device")` itself to get a private `IORequest`, violating AD-1’s *intent* while a lawyer can claim AD-1 “apps and disk depend only on the lib” if B wraps the open in a two-line helper still named from disk sources.

**ADs obeyed:** AD-5 (each “independently usable transport context” owns a request — undefined what creates a context when the API has no `ctx`), AD-1 (B’s helper still “the lib” if they move the open into `fn_transport.c` but keep one global).  
**Hole:** AD-5 names an entity (`fn_amiga_transport`) the spine never binds to a C API, allocation rule, or “static link / not a shared library” rule. Two owners of one `IORequest` is how the serial race returns one layer up.

### Pair 4 — Abort: two mutation paths for one completion (conflicting state-mutation)

**Unit A — broker.** AD-4: `io_Error = IOERR_ABORTED`, `fn_nio_error = FN_ERR_ABORTED`, length 0. AD-6: abort is completion-status, not remote rollback. Queued abort: A replies from `AbortIO`; in-progress: worker overwrites and replies (architecture §5.1 — not an AD). Alternate legal A′: worker always replies; `AbortIO` only sets a flag (also AD-6).

**Unit B — shim.** AD-9: if `DoIO` returns `io_Error != 0`, return a “mapped local/device failure” and zero length; do not return stale `fn_nio_error`. B maps every non-zero `io_Error` to `FN_ERR_IO` / `FN_ERR_UNKNOWN` and never reads `fn_nio_error`. Abort is indistinguishable from `IOERR_BADLENGTH`. Alternate B′ special-cases `IOERR_ABORTED` → `FN_ERR_ABORTED`.

**ADs obeyed:** both AD-4 (broker fields) and AD-9 (shim mapping). They contradict for the abort path through the shim.  
**Hole:** no single mutation path from `AbortIO` to the FN code callers see.

### Pair 5 — `CloseDevice` vs `backend_close` vs idle-close (conflicting state-mutation)

**Unit A — Stage 3 disk, idle-close still present (Stage 4 not done).** Worker calls `fn_transport_close` when the FIFO empties. That is `CloseDevice` on the broker context (AD-5 open flag). A treats that as “wire released / session reset” because that is what the brownfield serial path does (`fn_stream_session_close` in `fn_transport_close`).

**Unit B — Stage 2 broker.** AD-7: `OpenCnt` 0 does **not** `backend_close`. Serial stays exclusive; SLIP/session stays dirty. Next `OpenDevice` + exchange continues the same physical session.

**ADs obeyed:** AD-7, AD-10 (Stage 4 is later, so idle-close at Stage 3 is allowed), AD-5 (context owns the open flag).  
**Hole:** two writers of “is the session clean?” — shim close vs backend close. Stage 3 cut-over with leftover idle-close is a different machine than Stage 4, and AD-10 does not pin that CloseDevice ≠ session reset.

### Pair 6 — Frame bound and oversize reject (clashing shared-data shape)

**Unit A — broker BeginIO.** Consistency table: lengths `UWORD` while `FN_MAX_PACKET_SIZE` is 512. A rejects `fn_request_length > 512` with `IOERR_BADLENGTH`.

**Unit B — lib on amiga-gcc.** Brownfield `include/fn_protocol.h`: `FN_MAX_PACKET_SIZE` is **1024** unless `__CC65__`. B submits legal FujiBus frames up to 1024.

**ADs obeyed:** AD-2 (opaque bytes; no requirement to share one header), Stack row “512” is not an AD Rule.  
**Hole:** the spine’s 512 contradicts the Amiga library the cut-over must keep passing. Two owners of the bound (`fujinet-nio.h` / `fn_protocol.h` vs broker header).

---

## Findings

```json
[
  {
    "lens": "adversarial",
    "location": "AD-3; Consistency Conventions; Structural Seed; Capability map (Public broker ABI)",
    "trigger_condition": "No AD pins a single canonical FujiNetNIORequest: base type, field order, packing, CMD numeric, or which header the shim includes.",
    "guard_snippet": "Lift architecture §2 into an AD: IORequest not IOStdReq; exact field list; FUJINET_NIO_CMD_EXCHANGE = CMD_NONSTD+0; shim includes the driver public header (or a generated copy with a single owner); fn_struct_size is that header's sizeof.",
    "potential_consequence": "Stage 1 and Stage 3 ship two layouts; every exchange is BADLENGTH or silent pointer smash — cut-over looks like 'broker up' and still dead."
  },
  {
    "lens": "adversarial",
    "location": "AD-2 (binds worker + public ABI only)",
    "trigger_condition": "Opaque FujiBus is required of the broker, not of fn_transport_exchange_buffers; the current shim SLIP-encodes before the wire.",
    "guard_snippet": "Tighten AD-2 (or add AD): fn_request_data/fn_response_data are unframed FujiBus on both sides of EXCHANGE; SLIP exists only inside the serial backend; Stage 3 must delete shim SLIP.",
    "potential_consequence": "Double-SLIP or SLIP-vs-FujiBus at cut-over; integration assertions unchanged (AD-10) while the byte contract flipped."
  },
  {
    "lens": "adversarial",
    "location": "AD-5; Design Paradigm mermaid; architecture §3 vs fn_platform.h",
    "trigger_condition": "AD-5 requires per-context IORequest ownership but the brownfield API is void/global; 'independently usable transport context' is undefined; shared .library is unmentioned.",
    "guard_snippet": "AD: Amiga fn_transport remains per-link-unit BSS (not a shared library) OR the API grows an explicit context the disk device owns; two tasks must not call the void API; disk must not OpenDevice the broker.",
    "potential_consequence": "FLS + disk.device share one FujiNetNIORequest again — the serial race relocated onto the broker."
  },
  {
    "lens": "adversarial",
    "location": "AD-4 vs AD-9",
    "trigger_condition": "Broker abort pair is pinned; shim 'mapped local/device failure' on any io_Error != 0 is free to drop FN_ERR_ABORTED.",
    "guard_snippet": "One AD table: shim maps IOERR_ABORTED→FN_ERR_ABORTED, IOERR_OPENFAIL→FN_ERR_NOT_FOUND (AD-13), IOERR_NOCMD/BADLENGTH/invalid→FN_ERR_INVALID, else FN_ERR_IO; never return stale fn_nio_error; length 0 whenever io_Error != 0.",
    "potential_consequence": "Abort tests and callers disagree; Stage 2 suite can pass while Stage 3 tools never see 0x13."
  },
  {
    "lens": "adversarial",
    "location": "AD-6; architecture §5.1 (not an AD)",
    "trigger_condition": "Abort ReplyMsg owner (AbortIO vs worker) and Disable flag protocol are not in the spine Rule.",
    "guard_snippet": "AD: exactly one ReplyMsg; queued abort replies from AbortIO after FIFO remove under Disable; in-progress abort never ReplyMsg from AbortIO; dispatched flag as in architecture §5.1.",
    "potential_consequence": "Double-reply or hung DoIO — Exec-level corruption, not an FN error."
  },
  {
    "lens": "adversarial",
    "location": "AD-7, AD-10 Stage 3 vs Stage 4",
    "trigger_condition": "Idle-close CloseDevice is legal until Stage 4; AD-7 keeps backend+session open at OpenCnt 0. Spine never says CloseDevice is not a framing reset.",
    "guard_snippet": "AD: only backend_close resets framing/session; fn_transport_close/CloseDevice must not be treated as session reset; Stage 3 cut-over must not rely on idle-close for serial fairness; Stage 4 is required before claiming brownfield close semantics.",
    "potential_consequence": "Stage 3 integration: first exchange after disk idle-close is a dirty SLIP stream; flaky catalog/mount that 'only happens after FLS'."
  },
  {
    "lens": "adversarial",
    "location": "Stack / Consistency: FN_MAX_PACKET_SIZE 512; AD-2/AD-3 silent on the bound",
    "trigger_condition": "Spine pins 512; Amiga lib (non-cc65) uses 1024 in fn_protocol.h. No AD names a single included constant for BeginIO oversize.",
    "guard_snippet": "AD: broker and shim use the same FN_MAX_PACKET_SIZE from fujinet-nio-lib; reject fn_request_length > that value; do not silently shrink Amiga to 512 to match cc65.",
    "potential_consequence": "Legal lib frames fail BeginIO after cut-over; or broker accepts 1024 while tests assume 512."
  },
  {
    "lens": "adversarial",
    "location": "AD-3; Deferred timeout; brownfield FN_AMIGA_BAUD 19200, serial unit 0, 8N1, no XON",
    "trigger_condition": "Backend-neutral ABI forbids baud on the IORequest and therefore never ratifies the serial parameters the old shim already ships.",
    "guard_snippet": "AD (serial backend only, not public ABI): inherit current fn_transport serial contract (unit 0, FN_AMIGA_BAUD default 19200, 8N1, XON off) and a single timeout policy or 'must match pre-cut-over fn_transport'; pin timer.device as the timeout source if that is the brownfield.",
    "potential_consequence": "Stage 3 assertions unchanged (AD-10) against a 57600 or different-unit backend — silent hang, not a compile error."
  },
  {
    "lens": "adversarial",
    "location": "AD-12; architecture §9",
    "trigger_condition": "Compiling fn_session.c by path into both lib and broker does not forbid the Stage 3 shim from keeping its own session object while the backend also owns one.",
    "guard_snippet": "AD: after Stage 3 the Amiga shim must not run SLIP/session; session state lives only in the serial backend; lib copy of fn_session.c is for non-broker targets.",
    "potential_consequence": "Two session machines flush/open independently; exclusive serial plus leftover shim session_close fights AD-7."
  },
  {
    "lens": "adversarial",
    "location": "Capability map: Public broker ABI → fujinet_nio_device.h AND fujinet-nio.h; AD-4 Stage 1 constant",
    "trigger_condition": "Two files own FN-space codes; broker may define 0x13 locally 'coordinated with' the lib.",
    "guard_snippet": "AD: FN_ERR_* exist only in fujinet-nio.h; device header includes it or duplicates nothing; broker must not invent FN constants.",
    "potential_consequence": "0x13 collision or shim/broker disagree on abort vs UNKNOWN (0xFF) — AD-4's Prevents clause fails in the other header."
  },
  {
    "lens": "adversarial",
    "location": "AD-13 vs OpenDevice name; Deploy/env; AD-11 install name",
    "trigger_condition": "Load path DEVS:fujinet-nio.device vs OpenDevice(\"fujinet-nio.device\") vs DEVS: qualified OpenDevice is unpinned in an AD Rule.",
    "guard_snippet": "AD: OpenDevice name is FUJINET_NIO_DEVICE_NAME \"fujinet-nio.device\" (no DEVS: prefix); environment LoadResident/bind of DEVS:fujinet-nio.device; missing → IOERR_OPENFAIL → FN_ERR_NOT_FOUND only.",
    "potential_consequence": "Bootstrap loads a file the shim never opens; cut-over looks like NOT_FOUND with the binary sitting in DEVS:."
  },
  {
    "lens": "adversarial",
    "location": "AD-10 overlap; Stage 2 isolation",
    "trigger_condition": "'Do not dual-open serial.device' is an operational wish, not a compile/link/install fence.",
    "guard_snippet": "AD: Stage 3 is the first binary in which fn_transport references serial.device nowhere; Stage 2 broker tests are a separate image; mixing DEVS: broker + pre-Stage-3 lib on one guest is a failed config, detected (e.g. shim refuses if serial.device already exclusive / version stamp).",
    "potential_consequence": "The original race during 'overlap' — the cut-over's actual failure mode — remains easy to run by accident."
  },
  {
    "lens": "adversarial",
    "location": "Deferred: exec/errors.h invalid-request; fn_struct_size accept-smaller; backend C signatures; expunge drain",
    "trigger_condition": "Deferred items are exactly the Stage 2 BeginIO matrix and worker/backend seam; two Stage 2 implementers pick IOERR_* and drain/abort differently.",
    "guard_snippet": "Either pin the native invalid-request symbol now (one exec/errors.h name) and 'exact-match only' until a dated extension AD, or split Stage 2 so tests cannot pass against two matrices. Do not leave Abort/expunge ReplyMsg in Deferred if AD-8's Prevents clause is an unload race.",
    "potential_consequence": "Isolated broker tests pass on implementer A and fail on B; shim mapping (AD-9) cannot be written until the native codes exist."
  },
  {
    "lens": "adversarial",
    "location": "AD-9 BeginIO; architecture §2.1 NULL+nonzero / flags / pad",
    "trigger_condition": "Spine defers the native invalid-request symbol and does not list which BeginIO rows zero fn_response_length vs leave fn_nio_error undefined-until-ReplyMsg.",
    "guard_snippet": "AD: copy the §2.1 matrix into the spine (or bind 'BeginIO matrix in architecture §2.1 is normative, including immediate reject without queue'); accepted requests must not be read by callers until ReplyMsg.",
    "potential_consequence": "Shim and tests sample fn_nio_error on a still-queued request; 'stale error' AD-9 cannot be implemented consistently."
  },
  {
    "lens": "adversarial",
    "location": "AD-8 vs Deferred expunge drain/abort",
    "trigger_condition": "Invariant 'no unload race' without a chosen refuse-vs-defer or abort-queued-on-expunge path.",
    "guard_snippet": "AD: expunge returns without freeing if OpenCnt>0 or queue/in-progress non-empty (refuse), OR defers until drain; pick one; AbortIO of queued work is not implied.",
    "potential_consequence": "One binary RemDevice's under a live DoIO; the other leaks the device node forever — both claim AD-8."
  }
]
```

---

## Findings (readable)

### 1. Canonical `FujiNetNIORequest` is not an AD

AD-3 names the command and forbids hardware fields. It does not decide `IORequest` vs `IOStdReq`, field order, `CMD_NONSTD+0`, or a single includable header. Pair 1 is the cut-over ABI fork.

### 2. Shim payload shape is unbound

AD-2’s Binds line is the broker. The Amiga shim still SLIPs today. Pair 2 is double-framing at Stage 3 with every AD green.

### 3. Transport context vs `void` API

AD-5’s entity has no constructor in the spine. Brownfield `fn_transport_*` is global. Pair 3 re-creates a shared `IORequest` if anyone ships a shared library or two tasks.

### 4. AD-4 and AD-9 fight on abort

Broker sets `FN_ERR_ABORTED`. Shim is told to ignore `fn_nio_error` whenever `io_Error != 0`. Pair 4: two completion mappings.

### 5. Abort `ReplyMsg` owner

AD-6 says abort is not rollback. It does not say who replies. Double-`ReplyMsg` is legal-by-spine.

### 6. Stage 3 idle-close vs AD-7 session

CloseDevice is not `backend_close`. Framing used to die in `fn_transport_close`. After the broker owns the wire, it does not. Pair 5 is the Stage 3–4 trap.

### 7. `FN_MAX_PACKET_SIZE` 512 vs Amiga 1024

Stack/consistency assert 512. The library the cut-over keeps is 1024 on amiga-gcc. Pair 6.

### 8. Serial unit/baud/timeout not inherited

AD-3 correctly keeps them off the public ABI and therefore off the spine. Cut-over still needs the *backend* to match `fn_transport.c` (19200, unit 0, 8N1, no XON) or Stage 3’s “assertions unchanged” is false.

### 9. Two session objects after AD-12

Path-compile without `fn_internal.h` does not remove shim session. Two mutators of framing state.

### 10. Dual header ownership of `FN_ERR_*`

Capability map lists both headers. AD-4’s 0x13 can be minted twice.

### 11. Device name string vs `DEVS:` path

Load vs `OpenDevice` names are conventional in prose, not a Rule. Easy miss at bootstrap.

### 12. Overlap dual-open is policy, not a gate

AD-10 Prevents the race; nothing makes mixed Stage 2+pre-3 installs fail closed.

### 13. Deferred BeginIO symbol / size policy / backend signatures / expunge drain

These are Stage 2’s shared seams. Leaving them Deferred is permission for two brokers.

### 14. BeginIO matrix not in the spine

AD-9 points at the architecture doc. Units that only bind ADs do not share the matrix.

### 15. AD-8 refuse vs defer

Both satisfy “no unload race” and produce opposite RemDevice behavior.

---

## Cut-over-specific holes (not a new architecture)

The cut-over is Stage 3: `fn_transport` stops opening `serial.device`. The spine’s ADs protect dependency direction and FIFO atomicity. They do **not** protect:

| Cut-over need | Spine coverage |
| --- | --- |
| Identical bytes on EXCHANGE as today’s FujiBus-before-SLIP | AD-2 binds broker only |
| Identical serial line settings | Forbidden on ABI; not pinned for backend |
| Identical timeout | Deferred |
| Identical max frame on Amiga | Spine 512 vs lib 1024 |
| Shim includes Stage 1 header | Two ABI files, no include rule |
| Close/idle no longer resets SLIP | AD-7 vs leftover Stage 3 idle-close |
| Abort visible as `FN_ERR_ABORTED` to `fn_*` callers | AD-9 mapping hole |
| Cannot boot mixed old shim + new broker on one serial | AD-10 text only |

Closing these is tightening ADs (or marking architecture §2 / §3 / §5.1 / §11 / current `fn_transport.c` serial contract as **normative for implementers**). It is not a new broker shape.

---

## What already holds

AD-1 dependency direction, AD-3 “no serial fields on the public `IORequest`”, AD-6 single FIFO worker / no `IOF_QUICK` for EXCHANGE, AD-11 Option A binaries, AD-13 missing-broker ≠ serial-busy: those Rules do prevent the divergences they name. The failure is the unnamed seams between units that still have to meet at `DoIO`.

---

## Suggested AD closures (tighten, don’t redesign)

1. **ABI AD:** architecture §2 struct + command numeric + `IORequest` base + single header ownership + shim include.  
2. **Payload AD:** unframed FujiBus on EXCHANGE; SLIP only in serial backend; Stage 3 removes shim SLIP/session.  
3. **Context AD:** how disk vs CLI get distinct `FujiNetNIORequest`s under the current `void` API; no shared `.library` global.  
4. **Shim map AD:** `io_Error` → FN table including abort; one ReplyMsg protocol.  
5. **Serial-backend brownfield AD:** unit, baud default, framing reset only on `backend_close`; Stage 3 CloseDevice ≠ reset.  
6. **Bound AD:** one `FN_MAX_PACKET_SIZE` for Amiga broker+lib.  
7. **Stage 2 fence:** mixed old shim + broker on one guest is invalid; BeginIO native symbols pinned or tests cannot claim AD-9.

---

## Lens JSON (canonical array)

See the fenced `json` block above (15 findings). Empty adversarial list would have been a process failure; this pass is not empty.
