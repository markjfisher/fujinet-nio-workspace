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
  - **intent:** The shared gameplay/network code in `src/common` runs unmodified behind new Amiga platform shims (screen lifecycle/double buffer, keyboard control, timing/delay, shutdown).
  - **success:** No `src/common` or other-target source changes are needed beyond build wiring; keyboard commands work in-game and quit/cleanup returns cleanly to Workbench/CLI.
- **CAP-4**
  - **intent:** Collision/event sound effects equivalent to other targets play during gameplay.
  - **success:** Audible event sounds using OS audio APIs are demonstrated in an emulated WB 3.x session alongside rendering.

## Constraints

- Verification environment is Workbench 3.2 via the `wb32-a1200` Amiberry profile (`configs/amiga/workbenches.yaml`); Kickstart/Workbench 1.3 support is deferred, not designed against now — but only standard OS libraries (`intuition.library`, `graphics.library`, `dos.library`) are used, keeping later 1.3 porting plausible. No third-party graphics libraries.
- No server or wire-protocol change: registration dimensions are per-platform constants already; the server maps its 40.0x24.0 float space into any declared client resolution as integers. Shape geometry scales proportionally (a size-5 shape spans 5.0 world units).
- Shape table is embedded client-side (`shapes[19]`, same ids as other targets); rendering per id is hard-coded like the BBC teletext renderer.
- Network handling reuses `fujinet-nio-lib` unchanged.

## Non-goals

- No changes to the Bouncy World server, protocol, or other client targets' behavior.
- No Kickstart/Workbench 1.3 certification in this delivery — later goal.
- No Workbench-window mode, high-res or interlace screens, or AGA-specific enhancements in this first item.
- No new shape definitions or server-driven shape variants.

## Success signal

An Amiga binary connects through `fujinet-nio-lib`, registers a pixel resolution, and renders the live world as scaled filled vectors with sound and keyboard control in a `wb32-a1200` Amiberry WB 3.2 session, while every existing target still builds and passes its tests.

## Assumptions

- NTSC machines use 320x200, PAL uses 320x256; exact presentation of status/info text within the playfield is left to implementation, provided it stays legible.
