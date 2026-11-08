# Animation engine

Tags: **[V]** verified · **[R]** read in the SH-4 code · **[O]** observed · **[H]** hypothesis.
Tools: `tools/mkg_anim.py`, `tools/mkg_assets.py anim-table`. Tests: `tests/test_anim_vm.py`.

## Descriptor [V]

```c
struct anim_desc {          /* 12 bytes; tables at 0x8C5335F8 (494) and 0x8C558D68 (53) */
    u32 data;               /* absolute address of frame data inside 1ST_READ.BIN */
    u32 frames;             /* 1..n */
    u32 nodes_flags;        /* nodes = >>16 (18 x457, 24 x25, 6 x6, 4/20 x2, 9/13 x1); flags = &0xFFFF (0 or 1) */
};
```

- Global animation index = position in table 1, then table 2 (547 total). The VM references a
  descriptor with a **packed pointer** to its 12-byte record (`mkg_vm.anim_index`).
- Data is uncompressed: block size = `4 * nodes * frames` for 544 of 546 consecutive blocks.
- Flag bit 0 meaning: unknown. It is **not** "compressed" (MK4 PC's bit 15); flagged blocks are raw too.

## Frame layout

```
frame k = nodes dwords at data + 4*nodes*k
  [0..2]      float root translation (x, y, z)                 [R] copied to node+0x30/+0x34/+0x38 by 0x8C068CC0
  [3..n-1]    packed joint rotation, one dword per joint        [V] decoder 0x8C0692A0 (oracle-verified)
```

With 18 nodes: 3 translation dwords + **15 joint rotations**.

### Packed rotation [V]

```
31        22 21          11 10           0
+-----------+--------------+--------------+
|  c (10b)  |    b (11b)   |    a (11b)   |
+-----------+--------------+--------------+
dst[0] = a * K2048    K2048 = float 0x3B490FDB = 2*pi/2048   (stored at 0x8C2F7160)
dst[1] = b * K2048
dst[2] = c * K1024    K1024 = float 0x3BC90FDB = 2*pi/1024   (stored at 0x8C2F715C)
```

All three components cover a full turn [0, 2π) in radians, as IEEE single (`float FPUL` from a
signed int, then one `fmul`). Reconstructed in `decomp/engine/anim_rot.c`; **1,000 random trials
in the P-code emulator, 0 mismatches, bit-exact floats**. The Python model `mkg_anim.unpack_rotation_bits`
is checked against the same vectors.

Bit-flip statistics across all 18-node animations (Phase 1 survey) put the field boundaries at
bits 22 and 11 independently of the code. Wrap-arounds occur in about 1–2 % of consecutive frames,
consistent with angles.

**Not established:** which axis each of a/b/c drives and the Euler order. MK4 PC has three Euler
orders selected per joint type; Gold's matrix builder has not been read yet.

## Pipeline (current map)

| Function | Address | Status | Role |
|---|---|---|---|
| `AnimUnpackRot10_11_11` | `0x8C0692A0` | **verified** | one rotation dword → 3 floats |
| `Anim_ReadRootTranslation` | `0x8C068CC0` | [R] partial | 3 floats from the frame cursor → node+0x30/34/38, cursor += 3 |
| `Anim_NodeListWalk` | `0x8C069140` | [O] | walks a node list (assert in `.\code\game\DISPLAY.cpp`), stride fields `+0xF` and `+8`, calls the decoder |
| (pose builder) | `0x8C0693A0` | [O] | 976 bytes of float math, calls the decoder. Likely matrix composition and/or blending |
| (caller) | `0x8C068C00` | [O] | cursor setup (`+0xF`), callback install |

## Relationship with the fight VM [V]

13 opcodes take a clip (animation descriptor) operand: `01 02 09 0C 0E 0F 11 46 47 48 49 68 71`
(604 operand uses across the decoded streams). The prefixed forms store the clip into
`node(R311C)[+0x24]`, which is MK4's "group +0x24 = animation id" field. Playback opcodes
(`03` forward, `05` forward_to #n, `06` backward_count, `12` cursor_set, `4A`, `4D` …) carry frame
counts in the inline field. Frame timing is therefore script-driven and counted in game ticks [H].

## Open items (next targets)
1. Bone hierarchy: find the per-character rig table (MK4 PC: "executable rig records") and the
   binding of GEO blocks (37 for Scorpion) to the 15 animated joints plus static parts.
2. Euler order and axis assignment: read the matrix builder called after the decoder.
3. Interpolation: whether frames are blended (0x8C0693A0 float math) or stepped.
4. Animation events: sounds and effects are emitted by VM opcodes (25–2C sound ops, 2A, 40 spawn),
   not by the frame data, as far as the frame layout shows.
5. The two descriptors whose gap is not `4*nodes*frames` (index of the anomalies via `anim-table`).
