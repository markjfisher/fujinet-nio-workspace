---
title: FujiNet NIO product brief
status: draft
created: 2026-08-22
updated: 2026-08-22
---

# Product Brief: FujiNet NIO

## Executive summary

FujiNet NIO is a ground-up reworking of FujiNet client and device I/O. Classic FujiNet already delivers network-connected disk, file, network, clock, printer, modem, and related services to many retro machines. That ecosystem grew platform-by-platform and transport-by-transport. Service logic, physical I/O, and client interfaces are often more tightly coupled than a long-lived foundation can afford.

NIO keeps the useful product ideas and user-facing capabilities. It replaces historical coupling with a shared NIO/FujiBus request/response model, platform-independent service semantics, reusable client libraries, thin platform drivers, and physical transports that can be swapped without rewriting applications or service payloads. Strong automated tests across machines, transports, and services are part of the architecture, not an afterthought.

This is not a port of the old implementation. The project is pre-production: demos and early users exist, but accidental internal APIs and architectural mistakes are not compatibility obligations. Prefer a better long-term foundation now.

The Amiga NIO broker, serial backends, DiskDevice, and similar documents implement these principles on one platform. They do not define FujiNet NIO as a whole.

## The problem

Retro users want FujiNet-class services that feel native on their machine. Developers want to add a platform, a service, or a faster link without forking the protocol. Maintainers need one contract to test.

Today, convenient coupling fights that. A disk driver that also owns serial I/O cannot later share the wire with a file tool. A service invented per ROM or per DOS driver will not stay consistent. Timing sleeps instead of ownership will fail on a real multitasking OS. Serial proving-ground code that leaks into APIs makes Zorro, USB, or other packet links a rewrite instead of a backend.

## What we are building

A **common service model**: disk, file, network (HTTP, HTTPS, FTP, SMB, and similar), clock, modem/stream, printer, configuration/catalogue, and future services share NIO semantics. Platform code translates native OS conventions to that model. It does not fork the service contract.

**Clear layering:**

| Layer | Owns |
| --- | --- |
| Applications and native OS integrations | User commands, Exec devices, DOS drivers, filing systems, UIs |
| Service / client APIs | Stable, intentional public contracts (`fujinet-nio-lib` and peers) |
| NIO / FujiBus | Request/response packets and service payloads |
| Platform transport abstraction | How this OS submits one exchange |
| OS / device drivers | Native semantics (disk TD_*, DOS character/block, BBC FS) |
| Physical backend | Serial, Zorro, USB, SIO, PTY, TCP, and future links |

A disk device implements disk semantics. A network client implements network semantics. A backend transports opaque requests. Those jobs stay separate even when one serial path is convenient today.

**Replaceable physical transports.** No application, service API, or higher-level device depends on one physical link. Serial is an important proving-ground on several targets; it is not the product identity. On Amiga, RS-232 via `serial.device` must be replaceable by faster packet-native hardware without changing applications, DiskDevice behaviour, catalogue/mapping, NIO payloads, or public client APIs. The same rule applies on every platform.

**Multi-service, not disk-centric.** DiskService matters. The project is not a disk-only stack. An implementation that starts with disk must not force later services through disk abstractions.

**Native integration.** NIO enables Amiga Exec/AmigaDOS, MS-DOS drivers, BBC filing-system/ROM, Atari native interfaces, POSIX reference hosts, and ESP32-class adapter firmware. It does not force one UI or OS model.

**Concurrency as a principle.** On a multitasking OS, concurrent clients are real. Shared physical transports need explicit ownership and serialization, not sleeps, retries, or scheduling luck. The Amiga FLS vs disk-device `serial.device` race is an instance of this principle, not the whole of it.

**Testability.** Framing, protocol, catalogue/mapping, disk I/O, change notification, network/service behaviour, concurrency, and failure/recovery should be verifiable independently of a particular backend. A new physical backend is expected to pass the same higher-level integration suites as the reference backend, with environment/backend selection changing—not the assertions.

**Third-party foundations.** Success includes other people building apps, drivers, and ports on stable abstractions: libraries, examples, reference apps, architecture docs, platform examples, service contracts, and test harnesses. Public APIs are intentional. Early demo internals are not.

## Who this serves

| Group | Need |
| --- | --- |
| Retro-computer users | FujiNet services on a supported machine without learning NIO internals |
| Application developers | Stable libraries and service contracts, not transport-specific code |
| Platform-port developers | Thin adaptation to one service model |
| Driver / OS-integration developers | Native semantics plus a shared transport client |
| Firmware / service developers | One device/service core across POSIX and ESP32-class hardware |
| Physical-backend developers | A backend contract and parity tests, not a forked protocol |
| Maintainers | Predictable layering and reusable suites |

## Success looks like

- Several retro platforms share the same NIO service contracts.
- Applications use reusable libraries, not transport-specific code.
- Physical backends swap without rewriting apps or services.
- Native integrations behave idiomatically and correctly under concurrency.
- Multiple services coexist on one NIO architecture.
- New backends show parity through reusable integration suites.
- Docs and examples make third-party work practical.
- The stack evolves without repeating per-platform architectural forks.

## Non-goals

- One identical native UI or device model on every platform.
- Serial as a permanent architectural dependency.
- DiskService as the universal abstraction for unrelated services.
- Transport-specific details in application APIs.
- Preserving pre-production internal APIs merely for compatibility.
- Specifying every future hardware backend before one is needed.
- Duplicating service protocols independently in every port.
- Timing hacks in place of ownership and concurrency design.
- Claiming classic FujiNet wire or client-API compatibility where docs do not guarantee it.

## Principles that bind new work

1. Service semantics sit above platform transport.
2. Backends are replaceable; the public ABI and payloads stay transport-neutral.
3. Physical resources have a single clear owner and a serialized exchange path.
4. Share protocol and service implementations; keep platform layers thin.
5. Lifecycle and errors have explicit domains (native vs NIO).
6. Concurrent clients on multitasking systems are a design requirement.
7. Boundaries are testable; higher-level suites are backend-agnostic.
8. Dependency direction stays acyclic across firmware, lib, drivers, and apps.
9. Prefer simple implementations that remain correct.
10. While pre-production, prefer structural correctness over temporary compatibility hacks.

## Scope and maturity (product altitude)

NIO is a **multi-repository product**, not a single firmware binary. Workspace platform workflows today cover **Linux/POSIX, BBC/Master, MS-DOS, Atari, and Amiga**, plus ESP32-class adapter builds in `fujinet-nio`. Emulator and QEMU paths exist as development surfaces.

Not every mentioned host is equally mature or permanently committed. Firmware docs also list embeddable-library, emulator, and possible WebAssembly futures; C64 appears as a host example in firmware architecture, not as a workspace platform workflow. Treat those as intent or exploration until a backlog/completed record says otherwise.

**Proven enough to build on:** POSIX and ESP32 adapter cores with layered channels/transports/devices; multi-compiler `fujinet-nio-lib`; MS-DOS `FUJINET.SYS`; BBC `fn-rom` disk+network product shape; Amiga DiskDevice Phase 2 (standard DD/HD ADF) with catalogue mapping. **Active:** Amiga NIO broker (design for review, not implemented); Wi-Fi/network configuration; faster Amiga backends (depends on a replaceable transport). **Later:** whole-volume HDF/RDB; additional packet-native hardware.

Detail, repository map, and open questions: `addendum.md`.

## Where this brief sits

This brief is durable product context for future BMad and human work. It does not replace:

- `repos/fujinet-nio/docs/architecture.md` — adapter/firmware architecture
- `docs/amiga/nio-broker-architecture.md` — Amiga transport broker (one platform)
- `docs/amiga/disk-media-architecture.md` — Amiga media contract
- `backlog/` and `completed/` — active and accepted workspace goals
- Per-repo `README` / `AGENTS.md` — build and code ownership
