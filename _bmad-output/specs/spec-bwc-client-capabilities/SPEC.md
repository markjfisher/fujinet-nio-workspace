---
id: SPEC-bwc-client-capabilities
companions:
  - wire-protocol.md
  - ../../specs/spec-amiga-bounce-world-client/SPEC.md
sources:
  - backlog/bwc-client-capabilities.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. `wire-protocol.md` carries the byte-level payload layouts and decoding rules cited below.

# Client Capability Negotiation (v3 client, pre-release)

## Why

**Mandate + opportunity.** The pre-release Bouncy World server now negotiates per-client capabilities at registration instead of inferring features from version numbers. The unreleased v3 client must send a capabilities bitmask when registering and decode responses accordingly, or it cannot receive wide coordinates or rotation data. Clients registering without capabilities get exact legacy behaviour.

## Capabilities

- **CAP-1**
  - **intent:** A client can register with an optional capabilities bitmask using the 4/6/7-field add-client form (decimal or hex) and receives its assigned single-byte client id with the response format unchanged.
  - **success:** Registering without capabilities on port 9002 behaves byte-identically to the pre-release server; a 7-field registration returns an id and subsequent `w <id>` payloads parse at the documented sizes.
- **CAP-2**
  - **intent:** With WIDE_COORDS requested, the client decodes x/y as wide coordinates so fast bodies advance smoothly by small pixel deltas.
  - **success:** A shape at world position scaled near x=300 decodes as ~300 (not wrapped); motion shows no 8px quantised jumps; a body straddling a screen edge renders partially clipped (negative or oversized coords handled).
- **CAP-3**
  - **intent:** With ROTATION requested, the client decodes per-shape angle and angular velocity and renders shapes rotated and visibly spinning.
  - **success:** Shapes render per decoded angle and visibly spin over time — including immediately after spawn (anti-drift spawning gives non-zero ω from birth); a body with omega_bits=-384 spins at −1.5 rad/s and angle_bits≈16384 orients local north along −X.

## Constraints

- Capability bit values are fixed constants shared with the server: bit 0 = 0x01 WIDE_COORDS, bit 1 = 0x02 ROTATION. Request only what you will decode; ignore unknown bits; the server never sends data for unrequested capabilities.
- The 9002 (raw) / 9003 (2-byte little-endian length prefix + payload) port split is unchanged and orthogonal to capabilities. REST equivalent: POST /client with the same CSV body returns the 1-byte id with HTTP 201.
- World-data framing is unchanged (`w <id>`); header stays `[stepNumber u8][appStatus u8][shapeCount u8 ≤ 240]`. Per-shape size depends on requested caps: 3 bytes legacy, 5 bytes with WIDE_COORDS, 9 bytes with WIDE_COORDS|ROTATION (layouts in wire-protocol.md).
- Coordinate semantics are server-computed: region-relative to your top-left corner, scaled to your registered screen size, rounded to integer pixels. Without WIDE_COORDS, x/y are uint8 read unsigned; values ≥128 near edges are possible and treated as-is.
- Rotation conventions: positive ω is counter-clockwise; angle measured CCW from world +Y; all copies of the same bodyId carry identical angle/omega across wrap seams and rotate identically; local interpolation via ω is permitted but must re-sync from each packet.
- Capability negotiation fully replaces version gating: every `#ifdef`-style V3 guard in the client is removed; the capabilities bitmask is the only feature-selection mechanism — no version-number inference anywhere in client code.

## Non-goals

- No changes to the Bouncy World server; this spec covers the client side only.
- No new capability bits beyond WIDE_COORDS and ROTATION.
- No behavioural change for legacy clients (no caps) beyond what byte-identical compatibility requires.
- No persistence of negotiated capabilities beyond registration.

## Success signal

Against one pre-release server build: the client registers with caps and parses payloads at documented sizes, wide-coordinate motion of a fast body is smooth (no quantised jumps), shapes render rotated and spin, edge-straddling bodies render partially clipped, legacy mode still passes, and no V3 preprocessor guards remain in the client codebase.
