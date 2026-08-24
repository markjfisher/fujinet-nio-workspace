---
title: 'Amiga client skeleton — build, connect, render loop'
type: 'feature'
created: '2026-08-24'
status: 'done'
review_loop_iteration: 0
baseline_commit: '1d36b24c'
context:
  - '{project-root}/_bmad-output/specs/spec-amiga-bounce-world-client/SPEC.md'
  - '{project-root}/docs/agent-test-policy.md'
  - '{project-root}/docs/amiga/amiberry-testing.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Bouncy World has no graphical client; the Amiga is the first NIO-served retro platform capable of one, but `bounce-world-client-nio` has no Amiga target and the shared client cannot yet run there.

**Approach:** Add an `amiga` build target with platform shims (fullscreen custom lowres screen with double buffering, conio-style text I/O for prompts/status, keyboard, timing) so the shared gameplay/network code in `src/common` connects through `fujinet-nio-lib`'s broker transport, registers as a version-3 pixel-resolution client, and proves the fetch/render loop end-to-end in Amiberry WB 3.2 with a proportional placeholder renderer. Amiga-specific code stays behind shims; `src/common` changes are confined to platform-neutral protocol-version selection and version-guarded v3 coordinate decoding.

## Boundaries & Constraints

**Always:**
- Only standard Amiga OS libraries (`exec`, `intuition`, `graphics`, `dos`); m68k-amigaos-gcc from the workspace toolchain (`/opt/amiga/bin`, on PATH via `scripts/env.sh`).
- Registration: `REG_SCREEN_WIDTH/HEIGHT` = pixel resolution (320x256 PAL / 320x200 NTSC); `REG_WORLD_WIDTH/HEIGHT` = logical Bouncy World units 40x24. Rendering maps logical world coordinates into screen pixels.
- v3 shape x/y on the wire are signed int16 little-endian in the registered screen-pixel frame (server maps its 40x24 float space into the client-declared resolution). The human's server v3 implementation is final authority: any observed divergence from this contract means HALT and report before implementing further.
- Register version 3; other targets keep their current registration version (hardcoded `,2,` becomes a macro defaulting to 2).
- Version-3 world-state parsing must be guarded so version-2 clients parse exactly as today.
- `src/common` changes limited to platform-neutral protocol-version selection and the version/coordinate decode path; no changes to other targets' behavior.
- The custom screen is opened explicitly before the first conio operation (no lazy initialization); every failure/quit path after screen creation restores and closes it cleanly back to Workbench/CLI (including error exits via `handle_err`).
- Text UI (startup prompts, info/broadcast/status lines) stays legible on the custom screen via the conio shim.

**Ask First:** <!-- Agent: if any of these trigger during execution, HALT and ask the user before proceeding. -->
- The server's v3 response differs from the assumed layout (shape_id byte + 2-byte little-endian signed int16 x + y per shape in screen-pixel coordinates, count byte unchanged at `app_payload[2]`) — including coordinate-frame or signedness divergence.
- Guest-side prerequisites are missing (`fujinet-nio.device` not loadable in the wb32-a1200 environment) and cannot be resolved from `docs/amiga/amiberry-testing.md`.
- Anything requiring third-party libraries or KS1.3-specific workarounds.

**Never:**
- No sound work (story 3), no vector polygon fidelity work beyond proportional placeholder rectangles (story 2).
- No Workbench-window mode, high-res/interlace, or AGA features.
- No changes to the server repo or other clients' registered versions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path connect | Valid endpoint + name, server reachable | Client registers v3, receives world steps, placeholder shapes drawn each step | N/A |
| v2 parsing unchanged | Client compiled with default version 2 | Payload decoded 3 bytes/shape as today; existing targets behave identically | N/A |
| v3 coordinate decode | Payload bytes per shape: id, x_lo, x_hi, y_lo, y_hi (little-endian) | Signed 16-bit coords decoded correctly across full ±32000 range incl. values >127 | Clamp/wrap behavior identical to int8 semantics of other axes: draw only shapes within screen bounds |
| Shape partially off-screen | Coordinate near edge | Placeholder rectangle clipped to screen bounds | No out-of-bounds writes |
| Server unreachable / bad client id | Connection fails or `client_id == 0` | Error surfaced via existing `handle_err` path, clean exit to CLI | Existing error flow reused |
| Quit key | User presses quit during sim | `disconnect_service()`, cleanup restores console, returns to CLI | No crashes on second connect attempt |

</frozen-after-approval>

## Code Map

- `Makefile` -- target list (`TARGETS`, line 11); add `amiga`.
- `makefiles/build.mk` -- per-target platform mapping (13-22), lib artifact names (37-45: add `NIO_LIB_FILE_amiga := $(NIO_LIB_DIR)/build/fujinet-nio-amiga.a`), CC/LD selection (79-88), CFLAGS blocks (90-133), compile/link rule branching (162-200: linux/msdos/gcc vs cc65 `else` branch — amiga needs a gcc-family branch like linux, no `-t $(CURRENT_TARGET)`).
- `repos/fujinet-nio-lib` -- `make amiga` exists; artifact `build/fujinet-nio-amiga.a`; `src/platform/amiga/fn_transport.c` is a broker client of `fujinet-nio.device` (guest must have the device loaded before the client starts).
- `src/main.c` -- startup order: `get_info()` → `connect_service()` → `send_client_data()` → `show_shapes_preview()` → `get_world_state()` → `run_simulation()` → `cleanup_client()`; includes `<conio.h>`/`<cc65.h>` directly. On Amiga the screen must exist before `get_info()`'s first conio call — handled inside the amiga shim (explicit open + `atexit` close), not by reordering common startup.
- `src/common/connection.c:421-435` -- `send_client_data()`: hardcoded `",2,"` version string; sends `name,version,screenX,screenY,worldX,worldY`. Version becomes per-platform macro; screen fields are pixels for Amiga while world fields stay 40x24.
- `src/common/display.c` -- `show_screen()` (~150+): parses `app_payload[2]` count then 3 bytes/shape (`id,x,y` int8); `swap_buffer()` before redraw; BBC branch shows the gfx-shape precedent. This is where the version-guarded 16-bit decode goes; extract decode into a pure helper for host testing.
- `src/common/run_simulation.c` -- main loop: `fetch_client_state()` → status → `show_screen()` on step change → `handle_kb()`; exit → `disconnect_service()`.
- `src/linux/*` -- closest shim analog to mirror: `conio.{c,h}` (full cc65-style API: clrscr/gotoxy/gotox/wherex/wherey/cputc/cputs/cputcxy/cputsxy/revers/cursor/chlinexy/kbhit/cgetc), `cc65.h` (`doesclrscrafterexit` stub), `delay.c` (`wait_vsync`/`network_retry_pause`/`pause(count)`), `double_buffer.c` (`is_alt_screen`, `swap_buffer()`, no-op `show_other_screen()`), trivial `collision.c`, `convert_chars.c`, `playfield_clr.c`, `full_clr.c`, `shapes_preview.c`, `shutdown.c` (`cleanup_client`), no-op `sound.c`.
- `src/include/{display,double_buffer,delay,keyboard,sound,shutdown}.h` -- the shim contracts; `screen.h` is per-platform (see linux/bbc variants for `SCREEN_*`/`REG_*` pattern).
- `src/common/get_info.c` -- interactive endpoint/name prompts via app-store settings + `get_line.c`; runs before any graphics-heavy code, needs working text conio.

## Tasks & Acceptance

**Execution:**
- [x] `makefiles/build.mk` + `Makefile` -- add `amiga` target: platform mapping, `m68k-amigaos-gcc` CC/LD, gcc-family compile/link rules (linux-style, no cc65 `-t` flags), `-DBWC_CLIENT_VERSION=3`, lib path `fujinet-nio-amiga.a` -- wires builds without touching cc65 paths.
- [x] `src/amiga/screen.h` -- `SCREEN_WIDTH 320`, `SCREEN_HEIGHT 256` (NTSC height handled at screen open), `REG_SCREEN_WIDTH/HEIGHT = SCREEN_*`, `REG_WORLD_WIDTH 40`, `REG_WORLD_HEIGHT 24` -- registers pixel screen dimensions with the logical world grid unchanged.
- [x] `src/amiga/conio.{h,c}` -- cc65-style text API over an OS-provided console/raster font on the custom screen; explicit screen open before first conio use plus `atexit` close/restore covering all exit paths (error exits included) -- keeps all prompt/info/status common code working unmodified with a clean lifecycle.
- [x] `src/amiga/double_buffer.c` + screen lifecycle in `display.c` shims (`init_screen` support, `full_clr`, `playfield_clr`) -- custom lowres screen, PAL/NTSC-aware 320x256/200, two buffers swapped by `swap_buffer()` -- flicker-free frame presentation on the already-open screen.
- [x] `src/amiga/{delay,collision,convert_chars,shapes_preview,shutdown,sound}.c` -- mirror the linux implementations (sound no-op until story 3; `wait_vsync` via `WaitTOF`) -- completes the shim set the wildcard build expects.
- [x] `src/common/connection.c` -- replace hardcoded `",2,"` with `BWC_CLIENT_VERSION` macro (default 2, amiga overrides to 3); record the active version in a shared flag -- enables v3 without changing other targets.
- [x] `src/common/display.c` -- extract payload shape decoding into a pure helper; when active version >= 3 decode 5 bytes/shape (id + LE int16 x/y) else legacy 3 bytes; pass decoded coords to rendering -- single guarded parse path.
- [x] `tests/host/test_coord_decode.c` (+ tiny make rule) -- host-built unit test covering the decode helper's matrix rows -- cheapest test that can fail for the common-code change.
- [x] `README.md` -- amiga target section: build command, guest prerequisites (`fujinet-nio.device` loaded, NIO share), run notes -- documents the new target.

**Acceptance Criteria:**
- Given a clean env (`source scripts/env.sh`), when `make amiga`, then `build/bwcn.amiga` links against `fujinet-nio-amiga.a` with no warnings from new sources.
- Given the wb32-a1200 Amiberry WB 3.2 session with `fujinet-nio.device` loaded and the binary available via the NIO share, when the client is started and given a reachable endpoint, then it shows the familiar prompt flow, registers v3 at pixel resolution, and draws proportional filled rectangles per shape that move with live world steps.
- Given any existing target (`make atari bbc linux msdos`) is built, then it succeeds and behavior is observably preserved: version-2 registration, legacy 3-byte shape decode, and existing rendering unchanged.
- Given a connection failure or bad client id after the Amiga screen exists, when the client exits via the error path, then the custom screen is closed/restored and control returns cleanly to the CLI.
- Given the host unit test, when run, then all I/O-matrix decode rows pass including >127 coordinates and negative values.

## Spec Change Log

## Design Notes

- PAL/NTSC detection: `GfxBase->DisplayFlags & (PAL | NTSC)` selects 256/200 height before opening the screen.
- Screen lifecycle: open the custom screen from the amiga shim before any conio use (a GCC constructor in `conio.c` runs before `main`, keeping common startup order untouched) and register an `atexit` handler that closes it — this covers `handle_err` exits and quit paths alike without lazy init. Rejected: lazy first-use init (hides failure timing from prompt rendering).
- Conio on the custom screen: use a ROM-loaded font via `graphics.library` `Text()` on the current rastport rather than console.device, keeping fullscreen ownership simple; `kbhit/cgetc` poll `IDCMP_RAWKEY` on the screen/window.
- Endianness/frame assumption (signed int16 LE in screen-pixel coordinates) matches the framed-TCP header documented in README ("2-byte little-endian total packet size") and the server's float-to-client-resolution mapping; confirm against the server's v3 implementation if it diverges (Ask First).

## Verification

**Commands:**
- `source scripts/env.sh && make -C repos/bounce-world-client-nio amiga` -- expected: links `build/bwcn.amiga`, new sources compile warning-free.
- `make -C repos/bounce-world-client-nio linux` -- expected: existing target still builds (common-code change compiles clean in v2 mode).
- host unit test rule from `tests/host/` (e.g. `make -C repos/bounce-world-client-nio test-host-coords`) -- expected: all decode cases pass.

**Manual checks (if no CLI):**
- In the wb32-a1200 Amiberry session (procedure: `docs/amiga/amiberry-testing.md`): load `fujinet-nio.device`, run `bwcn.amiga` from NIO:, enter endpoint/name, observe prompt flow → registration → moving placeholder shapes; quit restores the CLI cleanly.

## Suggested Review Order

**Protocol version + wire contract**

- Registration now emits the build-time version between name and screen fields; width field restored after review caught its loss
  [`connection.c:428`](../../../repos/bounce-world-client-nio/src/common/connection.c#L428)

- Pure v2/v3 decoder: length-bounded, clamped to output capacity; the one piece of new logic with a host test
  [`shape_decode.c:8`](../../../repos/bounce-world-client-nio/src/common/shape_decode.c#L8)

- Compile-time-only version selection: `BWC_CLIENT_VERSION` guards both decode path and gfx_render.h include so v2 targets compile unchanged
  [`display.c:192`](../../../repos/bounce-world-client-nio/src/common/display.c#L192)

**Amiga platform shims**

- Explicit screen lifecycle: constructor opens custom lores screen before any conio use; atexit closes it on every exit path
  [`conio.c:311`](../../../repos/bounce-world-client-nio/src/amiga/conio.c#L311)

- Text-cell conio over topaz font on double-buffer rastports; grid wrap/clamp guards added during review
  [`conio.c:69`](../../../repos/bounce-world-client-nio/src/amiga/conio.c#L69)

- Rawkey input map with key-release filter; endpoint punctuation and quit key covered
  [`conio.c:182`](../../../repos/bounce-world-client-nio/src/amiga/conio.c#L182)

- Placeholder renderer: proportional rectangles scaled from 40x24 world units into registered pixels, clipped to screen
  [`gfx.c:8`](../../../repos/bounce-world-client-nio/src/amiga/gfx.c#L8)

- Registration dimensions: pixel screen extents, logical 40x24 world region per the corrected contract
  [`screen.h:18`](../../../repos/bounce-world-client-nio/src/amiga/screen.h#L18)

**Build wiring**

- Target mapping, m68k compiler flags, lib artifact, `-DBWC_CLIENT_VERSION=3`; duplicates from a botched edit removed
  [`build.mk:17`](../../../repos/bounce-world-client-nio/makefiles/build.mk#L17)

**Peripherals**

- Host unit tests incl. payload-length truncation case added in review
  [`test_coord_decode.c:81`](../../../repos/bounce-world-client-nio/tests/host/test_coord_decode.c#L81)

- `make test-host-coords` rule (host gcc, independent of cross targets)
  [`Makefile:41`](../../../repos/bounce-world-client-nio/Makefile#L41)
