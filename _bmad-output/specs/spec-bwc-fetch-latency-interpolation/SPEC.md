---
id: SPEC-bwc-fetch-latency-interpolation
companions:
  - ../../../repos/bounce-world-client-nio/docs/snapshot-interpolation.md
  - ../../../docs/agent-test-policy.md
  - ../../../backlog/bwc-amiga-fetch-latency-and-interpolation.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Bouncy World Amiga client: fetch-latency reduction and snapshot interpolation

## Why

**Pain to solve.** The Amiga Bouncy World client pays a ~200 ms fetch round trip and renders only when a fetch lands (~5 fps), so world motion is visibly choppy. Server logs prove the server answers in the same millisecond; the cost is client/transport side — prime suspect the ~40 ms `network_retry_pause()` (2×WaitTOF) charged per `FN_ERR_NOT_READY`/`FN_ERR_BUSY`/zero-byte read in `read_response_min()`. Reclaimed headroom goes to Amiga-only snapshot interpolation so rendering runs at the display's TOF rate while snapshots arrive at whatever rate the transport allows.

## Capabilities

- **CAP-1**
  - **intent:** An operator can see where each fetch's wall time goes during a live Amiberry session via an on-screen overlay (retry-pause hits, `fn_read` calls, bytes read, cycle wall time per fetch, plus render time per frame), screenshot-readable through the drive tooling.
  - **success:** With the instrumented client fetching from the live server, the overlay attributes the ~200 ms across retry pauses vs device reads vs other, and the numbers are recorded in the task review.
- **CAP-2**
  - **intent:** The client can reduce the dominant fetch-latency cost identified by CAP-1.
  - **success:** In the same live session setup, the measured fetch interval improves by at least 2× — or the task review records why the remaining floor belongs to the transport. Instrumentation stays available behind a runtime flag afterwards.
- **CAP-3**
  - **intent:** The Amiga client can render at WaitTOF pace (~50 fps) from blended past snapshots while fetches continue independently at transport rate, via a shapes-at-positions render entry decoupled from `app_payload`.
  - **success:** On Amiga with interpolation enabled, bodies moving in the live world render smoothly at the TOF rate between snapshots and a fresh bounce appears without extrapolation artifacts; on every other target, behaviour and rendering are unchanged versus baseline.
- **CAP-4**
  - **intent:** The client can blend matching shapes between the two most recent snapshots using the wrap-aware matcher, ω-based angle advance with per-packet re-sync, and stall freeze documented in `snapshot-interpolation.md`.
  - **success:** Host unit tests over the pure parts (matcher, blender, angle advance) pass in the existing `tests/host` pattern, and before/after Amiberry captures demonstrate smooth motion where raw-packet rendering showed stepping.

## Constraints

- Server wire changes must be opt-in capability extensions that preserve the
  legacy record layout. The implemented `BODY_ID` capability provides stable
  body identity and deterministic record ordering for Amiga interpolation.
- All instrumentation and interpolation changes are Amiga-only; atari/bbc/linux/msdos loop, fetch path, and rendering stay byte-identical.
- Render clock draws only blends of *past* snapshots; never extrapolate. If packets stall, u clamps at 1.0 and freezes on the newest snapshot.
- Must not regress the 9-byte ROTATION decode path (`shape_decode.h`); angle/omega are consumed by blending but not rendered.
- Instrumentation must not perturb measurements beyond its own display cost.
- Verification follows `docs/agent-test-policy.md`: `make test-host`, `make linux`, `make amiga` all pass.

## Non-goals

- No extrapolation / dead reckoning in any form.
- No ROTATION rendering (deferred goal in `_bmad-output/implementation-artifacts/deferred-work.md`).
- No changes to other targets' behaviour, loop, or fetch path.
- No adaptive jitter buffer: `interp_delay` starts fixed at one packet period; tuning comes later.

## Success signal

In one live Amiberry session against the real server, the operator reads the overlay showing where the former ~200 ms went, the measured fetch interval is at least halved (or its transport floor is documented), and bouncing bodies move smoothly at the TOF frame rate with fresh bounces landing without prediction artifacts — while every other target still behaves exactly as before.

## Assumptions

- Instrumentation ships as a runtime flag (keyboard-toggleable overlay), not a separate build — the ticket states this preference for live A/B comparison in one session.
- The ticket's verified code map (2026-08-26) is accurate as of build time; any drift is corrected during implementation rather than re-specced.
