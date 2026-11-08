# GEO: all block kinds (extends FORMATS.md)

Tags: **[V]** verified on every file · **[O]** observed · **[H]** hypothesis.
Parser: `tools/mkg_geo.py` (new). The Phase 0 character check `mkg_assets.py geo-check` is unchanged.
Full check: `python -I tools/mkg_assets.py geo-tile EXTRACTED/disc`.
Tests: `tests/test_geo.py` (synthetic fixtures for every block kind, plus disc tests when available).

## Result [V]

**148 / 148 non-empty GEO files are tiled exactly**: header (32 B) + `count` block records (32 B
each) + payloads cover every byte, with no gaps or overlaps.

| Kind | Flags (u16 @+0) | Blocks | Files (examples) |
|---|---|---|---|
| mesh | 0x000 | 825 | arenas (CAVE, CHURCH, ICE_PIT…), FAT/fatality props, fonts |
| mesh | 0x001 | 1,976 | characters (`XX_GEO`, `XX_A_GEO`, …) |
| mesh | 0x002 | 60 | ATTRACT2, FONT3D_G, SHARE3_G, WEAPON_G |
| mesh | 0x004 | 5 | BUYIN_GE |
| mesh | 0x040 | 7 | CHURCH_G, NREALM_G |
| mesh | 0x200 | 201 | arenas (CAVE, FOREST, LAIR, PRISON, TOMB, WIND…), SHARED_G, WEAPON_G |
| sprite | 0x080 | 114 | placeholders (`XX_M_GEO`, ATTRACT_, LEGAL_GE) |
| sprite | 0x180 | 367 | fonts, SELECT_G, VS_*, TEAM_GEO |
| sprite | 0x280 | 453 | FAT props, VS_GEO, SHARED_G, ICE_PIT |
| sprite | 0x380 | 119 | MK4FONT1, SHARED/SHARE2, SC_FAT_G |
| sprite | 0x480 | 23 | MK4FONT2, SELECT_G, VS_* |

The u16 at +0 is a **flag word**, not a type enum. Bit `0x80` selects the record layout.
For sprites, `(flags >> 8)` equals the sub-header mode `h[5]` on every sprite (0x180→1, 0x280→2,
0x380→3, 0x480→4).

## Mesh record (flags & 0x80 == 0) [V]

```c
struct geo_mesh_rec { u16 flags; u16 n_sub; s32 rel; u8 zero[24]; };   /* payload = &rel + rel */
```
Payload = `n_sub` x (`sub_header[32]` + `n_vert` x `vertex[32]`), vertex = `{float nx,ny,nz, x,y,z, u,v}`.
This holds for all mesh flag values (3,074 blocks), not only characters.

## Sprite record (flags & 0x80 != 0) [V]

```c
struct geo_sprite_rec {
    u16 flags;        /* 0x080 | mode << 8 */
    u16 aux;          /* 0, 1, 256, 257 seen [O] */
    u16 w, h;         /* integer copies of fw, fh (truncated; 12 records have fractional floats) */
    s16 x0, y0;       /* -left, -top extent */
    s32 rel;          /* @+12: payload = &rel + rel */
    float fw, fh;     /* on-screen size */
    float fright, fbottom;   /* = w + x0, h + y0 */
};
```
Payload = exactly **160 bytes** on all 1,076 sprites: one sub-header (`n_vert = 4`, `h[5] = mode`)
followed by 4 vertices with normal and position all 0 (built at run time from the rect) and
UVs that select an axis-aligned **atlas region** in the paired IMG.
The UV region size is **not** the on-screen size (VS_SC: 233 texels for w = 234; CY_FAT block 2:
37×26 texels for 450×324), so sprites are scaled.

## Sub-header fields [O]
`h[3]` = vertex count [V]. `h[5]` = mode: 0/1/2 on meshes, 1–4 on sprites. On meshes it correlates
with block flag 0x200 (1,365 of the 1,557 sub-meshes in 0x200 blocks have mode 2) [O]. Probably a blend or
translucency class [H]. `h[0]`, `h[1]`, `h[2]` take 0/1 [O]. `h[2]` is set on about half the
sub-meshes, perhaps winding or double-siding [H]. `h[4]`, `h[6]` and `h[7]` are 0 on all 26,498
sub-headers. `h[8..15]` have not been surveyed yet.

## Still open
- Meaning of mesh flags 0x001/0x002/0x004/0x040/0x200 (render pass? collision? skinned part?).
- Texture page selection for IMG files with 2 surfaces (512×1024 total): whether UVs > 0.5 or the
  mode picks the page.
- How the engine binds character blocks to animation joints (see animation-engine.md).
