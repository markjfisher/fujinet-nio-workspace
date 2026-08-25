---
title: 'Amiga vector shape rendering with selectable block mode'
type: 'feature'
created: '2026-08-25'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'ea98ecb7e29e7e63722e528db88c75a3954434d8'
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-bounce-world-client/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/docs/amiga/amiberry-testing.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Amiga client draws every shape as a plain proportional rectangle (story 1 placeholder). Bouncy World shapes deserve real vector rendering on its most graphics-capable platform, and the block view is worth keeping as a selectable alternative.

**Approach:** Render each shape as filled polygon geometry derived from its embedded cell bitmap, scaled proportionally from the 40x24 world grid to registered pixels, on the existing double-buffered screen. Retain the block renderer behind the same render entry point; a `v`/`V` key press toggles between vector and block modes live, effective on the next frame.

## Boundaries & Constraints

**Always:**
- Only standard Amiga OS libraries (`graphics.library` area/fill functions for polygon filling); no third-party graphics libs.
- Vector geometry derives from the same embedded shape data (`shapes[19]`, cell-bitmap silhouette) — no hand-authored per-shape art, no new shape definitions.
- `vector_outline` represents **zero or more closed rectilinear contours** derived from the cell bitmap — never assume one simple polygon. The contour set must faithfully represent connected filled regions, disconnected components, and enclosed holes present in the embedded shapes.
- Deterministic fill policy (not an implementation choice): contours are classified outer vs hole by even-odd containment; rendering fills each outer contour with the shape pen (colour 2), then fills its holes with the playfield background pen, in deterministic contour order. The observable contract: the filled result equals the source cell bitmap.
- Scaling is proportional to the world grid exactly like the block renderer: `shape_width` world units map through `SCREEN_PIXEL_WIDTH/REG_WORLD_WIDTH` horizontally and the **runtime** drawable height (`amiga_conio_height()`, PAL 256 / NTSC 200) vertically.
- Both renderers sit behind the single `gfx_show_shape_px()` entry point called from `src/common/display.c`; common code learns only a small render-mode enum (`RENDER_VECTOR` / `RENDER_BLOCK`, default `RENDER_VECTOR`) — no vector knowledge in common code. No additional modes in this story.
- Renderer storage is bounded up front: before coding, derive a safe maximum contour/vertex count from the embedded shape dimensions (max `width²` cells ⇒ bounded total perimeter); allocate AreaInfo/vector working storage once at renderer init (static or single init-time allocation), never heap-allocate/free geometry per frame; if unexpected geometry exceeds the bound, enforce it safely (truncate/skip that shape) rather than overflow; keep large buffers off the 64KB application stack.
- Toggle is bound to `v`/`V` (verified free across all targets); switching takes effect on the next rendered frame with no reconnect, restart, or screen rebuild; both modes stay available all session; vector is the startup default and pressing `v` again returns to it.
- Toggle guard is Amiga-capability-based only (`#ifdef __AMIGA__` or an explicit renderer-capability macro) — protocol v3 does not imply this UI, so a future non-Amiga v3 client must not inherit the key.
- Existing targets (`atari bbc linux msdos`) preserve their current behavior observably: shared source files may be edited, but all Amiga-only toggle/renderer code must compile out for them, and they retain their existing key mappings and rendering exactly as today.
- Text UI (prompts, status/info lines) stays legible; the key legend gains the toggle hint.

**Ask First:**
- graphics.library area-buffer allocation fails at runtime or any new guest crash/divergence in the wb32-a1200 session appears.
- Any observed wire/v3 divergence (should not arise — decode path is story-1 code, unchanged).
- Temptation to change `src/common/display.c` beyond the render-mode enum read and legend support.

**Never:**
- No sound work (story 3), no changes to server or other clients, no Workbench-window/high-res/AGA features, no persistent preference storage, no on-screen selection menu.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live toggle | `v` pressed during play | Next frame renders all shapes as filled vector polygons; pressing again returns to block rectangles | N/A |
| Vector happy path | Valid shape id, on-screen center | Solid silhouette matching the shape's cell bitmap, correct size (width × px/unit) and position | N/A |
| Hollow / disconnected shape | Shape bitmap with enclosed hole or separate components | Hole stays unfilled; every component renders; filled result equals the source bitmap | N/A |
| Partially off-screen | Center near edge | Clipped cleanly at screen bounds; fully off-screen shapes skipped | No out-of-bounds writes, no reversed-fill crashes |
| Degenerate shape | `id >= shape_count` or `shape_width == 0` | Skipped, same guards as block mode today | N/A |
| NTSC machine | 200px runtime height | Vertical scaling/clipping uses runtime height; nothing registers against the unused PAL rows | N/A |
| Info overlay visible | `is_showing_info` set | Status/info text remains legible above the playfield render (existing max-row clamp preserved) | N/A |

</frozen-after-approval>

## Code Map

- `repos/bounce-world-client-nio/src/amiga/gfx.c` -- placeholder block renderer `gfx_show_shape_px()` (:8); scaling math :30-31, clamp/drop logic :38-56, hardcoded pen `SetAPen(rp, 1)` :58. Extend here: keep block path, add vector path + mode dispatch. Note pen comment: colour 2 (red) reserved for shapes (`conio.c:484-488`).
- `repos/bounce-world-client-nio/src/amiga/gfx_render.h` -- declares `gfx_show_shape_px()` for common code (`BWC_AMIGA_GFX_RENDER_H`, included only when `BWC_CLIENT_VERSION >= 3`).
- `repos/bounce-world-client-nio/src/amiga/conio.c` -- `amiga_conio_draw_rp()` :116-122 (NULL until screen ready), `amiga_conio_height()` :179-182 (runtime PAL/NTSC height — vectors must use this, not `SCREEN_PIXEL_HEIGHT`); palette setup :484-488.
- `repos/bounce-world-client-nio/src/common/display.c` -- three-way compile-time dispatch in `show_screen()` :190-221; v3 branch :198-212 decodes then calls `gfx_show_shape_px()` per shape — the only common-code touchpoint; swap_buffer :174 precedes drawing, present :231 follows (flicker-freedom already handled).
- `repos/bounce-world-client-nio/src/include/shapes.h` + `src/common/shapes.c` -- `ShapeRecord {shape_id, shape_width, shape_data_len, *shape_data}` (:6-11); `shape_data` is `width²` neutral-coded cell bytes (non-space = filled cell); loaded pre-game via `shapes_load_embedded()`.
- BBC precedent for id→rendering tables: `src/bbc/gfx_shapes.c:154-174`.
- `repos/bounce-world-client-nio/src/common/keyboard.c` -- `handle_kb()` :61-101 switch on ASCII; `toggle_info()/toggle_darkmode()` :46-59 are the toggle-flag pattern; bound keys everywhere: `+ - f 1-5 r i w q` (BBC adds `c`, Atari `d l`). Add `v`/`V` case guarded `#ifdef __AMIGA__` (or a renderer-capability macro) — never on protocol version.
- `repos/bounce-world-client-nio/src/common/data.c` / `src/include/data.h:59-70` -- shared gameplay globals (`is_showing_info` etc.); add the render-mode enum variable here.
- `repos/bounce-world-client-nio/src/common/show_info.c:74-81` -- platform-ifdef legend lines; add Amiga line documenting the toggle key.
- `repos/bounce-world-client-nio/tests/host/test_coord_decode.c` + `Makefile:41-46` rule `test-host-coords` -- self-contained host-test pattern (plain gcc, freestanding common units only); mirror it for the outline builder.
- Stack is 64KB via `__stack_size` (`conio.c:28`) — size any area-buffer statically or heap-allocate, not on the stack.

## Tasks & Acceptance

**Execution:**
- [x] `src/amiga/vector_outline.{c,h}` (new, freestanding C99) -- pure helper: given `ShapeRecord.shape_data`/`shape_width`, produce zero or more closed rectilinear contours (ordered vertices, world-unit coordinates) covering all filled regions, disconnected components, and holes; expose each contour's outer/hole classification -- keeps geometry logic host-testable, mirrors `shape_decode.c` discipline.
- [x] `tests/host/test_vector_outline.c` + `Makefile` rule `test-host-vectors` -- include a host-side even-odd rasterizer and assert the **filled silhouette equals the source cell bitmap** for every case: single cell, plus/star silhouettes, disconnected components, hollow ring (hole preserved), empty bitmap, width 1 -- not merely that vertex lists were produced.
- [x] `src/amiga/gfx.c` -- vector renderer: derive the storage bound from max embedded `width²`, allocate AreaInfo/vector storage once at init; scale outline vertices world→pixels (runtime height); fill outers with pen 2 then holes with background pen per the deterministic policy via `AreaDraw`/`AreaEnd`; enforce the bound safely on oversized geometry; retain block renderer intact; dispatch inside `gfx_show_shape_px()` on the render-mode enum -- one entry point, two modes.
- [x] `src/include/data.h` + `src/common/data.c` -- add `enum render_mode { RENDER_VECTOR, RENDER_BLOCK }` with a current-mode global defaulting to `RENDER_VECTOR`, beside the other gameplay flags -- common code carries selection, not rendering.
- [x] `src/common/keyboard.c` -- `v`/`V` case flipping the render-mode between `RENDER_VECTOR`/`RENDER_BLOCK`, guarded `#ifdef __AMIGA__` (or renderer-capability macro) so it compiles out of every other target regardless of protocol version -- live toggle without touching existing keymaps.
- [x] `src/common/show_info.c` -- Amiga legend line for the toggle key -- discoverable UI.
- [x] `README.md` -- note the Amiga renderer toggle key -- documents user-visible behavior.

**Acceptance Criteria:**
- Given a clean env (`source scripts/env.sh`), when `make amiga`, then `build/bwcn.amiga` links warning-free from new/changed sources.
- Given the host tests, when `make test-host-coords && make test-host-vectors`, then all cases pass.
- Given `make linux` (and atari/bbc/msdos), then existing targets build and behave observably as today: same key mappings, v2 decode, existing rendering; Amiga-only toggle/renderer code compiles out of them.
- Given the wb32-a1200 Amiberry WB 3.2 session with a live server, when the client runs, then shapes render as solid vector silhouettes at proportional sizes/positions with no flicker; pressing `v` flips the whole playfield to block rectangles on the next frame and back; quit/error paths still restore the CLI cleanly.

## Spec Change Log

- **2026-08-25 — wrapping-world render contract.** Server change: in wrapping mode the server sends one wire copy per visible wrap, with shape centres that may sit outside the client screen (e.g. −2 or 322). Client consequence: the seam-duplication draw was removed (the server owns wrap copies), the stroke path clips each contour segment against the screen via `vo_clip_segment` (Cohen–Sutherland, host-tested) preserving true slopes, and per-vertex clamping was removed — vertex clamping drew false diagonals for off-screen centres. Verified live: shapes straddle wrap seams correctly in all four directions.

- **2026-08-25 — requirement pivot: filled polygons → line-art outlines.** After live review the filled-polygon aesthetic was rejected in favour of stroked outlines (Asteroids/Tempest/Elite style): every traced contour — outers *and* holes — is drawn as a closed pixel-line path; nothing is filled. Consequences: the deterministic hole-fill policy and the even-odd rasterizer equivalence test no longer apply (holes render naturally as inner outlines); palette changed to black background / white lines / white text; `AreaEnd`+`TmpRas` machinery removed from the render path (its absence had also been the root cause of the garbage fills, freeze and Guru — fills rasterize through `rp->TmpRas`). New follow-on requirement captured as SPEC CAP-5: hand-craftable per-shape vector override tables (`s_hand_shapes[]` in `gfx.c`) with lattice-coordinate vertex loops, so shapes can be designed by hand instead of traced.

## Design Notes

- Silhouette tracing beats hand-drawn polygons: the embedded blob is the single source of shape truth (same as every other target), so vectors stay automatically consistent if shapes ever change. A rectilinear contour walk of the cell grid (unit edges between filled/empty neighbours) yields the contour set; outer/hole classification is even-odd containment, and rendering applies outers (pen 2) then holes (background pen) in deterministic order so the filled result equals the source bitmap.
- Storage bound: worst-case rectilinear contour complexity for a `w×w` cell grid is O(w²) vertices per contour and O(w²) total; with max embedded `width` = 5 this is tiny — compute the exact figure from `embedded_shapes.c` during implementation, add headroom, document the derivation in code.
- `graphics.library` area fill needs an `InitArea()` buffer; allocate it once at renderer init (static storage or single init-time allocation), never per frame, never on the stack.
- Toggling needs no erase pass: every frame starts from `swap_buffer()` + `playfield_clr()`/`full_clr()` which wipes bitmap and text shadow grid (`playfield_clr.c:5-8`), so mode switches cannot leave stale pixels.
- Do not reuse pen 1 (black text) — colour 2 is the reserved shape colour (`conio.c:484-485`).

## Verification

**Commands:**
- `source scripts/env.sh && make -C repos/bounce-world-client-nio amiga` -- expected: links `build/bwcn.amiga`, new sources warning-free.
- `make -C repos/bounce-world-client-nio linux` -- expected: existing target builds unchanged (common change compiles clean in v2 mode).
- `make -C repos/bounce-world-client-nio test-host-coords && make -C repos/bounce-world-client-nio test-host-vectors` -- expected: all decode and outline cases pass.

**Manual checks (if no CLI):**
- In the wb32-a1200 Amiberry WB 3.2 session (procedure: `docs/amiga/amiberry-testing.md`): run `bwcn.amiga` against a live server, confirm vector silhouettes move with world steps, press `v` mid-play to see block rectangles next frame and again for vectors, verify the legend shows the key, and confirm quit restores the CLI cleanly.

## Suggested Review Order

**Geometry core — silhouette tracing**

- Contour tracer: directed boundary edges, deterministic saddle choice, even-odd hole classification
  [`vector_outline.c:74`](../../../repos/bounce-world-client-nio/src/amiga/vector_outline.c#L74)

- Outer/hole classification by shoelace sign; truncation reported, never silent
  [`vector_outline.c:166`](../../../repos/bounce-world-client-nio/src/amiga/vector_outline.c#L166)

**Renderer — dispatch and fill policy**

- Single entry point: block vs vector selected by the render-mode enum; trace failure falls back to blocks
  [`gfx.c:189`](../../../repos/bounce-world-client-nio/src/amiga/gfx.c#L189)

- Deterministic two-pass policy: outers in shape pen, holes in background pen
  [`gfx.c:65`](../../../repos/bounce-world-client-nio/src/amiga/gfx.c#L65)

- Vertices clamped in int32 before narrowing — no wrap for off-screen bodies
  [`gfx.c:100`](../../../repos/bounce-world-client-nio/src/amiga/gfx.c#L100)

- AreaInfo storage: static, bounded from VO_MAX_PTS, init-once per rastport with eviction fallback
  [`gfx.c:20`](../../../repos/bounce-world-client-nio/src/amiga/gfx.c#L20)

- Block path retained, now on runtime height and reserved shape pen
  [`gfx.c:135`](../../../repos/bounce-world-client-nio/src/amiga/gfx.c#L135)

**Selection plumbing**

- Render-mode enum beside other gameplay flags; default vector
  [`data.h:66`](../../../repos/bounce-world-client-nio/src/include/data.h#L66)

- v/V toggle guarded __AMIGA__ only — protocol version implies nothing here
  [`keyboard.c:100`](../../../repos/bounce-world-client-nio/src/common/keyboard.c#L100)

- Legend hint for the toggle key
  [`show_info.c:75`](../../../repos/bounce-world-client-nio/src/common/show_info.c#L75)

**Tests and build wiring**

- Even-odd rasterizer asserts filled silhouette equals source bitmap, all embedded shapes included
  [`test_vector_outline.c:27`](../../../repos/bounce-world-client-nio/tests/host/test_vector_outline.c#L27)

- Truncation-path coverage (8x8 checkerboard exceeds storage bound)
  [`test_vector_outline.c:180`](../../../repos/bounce-world-client-nio/tests/host/test_vector_outline.c#L180)

- Aggregate host-test target running both suites
  [`Makefile:55`](../../../repos/bounce-world-client-nio/Makefile#L55)
