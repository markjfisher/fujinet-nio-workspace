# Bouncy World Amiga client: fetch-latency instrumentation and snapshot interpolation

Status: `TODO`

## Goal

Reduce the ~200 ms fetch round trip on the Amiga Bouncy World client and
use the reclaimed headroom to render smooth, interpolated motion at the
display's frame rate. Two sequenced goals:

1. **Instrument and reduce** the per-fetch cost so the client knows where
   the ~200 ms goes and shrinks it.
2. **Amiga-only snapshot interpolation** — split the fetch and render
   loops so rendering runs at ~50 fps (WaitTOF-paced) while world
   snapshots continue to arrive at whatever rate the transport allows.

Design background and algorithm live in
`repos/bounce-world-client-nio/docs/snapshot-interpolation.md`
(two-snapshot interpolation, wrap-aware shape matching, angle handling,
prior art). That document is the design record; this ticket is the
actionable scope.

## Non-goals

- No server changes; the server keeps broadcasting authoritative
  snapshots exactly as today.
- No behaviour change for atari/bbc/linux/msdos targets: their loop,
  fetch path, and rendering stay byte-identical.
- No extrapolation/dead reckoning: the render clock only ever draws
  blended *past* snapshots, never predicts.
- No ROTATION rendering (separate deferred goal in
  `_bmad-output/implementation-artifacts/deferred-work.md`); the
  interpolation work must not regress the 9-byte decode path.

## Verified code map (2026-08-26 investigation)

Repo: `repos/bounce-world-client-nio` (branch master).

- `src/common/run_simulation.c:40-62` — main loop:
  `fetch_client_state()` → handle `app_status` → `show_screen()` only
  when `app_payload[0]` (step) advanced → `handle_kb()`. Render rate
  equals fetch rate (~5 fps measured).
- `src/common/world.c:26-33` — `fetch_client_state()`:
  `memset(app_data, 0, APP_DATA_SIZE)` + `request_client_data()` +
  `read_response_min(app_data, 1, APP_PAYLOAD_SIZE)`.
- `src/common/connection.c:89-125` — `request_client_data()`: single
  `fn_write` of `x-w <id>\n`, up to 3 attempts, `network_retry_pause()`
  between attempts.
- `src/common/connection.c:295-360` — `read_response_min()`: blocking
  `fn_read` loop asking for the whole remaining frame each call.
  **Every `FN_ERR_NOT_READY` / `FN_ERR_BUSY` / zero-byte result costs
  `network_retry_pause()` = 2×WaitTOF ≈ 40 ms** (PAL). Prime suspect
  for the ~200 ms round trip.
- `src/amiga/delay.c:7-23` — `wait_vsync()` = WaitTOF (~20 ms PAL);
  `network_retry_pause()` = 2×WaitTOF; `pause(count)` = count TOFs.
- `src/common/display.c:152-229` — `show_screen()`: `swap_buffer()` →
  full/playfield clear → caps-gated `bwc_decode_shapes()` →
  `gfx_show_shape_px(id, x, y)` per shape → clients/broadcast/other
  overlays. Interpolation needs a shapes-at-positions render entry
  decoupled from `app_payload` (decode currently happens inside
  `show_screen`).
- `src/amiga/gfx.c` + `src/amiga/gfx_render.h` —
  `gfx_show_shape_px(id, x, y)` renders one shape at pixel coords
  (block/vector modes); the interpolation render path extends this
  call chain.
- `src/include/data.h:14-16` — `APP_DATA_SIZE` 2304 on Amiga (fits a
  full 240×9-byte world frame + header); `app_payload = &app_data[2]`.
- `src/include/shape_decode.h` — `ShapePos {shape_id, x, y, angle,
  omega}`, `SHAPE_POS_MAX 84`, caps-driven `bwc_decode_shapes()`
  (3/5/9-byte strides). The 9-byte layout is implemented and
  unit-tested; angle/omega land in the struct but are not rendered.

## Measured evidence

- Server log (2026-08-26): `x-w 1` request and 104-byte response land in
  the same millisecond — server response latency is not the bottleneck;
  the ~200 ms is client/transport side.
- Payload step counters advance by exactly 20 per fetch at the observed
  5 Hz poll rate → server simulates at 100 steps/s; the client samples
  every 20th step.
- Round trip measured at ~0.2 s intervals across many packets
  (54.021 → 54.221 → 54.421 → 54.622).
- Cost model: each `network_retry_pause()` ≈ 40 ms; a handful of
  NOT_READY/zero-byte `fn_read` round trips per fetch plausibly accounts
  for most of the 200 ms. **Unverified — instrumentation is the first
  deliverable.**

## Work

### Goal 1: instrument and reduce fetch latency

- [ ] Add Amiga-only timing instrumentation: per-fetch counters for
      `network_retry_pause()` hits, `fn_read` calls, bytes read, and
      cycle wall time, plus render time per frame. Display as an
      unobtrusive on-screen overlay (screenshot-readable via the
      Amiberry drive tooling); must not perturb measurements beyond the
      display cost itself.
- [ ] Run the instrumented client under Amiberry against the live
      server (`repos/bounce-world-client-nio/scripts/drive_bwcn.py`)
      and record where the ~200 ms goes.
- [ ] Reduce the dominant cost based on findings. Candidate levers, in
      expected order: shrink `network_retry_pause()` (2×TOF → 1×TOF or
      bounded busy-poll), avoid partial-read stalls by reading the
      framed response in fewer calls, and re-examine `read_response_min`'
      eager-over-return guard for avoidable extra round trips.
- [ ] Re-measure and record the improved fetch interval; keep the
      instrumentation available behind a runtime flag for future use.

### Goal 2: Amiga-only snapshot interpolation

- [ ] Factor a shapes-at-positions render entry out of `show_screen()`
      so the interpolated loop can draw decoded shapes without touching
      `app_payload` (other targets keep the existing path).
- [ ] Add a two-snapshot buffer (prev/curr `ShapePos` arrays + arrival
      timestamps; ~1.5 KB worst case at 84 shapes × 9 bytes) filled from
      `bwc_decode_shapes()` on each fetch.
- [ ] Restructure the Amiga main loop per the design doc's sketch:
      pump fetch (non-blocking-ish), WaitTOF-paced render of blended
      frames at ~50 fps, `handle_kb()` each frame; other targets keep
      the current loop unchanged.
- [ ] Implement the wrap-aware matcher (equal `shapeId`, nearest to
      previous position advanced by one packet, copy-to-copy across
      seams; implausible moves draw snapshot N directly).
- [ ] Angle handling: advance by ω between packet angles with per-packet
      re-sync (blend-unwrap alternative documented in the design doc).
- [ ] Stall behaviour: `u` clamps at 1.0 — freeze on the newest
      snapshot; never extrapolate.
- [ ] Host-unit-test the pure parts (matcher, blender, angle advance)
      in the existing `tests/host` pattern; live-verify smoothness via
      the Amiberry drive tooling with before/after captures.

## Acceptance criteria

- Given the instrumented client, when fetching from the live server,
  then the overlay reports where the ~200 ms is spent (retry pauses vs
  device reads vs other), recorded in the task review.
- Given the reduction work, when the client runs the same live session,
  then the measured fetch interval improves by at least 2× or the
  review records why the floor is the transport's.
- Given interpolation enabled on Amiga, when bodies move in the live
  world, then motion renders smoothly at the TOF rate between snapshots
  and a fresh bounce appears without extrapolation artifacts.
- Given any other target builds and runs, when compared against
  baseline, then behaviour and rendering are unchanged.
- Given `make test-host`, `make linux`, `make amiga`, then all pass
  (per `docs/agent-test-policy.md` owner table).

## Dependencies and notes

- Amiberry control tooling is ready:
  `tools/amiga_emulator/keyboard.py`, `scripts/amiberry-type`,
  `repos/bounce-world-client-nio/scripts/drive_bwcn.py` (verified
  end-to-end 2026-08-26).
- The deferred ROTATION-rendering goal (workspace
  `deferred-work.md`) composes with this: interpolation's angle
  handling already consumes angle/omega from the decoder, so enabling
  rotation later is a render-transform change, not a loop change.
- Open question for spec distillation: whether instrumentation should
  be a runtime flag (keyboard-toggleable overlay) or a separate build;
  runtime flag preferred for live A/B comparison in one session.
