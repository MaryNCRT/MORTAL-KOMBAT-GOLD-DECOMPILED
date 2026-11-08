# MK Gold (Dreamcast) data formats

Tags: **[V]** verified on every file of the retail disc with `tools/`; **[O]** observed;
**[H]** hypothesis. All offsets little-endian. Source: *MK Gold (USA) Rev 1*.

## `0.1v` container header (GEO and IMG) [V]

```c
struct mkg_container {       // 32 bytes
    char  magic[4];          // "0.1v"
    u32   file_size;         // == real file size on all 297 non-empty files
    u32   count;             // GEO: blocks, IMG: surfaces
    u32   zero[5];
};
```

`VS_NS_GE.GEO` and `VS_NS_GE.IMG` are 12-byte stubs (magic, size=12, count=0).

## IMG: textures [V]

```c
struct img_surface {         // repeated `count` times right after the header
    u16 width, height;
    u8  zero[28];
    u16 pixels[width*height];   // ARGB1555, row-major, NOT twiddled, NOT VQ
};
```

`file_size == 0x20 + sum(0x20 + w*h*2)` holds on all 149 IMG files. Bit 15 is alpha
(punch-through). `python -I tools/mkg_assets.py img2png <file> <dir>`.

## GEO: geometry

```c
struct geo_block_rec {       // `count` records from 0x20, 32 bytes each
    u16 type;                // 1 = strip mesh (characters); 2, 0x80 seen in UI/2D files
    u16 n_sub;               // sub-meshes in this block
    s32 rel_ofs;             // data = &rel_ofs + rel_ofs   (field-relative, as in MK4 PC)
    u8  zero[24];
};
struct geo_sub_hdr {         // type 1 only, 32 bytes
    u8  unk0[6];             // [H] material/texture/flags
    u16 n_vert;
    u8  unk1[24];
};
struct geo_vertex {          // 32 bytes, n_vert per sub-mesh
    float nx, ny, nz;        // unit normal (checked: |n| ~ 1)
    float x, y, z;
    float u, v;              // into the paired .IMG atlas
};
```

Each sub-mesh is ONE triangle strip (degenerate vertices join pieces; mkggeotool builds
faces as `(i,i+1,i+2)` alternating winding and skips degenerate triangles).
**Validated [V]:** the 57 files whose blocks are all type 1 parse contiguously from
the first block to the last (`tools/mkg_assets.py geo-check`).
Scorpion has 37 blocks, the same as MK4 PC `sc_geo.geo`.
**Open:** block types other than 1; the unknown sub-header fields; how blocks bind to
skeleton nodes (MK4 PC: the node tree binds a block index at runtime).

## Animations: embedded in 1ST_READ.BIN [V]

Descriptor tables at `0x8C5335F8` (494 x 12 B) and `0x8C558D68` (53 x 12 B):

```c
struct anim_desc { u32 data; u32 frames; u32 nodes_flags; }; // nodes = >>16, flags = &0xffff (0/1)
```

The data is uncompressed: `4 * nodes * frames` bytes per animation (544 of 546 gaps exact).
Frame = `nodes` dwords: dwords 0..2 are floats (root translation, values ~±0.3) **[O]**;
the remaining `nodes-3` dwords are packed integers, probably three rotation fields per joint **[H]**.
`python -I tools/mkg_assets.py anim-table ORIGINAL/1ST_READ.BIN`.

## KAT: sound banks [V] layout, [H] codec

```c
struct kat_entry {           // `count` entries after u32 count, 44 bytes each
    u32 type;                // 1
    u32 offset;              // first == 4 + 44*count (verified on 25/25)
    u32 size;
    u32 sample_rate;         // 11025 (1477), 22050 (18), 31250 (1)
    u32 zero;
    u32 format;              // 4 on all 1496 samples -> [H] AICA 4-bit ADPCM
    u32 rest[5];
};
```

## Other files

| File | Format |
|---|---|
| `*.SFD` | CRI Sofdec: MPEG-1 PS video + ADX audio [O] |
| `WARNING.DA` | raw signed 16-bit PCM, stereo interleaved [O] |
| `AUDIO64.DRV`, `MANATEE.DRV` | ARM7 AICA driver images (Sega) [O] |
| `STREAM.MLT` | Sega `SMLT` multi-unit with `SPSR` stream-buffer declarations [O] |
| `0GDTEX.PVR` | GBIX + PVRT 256x256 (disc logo) [V] |
| CDDA tracks 2, 4–52 | Red Book audio: 50 tracks, 31.1 min [V] |
