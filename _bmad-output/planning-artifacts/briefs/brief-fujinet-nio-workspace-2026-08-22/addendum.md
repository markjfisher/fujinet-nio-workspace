---
title: FujiNet NIO product brief — addendum
status: draft
created: 2026-08-22
updated: 2026-08-22
---

# Addendum

Evidence, repository map, maturity notes, and disagreements between the product-brief seed and existing documentation. Not a second architecture.

## Repository / product map

| Repository | Product role |
| --- | --- |
| `fujinet-nio` | Adapter/firmware/runtime: FujiBus services (disk, file, network, clock, modem, printer, Fuji config) on ESP32-S3 and POSIX; channel/transport/core layering |
| `fujinet-nio-lib` | Reusable client library: public service APIs, FujiBus packets, per-target transport/channel |
| `fujinet-nio-driver` | Native OS drivers: MS-DOS `FUJINET.SYS`; Amiga `fujinet-disk.device` (ADF) as a lib client |
| `nio-core-apps` | User-facing portable `F*` utilities (`fls`, `fmount`, `fhost`, …) on msdos/atari/linux/amiga; BBC `F*` still generated from `fn-rom` |
| `nio-apps` | Examples, diagnostics, smoke tests — not product utilities |
| `nio-config` | `config-nio` and platform config stages (msdos, bbc, linux shipped; Atari UI present but not in `all-targets` due to cc65 memory) |
| `fn-rom` | BBC/Master native integration: DFS-compatible ROM + network; boot/config disk for bulky commands |
| `fujinet-nio-workspace` | Orchestration, env, cross-repo images/tests, `docs/`, `backlog/`, `completed/` — no product source |
| `fujinet-qemu-msdos` | MS-DOS QEMU image/base for host-side NIO development |
| `bounce-world-client-nio` | Example higher-level app on the NIO stack (not classic `fujinet-lib`) |

Workspace `README.md` submodule list omits `nio-core-apps` and `nio-config`; `docs/build-orchestration.md` names them as owners. The brief follows orchestration + those READMEs.

Also in `repos/` but not NIO product cores: toolchains (`cc65`), emulator bits (`AltirraSDL`, `PDCurses`), `fujinet-emulator-bridge`. `fujinet-lib` (legacy client) appears under some trees; bounce-world explicitly contrasts NIO vs that older stack.

## Relationship to classic FujiNet

Firmware README: “fresh start”, avoid legacy architectural constraints. Firmware architecture: replace macro-heavy, platform-entangled firmware with a layered, testable core. Lib: optional legacy appkey compatibility in a separate header/archive — capability bridge, not a claim that the whole public API matches classic `fujinet-lib`.

No inspected document guarantees full wire or host-API compatibility with historical fujinet-firmware. Preserve **product capability**; do not preserve **implementation internals**.

## Maturity (from workspace completed / backlog / READMEs)

**Completed (workspace):** Amiga DiskDevice Stage 8 and Phase 2 (standard DD/HD ADF, `FMOUNT`/`FUMOUNT`/`FMOUNTRESTORE`, units DN0–DN7); build-orchestration migration; disk-image build reorganization.

**Active backlog (not this brief’s job to execute):** NIO broker (Amiga transport arbitrator, design for review); faster Amiga backends (parity with RS-232 suites); Wi-Fi/network configuration; HDF/RDB; disk-image tooling cleanup; build-orchestration follow-ups.

**Platform snapshot (uneven by design):**

| Surface | Docs say |
| --- | --- |
| POSIX/Linux adapter + lib | Primary development/reference host |
| ESP32-S3 | Production-intent firmware target in `fujinet-nio` |
| BBC/Master | Product ROM shape (disk+net); serial default, userport/1MHz build variants |
| MS-DOS | Driver + core apps + QEMU; serial, IOCTL, INT F5 backends |
| Atari | Lib + apps + boot disk + emulator-side FujiNet in workspace `atari` workflow |
| Amiga | Lib, core apps, DiskDevice; serial proving-ground; broker not implemented |
| Apple II / C64 / WASM | Mentioned in legacy lib or firmware futures; not workspace `build.sh` platform workflows |

## Seed vs documentation — open for review

1. **Product boundary.** Seed: whole stack. `fujinet-nio` docs: adapter/firmware (channels → transports → core → devices). Both can be true if this brief is the product umbrella and firmware docs stay device-side. Confirm that naming (“FujiNet NIO” vs “fujinet-nio firmware”) in public materials.
2. **`fujinet-nio-lib` audience.** README lead: “multi-platform 6502 library”; body: Atari, BBC, MS-DOS, Amiga, Linux, Watcom, amiga-gcc. Lead sentence is narrower than the product.
3. **Workspace repo inventory.** `README.md` layout vs `build-orchestration.md` / actual `repos/` (core-apps, config).
4. **Exploratory hosts.** Firmware architecture: embeddable library, emulators, WebAssembly, C64 as a host example. Seed: do not treat exploratory targets as equal or committed. Brief treats them as non-equal.
5. **BBC core utilities.** Seed groups “core apps” together. Docs: BBC `F*` utilities come from `fn-rom`, not `nio-core-apps` C programs.
6. **Atari config.** Seed lists Atari native interfaces as in-scope. `nio-config` Atari link is currently out of `all-targets`.
7. **Amiga serial.** Seed and Amiga architecture agree serial is proving-ground. `nio-core-apps` / `nio-apps` Amiga READMEs still say they use `serial.device` through the lib — true until broker Stage 3.
8. **Packet size / ABI numbers.** Architecture prose vs Amiga `FN_MAX_PACKET_SIZE` 1024 is a **platform ABI** issue, not product-brief material. Tracked in the Amiga spine/architecture, not here.
9. **`fujinet-lib` vs NIO.** Bounce-world and optional appkey shim show a migration story. How long dual stacks are supported is not stated as a product policy.

## Principles already written down (firmware) that this brief generalizes

`fujinet-nio` architecture: no `#ifdef` in core; explicit testable layer APIs; FujiBus/SLIP as first-class; no shared state across channel/transport/device; same device logic on ESP32 and POSIX. Those are **adapter-core** rules. The product brief extends the same separation to **host** lib, drivers, and apps (replaceable backends, concurrency ownership, non-disk-centric services).
