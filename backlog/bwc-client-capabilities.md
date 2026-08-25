# SPEC: Client Capability Negotiation (v3 client, pre-release)

## 1. Summary

The server now negotiates per-client capabilities at registration instead of inferring features from version numbers. The unreleased v3 client must send a capabilities bitmask when registering and decode responses accordingly. Clients that register without capabilities get exact legacy behaviour.

## 2. Registration changes

TCP add-client command (port 9002/9003 unchanged)

```
add-client name,version,screenWidth,screenHeight[,worldWidth,worldHeight[,capabilities]]
```

- capabilities is an optional integer bitmask: decimal (3) or hex (0x03).
- Omitting it, or sending 0, means "legacy behaviour".
- The response is unchanged: single byte containing the assigned client id.
- The 9002 (raw) / 9003 (2-byte little-endian length prefix + payload) port split is unchanged and orthogonal to capabilities.

### REST equivalent

POST /client with the same CSV body; returns 1-byte id with HTTP 201. Same 4/6/7-field forms accepted.

Capability bits (server constants — clients must use identical values)

| Bit | Value | Name | Meaning |
|--|--|--|--|
|0|0x01|WIDE_COORDS|x/y are little-endian int16 instead of uint8|
|1|0x02|ROTATION|each shape carries angle + angular velocity|

Example: wide coords + rotation = 0x03.

Rule: request only what you will decode. The server never sends data for unrequested capabilities, and may add new bits later — ignore unknown bits on any future server.

## 3. World data response (w <id>)
Framing as today (9002 raw; 9003 = [len: uint16 LE][payload]). Payload layout:

```
[stepNumber: uint8]        simulation step counter (wraps 0-255)
[appStatus: uint8]         event bitmask (unchanged semantics)
[shapeCount: uint8]        number of shapes, max 240
{ per shape:
    [shapeId: uint8]
    [x] [y]                see coordinate rules below
    ([angle: uint16 LE])   if ROTATION requested
    ([omega: int16 LE])    if ROTATION requested
}
```

### Coordinate decoding

Coordinates are relative to your region's top-left corner (subtract nothing; server has done it), scaled to your registered screen size, rounded to integer pixels.

- Without WIDE_COORDS: [x: uint8][y: uint8], range 0..255 read unsigned. Values ≥128 near edges are possible; treat as-is.
- With WIDE_COORDS: [x: int16 LE][y: int16 LE]. Values may be slightly negative or slightly ≥ screen size when a shape straddles your region edge or the wrap seam — this is intentional (partial visibility). Clip to viewport when drawing. Typical magnitude of out-of-range values: a few pixels.

### Rotation decoding (only if ROTATION requested)

#### Appended after x/y for every shape:

- angle: uint16 LE — orientation of the shape's local north. Full turn maps to 0..65535: θ_radians = angle_bits / 65535 × 2π
- omega: int16 LE — angular velocity in fixed point: ω_rad_per_sec = omega_bits / 256
- All copies of the same bodyId carry identical angle/omega regardless of how many times the body appears across wrap seams — rotate every copy identically.
- Angle is constant between collisions except as advanced by ω; you may interpolate locally between updates using ω for smoother animation, but always re-sync from the next packet.

## 4. Behavioural notes for testing

1. Registering without caps on 9002 must behave byte-identically to the pre-release server.
2. WIDE_COORDS alone: payload per shape is 5 bytes (id + 4). Verify a shape at world position scaled near x=300 decodes as ~300, not wrapped.
3. WIDE_COORDS|ROTATION: payload per shape is 9 bytes (id + 4 + 4). Sanity check: a body with omega_bits = -384 is spinning at −1.5 rad/s (clockwise); angle_bits ≈ 16384 means north points along −X (quarter turn CCW).
4. Rotation direction convention: positive ω is counter-clockwise; angle measured CCW from world +Y.
5. Bodies spawned by the server now have non-zero ω from birth (anti-drift spawning) — expect visible spin immediately, not only after collisions.


## 5. Acceptance criteria
- [ ] Client registers with caps field; id returned and subsequent w <id> payloads parse at the documented sizes.
- [ ] With WIDE_COORDS, motion of a fast body advances smoothly by small pixel deltas (no 8px quantised jumps).
- [ ] With ROTATION, shapes render rotated per angle and visibly spin over time.
- [ ] A body straddling a screen edge renders partially clipped (negative or oversized coords handled).
- [ ] Legacy mode (no caps) still passes against the same server build.