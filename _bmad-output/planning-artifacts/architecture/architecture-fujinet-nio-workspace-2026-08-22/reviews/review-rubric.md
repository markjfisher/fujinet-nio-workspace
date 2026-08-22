# Good-spine rubric — Amiga NIO broker

- **Spine:** `ARCHITECTURE-SPINE.md`
- **Altitude:** feature → epics/stories
- **Cross-check (no redesign):** `docs/amiga/nio-broker-architecture.md`, `backlog/nio-broker.md`
- **Brownfield spot-check:** `repos/fujinet-nio-lib/include/fujinet-nio.h`, `include/fn_protocol.h`
- **Verdict:** concerns

The spine ratifies the locked cut-over (who owns the wire, two error domains, FIFO worker, staged overlap ban, Option A, load order). It is not a clean pass: a few load-bearing source invariants never became `AD`s, one Stack pin fights the Amiga library bound, and several Deferred items can still fork Stage 2 stories.

---

## Checklist

| Criterion | Result |
| --- | --- |
| Fixes real divergence points for the level below; misses none that would let two epics/stories choose incompatibly | **Concerns** |
| Every `AD` Rule is enforceable and actually prevents its stated divergence | **Pass** (with two weak Rules) |
| Nothing under Deferred could let two units diverge | **Fail** |
| Named tech is verified-current | **Concerns** |
| Ratifies rather than contradicts brownfield | **Concerns** |
| Spec capabilities covered | **N/A** (no spec package) |
| Inherited parent `AD`s not weakened | **N/A** (no parent spine) |
| Every dimension this altitude owns is decided, deferred, or an open question (esp. deploy/env) | **Concerns** |

---

## What it gets right

AD-1, AD-2, AD-5, AD-6 (wire atomicity), AD-7, AD-10, AD-11, AD-13 are the actual epic forks: clients vs broker vs backend, opaque payloads, no shared global `IORequest`, no dual `serial.device` during overlap, Option A until coexistence is required, missing broker ≠ serial-busy.

AD-4 abort pair (`IOERR_ABORTED` + `FN_ERR_ABORTED` `0x13`) matches `fujinet-nio.h` (gap at `0x13`; `FN_ERR_UNKNOWN` remains `0xFF`) and the architecture locked table.

Staging in AD-10 matches `backlog/nio-broker.md` gates. Deploy/env is not silent: Startup-Sequence / `S:User-Startup` / Amiberry bootstrap, `DEVS:fujinet-nio.device`, serial exclusive while resident.

The file correctly refuses to be a second design (`Authoritative prose remains docs/amiga/nio-broker-architecture.md`). That does **not** excuse missing `AD`s for BMad work-items that will cite this spine rather than re-read 742 lines.

---

## Findings

### Critical

None. The cut-over cannot be implemented as two competing architectures from this spine alone.

### High

**H1 — AbortIO exactly-once `ReplyMsg` is not an invariant here**  
Source §5 / §5.1 (queued vs in-progress vs completing, `Disable` flag-check, AbortIO must not reply after worker dispatch) is the other half of the race that AD-6’s Prevents does not cover. AD-6 Prevents interleaved send/receive; AD-6 Rule only says abort is completion-status, not remote rollback. Two Stage 2 stories (AbortIO vs worker) can still double-complete.  
**Disposition:** autofix — add an `AD` (do not reuse a retired ID): `ReplyMsg` exactly once; queued abort replies from AbortIO; in-progress abort finishes the physical exchange then worker replies abort; after dispatched/completing, AbortIO never `ReplyMsg`. Cite §5.1.

**H2 — Stack/`UWORD` pin of `FN_MAX_PACKET_SIZE` = 512 contradicts Amiga brownfield**  
`fn_protocol.h`: 512 only under `__CC65__`; **else 1024** (Amiga gcc). Spine Stack and Consistency Conventions pin 512. Architecture §2 says the same. Broker BeginIO (`fn_request_length > FN_MAX_PACKET_SIZE`) vs lib transport can disagree. `UWORD` lengths remain valid at 1024; the bound is the fork.  
**Disposition:** discuss — ratify Amiga `FN_MAX_PACKET_SIZE` (1024 unless an Amiga override exists) or name an explicit broker cap and why it is not the lib macro; do not leave 512 as if it were the Amiga value.

**H3 — Deferred items that Stage 2 stories can choose incompatibly**  
- Exact `exec/errors.h` symbol for generic invalid-request (flags/pad, NULL+nonzero): tests vs `BeginIO` can pick different `IOERR_*`. AD-4 bans numeric literals but does not name the symbol.  
- Numeric exchange timeout and timer source: serial backend vs isolated broker tests vs integration timing. Architecture requires internal timeout; the value is user-visible (`FN_ERR_TIMEOUT`).  
- Expunge drain/abort beyond refuse-while-busy: AD-8 allows deferred **or** refused; two stories can ship different operator-visible unload.  
- Concrete `backend_*` C signatures: two Stage 2 files can invent different calling conventions while matching §11 prose.  
**Disposition:** discuss — promote timeout (or “inherit current Amiga serial timeout”) and the invalid-request `IOERR_*` to `AD`s or a single named Stage 2 ABI story that other stories must not invent; keep signatures deferred only if one story owns `nio.device/` exclusively. Expunge: pick refuse-until-idle **or** drain-then-expunge as the Stage 2 rule.

### Medium

**M1 — Public ABI gaps not in an `AD`**  
Architecture §2.3: base type `IORequest`, not `IOStdReq`; caller-owned buffers until reply; no broker copy/retain of payload. AD-3 only bans serial/Zorro/SLIP fields and extra commands. Stage 1 header vs Stage 2 worker can still alias buffers or use `IOStdReq`.  
**Disposition:** autofix — fold into AD-3 (or a new AD): `IORequest` not `IOStdReq`; caller-owned in-place buffers; worker must not retain payload after `ReplyMsg`.

**M2 — AD-8 / AD-9 Rules are not fully local**  
AD-8 “deferred or refused” does not pick a policy (see H3). AD-9 Rule points at “BeginIO matrix in the architecture doc” and “native invalid-argument symbols at Stage 2” — enforceable only if every story reads the other file; the spine’s own Rule does not prevent two reject matrices.  
**Disposition:** autofix — copy the locked matrix rows that already have symbols (`IOERR_NOCMD`, `IOERR_BADLENGTH`); leave only the unnamed invalid-request row as Deferred/open **or** name it (H3).

**M3 — Serial backend envelope is neither decided, deferred, nor an open question**  
Deploy/env covers load order and exclusivity, not `serial.device` unit, baud, or which timer.device unit the backend uses. Those are not public ABI (AD-3) but they are Stage 2 implementation forks and guest-env setup. Architecture mentions baud only as backend_open configuration, unpinned.  
**Disposition:** defer — add a Deferred/open line: serial unit/baud/timer inherit current Amiga `fn_transport` serial settings unless a later AD says otherwise.

**M4 — `FN_AMIGA_EXPLICIT_LIFECYCLE` unnamed**  
Architecture §3 keeps it meaningful (disk vs CLI close). Spine never decides, defers, or asks. A Stage 3/4 story could drop it.  
**Disposition:** defer — one convention row or Deferred: flag remains; disk owns explicit close; CLI `atexit`.

### Low

**L1 — AD-12 on the capability map under “Public broker ABI”**  
The include-cycle fix is a Stage 1 build constraint, not ABI. Harmless mis-bucket.  
**Disposition:** ignore or autofix the map cell.

**L2 — Stack versions are workspace-relative, not public product pins**  
amiga-gcc + NDK “via `scripts/env.sh`” matches brownfield and the memlog assumption; it is not a verified upstream version. Acceptable for this repo; do not invent a gcc version.  
**Disposition:** ignore.

**L3 — Frontmatter `status: draft`**  
Expected pre-finalize; not a semantic defect.

---

## AD Rule audit (enforceability)

| AD | Prevents vs Rule | Notes |
| --- | --- | --- |
| AD-1 | Match | Code-reviewable `OpenDevice` names. |
| AD-2 | Match | Opaque `fn_request_data` / `fn_response_data`. |
| AD-3 | Match, incomplete | Prevents backend fields; misses `IORequest` vs `IOStdReq` (M1). |
| AD-4 | Match | Symbols + `0x13`; bans numeric `IOERR_*` literals. |
| AD-5 | Match | Per-context request; disk vs CLI. |
| AD-6 | Partial | Prevents interleaving; does not prevent double-reply (H1). |
| AD-7 | Match | Lazy-open; `OpenCnt` 0; reopen after close. |
| AD-8 | Weak | Prevents unload race; Rule allows two policies (H3). |
| AD-9 | Weak | IOF_QUICK + stale `fn_nio_error` are local; reject matrix is off-file (M2). |
| AD-10 | Match | Stage gates match backlog. |
| AD-11 | Match | Option A binaries. |
| AD-12 | Match | Specific, testable. |
| AD-13 | Match | No autoload; `IOERR_OPENFAIL` → `FN_ERR_NOT_FOUND`. |

---

## Deferred vs divergence

Safe as Deferred (not this cut-over’s epic fork): `fn_struct_size` accept-smaller policy; Zorro/HDF; loadable Option B.

Unsafe as Deferred without a single owning story: invalid-request `IOERR_*`; timeout value/source; expunge drain vs refuse; `backend_*` signatures (H3).

---

## Named tech / brownfield

| Named | Check |
| --- | --- |
| AmigaOS 3.1 / 3.2 | Matches `docs/amiga/environment-setup.md`. |
| exec / serial.device / timer.device | Guest-supplied; correct. |
| amiga-gcc + NDK | Workspace toolchain; no public version (L2). |
| fujinet-nio-lib in-tree | Correct. |
| `FN_ERR_ABORTED` `0x13` | Unused in current `fujinet-nio.h`; good. |
| `FN_MAX_PACKET_SIZE` 512 | **Wrong for Amiga** (H2). |
| Device/command/struct names | Match architecture + backlog. |
| Cut-over vs today’s serial-direct shim | AD-10 stages the change; does not pretend brownfield already uses the broker. |

No contradiction of disk-device TD_* ownership or “apps stay on the lib.” Idle-close removal is Stage 4, consistent with backlog.

---

## Dimensions (feature altitude)

| Dimension | Status |
| --- | --- |
| Paradigm / boundaries / deps | Decided (AD-1–3, 11–12) |
| Concurrency / state | Decided except AbortIO reply ownership (H1) |
| Errors | Decided except one native invalid-request symbol (H3) |
| Migration | Decided (AD-10) |
| Deploy / load order | Decided (AD-13 + seed) |
| Serial unit / baud / timer | **Silent** (M3) |
| Infra / guest (Amiberry vs real HW) | Implied by bootstrap; not named as decided/deferred |
| Operations / logging | Partial (remove race `DBG_PRINTF`) |
| Auth | Out of scope (named) |

---

## Gate actions

1. **Autofix:** AbortIO exactly-once `AD`; ABI `IORequest` + caller-owned buffers; BeginIO matrix rows that already have symbols.  
2. **Discuss:** Amiga `FN_MAX_PACKET_SIZE`; timeout; invalid-request `IOERR_*`; expunge refuse vs drain.  
3. **Defer (explicit):** serial unit/baud/timer inherit current shim; `FN_AMIGA_EXPLICIT_LIFECYCLE`; backend C signatures if one story owns `nio.device/`.  
4. **Ignore:** AD-12 map bucket; unpinned gcc; draft status.

Plus 4 more in this file (M4, L1–L3) beyond the high items.
