# Wire protocol reference

Byte-level layouts and decoding rules for capability-aware registration and world data. Cited by SPEC-bwc-client-capabilities CAP-1..CAP-3.

## Registration

TCP add-client command (ports 9002/9003 unchanged):

```
add-client name,version,screenWidth,screenHeight[,worldWidth,worldHeight[,capabilities]]
```

- `capabilities`: optional integer bitmask, decimal (`3`) or hex (`0x03`). Omitting it or sending `0` means legacy behaviour.
- Response unchanged: single byte containing the assigned client id.
- REST equivalent: `POST /client` with the same CSV body → 1-byte id, HTTP 201. Same 4/6/7-field forms accepted.

### Capability bits (server constants — clients use identical values)

| Bit | Value | Name | Meaning |
|--|--|--|--|
| 0 | 0x01 | WIDE_COORDS | x/y are little-endian int16 instead of uint8 |
| 1 | 0x02 | ROTATION | each shape carries angle + angular velocity |

Wide coords + rotation = `0x03`.

## World data response (`w <id>`)

Framing unchanged: 9002 raw; 9003 = `[len: uint16 LE][payload]`.

```
[stepNumber: uint8]        simulation step counter (wraps 0-255)
[appStatus: uint8]         event bitmask (unchanged semantics)
[shapeCount: uint8]        number of shapes, max 240
{ per shape:
    [shapeId: uint8]
    [x] [y]                see coordinate rules
    ([angle: uint16 LE])   if ROTATION requested
    ([omega: int16 LE])    if ROTATION requested
}
```

Per-shape sizes: 3 bytes legacy · 5 bytes WIDE_COORDS · 9 bytes WIDE_COORDS|ROTATION.

## Coordinate decoding

Coordinates are relative to your region's top-left corner (server has already subtracted/scaled), scaled to your registered screen size, rounded to integer pixels.

- Without WIDE_COORDS: `[x: uint8][y: uint8]`, range 0..255 read unsigned. Values ≥128 near edges are possible; treat as-is.
- With WIDE_COORDS: `[x: int16 LE][y: int16 LE]`. Values may be slightly negative or slightly ≥ screen size when a shape straddles your region edge or the wrap seam — intentional partial visibility. Clip to viewport when drawing. Typical out-of-range magnitude: a few pixels.

## Rotation decoding (only if ROTATION requested)

Appended after x/y for every shape:

- `angle`: uint16 LE — orientation of the shape's local north. Full turn maps to 0..65535: θ_radians = angle_bits / 65535 × 2π.
- `omega`: int16 LE — angular velocity fixed point: ω_rad_per_sec = omega_bits / 256.
- All copies of the same bodyId carry identical angle/omega regardless of how many times the body appears across wrap seams — rotate every copy identically.
- Angle is constant between collisions except as advanced by ω; local interpolation between updates using ω is allowed for smoother animation, but always re-sync from the next packet.

Sanity anchors: omega_bits = −384 → −1.5 rad/s (clockwise); angle_bits ≈ 16384 → north along −X (quarter turn CCW).
