# Asset formats: MK4 PC vs MK4 DC prototype vs MK Gold DC

Gold layouts are specified in [../formats/FORMATS.md](../formats/FORMATS.md). This
page compares them. **Do not use a column to decode another game's files.**

| Asset | MK4 PC (mk4decomp) | MK4 DC prototype (article only) | MK Gold DC (this project) |
|---|---|---|---|
| Container | `FILESYS.DAT`: 0x3000-byte hash index (`{hash, ofs, size}`), full-path hash | unknown | none: ISO9660 root, 375 files [V] |
| GEO header | `"0.1v"`, `tex_table_offset`, `file_size` (12 B) | "same structure as PC" | `"0.1v"`, `file_size`, `count`, padding (32 B) [V] |
| GEO block record | 16 B `{u16 type, u16 tri_count, s32 ofs_a, s32 ofs_b, s32 ofs_c}`, field-relative | — | 32 B `{u16 type, u16 n_sub, s32 rel_ofs, pad}`, field-relative [V] |
| Vertices | 12 B: s16 pos[3] + s16 normal[3]; strips via `(flag,count)` list; UV in a separate 8 B/tri table | 30–80 % more vertices than Gold | 32 B: float normal[3], pos[3], uv[2]; one strip per sub-mesh [V] |
| Textures | RLE-16 stream inside the .geo, 256×256, ≤15 slots | 15-bit RLE, two textures per character | separate `.IMG`, raw ARGB1555, 512×256 or 512×512 atlases [V] |
| Animations | `.AP0` directory + `.AP1` blobs; 13-bit bit-packed (571/612) | — | embedded in 1ST_READ.BIN; raw `nodes×frames` dwords; descriptor tables at 0x8C5335F8 / 0x8C558D68 [V] |
| Sounds | `.esf` (8/16-bit PCM + ADPCM tables), `pcmk%04ld.esf` | — | `.KAT` banks, 44-byte entries, 11.025 kHz, fmt 4 (ADPCM?) [V]/[H] |
| Music | CD-DA via MCI | — | CDDA, 50 tracks [V] |
| Movies | `.ECM` Eurocom Custom Movie | — | CRI `.SFD` Sofdec [V] |
| Fonts / UI | `menu.tga` + geo fonts | — | `MK4FONT1/2/3/N`, `FONT3D_G` GEO/IMG pairs (non-type-1 blocks) [O] |

## Tools per game

| Tool | Game it targets | Use for Gold |
|---|---|---|
| mk4decomp `tools/geo_mesh.py`, `geo_decode.py`, `anim_pack.py`, `esf_to_wav.py`, `fsys_*` | MK4 PC | No (different layouts); read as method only |
| open-mk4 `fsys.cpp`, script decoder | MK4 PC, War Gods | No |
| ermaccer `img2bmp` / `bmp2img` | **MK Gold DC** | Yes, agrees with our IMG decode |
| ermaccer `mkggeotool` | **MK Gold DC** | Characters only; ignores block types and offsets |
| ermaccer `fsysextract`, `esfcon` | MK4 PC | No |
| `tools/mkg_assets.py` (ours) | MK Gold DC | IMG→PNG, GEO validation, KAT listing, animation table |

## Open-format targets (for modding, Phase 3)

| Original | Export | Re-import requirement |
|---|---|---|
| IMG | PNG (RGBA, alpha from bit 15) | ARGB1555 quantisation + size rules |
| GEO (characters) | glTF 2.0 (one node per block, strips → triangle lists) | Keep block order and count (skeleton binding) |
| Animations | glTF animation channels, once the packed dwords are decoded | Lossless back-conversion test |
| KAT | WAV per sample + JSON bank manifest | Re-encode to AICA ADPCM |
| CDDA | WAV/FLAC/OGG | Mod override folders |
