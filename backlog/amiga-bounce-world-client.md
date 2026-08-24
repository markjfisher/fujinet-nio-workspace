# Amiga Bouncy World graphical client

Status: `TODO`

## Goal

Add a native Amiga target to `repos/bounce-world-client-nio` that renders
Bouncy World as vector graphics on a fullscreen custom screen, registering as
a high-resolution pixel client instead of a text client. The working
verification environment is Workbench 3.2 (`wb32-a1200` profile); running on
Workbench 1.3 and unexpanded machines is a later goal, but only standard
Amiga OS libraries are used to keep that porting plausible.

## Context

- Existing targets (`atari`, `bbc`, `linux`, `msdos`) are character-based.
  Shared C99 gameplay/network logic lives in `src/common`; each platform
  implements render/input shims behind headers such as `screen.h`,
  `display.h`, `double_buffer.h`.
- The server accepts any client-declared resolution and maps its internal
  40.0x24.0 float world space into that resolution as integers, so no server
  or protocol change is required. Registration dimensions are already
  per-platform constants (`REG_SCREEN_WIDTH/HEIGHT`, `REG_WORLD_WIDTH/HEIGHT`
  in each `screen.h`, sent during registration in `connection.c`).
- The server sends neutral shape ids; clients embed the shape table
  (`shapes[19]`, `embedded_shapes.c`) and hard-code rendering per id, as the
  BBC teletext renderer does. The Amiga client converts these known block
  shapes into ordered vector geometry at build time or startup.

## Deliverables

- [ ] New `src/amiga` target implementing the platform shims
      (screen init/double buffer, keyboard input, delay, shutdown, sound)
      using `intuition.library`/`graphics.library`/`dos.library` only;
      using only standard OS libraries on A1200-class machines.
- [ ] Fullscreen custom lowres screen (320x256 PAL / 320x200 NTSC) with
      double buffering; client registers its pixel resolution so the server
      maps world coordinates to pixels.
- [ ] Shape-to-vector conversion: map every embedded shape record the server
      can send to ordered polygon data scaled proportionally from the
      40x24 world grid to the registered pixel resolution.
- [ ] Vector renderer drawing filled polygons per frame via
      `graphics.library` area functions, replacing the character renderer
      for the playfield while keeping status/info text legible.
- [ ] Sound effects for collisions/events equivalent to other targets,
      using standard OS audio APIs.
- [ ] Build system target (`make amiga`) producing a binary packaged for
      transfer to Amiga test environments (NIO share / disk image as
      appropriate), plus README updates.
- [ ] Verification: host-runnable tests where possible (vector conversion,
      coordinate mapping) plus interactive Amiberry checks in the
      `wb32-a1200` WB 3.2 profile from `configs/amiga/workbenches.yaml`.

## Constraints

- No changes to the Bouncy World server, wire protocol, or other client
  targets.
- No third-party graphics libraries; OS libraries only.
- Credentials/network handling reuses `fujinet-nio-lib` unchanged.

## Exit criteria

An Amiga binary connects through `fujinet-nio-lib`, registers a pixel
resolution, and renders live world shapes as scaled filled vectors on a
fullscreen custom screen with sound and keyboard control in the WB 3.2
environment; existing targets still build and their tests pass. Kickstart
1.3 support is a later goal.
