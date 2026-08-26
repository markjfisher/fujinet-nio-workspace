---
title: 'BWC Amiga fetch-latency instrumentation and reduction'
type: 'feature'
created: '2026-08-26'
status: 'in-progress'
review_loop_iteration: 0
baseline_commit: 432c392dcf3e0cb3a0967b57ecae7c951a4b3572
context:
  - '{project-root}/backlog/bwc-amiga-fetch-latency-and-interpolation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Amiga Bouncy World client pays ~200 ms per snapshot fetch and renders only when a fetch lands (~5 fps). The server answers instantly; the cost is client/transport side (prime suspect: ~40 ms `network_retry_pause()` charged per empty poll in `read_response_min()`), but the split is unverified.

**Approach:** Amiga-only: (1) a keyboard-toggleable on-screen instrumentation overlay attributing per-fetch wall time across retry pauses vs device reads vs other, plus render time per frame; (2) measure a live session, then reduce the dominant measured cost so the fetch interval improves ≥2× (or document why the floor belongs to the transport); instrumentation stays available behind the runtime flag. Snapshot interpolation is deferred separately.

## Boundaries & Constraints

**Always:**
- All instrumentation and latency changes gated to `__AMIGA__`; atari/bbc/linux/msdos loop, fetch path, rendering byte-identical.
- Instrumentation is a runtime flag (keyboard-toggleable overlay), not a separate build; must not perturb measurements beyond its own display cost.
- Measure first with the live instrumented client; gate the reduction choice on recorded findings.
- Record measured numbers (cost attribution, before/after fetch interval) in the task review.
- Keep instrumentation compiled in behind the runtime flag after reduction lands.

**Ask First:** <!-- HALT if triggered -->
- Dominant measured cost requires touching transport/library code outside `repos/bounce-world-client-nio`.
- Findings contradict the retry-pause hypothesis so fundamentally that the reduction target is unclear.

**Never:**
- No server changes; wire contract fixed as today.
- No snapshot interpolation / loop splitting / extrapolation (deferred goal in `_bmad-output/implementation-artifacts/deferred-work.md`).
- No behaviour change for other targets' loop or fetch path.
- Do not regress the ROTATION decode path (`shape_decode.h`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Overlay toggle | Overlay key pressed on Amiga | Overlay appears/disappears next frame; off state costs nothing | N/A |
| Empty poll | `fn_read` returns NOT_READY/BUSY/zero bytes | Counted in overlay; pause strategy follows reduced-cost policy | Never spins unbounded without yield |
| Write retry | `request_client_data` attempt fails | Counted; ≤3 attempts as today unless findings justify change | Falls back per current behaviour |

</frozen-after-approval>

## Code Map

Repo: `repos/bounce-world-client-nio`. Platform gating via source dirs + `#ifdef __AMIGA__` (only defined in `CFLAGS_amiga`, `makefiles/build.mk:136`). Source `$NIO_WORKSPACE/scripts/env.sh` first.

- `src/common/run_simulation.c:40-62` -- shared loop: fetch → status → render-if-step-advanced → `handle_kb()`. Render-time hook site.
- `src/common/world.c:26-33` -- `fetch_client_state()`: memset + `request_client_data()` + `read_response_min(app_data,1,APP_PAYLOAD_SIZE)`. Per-fetch timing wraps this.
- `src/common/connection.c:89-125` -- `request_client_data()`: `fn_write` `x-w <id>\n`, ≤3 attempts, pause between.
- `src/common/connection.c:295-389` -- `read_response_min()`: NOT_READY/BUSY (`:315-318`) and zero-byte (`:332-335`) each pay `network_retry_pause()`; check eager-over-return guard. Prime lever.
- `src/amiga/delay.c:7-23` -- 1×WaitTOF ≈ 20 ms PAL; `network_retry_pause()` = 2×TOF.
- `src/include/data.h` -- don't reorder externs (atari `data.s` mirrors them).
- `src/common/keyboard.c:99-106` -- Amiga-only `'V'` toggle pattern to copy. Text: `cputsxy/revers` (`amiga/conio.c:219-256`), `printu16` (`show_info.c:24-29`); overlay redraws after each swap (back buffer).
- No timing helpers exist; add amiga-only wall-time primitive (timer.device/DOS DateStamp).
- `scripts/drive_bwcn.py` (+ `tools/amiga_emulator/keyboard.py`, `scripts/amiberry-type`) -- live-session tooling.

## Tasks & Acceptance

**Execution:**
- [x] New amiga-only timing primitive + `__AMIGA__`-gated counters in `connection.c`/`world.c`/`run_simulation.c` -- retry-pause hits, write retries, `fn_read` calls, bytes read, per-fetch wall time, render time per frame. Inert without `__AMIGA__`; near-zero cost when disabled.
- [x] `keyboard.c` + amiga-only overlay drawing -- runtime toggle key ('V' pattern); draws counts/timings via `cputsxy`/`printu16`, screenshot-readable through drive tooling.
- [x] Live measurement under Amiberry + `drive_bwcn.py` -- capture overlay showing where ~200 ms goes; record attribution in task review before changing any latency code.
- [ ] `connection.c` / `delay.c` reduction of the dominant measured cost -- candidate levers in expected order: shrink `network_retry_pause` (2×TOF → 1×TOF or bounded busy-poll), read the framed response in fewer calls, fix `read_response_min` eager-over-return extra round trips.
- [ ] Re-measure same-session after reduction; keep overlay available behind the runtime flag; record improved interval in task review.

**Acceptance Criteria:**
- Given the instrumented client fetching from the live server, when the operator reads the overlay, then the ~200 ms is attributed across retry pauses vs device reads vs other and the numbers appear in the task review.
- Given the same live session setup, when reduction lands, then measured fetch interval improves ≥2× or the review records why the floor belongs to the transport.
- Given the overlay toggled off, then rendering and fetch behaviour match baseline.
- Given any other target built and run versus baseline, then behaviour and rendering are unchanged.
- Given `make test-host`, `make linux`, `make amiga`, then all pass.

## Design Notes

Overlay rows mirror the cost buckets (retries, reads, bytes, fetch ms, render ms) on reserved bottom rows via `cputsxy`, redrawn each frame while enabled. Wall-time granularity must resolve single-digit-ms deltas. Counters are plain globals bumped in the existing NOT_READY/BUSY/zero-byte branches — no control-flow changes beyond the gated pause-policy swap that follows measurement.

## Verification

**Commands:** (from `repos/bounce-world-client-nio`, after `source "$NIO_WORKSPACE/scripts/env.sh"`)
- `make test-host` -- all host tests pass.
- `make linux` -- builds; shared-code changes compile inert off-Amiga.
- `make amiga` -- builds `build/bwcn.amiga`.
- Live session via `scripts/drive_bwcn.py` under Amiberry (defaults `wb32`/`a1200-030`) -- overlay readable in screenshots; before/after fetch intervals captured.

**Manual checks:**
- `git diff` of shared files shows only `#ifdef __AMIGA__` additions (other targets byte-identical).
- Cost attribution + interval improvement (or documented transport floor) recorded in the task review per `docs/agent-test-policy.md`.

## Spec Change Log

- 2026-08-26: Live Amiberry baseline captured with the `O` overlay toggle after `scripts/drive_bwcn.py`. Two representative completed fetches show 0 retry pauses, 0 write retries, 1 `fn_read`, and 60/65 bytes. The fetch interval/fetch wall/read-call values were 140/121/47 ms and 120/181/96 ms respectively; render time was 8/9 ms. Screenshots are retained at `/tmp/kilo/bwcn-latency-before-current/70-overlay.png` and `80-overlay-confirm.png`. This contradicts the retry-pause hypothesis; no latency-policy change has been made pending the spec's Ask First decision.
