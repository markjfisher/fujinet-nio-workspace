---
id: SPEC-amiga-bounce-world-client
companions: []
sources:
  - backlog/amiga-bounce-world-client.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate.

# Amiga graphical Bouncy World client

## Why

**Opportunity + vision.** Every existing Bouncy World client (`atari`, `bbc`, `linux`, `msdos`) is character-based. With the Amiga now served by the FujiNet NIO stack (network and disk), an opportunity exists for the first graphical client: vector-rendered shapes on native Amiga hardware, running on A1200-class machines under Workbench 3.x (Kickstart 1.3 compatibility is a later goal). It showcases the NIO stack on its most graphics-capable retro platform.

## Capabilities

- **CAP-1**
  - **intent:** A user can build (`make amiga`) and launch an Amiga client that registers a pixel resolution with a live Bouncy World server through `fujinet-nio-lib` and joins the world.
  - **success:** On an Amiberry WB 3.x session (`wb32-a1200` profile) with NIO transport available, the binary connects, registers its pixel dimensions, receives world state, and displays it; existing targets still build and pass their tests.
- **CAP-2**
  - **intent:** The client renders live world state as filled vector polygons instead of characters, converting each embedded shape id into ordered polygon geometry scaled proportionally from the 40x24 world grid to the registered pixel resolution.
  - **success:** Every shape id the server can send draws as the correct solid shape at correct position/size on a double-buffered fullscreen lowres screen, with no flicker or tearing during play.
- **CAP-3**
  - **intent:** Amiga-specific display/input/timing/shutdown lives behind platform shims while the gameplay/network architecture stays in shared `src/common`; `src/common` changes are permitted only for platform-neutral protocol-version selection and version-guarded v3 coordinate decoding.
  - **success:** Existing targets keep v2 registration, legacy 3-byte shape decoding, and their current rendering behavior; keyboard commands work in-game on Amiga and every quit/failure path after screen creation restores the console and returns cleanly to Workbench/CLI.
- **CAP-4**
  - **intent:** Collision/event sound effects equivalent to other targets play during gameplay.
  - **success:** Audible event sounds using OS audio APIs are demonstrated in an emulated WB 3.x session alongside rendering.
- **CAP-5**
  - **intent:** During live rendering the user can switch between vector polygon rendering and block (proportional rectangle) rendering with a key press; both modes stay available for the whole session and the switch takes effect immediately without reconnecting or restarting.
  - **success:** In a `wb32-a1200` Amiberry WB 3.x session with live world state on screen, pressing the toggle key flips every rendered shape between filled vectors and proportional blocks on the next frame; toggling back restores vector mode, and no other behavior (connection, sound, quit) is disturbed.

## Constraints

- Verification environment is Workbench 3.2 via the `wb32-a1200` Amiberry profile (`configs/amiga/workbenches.yaml`); Kickstart/Workbench 1.3 support is deferred, not designed against now — but only standard OS libraries (`intuition.library`, `graphics.library`, `dos.library`) are used, keeping later 1.3 porting plausible. No third-party graphics libraries.
- Registration model: `REG_SCREEN_WIDTH/HEIGHT` are pixel dimensions (320x256 PAL / 320x200 NTSC); `REG_WORLD_WIDTH/HEIGHT` remain logical Bouncy World units (40x24). Rendering maps logical world coordinates into screen pixels. v3 shape x/y are signed int16 little-endian expressed in the registered screen-pixel frame; the human's server v3 implementation is final authority — divergence means stop and report, never guess.
- Wire protocol: registration version >=3 makes the server respond with 2 bytes per shape x/y coordinate (human is adding this server-side). Amiga registers version 3; all other clients stay on their current version. Common-code response parsing gains a version-guarded 16-bit coordinate path. Shape geometry scales proportionally (a size-5 shape spans 5.0 world units).
- Shape table is embedded client-side (`shapes[19]`, same ids as other targets); rendering per id is hard-coded like the BBC teletext renderer.
- The block renderer from story 1 is retained, not replaced: vector and block modes coexist as selectable renderers behind the same render entry point, and the toggle key must not conflict with existing in-game keys (quit and other controls). The exact key is an implementation choice.
- Network handling reuses `fujinet-nio-lib` unchanged.

## Non-goals

- No changes to the Bouncy World server beyond the human-owned version-3 wire addition; no changes to other client targets' behavior or registered versions.
- No Kickstart/Workbench 1.3 certification in this delivery — later goal.
- No Workbench-window mode, high-res or interlace screens, or AGA-specific enhancements in this first item.
- No new shape definitions or server-driven shape variants.
- No persistent renderer preference (choice resets each run) and no on-screen renderer-selection UI beyond the toggle key.

## Success signal

An Amiga binary connects through `fujinet-nio-lib`, registers a pixel resolution, and renders the live world as scaled filled vectors with sound and keyboard control in a `wb32-a1200` Amiberry WB 3.2 session, switching to block rendering and back on a key press, while every existing target still builds and passes its tests.

## Assumptions

- NTSC machines use 320x200, PAL uses 320x256; exact presentation of status/info text within the playfield is left to implementation, provided it stays legible.
- The specific toggle key is left to implementation (must not collide with existing in-game keys); no on-screen menu is required — a single key press suffices.
