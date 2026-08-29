# Backlog: Separate FujiBus packet parsing from SLIP stream framing

## One-line summary

Extract SLIP framing out of `FujiBusTransport` into a distinct framer layer so
that packet-native channels (Zorro, SPI, floppy/Pico) can share the same
FujiBus parser without SLIP, and so that stream channels remain maintainable in
isolation.

---

## Background and motivation

The architecture docs (`docs/architecture.md`, `docs/driver_architecture.md`,
`docs/amiga-floppy-channel.md`) are explicit and consistent: FujiBus is the
logical packet protocol; SLIP is one framing mechanism used to carry FujiBus
over byte-stream channels. They are intentionally distinct concepts and must
not be used interchangeably.

Today that separation exists only in the docs. In code, `FujiBusTransport`
collapses both concerns into a single class:

- `extractSlipFrame` (SLIP boundary detection, `_rxBuffer` management) and
- `FujiBusPacket::fromSerialized` / `FujiBusPacket::serialize` (FujiBus
  packet parsing and encoding)

both live inside `src/lib/fujibus_transport.cpp`.

This coupling has already caused one real maintenance problem: a SLIP-specific
buffer-state bug (`_rxBuffer` retaining a stale trailing `C0` after a broken
session) was difficult to isolate precisely because the SLIP state and the
FujiBus logic share a class. It also means that adding a Zorro or SPI channel
requires writing a completely new transport class from scratch rather than
plugging a different framer under a shared FujiBus parser.

The intended future channels explicitly call for this separation:

- Amiga Zorro — parallel, packet-native; no SLIP
- Amiga floppy/Pico — `docs/amiga-floppy-channel.md` explicitly states "the
  integrated design will not use SLIP between Pico and ESP32"
- USB CDC on existing hardware — could reuse packet-native FujiBus once framing
  is decoupled

---

## Desired outcome

A clean implementation session should produce the following:

### 1. A `IFramer` interface (or equivalent name)

Sits between `Channel` (raw bytes) and the FujiBus parser. Responsibility:
given a raw byte stream, produce complete packet byte-buffers with known
boundaries; given a packet byte-buffer, write it to the channel.

Minimum contract:

```cpp
class IFramer {
public:
    virtual ~IFramer() = default;

    // Accumulate bytes from channel into internal state.
    // Called every poll cycle.
    virtual void poll(Channel& ch) = 0;

    // Try to extract one complete packet payload (without framing bytes).
    // Returns true and populates outPacket if a complete packet is ready.
    virtual bool nextPacket(ByteBuffer& outPacket) = 0;

    // Frame and write one packet to the channel.
    virtual void sendPacket(Channel& ch, const ByteBuffer& packet) = 0;
};
```

### 2. `SlipFramer : IFramer`

The existing `extractSlipFrame` logic, `_rxBuffer`, and SLIP encode/decode
moved here. This is where the `C0`-delimiter handling and the bug fixed in
this session live. No FujiBus knowledge.

### 3. `NativeFramer : IFramer` (or `LengthPrefixFramer`)

For packet-native channels. The channel itself provides packet boundaries
(e.g. Zorro DMA transfer, SPI transaction), so this framer is a thin pass-
through or uses a simple length-prefix. No SLIP.

### 4. `FujiBusTransport` refactored to accept an `IFramer`

`FujiBusTransport` becomes responsible only for FujiBus packet parsing and
encoding (`FujiBusPacket::fromSerialized`, `serialize`, `IORequest`/
`IOResponse` mapping). It no longer owns `_rxBuffer` or any framing code. It
delegates to the injected `IFramer` for packet extraction and writing.

```cpp
class FujiBusTransport : public ITransport {
public:
    FujiBusTransport(Channel& channel, IFramer& framer);
    ...
};
```

Existing POSIX/RS-232/PTY/USB-CDC builds construct:

```cpp
SlipFramer slipFramer;
FujiBusTransport transport(channel, slipFramer);
```

A future Zorro build constructs:

```cpp
NativeFramer nativeFramer;
FujiBusTransport transport(zorroChannel, nativeFramer);
```

### 5. All existing tests continue to pass; new unit tests cover each framer

- `SlipFramer` unit tests for the `C0`-consecutive-delimiter cases (the tests
  added in this session can be adapted to target `SlipFramer::nextPacket`
  directly, not via `FujiBusTransport`).
- `NativeFramer` unit tests for pass-through / length-prefix correctness.
- `FujiBusTransport` integration tests remain unchanged (they drive through
  the full stack via the loopback channel pattern already established in
  `test_embed_core.cpp`).

---

## Scope and constraints

| In scope | Out of scope |
|---|---|
| `FujiBusTransport` + framer split in `repos/fujinet-nio` | Amiga driver (`repos/fujinet-nio-driver`) changes |
| `SlipFramer` carrying all existing SLIP logic | Any new physical channel (Zorro hardware, SPI) |
| `NativeFramer` stub for future use | Amiga lib (`repos/fujinet-nio-lib`) framing changes |
| Unit tests for both framers | BMAD spec-level work for Zorro or floppy |
| All existing tests green | |

The Amiga serial backend (`fujinet_nio_serial_backend.c`) owns its own
SLIP framing independently (via `fn_session.c`). That layer is not affected
by this refactor; it is on the Amiga side of the broker, not the ESP side.

---

## Files likely to change

| File | Change |
|---|---|
| `src/lib/fujibus_transport.cpp` | Remove `extractSlipFrame`, `_rxBuffer`; delegate to framer |
| `include/fujinet/io/transport/fujibus_transport.h` | Add `IFramer&` member; remove `_rxBuffer` |
| `src/lib/slip_framer.cpp` (new) | `SlipFramer` implementation |
| `include/fujinet/io/transport/slip_framer.h` (new) | `SlipFramer` declaration |
| `include/fujinet/io/transport/iframer.h` (new) | `IFramer` interface |
| `src/lib/native_framer.cpp` (new) | `NativeFramer` stub |
| `tests/test_fujibus_transport_framing.cpp` | Adapt to test `SlipFramer` directly |
| Channel factory / build-profile wiring | Pass correct framer for each profile |

---

## Acceptance criteria

1. `FujiBusTransport` contains no SLIP byte constants, no `_rxBuffer`, and no
   reference to `0xC0` or `SlipByte::End`.
2. `SlipFramer` passes all existing SLIP framing tests including the
   consecutive-`C0` / stale-delimiter cases.
3. A POSIX `fujibus-pty-debug` build with `SlipFramer` injected passes all
   existing ctest tests with no regressions.
4. A notional `NativeFramer` compiles and is reachable from a build-profile
   selection point (even if no physical Zorro channel exists yet).
5. No `#ifdef` introduced to select framer — selection is by construction at
   the factory/profile level.

---

## Reference material for the implementing session

- `docs/driver_architecture.md` §"Channel framing and transport" — the
  intended interface contract for channel adapters
- `docs/amiga-floppy-channel.md` §"Why the integrated channel will not use
  SLIP" — the explicit rationale for packet-native framing
- `docs/architecture.md` §"FujiBus & SLIP Protocol Layer" — the layer
  separation intent
- `src/lib/fujibus_transport.cpp` — current monolithic implementation to split
- `tests/test_fujibus_transport_framing.cpp` — SLIP framing tests written in
  this session; adapt these to target `SlipFramer` directly
- `tests/test_embed_core.cpp` — `InMemoryChannel` pattern for integration tests

---

## Follow-on: Replace #ifdef build-profile chain with per-platform profile files

**Context:** `build_profile.cpp` currently selects the active `BuildProfile` via a long `#elif defined(FN_BUILD_*)` preprocessor chain. After the IFramer separation (Stories 1–4), framer selection is by construction in `bootstrap.cpp` — the `TransportKind` switch drives it. A cleaner pattern (already used for POSIX channel creation in `channel_factory.cpp`) is CMake-selected per-platform source files: each build target gets its own `build_profile_<target>.cpp` that returns a hardcoded `BuildProfile` with no preprocessor. `TransportKind` then becomes pure metadata/introspection, and `bootstrap.cpp`'s switch can be replaced by a platform-specific bootstrap or factory.

**Why now is a good time:** The IFramer work is done; framer and transport concerns are cleanly separated. The `build_profile.cpp` file is the last remaining concentration of `#ifdef`-based platform selection in the transport/framing layer.

**Rough scope:**
- Add `build_profile_<target>.cpp` per build variant (amiga_rs232, fujibus_pty, esp32_usb_cdc, zorro, …)
- CMake selects the right file per preset/env
- Delete `build_profile.cpp`'s `#elif` chain
- Optionally flatten `bootstrap.cpp`'s `TransportKind` switch into per-platform bootstrap files

**Non-goals:** Any new hardware or protocol support.
