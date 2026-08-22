---
title: FujiNet NIO product brief — addendum
status: draft
created: 2026-08-22
updated: 2026-08-22
---

# Addendum

Evidence and repository map. Product decisions live in `brief.md`.

## Repository / product map

| Repository | Product role |
| --- | --- |
| `fujinet-nio` | Adapter/runtime repo within FujiNet NIO: FujiBus services on ESP32-S3 and POSIX; channel/transport/core |
| `fujinet-nio-lib` | Multi-platform FujiNet NIO client library (6502 is one important target class, not the definition) |
| `fujinet-nio-driver` | Native OS drivers: MS-DOS `FUJINET.SYS`; Amiga `fujinet-disk.device` (ADF) as a lib client |
| `nio-core-apps` | Portable `F*` utilities where that model fits (msdos, atari, linux, amiga) |
| `fn-rom` | BBC/Master native integration, including BBC implementations of equivalent user-facing functions |
| `nio-apps` | Examples, diagnostics, smoke tests — not product utilities |
| `nio-config` | `config-nio` and platform config stages (component shipping is per-target) |
| `fujinet-nio-workspace` | Orchestration, env, cross-repo images/tests, `docs/`, `backlog/`, `completed/` — no product source |
| `fujinet-qemu-msdos` | MS-DOS QEMU image/base for host-side NIO development |
| `bounce-world-client-nio` | Example higher-level app on the NIO stack (not classic `fujinet-lib`) |

Also in `repos/` but not NIO product cores: toolchains (`cc65`, `cc65-clib`), emulator bits (`AltirraSDL`, `PDCurses`, `fujinet-emulator-bridge`).

## Review dispositions (2026-08-22)

| Point | Disposition |
| --- | --- |
| Product boundary | **Decided** in brief: FujiNet NIO = umbrella; `fujinet-nio` = adapter/runtime repo |
| Lib README lead | **Follow-up:** change lead to “multi-platform FujiNet NIO client library”; 6502 as a target class |
| Workspace README inventory | **Maintenance:** layout should match `repos/` / `.gitmodules`; stale composition lists should be removed rather than left to drift |
| C64 / WASM / embeddable | **Decided:** active / experimental / future-possibility vocabulary in the brief |
| BBC `F*` in `fn-rom` | **Decided:** native shape; do not move into `nio-core-apps` |
| Atari `nio-config` | **Decided:** Atari is in scope; not every component ships; cc65 memory is maturity, not scope |
| Classic wire/API | **Decided** in brief: preserve/evolve capability; no blanket historical compatibility |
| Amiga READMEs still say `serial.device` | **No premature edit.** Update as part of broker Stage 3 cut-over |
| Packet size / ABI | **Out of brief.** Amiga architecture/spine |
| `fujinet-lib` dual-stack duration | **Open product question** (also in the brief) |

## Maturity snapshot

**Completed (workspace):** Amiga DiskDevice Stage 8 and Phase 2; build-orchestration migration; disk-image build reorganization.

**Active backlog:** NIO broker; faster Amiga backends; Wi-Fi/network configuration; HDF/RDB; disk-image tooling cleanup; build-orchestration follow-ups.

| Surface | Label |
| --- | --- |
| POSIX/Linux adapter + lib | Active / current |
| ESP32-S3 (`fujinet-nio`) | Active / current |
| BBC/Master (`fn-rom`) | Active / current |
| MS-DOS driver + core apps | Active / current |
| Atari lib + apps + workspace `atari` workflow | Active / current (not every component ships) |
| Amiga lib, core apps, DiskDevice | Active / current; broker experimental (design, not implemented) |
| C64 as firmware host example, WASM | Future architectural possibility |
| Embeddable adapter library / extra emulator embeddings | Experimental or future — confirm per doc, do not treat as committed |

## Firmware principles this brief generalizes

`fujinet-nio` architecture: no `#ifdef` in core; explicit testable layer APIs; FujiBus/SLIP as first-class; no shared state across channel/transport/device; same device logic on ESP32 and POSIX. Those are **adapter-core** rules. The product brief extends the same separation to **host** lib, drivers, and apps.
