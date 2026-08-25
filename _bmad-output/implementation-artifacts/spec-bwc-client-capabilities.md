---
title: 'Bouncy World client capability negotiation + WIDE_COORDS'
type: 'feature'
created: '2026-08-25'
status: 'done'
review_loop_iteration: 0
baseline_commit: f5a80d888719b6ce8e96783be625564b486d6eb8
context:
  - _bmad-output/specs/spec-bwc-client-capabilities/wire-protocol.md
  - docs/agent-test-policy.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The pre-release Bouncy World server negotiates per-client capabilities at registration instead of inferring features from version numbers. The client cannot yet send a capabilities bitmask, so it cannot receive wide coordinates, and its codebase still gates v3 behaviour behind compile-time/version checks.

**Approach:** In `repos/bounce-world-client-nio`, let registration optionally carry a capabilities bitmask appended to the add-client CSV as a text number in hex form (leading `0x`, e.g. `0x03`); the Amiga client requests `0x01` (WIDE_COORDS), all other targets request none and keep exact legacy behaviour. Decode per-shape records at 3/5/9 bytes according to the negotiated caps, render wide signed coordinates with edge clipping in the Amiga renderer, and delete every V3/version-based feature guard — the bitmask becomes the only feature-selection mechanism. ROTATION rendering is deferred (see `deferred-work.md`); this spec only lands the 9-byte-aware decoder groundwork so that follow-up is render-only.

## Boundaries & Constraints

**Always:**
- The capabilities field on the wire is a text number inside the CSV: the client always formats its mask as a hex string with a leading `0x` (e.g. `0x03`); the server also accepts decimal when the value does not lead with `0x`. There is no fixed 8- or 16-bit width — the server accepts any number of bits, so the client's internal mask is an `unsigned` wide enough for future bits. Bit values match the server constants exactly: 0x01 WIDE_COORDS; unknown bits are masked off/ignored, never acted on.
- Registration response handling is unchanged: single byte containing the assigned client id; ports 9002/9003 framing unchanged.
- Without caps, behaviour is byte-identical to today for every target (legacy 3-byte records, current rendering).
- With WIDE_COORDS, x/y are little-endian int16 and may be slightly negative or ≥ screen size (edge/wrap straddling) — draw with clipping, never wrap or reject them.

**Ask First:**
- Any divergence between this spec / `wire-protocol.md` and observed pre-release server behaviour — stop and report, never guess.
- Growing `APP_DATA_SIZE` beyond the value named in Tasks, or any change forcing edits outside the files listed below.

**Never:**
- No changes to the Bouncy World server or any other repo.
- No behavioural change for atari/bbc/linux/msdos targets (they keep registering and rendering exactly as today).
- No new capability bits, no persistence of negotiated caps.
- No ROTATION work beyond the decode layout: do not request bit 0x02, do not add angle/omega rendering, transforms, or interpolation (deferred).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Legacy registration | 6-field add-client (no caps field or 0), any target | Id byte returned; subsequent `w <id>` payload parsed as 3-byte records, byte-identical to today | Short/truncated payload clamps shape count as today |
| Caps registration | 7-field add-client with caps formatted as hex text, e.g. `add-client myclient,1,320,256,40,24,0x01` | Id byte returned; records parsed at 5 bytes (id, x int16 LE, y int16 LE) | Unknown server bits in future → client masks to bits it knows |
| 9-byte decode (host unit level only) | 9-byte records fed directly to the decoder with angle/omega bytes | Decoded into reserved ShapePos fields; not rendered anywhere yet | Values pass through unvalidated (render deferral owns semantics) |
| Wide coords near x=300 | 5-byte record with x encoded ≈300 | Decodes ~300, no uint8 wrap | Values slightly out of screen range pass through signed |
| Edge-straddling shape | Wide x = −3 or 322 (320px screen) | Shape renders partially clipped at viewport edge | Segment clip drops fully-offscreen geometry |

</frozen-after-approval>

## Code Map

Repo root: `repos/bounce-world-client-nio` (workspace submodule, branch master @ f5a80d88). No capability/wide-coordinate code exists yet.

- `src/common/connection.c:433-465` -- `send_client_data()` builds the CSV (`name,version,screenW,screenH,worldW,worldH`) and sends `x-add-client`; the 7th caps field is appended here. Helpers `create_command/append_command/send_command` at :37-66; `cmd_tmp[64]` buffer at `src/common/data.h:34`.
- `src/common/shape_decode.c:4,12,28` -- `bwc_client_version` const and `bwc_decode_shapes(payload,len,count,version,out,out_max)`; stride 5 vs 3 chosen by `version >= 3U`. Becomes caps-driven.
- `src/include/shape_decode.h:6-19` -- `BWC_CLIENT_VERSION` macro (default 2), `ShapePos {shape_id; int16 x,y}`, `SHAPE_POS_MAX 84`. Extend struct with reserved `angle`/`omega`, define the caps constants here as bits of an `unsigned` mask (`BWC_CAP_WIDE_COORDS 0x01`); drop/relocate the version macro.
- `src/common/display.c:23,156-164,190-196,198-221` -- `show_screen()`: `#if BWC_CLIENT_VERSION >= 3` include + decode path vs v2/BBC inline 3-byte parses calling `show_shape(id,int8,int8)` (:86-150). Replace compile-time guards with runtime caps branch: caps==0 → existing inline paths untouched; caps≠0 → decode then `gfx_show_shape_px(id,x,y)`.
- `src/amiga/gfx.c` -- `gfx_show_shape_px()` :256-285 already takes int16 centre coords; `draw_shape_at()` off-screen cull at :246-250 drops fully-offscreen shapes; `draw_contour_lines()` :84-116 + `vo_clip_segment()` (`vector_outline.c:195`) Cohen-Sutherland-clip segments — edge clipping for slightly-out-of-range centres comes from these two mechanisms; verify cull bounds tolerate small negative/oversized centres rather than dropping straddlers.
- `src/amiga/screen.h` -- `SCREEN_PIXEL_WIDTH 320/HEIGHT 256`; server sends region-relative pixels scaled to registered size.
- `src/include/data.h:14-16,34-38` -- `APP_DATA_SIZE` (default 256; Amiga overrides 768 via build flag), `app_payload = &app_data[2]`. Max world payload = 3 + 240×9 = 2163 (+2 len prefix) exceeds 768 — Amiga override must grow.
- `makefiles/build.mk:133` -- Amiga CFLAGS `-DBWC_CLIENT_VERSION=3 -DAPP_DATA_SIZE=768`; compilers :84-91 (amiga = `m68k-amigaos-gcc`). Remove the version define; raise the size define.
- `tests/host/test_coord_decode.c` -- gcc-built unit tests for `bwc_decode_shapes` (v2/v3, extremes ±32000, truncation). Extend for caps strides.
- `Makefile:41-55` -- `test-host-coords`, `test-host-vectors`, aggregate `test-host`; per-target builds `atari|bbc|linux|msdos|amiga`.
- Read-only evidence: fn-rom BASIC client (`repos/fn-rom/bas/bwc/bwc.bas:129`) sends the 6-field legacy form — unaffected. BBC excludes embedded_shapes from its build (`build.mk:67-70`).

## Tasks & Acceptance

**Execution:**
^- [x] `src/include/shape_decode.h` -- define `BWC_CAP_WIDE_COORDS 0x01` (+ reserve `BWC_CAP_ROTATION 0x02` for the deferred follow-up), all as bits of an `unsigned` mask type used by every caps parameter (no fixed 8/16-bit width — the server accepts any bit count); extend `ShapePos` with `uint16_t angle` + `int16_t omega` (unused now); change `bwc_decode_shapes` to take a caps mask instead of version; remove `BWC_CLIENT_VERSION` (move the literal version value for the CSV into `connection.c`, unused for feature selection) -- caps become the only selection mechanism.
^- [x] `src/common/shape_decode.c` -- decode 3/5/9-byte records by caps mask (legacy = 3; WIDE widens x/y to int16 = 5; ROTATION appends angle+omega = 9); wide x/y read signed LE; keep truncation clamping -- supports all layouts incl. the future rotation follow-up.
^- [x] `src/common/connection.c` -- append the caps bitmask as optional 7th CSV field formatted as a hex string with leading `0x` (e.g. `sprintf(..., "0x%02X", caps)` style — grow/verify `cmd_tmp` headroom); Amiga requests `BWC_CAP_WIDE_COORDS`, all other targets send none (6-field, byte-identical) -- implements CAP-1/CAP-2 request side.
^- [x] `src/common/display.c` -- delete all `#if BWC_CLIENT_VERSION` guards (:23,156-164,198-204); branch at runtime on negotiated caps: 0 → existing inline legacy parses untouched; otherwise decode via caps and call `gfx_show_shape_px` -- removes version gating everywhere.
^- [x] `src/amiga/gfx.c` -- audit the off-screen cull (:246-250) and block-mode clamp (:142-181) so a shape whose centre is a few pixels outside the viewport still draws its visible part (vector path already segment-clips) -- edge-straddling bodies render partially clipped.
^- [x] `makefiles/build.mk` -- remove `-DBWC_CLIENT_VERSION=3`; raise Amiga `APP_DATA_SIZE` override to fit max 240×9-byte world (≥2170 incl. length prefix + header; pick a round value ≤ ~2.5 KB) -- prevents silent truncation of dense worlds.
^- [x] `README.md` (lines ~26-29, ~197) -- replace version-3 narrative with capability-negotiation description -- docs match reality.
^- [x] `tests/host/test_coord_decode.c` -- add cases: 5-byte record decoding ≈300 and negative coords; 9-byte record with known LE bytes (angle 16384, omega −384 land in reserved fields); caps=0 legacy parity; truncated-payload clamp per caps mode -- unit-covers the I/O matrix.
- [x] All touched-owner gates in Verification -- run and pass.

**Acceptance Criteria:**
- Given the workspace env sourced, when `make linux` and `make amiga` run, then both targets compile with zero references to `BWC_CLIENT_VERSION` or version-based feature `#if`s remaining in `src/` (grep-clean).
- Given caps `0x01` negotiated, when a `w <id>` payload arrives, then records parse at exactly 5 bytes/shape and decoded x≈300 stays ≈300 (no wrap); negative/oversized coords survive decode.
- Given a dense 240-shape world, when the full payload arrives on Amiga, then no shapes are lost to receive-buffer truncation.
- Given a body whose centre is slightly outside the 320×256 viewport, when rendered, then its visible part draws and nothing out-of-bounds does.
- Given legacy mode, when any text target runs against the same server, then registration bytes and rendered output are indistinguishable from the pre-change client.

## Spec Change Log

## Design Notes

- Client-requested caps: Amiga asks for `0x01` because wide coords is what it decodes today; text targets ask for nothing (request-only-what-you-decode). The `0x02` constant is reserved but never sent — flipping Amiga's mask to `0x03` plus renderer work is exactly the deferred ROTATION goal. On the wire the mask always goes out as a `0x`-prefixed hex string; decimal remains server-side tolerance, not something the client emits.
- Byte-identical legacy requirement is why text targets keep their inline int8 parsers instead of routing through `bwc_decode_shapes` with caps=0.

## Verification

**Commands:**
- `source "$NIO_WORKSPACE/scripts/env.sh"` -- expected: toolchains available (cc65, m68k-amigaos-gcc, gcc, WATCOM). Run this in the SAME shell session as every `make` below — `scripts/env.sh` exports the WATCOM env vars and PATH entries the msdos build needs; a fresh shell without it is why msdos builds typically fail.
- `make test-host-coords && make test-host-vectors` (repo root) -- expected: all host tests pass including new decode cases.
- `make linux` -- expected: clean build of the linux target (shared-code regression gate).
- `make amiga` -- expected: clean cross-build with no `-DBWC_CLIENT_VERSION` and grown `APP_DATA_SIZE`.
- `grep -rn "BWC_CLIENT_VERSION\|>= 3U\|version >= 3" src/ makefiles/` -- expected: no matches (guard removal proof).
- Best-effort if toolchains present (same sourced shell): `make atari`, `make bbc`, `make msdos` -- expected: clean builds proving legacy paths compile unchanged; record any missing-toolchain blocker rather than skipping silently.

**Manual checks (if no CLI):**
- Live pre-release-server session (human-owned): register with caps `0x01` on 9002/9003, confirm id return, smooth wide-coordinate motion of a fast body (no 8px jumps), edge-clipped bodies, and unchanged legacy mode. Requires the human's pre-release server build; report as environment-blocked if unavailable to the agent.

## Suggested Review Order

**Capability contract (types + constants)**

- Caps mask type and bit constants — the only feature-selection mechanism, no fixed width.
  [`shape_decode.h:9`](../../repos/bounce-world-client-nio/src/include/shape_decode.h#L9)

- ShapePos gains reserved angle/omega fields for the deferred ROTATION follow-up.
  [`shape_decode.h:26`](../../repos/bounce-world-client-nio/src/include/shape_decode.h#L26)

- Stride documentation: WIDE adds +2 (3→5), ROTATION adds +4 (5→9).
  [`shape_decode.h:33`](../../repos/bounce-world-client-nio/src/include/shape_decode.h#L33)

**Registration wire format**

- Pure CSV builder — bounded shift-only hex emission, host-testable, no transport deps.
  [`add_client_csv.c:17`](../../repos/bounce-world-client-nio/src/common/add_client_csv.c#L17)

- Per-target requested caps and the single call site wiring the builder into the transport.
  [`connection.c:460`](../../repos/bounce-world-client-nio/src/common/connection.c#L460)

**Decode path**

- Caps-driven stride selection replacing the version comparison; truncation clamping kept.
  [`shape_decode.c:12`](../../repos/bounce-world-client-nio/src/common/shape_decode.c#L12)

- Runtime caps branch in show_screen — legacy inline parses untouched when caps==0.
  [`display.c:194`](../../repos/bounce-world-client-nio/src/common/display.c#L194)

**Build sizing**

- APP_DATA_SIZE 768→2304 with payload-math justification; version define removed.
  [`build.mk:136`](../../repos/bounce-world-client-nio/makefiles/build.mk#L136)

**Tests**

- New builder tests: exact 6-field legacy parity, 7-field hex caps, full-width mask.
  [`test_add_client_csv.c:36`](../../repos/bounce-world-client-nio/tests/host/test_add_client_csv.c#L36)

- Rewritten decoder tests incl. reserved-field zeroing and unknown-bits tolerance.
  [`test_coord_decode.c:32`](../../repos/bounce-world-client-nio/tests/host/test_coord_decode.c#L32)

**Docs**

- README capability-negotiation narrative; version field documented as data only.
  [`README.md:26`](../../repos/bounce-world-client-nio/README.md#L26)
