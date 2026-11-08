# Engine comparison: MK4 PC vs MK Gold DC

Left: what mk4decomp (commit `af88007`) documents for MK4 PC. Right: what we have
established for Gold. Status: **[V]** verified · **[O]** observed · **[H]** hypothesis · **—** not yet looked at.

| Area | MK4 PC (mk4decomp) | MK Gold DC | Status |
|---|---|---|---|
| Overall architecture | WinMain → AppInit (27 helpers) → `MainLoopStep` ×2 per loop; fixed-step `GameLogicStep` at 60 Hz with catch-up | Shinobi boot → game main (not located). C++ game sources + `code\system\dc` platform layer | — / [O] |
| Combat system | `GameTick` → `FightFrameStep` (3 groups) → `DispatchEventQueue` → per-player tick | Script wordcode present; tick not located | [O] |
| Character state machine | Cooperative task-FSM on pool nodes (+0x84 state, +0x74 move_state `cat<<8|variant`) driven by the wordcode VM | VM entry helpers + candidate 114-entry handler table | [O]/[H] |
| Animation | AP0/AP1 pack, 612 anims, 571 bit-packed, 18-node skeleton, 6 joint records of 3 dwords, BAM and 16.16 angles | 547 anims embedded raw, 18-node skeleton; frame = 3 floats + 15 packed dwords | [V] / [H] |
| Collision / physics | Horizontal leash `dx²+dz² ≤ limit`, gravity on +0x58, 16.16 ballistic loop | — (expect float) | — |
| Weapons | Weapon queries / disarm opcodes in the VM (open-mk4 taxonomy) | `WEAPON_G.GEO/.IMG` asset, weapon strings | [O] |
| AI | AI walk counter on per-player blocks | — | — |
| Scenegraph | 63-slot pool, 0xE8-byte nodes, packed pointers, 9 transform setters, 3 Euler orders | Packed-pointer idiom present; pool not located | [O] |
| Rendering | 5 back ends (Glide, D3D2, 3 × DirectDraw SW); 28-byte draw entries; counting sort by hyperbolic z-bucket LUT | Kamui 1.10 → PowerVR2 TA (hardware sort); `DCDRAW.cpp` | [O] |
| Lighting | Per-vertex normals transformed with the vertex (s16) | Float normals per vertex in GEO **[V]**; lighting code not located | [V]/— |
| Memory | Static globals + node pool + `Mem_Malloc` | 16 MB RAM; image includes 1.25 MB + 0.5 MB zero areas | [O] |
| Audio | DirectSound SFX (ESF 8/16-bit), MCI CD-DA music, ECM movies | AICA driver (`AUDIO64.DRV`/`MANATEE.DRV`), KAT banks (11.025 kHz, fmt 4), CDDA music, CRI ADX | [V]/[O] |
| Resource management | `FILESYS.DAT` hashed index, `FSYS_fopen` | ISO9660 files by name via Shinobi `gdFs` (`MyFileRead` wrappers) | [O] |
| GEO format | 12 B header, 16 B block records, s16 vertex + s16 normal, separate tri UV table, RLE-16 textures in file | 32 B header, 32 B block records, float strip vertices with normal+UV, textures in IMG | [V] |
| IMG / textures | (none: RLE-16 inside .geo, 256×256) | Raw ARGB1555 surfaces, 512×256/512×512/… | [V] |
| Character & move tables | Wordcode scripts in the exe; asset table at `0x004f65a0`, roster `0x00516d2c`; per-char skin LUT `0x004d5718` | Wordcode in `.text`; asset tables not yet searched (search for name-string pointers, like mk4decomp did) | [O] |
| Save / config | Registry `Config` blob XOR-obfuscated + hash | VMU `SAVEFILE` (5 blocks), config + high scores | [O] |
| Video | ECM (Eurocom Custom Movie) | CRI Sofdec SFD | [V] |

## Consequences for the port

- **Logic fidelity**: Gold's float math means MK4's fixed-point results are not
  reference values for Gold. Only Gold's own SH-4 code (via the oracle) defines
  correct behaviour.
- **Renderer**: there is no software rasteriser to reproduce. The "original
  graphics" mode has to mimic PowerVR behaviour (order-independent translucency,
  punch-through alpha from ARGB1555 bit 15, fog, modifier volumes if used).
- **Determinism for netcode**: floats on SH-4 (single precision, FPSCR rounding mode)
  must be reproduced bit-for-bit. Use strict IEEE single and no FMA contraction on x86/ARM.
  This is a hard requirement from day one of the combat-core decomp.
