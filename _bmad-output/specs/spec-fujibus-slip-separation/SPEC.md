---
id: SPEC-fujibus-slip-separation
companions:
  - brownfield.md
sources:
  - ../../planning-artifacts/backlog-fujibus-slip-separation.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# FujiBus / SLIP Separation

## Why

`FujiBusTransport` collapses SLIP framing and FujiBus packet parsing into one class. This coupling made a SLIP buffer-state bug (`_rxBuffer` stale `C0`) hard to isolate, and it means every future packet-native channel (Zorro, SPI, floppy/Pico) must rewrite the entire transport rather than plugging a different framer under a shared parser. The architecture docs already treat these as distinct concerns; this refactor makes the code match.

## Capabilities

- **CAP-1**
  - **intent:** `FujiBusTransport` is responsible only for FujiBus packet parsing and encoding; it delegates all framing to an injected `IFramer` and contains no SLIP byte constants, no `_rxBuffer`, and no reference to `0xC0` or `SlipByte::End`.
  - **success:** `grep` over `fujibus_transport.cpp` and `fujibus_transport.h` finds zero SLIP references; the `fujibus-pty-debug` `ctest` suite passes green with no regressions.

- **CAP-2**
  - **intent:** `SlipFramer` implements `IFramer` and carries all existing SLIP logic — `extractSlipFrame`, `_rxBuffer`, and `C0`-delimiter handling including the consecutive-`C0`/stale-delimiter bug fix — with no FujiBus knowledge.
  - **success:** All existing SLIP framing tests pass when targeted at `SlipFramer::nextPacket` directly, including the `C0`-consecutive-delimiter cases from `test_fujibus_transport_framing.cpp`.

- **CAP-3**
  - **intent:** `NativeFramer` implements `IFramer` as a pass-through or length-prefix framer for packet-native channels, with no SLIP logic.
  - **success:** `NativeFramer` compiles and is reachable from a build-profile selection point; its unit tests cover pass-through/length-prefix correctness.

- **CAP-4**
  - **intent:** Build-profile factories wire the correct framer by construction — `SlipFramer` for existing POSIX/RS-232/PTY/USB-CDC profiles, `NativeFramer` for future Zorro — with no `#ifdef` to select framer type.
  - **success:** No `#ifdef` appears in any framer-selection path; a notional Zorro build profile compiles end-to-end with `NativeFramer` injected.

## Constraints

- No `#ifdef` for framer selection — framer choice must be by construction at the factory/profile level.
- Scope is `repos/fujinet-nio` only; `fujinet-nio-driver`, `fujinet-nio-lib`, and the Amiga serial backend (`fujinet_nio_serial_backend.c` / `fn_session.c`) are not touched.
- `FujiBusTransport` integration tests (`test_embed_core.cpp` `InMemoryChannel` pattern) must not be rewritten — they drive the full stack unchanged.
- All existing `ctest` tests must pass green after the refactor; zero regressions permitted.

## Non-goals

- Any new physical channel (Zorro hardware, SPI hardware integration).
- Amiga driver or Amiga lib framing changes.
- Runtime framer selection (build-time selection is sufficient).
- Write support or any DiskDevice protocol changes.
- Spec-level work for Zorro or floppy-port/Pico channels.

## Success signal

`fujibus-pty-debug` ctest runs clean; `FujiBusTransport` contains no SLIP symbols; `SlipFramer` passes all SLIP framing tests directly; `NativeFramer` compiles from a build profile. See `brownfield.md` for the full acceptance checklist and file change table.
