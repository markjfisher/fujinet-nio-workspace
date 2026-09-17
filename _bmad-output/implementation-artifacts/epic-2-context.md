# Epic 2 Context: Bridge developers can make an evidence-backed feasibility and ABI decision

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Give bridge developers an isolated, reproducible RP2350B project and measured evidence for deciding whether a Zorro-II packet bridge to ESP32-S3 is feasible. Deliver a defensible proceed/hold decision before committing to the hardware packet ABI. Software builds and modeled PIO behavior provide useful preliminary evidence, but physical feasibility and acceptance of the canonical software packet contract are separate prerequisites for ABI approval.

## Stories

- Story 2.1: Create an isolated, reproducible bridge project skeleton
- Story 2.2: Establish RP2350B/Zorro bus and PIO feasibility evidence
- Story 2.3: Establish bridge-to-ESP transfer and reset feasibility
- Story 2.4: Approve an evidence-backed bridge packet ABI

## Requirements & Constraints

- Transfer complete opaque FujiBus packets with bounded ownership, readiness, capacity, error handling and reset behavior. Preserve packet bytes and service semantics; leave disk, file, clock and other service interpretation on the existing service side.
- Native transfers carry raw packets without SLIP. Preserve explicit packet boundaries: byte reads and polling intervals do not define a packet. Distinguish raw packet capacity from SLIP-expanded size and from any provisional hardware experiment size.
- Keep electrical mapping and routing unchanged. Do not invent production register addresses, mailbox layouts, PIO allocation, firmware task/core architecture, clock assumptions, DMA policy or an RP2350-to-ESP protocol before evidence supports those decisions.
- All hardware/PIO development uses test-first epio behavioral tests and shared apio C implementations. Record a deterministic failing behavior test before implementation, then demonstrate green. Never author or consume `.pio` programs or use a `pioasm` generation workflow in first-party bridge code.
- Native tests execute the same program/configuration source as firmware, with emulation enabled only for the host build. Keep hardware-only accesses outside host-executed code or behind explicit stubs; keep test assertions active in all supported host configurations. Expected data, IRQ state and instruction cycles must be independent oracles, not values copied from the implementation.
- Pin compatible epio/apio releases and resolved revisions. Build native epio from source, use the same apio revision and compatible ABI options in both builds, and reject or explicitly update stale dependency checkouts. The inspected initial pair is epio v0.2.1 and apio v0.3.0.
- Bootstrap a pinned Pico SDK with required submodules; validate a documented SDK path override. Record the verified compiler version and actual RP2350 platform/board/package selection. RP2040 or Pico 2/RP2350A output is not RP2350B verification.
- Host tests must build and run without Pico SDK, an ARM compiler, ESP-IDF or hardware. Firmware must build independently of the epio emulator and host test archive. Use separate configurations and build directories; keep caches and generated artifacts out of version control.
- Record reproducible bootstrap, CMake, CTest and firmware build commands, dependency revisions, ELF/UF2 outputs, repeated-setup and stale-pin behavior, and source/build-rule guards. Existing POSIX/ESP source lists must remain free of bridge and SDK sources.
- Emulator evidence establishes modeled PIO behavior only. Document limitations and retain instrumented physical checks for bus timing, synchronization, DMA/peripheral interactions, electrical behavior and bridge-link operation. A firmware skeleton does not establish functioning RP2350B or Zorro hardware support.

## Technical Decisions

The bridge belongs in `repos/fujinet-nio/bridges/rp2350-zorro/` with a standalone CMake build, C program sources, tests and README. The name expresses component role, MCU family and bus; RP2350B and Zorro-II specifics belong in target configuration and documentation. Keep SDK integration isolated from existing firmware platform selection. The experimental `repos/core2350-test` project is a structural reference, never a build/runtime prerequisite or source of prebuilt archives; its PIO text-generation rules are excluded.

Import Pico SDK before the firmware CMake `project()` and initialize it afterward. Keep host configuration independent. Reuse existing protocol definitions and fixtures only where actual consumers require them; do not duplicate constants, link service libraries merely to transfer opaque packets, or depend on an external FujiNet firmware checkout.

Keep durable bridge design and feasibility evidence in the owning firmware repository; workspace planning tracks cross-repository scope and acceptance. Source the shared workspace environment before verification and run the cheapest meaningful check in every changed owner. Existing source-generation/build isolation is an explicit gate for the skeleton.

Preserve the Amiga broker's public exchange ABI, caller-owned buffers, reply ownership and separate Exec/FN error domains. Backends remain service-agnostic and selected by installation/build, with no serial fallback or runtime physical failover in a Zorro installation. Observable ordering is preserved without permanently mandating a particular internal worker design. Remote exchanges remain serialized until a future design supplies safe correlation.

Timeout or abort does not prove remote completion or rollback. Recovery must prevent stale data from completing a later exchange; ambiguous writes cannot be made safe by automatic replay. Link experiments must distinguish measured reset/quiescence guarantees from assumptions and treat unresolved stale-completion risks as blockers.

## Cross-Story Dependencies

Story 2.1 has no Epic 1 dependency. Stories 2.2 and 2.3 require its skeleton and can proceed independently of each other and alongside Epic 1. Both require suitable physical fixtures and instrumentation, documented procedures, exact configurations and captured measurements; bounded experimental probes are not production architecture.

Story 2.4 requires accepted Story 1.6 software packet representation, boundaries, ownership and relevant failure behavior, plus positive relevant evidence from both physical feasibility stories. Missing or contradictory evidence blocks ABI sign-off even if builds or probes pass. Unrelated unfinished Epic 1 tooling does not block that design review once Story 1.6 is accepted.

Production hardware implementation in Epic 3 requires the agreed ABI, suitable hardware and Epic 1 acceptance. Keep later bus/link choices and implementation sizing deferred until those gates are met; a hardware redesign is outside this epic's authorized scope.
