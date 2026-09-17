# Epic 2 Context: Bridge developers can make an evidence-backed feasibility and ABI decision

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Provide an isolated, reproducible RP2350B project and measured evidence for deciding whether a Zorro-II packet bridge to ESP32-S3 is feasible. Establish a defensible proceed/hold decision before hardware packet ABI commitment. Modeled PIO behavior, physical feasibility and acceptance of the canonical software packet contract are distinct evidence and approval requirements.

## Stories

- Story 2.1: Create an isolated, reproducible bridge project skeleton
- Story 2.2: Establish RP2350B/Zorro bus and PIO feasibility evidence
- Story 2.3: Establish bridge-to-ESP transfer and reset feasibility
- Story 2.4: Approve an evidence-backed bridge packet ABI

## Requirements & Constraints

- Keep bounded ownership, readiness, error and reset rules explicit; preserve observable exchange ordering. Runtime physical switching, serial fallback and automatic failover remain prohibited.
- The eventual bridge transfers complete opaque FujiBus packets without SLIP, preserving packet bytes, boundaries and service semantics. Keep service interpretation outside transport. Distinguish raw packet capacity from SLIP-expanded size and provisional experimental sizes.
- Temporary laboratory wiring and protective buffering are authorized; production electrical/pin-mapping/routing redesign is outside scope. Do not prematurely define production registers, mailbox layouts, PIO allocation, firmware concurrency, DMA policy or the RP2350-to-ESP protocol.
- Use test-first epio behavioral tests and shared APIO C implementations for PIO development. Record deterministic red/green evidence for representable new behavior. Keep assertions active in all host configurations and use independent expected data, IRQ and cycle oracles. Model gaps require explicit physical oracles, never fabricated emulator coverage.
- Never author or consume first-party `.pio` programs, copied instruction-array implementations, or a `pioasm` generation workflow. Native tests and firmware consume the same program/configuration source; keep hardware accesses outside host-executed paths or behind explicit stubs.
- Pin compatible epio/APIO revisions and Pico SDK/submodules. Bootstrap from source without prebuilt reference-project archives, validate SDK overrides, and reject or explicitly update stale dependency checkouts. Record verified compiler and actual board/package selection.
- Native tests must run without Pico SDK, ARM compiler, ESP-IDF or hardware. Firmware builds independently of host emulation. Keep target configurations/caches separate and generated artifacts ignored. Existing POSIX/ESP source lists must remain free of bridge and SDK sources.
- Emulator results establish modeled behavior only. Physical checks must cover synchronization, timing, peripheral interactions and electrical behavior. A successful build is not hardware feasibility evidence.

Story 2.2 concerns the RP2350B Zorro-facing side only. Use an independent RP2040 PIO stimulus generator and Core2350B DUT at 3.3 V, with common ground and separate USB diagnostics. RP2040 firmware is laboratory equipment. Do not create an ESP32-S3 test project, integrate FujiBus, or define the interprocessor protocol in this story.

Progress from four-bit /AS capture to representative wider data/control, FIFO pressure, reads, direction/release and recovery, then real-bus validation. Record wiring, revisions, commands, independent expected/observed results, losses, instrument uncertainty, margins, failures and untested conditions. Report software verification, bench functionality, instrumented bench timing and real-bus evidence separately. USB results do not measure external timing; epio and synthetic/loopback success do not establish Zorro timing feasibility.

## Technical Decisions

Reuse the standalone `repos/fujinet-nio/bridges/rp2350-zorro/` skeleton for experiments, native tests and firmware. Its name identifies role, MCU family and bus; package specifics belong in target configuration. `repos/core2350-test` is a structural reference only. The required Story 2.2 companion is `repos/fujinet-nio/bridges/rp2350-zorro/docs/story-2-2-experiment-plan.md`; its staged wiring, cases, implementation packages and evidence rules govern experiment work.

Verify the RP2040 APIO instruction-builder/SDK-loader seam before use: pinned APIO hardware initialization is RP2350-specific. Preserve shared-source testing and the no-`.pio` policy. Validate the TZT Pico-style board's header mapping and flash/SDK configuration, and isolate its build from the RP2350B target. RP2040 or RP2350A output does not verify RP2350B firmware.

Keep durable implementation/evidence documentation in the owning firmware repository and cross-repository scope in workspace planning. Provide discoverable workspace build/run commands, without coupling ordinary builds to physical experiments. Source the shared workspace environment before verification; run the cheapest meaningful checks in each changed owner.

Preserve the Amiga broker's backend-neutral public exchange ABI, caller-owned buffers, reply ownership and separate Exec/FN error domains. Backends remain service-agnostic and selected by installation/build, without serial fallback in Zorro installations. Remote exchanges remain serialized until a future design provides safe correlation.

Timeout or abort does not prove remote completion or rollback. Recovery must prevent stale data from completing a subsequent exchange. Do not automatically replay ambiguous writes; unresolved reset/quiescence guarantees block ABI readiness.

## Cross-Story Dependencies

Story 2.1 has no Epic 1 dependency. Stories 2.2 and 2.3 require its skeleton and may proceed independently alongside Epic 1. Story 2.2 can start with the available USB-connected boards and analyzer while the passive breakout is fabricated. Actual-bus work additionally requires the host/adapter, reviewed buffering and adequate instrumentation: the passive breakout provides no voltage protection. Missing later hardware blocks only dependent experiments.

Story 2.4 requires accepted Story 1.6 packet representation, boundaries, ownership and relevant failure semantics, plus positive relevant physical evidence from both 2.2 and 2.3. Missing real-bus evidence keeps the 2.2 prerequisite on hold. Builds and provisional probes cannot authorize ABI approval; unrelated remaining Epic 1 tooling does not block review after 1.6 acceptance.

Epic 3 production hardware implementation requires Epic 1 acceptance, the agreed ABI and suitable hardware. Retain these gates and escalate any required production hardware redesign outside this scope.
