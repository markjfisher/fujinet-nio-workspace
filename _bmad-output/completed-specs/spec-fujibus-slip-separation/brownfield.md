# Brownfield Notes — FujiBus/SLIP Separation

## Current state (the thing being split)

`src/lib/fujibus_transport.cpp` collapses two concerns into one class:

- **SLIP framing:** `extractSlipFrame`, `_rxBuffer`, `C0`-delimiter handling
- **FujiBus parsing:** `FujiBusPacket::fromSerialized`, `FujiBusPacket::serialize`, `IORequest`/`IOResponse` mapping

A SLIP buffer-state bug (`_rxBuffer` retaining a stale trailing `C0` after a broken session) was hard to isolate because both concerns share the class. SLIP framing tests currently target `FujiBusTransport` indirectly.

## IFramer interface contract

```cpp
class IFramer {
public:
    virtual ~IFramer() = default;

    // Accumulate bytes from channel into internal state. Called every poll cycle.
    virtual void poll(Channel& ch) = 0;

    // Extract one complete packet payload (without framing bytes).
    // Returns true and populates outPacket if a complete packet is ready.
    virtual bool nextPacket(ByteBuffer& outPacket) = 0;

    // Frame and write one packet to the channel.
    virtual void sendPacket(Channel& ch, const ByteBuffer& packet) = 0;
};
```

## Construction patterns

**Existing POSIX / RS-232 / PTY / USB-CDC builds:**
```cpp
SlipFramer slipFramer;
FujiBusTransport transport(channel, slipFramer);
```

**Future Zorro build:**
```cpp
NativeFramer nativeFramer;
FujiBusTransport transport(zorroChannel, nativeFramer);
```

Selection is by construction at the factory/profile level — no `#ifdef`.

## Files changing

| File | Change |
|---|---|
| `src/lib/fujibus_transport.cpp` | Remove `extractSlipFrame`, `_rxBuffer`; delegate to injected `IFramer` |
| `include/fujinet/io/transport/fujibus_transport.h` | Add `IFramer&` member; remove `_rxBuffer` |
| `include/fujinet/io/transport/iframer.h` | **new** — `IFramer` interface |
| `include/fujinet/io/transport/slip_framer.h` | **new** — `SlipFramer` declaration |
| `src/lib/slip_framer.cpp` | **new** — `SlipFramer` implementation (all existing SLIP logic) |
| `include/fujinet/io/transport/native_framer.h` | **new** — `NativeFramer` declaration |
| `src/lib/native_framer.cpp` | **new** — `NativeFramer` stub (pass-through or length-prefix) |
| `tests/test_fujibus_transport_framing.cpp` | Adapt: target `SlipFramer::nextPacket` directly |
| Channel factory / build-profile wiring | Pass correct framer per build profile |

## Test strategy

- `SlipFramer` unit tests: all existing SLIP framing cases including `C0`-consecutive-delimiter and stale-delimiter; adapt from `test_fujibus_transport_framing.cpp`
- `NativeFramer` unit tests: pass-through / length-prefix correctness
- `FujiBusTransport` integration tests: unchanged — `test_embed_core.cpp` `InMemoryChannel` pattern drives the full stack and must not be rewritten

## Scope boundary

The Amiga serial backend (`fujinet_nio_serial_backend.c` / `fn_session.c`) owns its own independent SLIP framing on the Amiga side. It is not affected by this refactor.
