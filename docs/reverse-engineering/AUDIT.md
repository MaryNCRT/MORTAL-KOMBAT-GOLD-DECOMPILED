# MK Gold (Dreamcast) — Technical Audit, Phase 0

**Date:** 2026-11-08 · **Scope:** investigation only, no port code written.
**Target:** *Mortal Kombat Gold (USA) (Rev 1)*, GDI dump, product `T-9701N`, version `V1.006`, build date `1999-09-09`.

Every statement in this report is tagged:

- **[V] verified**: checked against the disc data or binary with a reproducible command or tool in `tools/`.
- **[O] observed**: seen once (string, hex dump, decompiler output) but not yet systematically checked.
- **[H] hypothesis**: plausible, needs confirmation. Never build on it without checking.

> **Phase 1 corrections (2026-11-08)**. Three Phase 0 statements below were wrong and are superseded:
> 1. "Opcode numbering differs from MK4 PC": **false**. Gold uses MK4's numbering (nop slots, the
>    null `0x31` and 118/120 operand counts match). See docs/systems/combat-vm.md.
> 2. "Script streams around `0x8C106300`": that region is a data table, not wordcode (`0x4F` has no
>    operand in Gold). Real scripts live in `0x8C2D0000–0x8C33B954`.
> 3. "`0x8C11E880/8E0/960` = script entry helpers" and "`0x8C32AF14` = VM handler table": **false**.
>    Those are table-lookup-and-call helpers. The VM entry is `0x8C0DC920`, the dispatcher `0x8C0DC960`,
>    the handler table `0x8C322268`.
> Also: Flycast 2.2.0 has **no** GDB server (tested), and REA rejects the SH-4 ELF (tested).
> See docs/reverse-engineering/dynamic-analysis.md.

Cross-reference with MK4 lives in [../cross-reference/](../cross-reference/mk4-to-mkg.md).

---

## 0. Local environment

| Item | Path | Notes |
|---|---|---|
| Original disc (read-only) | `ISO/Mortal Kombat Gold (USA) (Rev 1).gdi` + 53 tracks | Never modified. `Dreamcast/Roms/` holds an identical copy (track 3 compared byte-for-byte with `cmp`) **[V]** |
| Emulator | `Dreamcast/flycast.exe` | Flycast **2.2.0** (mingw x86_64). `emu.cfg` has `Debug.GDBEnabled = no`, port 3263, **no BIOS** (HLE boot). It also carries ReShade and a DualSense mapping. Whether this release build includes the GDB server is **not tested yet**. |
| Ghidra | `E:\MANHUNT 2 DESCOMP\tools\ghidra_12.1.2_PUBLIC` (shared) | SuperH4 LE processor included **[V]**. JDK 21 at `C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot`. |
| Ghidra project | `OUTPUT/ghidra/MKG.gpr` | Import of `ORIGINAL/1ST_READ.elf`, full auto-analysis. |
| REA | `E:\rea-rea-agents-6.3.0` (source), used through `npx rea-agents` | Native admission needs PE/ELF/Mach-O. `tools/bin2elf.py` produces an SH-4 ELF32 wrapper for that reason. REA on SH-4 is **not yet tested**. See §9. |
| References (read-only, pinned) | `REFERENCE/` | See [REFERENCES.md](REFERENCES.md). |
| Working copies | `EXTRACTED/disc/` (375 files), `EXTRACTED/IP.BIN`, `ORIGINAL/1ST_READ.BIN` | Produced by `tools/gdi_extract.py`, which only reads the source. |

---

## 1. Disc inventory

### 1.1 Layout **[V]**

GD-ROM with 53 tracks (`tools/gdi_extract.py`, full listing in `OUTPUT/inventory/iso_files.tsv`):

| Area | Tracks | Content |
|---|---|---|
| Low density (CD area) | 1 (data, LBA 0), 2 (audio) | Standard "this is a Dreamcast disc" track + audio warning. |
| High density | **3** (data, LBA 45000) | `IP.BIN` (boot sector) + ISO9660 PVD (volume id `MKGOLD1`). |
| High density | **4–52** (49 tracks, all audio) | **CDDA music**. Tracks 2–52 together hold 50 audio tracks, **31.1 minutes** in total. |
| High density | **53** (data, LBA 218493) | The ISO9660 file data (the directory lives in track 3 and points into track 53). |

There are no subdirectories. All 375 files sit in the root directory.

### 1.2 Files by type **[V]**

| Ext | Count | Size | What it is | Status |
|---|---|---|---|---|
| `.SFD` | 46 | 552.3 MB | CRI **Sofdec** movies (MPEG-1 system stream, `00 00 01 BA` pack header). 22 bios `MVBIO??`, 21 endings `MVEND??`, `MVINTRO`, `MVMIDWAY`, `MVEURO`. | Format known (CRI). **[V]** header |
| `.IMG` | 149 | 50.0 MB | `0.1v` texture container, raw **ARGB1555**. | **Decoded [V]**, 149 of 149 convert |
| `.GEO` | 149 | 27.9 MB | `0.1v` geometry container, float triangle strips. | Character type decoded **[V]**. Stages and 2D still open. |
| `.KAT` | 25 | 8.2 MB | Sound banks: 23 character banks, `FX.KAT`, `MENU.KAT`. | Directory decoded **[V]**. Sample codec **[H]** AICA ADPCM. |
| `.BIN` | 1 | 6.0 MB | `1ST_READ.BIN`, the game executable. | §2–4 |
| `.DA` | 1 | 0.8 MB | `WARNING.DA`: raw 16-bit PCM, interleaved stereo. | **[O]** |
| `.DRV` | 2 | 54 KB | `AUDIO64.DRV` (Sega AICA ARM7 driver, "1999.09.16"), `MANATEE.DRV` (`SDRV` Sega Manatee/GM driver). | ARM7 code, not SH-4 **[O]** |
| `.MLT` | 1 | 288 B | `STREAM.MLT`: Sega multi-unit (`SMLT`) that declares `SPSR` stream regions in sound RAM. | **[O]** |
| `.PVR` | 1 | 128 KB | `0GDTEX.PVR`: standard disc-boot logo (GBIX+PVRT, 256×256). | Standard **[V]** |

### 1.3 Naming conventions **[V]/[H]**

- **Characters** use a two- or three-letter prefix: `BA CY GO JA JC JX KI KL LK ME MI NS NNS QC RA RE SB SC SE SH SZ TA WG`. These match the 23 `CH_*.KAT` banks plus Goro (`GO`). Suffix variants:
  - `XX_GEO`: base model.
  - `XX_A_GEO`: alternate costume. Same size as the base, e.g. `SC_A_GEO.GEO` = `SC_GEO.GEO` = 385152 bytes **[H]**.
  - `XX_M_GEO`: 224-byte placeholder. All `_M_` files, `ATTRACT_.GEO` and `LEGAL_GE.GEO` are byte-identical (same MD5) **[V]**.
  - `XX_G_GEO` / `XX_E_GEO` / `XX_FAT_G` / `SC_FAT2_`: G = alternate model set, E = ending model, FAT = fatality props **[H]**.
- **Arenas:** `CAVE CHURCH ELDER FOREST ICE_PIT LAIR NREALM PRISON SHAOLIN SNAKE TOMB WELL WIND THEATRE GO/HSTD/NIGHTS/SHINX/SHINCHI…`
- **UI:** `SELECT_G MODE_SEL OPT_GEO LADDER_G VS_*_GE BUYIN_GE TEAM_GEO FONT3D_G MK4FONT1/2/3/N SOFDEC_G LEGAL_GE ATTRACT*`.
- The same `xx_geo.geo` / `_a_` / `_g_` / `_m_` / `_e_` names exist in **MK4 PC's** `FILESYS.DAT` (mk4decomp, *Character / scene naming convention*). This is direct evidence of a shared asset pipeline.

---

## 2. Main executable

| Field | Value |
|---|---|
| File | `1ST_READ.BIN`, 6,326,337 bytes, SHA-256 `0518524820d8a24d6978b494cf71a319635bbe6f8ad2c8941cf85bfa41d1e37a` **[V]** |
| Boot | `IP.BIN` names `1ST_READ.BIN`. Load and entry at **0x8C010000** (Katana standard) **[V]** |
| Format | Raw SH-4 little-endian image, not scrambled (GD-ROM, not MIL-CD). The first bytes are the Shinobi startup stub ("Lib Handle Start" at +0x30) **[V]** |
| CPU | Hitachi SH-4 (SH7091), FPU in use: vertices and animation root translations are IEEE float **[V]** |
| Compiler | Hitachi SHC (Katana SDK) **[H]**. Source paths are C++: `.\code\game\DISPLAY.cpp`, `Mkbgnd.cpp`, `Mkladder.cpp`, `Particle.cpp`, `.\code\system\dc\DCDRAW.cpp` **[O]** |

### 2.1 Memory map of the image **[O]**

From a 128 KB-block scan of instruction patterns (`sts.l pr,@-r15`), zero runs and the Ghidra function list:

| Range | Size | Content |
|---|---|---|
| `0x8C010000–~0x8C17A000` | ~1.45 MB | **Code**, with literal pools, jump tables and *inline script wordcode* (§8). |
| `~0x8C17A000–0x8C190000` | small | Code tail and constants. |
| `0x8C190000–0x8C2D0000` | ~1.25 MB | **Zero-filled** (pre-allocated buffers, BSS-like, stored in the file). |
| `0x8C2D0000–0x8C33B954` | ~0.4 MB | Data tables: code-pointer tables at `0x8C31DADC`, `0x8C322AC4`, `0x8C32AF14`, `0x8C32B0EC`, strings. |
| `0x8C33B954–0x8C5590C0` | ~2.1 MB | **Animation frame data**, embedded (§6.4). Includes the descriptor tables at `0x8C5335F8` and `0x8C558D68`. |
| `0x8C590000–0x8C618841` | ~0.5 MB | Zero-filled. |

The Dreamcast has 16 MB of main RAM, `0x8C000000–0x8CFFFFFF`. The heap and stack lie beyond the image.

### 2.2 Linked SDK and middleware **[O]** (version strings)

| Library | Version string | Role |
|---|---|---|
| Shinobi | `Shinobi Library for Dreamcast Version 1.43` (Build Jul 23 1999) | System: GD-ROM file system (`gdFs*`), peripherals (`per*`), memory, VMU backup. |
| Kamui | `KAMUI Ver 1.10.0.1` (Jul 09 1999) | PowerVR2 (Holly / Tile Accelerator) low-level rendering API. |
| Ninja | `Ninja Ver 01000086` (Apr 09 1999) | Higher-level 3D library. Its real use is unknown, possibly only init or Sofdec **[H]**. |
| CRI ADX / ADXF / SJ / SFA | `ADXF Ver.5.52`, `SFA Ver.5.55`, `SJ Ver.5.45` | Streamed audio and file partitions. |
| CRI Sofdec | `SFD/MPS/MPV/MWGSC Version 1.12` | FMV playback (`.SFD`). |
| Audio64 / AC | `_acSetHostCommand`, `amInit - Unable to load audio64.drv`, `MidiDa.drv` | AICA sound driver host side. |
| NEC copyright | `COPYRIGHT (C) NEC Corporation 1998` | PowerVR / Kamui. |

A large share of the binary is SDK code. Classifying it is a priority: SDK functions are **replaced** by the platform layer, never decompiled. See §10.

---

## 3. Architecture and code format

- One flat SH-4 image. No overlays, no other SH-4 binary on the disc **[V]** (the `.DRV` files are ARM7 code for the AICA).
- C++ game sources under `code\game\` and a platform layer under `code\system\dc\`. This is unlike MK4 PC, which mk4decomp reconstructs as C **[O]**.
- Strong lineage marker: the game code uses the same **packed-pointer / pseudo-register** idiom as MK4 PC. Pointers are stored as `(addr & 0xFFFFFF) >> 2` in globals and unpacked as `((x & mask) << 2) | base` (Ghidra output for `0x8C11E880`, `0x8C11E8E0`, `0x8C11E960`) **[O]**. mk4decomp documents exactly this encoding (`g_currentNodeIdx`, *packed_ptr*). It is the signature of the shared Midway/Eurocom engine.
- Fixed-point to float: MK4 PC is 16.16 fixed-point with BAM angles. Gold uses floats for vertices and for root translations in animation frames **[V]**. The remaining animation channels are packed integers **[H]**, so the combat math has to be re-read on SH-4 rather than assumed to be the MK4 version.

---

## 4. Functions and entry points

### 4.1 Ghidra baseline **[V]**

- Import: ELF wrapper (`tools/bin2elf.py`, EM_SH, EF_SH4, base 0x8C010000), language `SuperH4:LE:32:default`, full auto-analysis.
- Result: **4,220 functions**, 540,894 bytes in function bodies, and 1,218 defined strings (`OUTPUT/inventory/functions.tsv`, `strings.tsv`).
- **Coverage problem:** the code region is about 1.45 MB, but Ghidra only reached about 0.54 MB, roughly **37 %**. SH-4 code reaches much of its code through function-pointer tables (script handlers, state tables, SDK callbacks), which recursive descent does not follow. Next step: seed functions from (a) every code pointer in the data tables of §2.1 and (b) the `sts.l pr,@-r15` / `mov.l r14,@-r15` prologue patterns, then re-run the analysis. In Manhunt 2, `CreateFunctions.java` already did this.
- The tracker `decomp/functions.tsv` (`tools/tracking.py`) lists every function with separate **research / reconstruction / verification** columns. It currently holds 4 identified functions and 0 reconstructed or verified ones.

### 4.2 Entry points **[V]/[O]**

| Address | What |
|---|---|
| `0x8C010000` | `entry`: Shinobi startup stub (sets up the stack and jumps to the library init). |
| `0x8C11E880 / 0x8C11E8E0 / 0x8C11E960` | Script entry helpers: pack a byte address into a word cursor, fetch, dispatch (§8) **[O]**. |
| `0x8C32AF14` | 114-entry code-pointer table, referenced as `base+4` from literal pools at `0x8C11E8B8` and `0x8C11E924`. Candidate script-VM handler table **[H]**. |
| `0x8C322AC4` | 156-entry code-pointer table, 107 entries pointing to one default handler at `0x8C150B60`, referenced from `0x8C0E1E98`. Looks like a sparse state or event dispatch **[H]**. |

`main()` and the per-frame loop have not been located yet. They are the first Ghidra task after the coverage fix.

---

## 5. Resource inventory

See §1.2 and [../formats/FORMATS.md](../formats/FORMATS.md). Measured counts:

- 149 GEO, 149 IMG (one per GEO, same basename), 1 empty pair (`VS_NS_GE.*`: 12-byte containers with count 0).
- 25 KAT with **1,496** samples. Sample rates are 11025 Hz (1,477), 22050 Hz (18) and 31250 Hz (1). The format field is 4 for all **[V]**.
- 46 SFD movies. 50 CDDA tracks (music, 31.1 min).
- 547 animation descriptors embedded in the executable (§6.4) **[V]**.
- No separate animation, move-list or AI data files: **all gameplay data is inside `1ST_READ.BIN`** **[V]** (absence verified on the disc listing).

---

## 6. Model and texture formats (summary; details in docs/formats)

### 6.1 Container `0.1v` **[V]**
Shared by GEO and IMG: `char magic[4]="0.1v"; u32 file_size; u32 count; u32 0;` and 16 more zero bytes, so the header is 32 bytes. `file_size` equals the real size on every file.

### 6.2 IMG **[V]**
`count` surfaces, each a 32-byte sub-header `{u16 w, u16 h, 28×0}` followed by `w*h` **ARGB1555** pixels, **linear (not twiddled, not VQ)**. Sizes seen: 512×256, 512×512, 256×256, 128×64, and others. `tools/mkg_assets.py img2png` converts all 149 files with no size mismatch. mkggeotool's companion tools (`img2bmp` / `bmp2img`) treat it as XRGB 16-bit, which agrees.

### 6.3 GEO **[V] for type-1 blocks**
After the header, `count` block records of 32 bytes: `{u16 type, u16 n_sub, s32 rel_ofs, 24×0}`. `rel_ofs` is **relative to its own field** (`record+4`), the same convention MK4 PC uses for its 16-byte block records. Each type-1 block holds `n_sub` sub-meshes: a 32-byte header with the vertex count at +6, then `count` vertices of 32 bytes `{float nx,ny,nz, x,y,z, u,v}` forming a **single triangle strip** (degenerate-joined).
- Validated: 57 files whose blocks are all type 1 parse contiguously end to end (`mkg_assets.py geo-check`). Under the same rule, 76 files are contiguous counting partial matches.
- Scorpion `SC_GEO.GEO` has **37 blocks**, exactly the 37 blocks mk4decomp reports for MK4 PC `sc_geo.geo`. That makes it the same skeleton or part split.
- Not decoded yet: block types 2 and 128 (2D or sprite records in `ATTRACT*`, fonts, UI) and arena block types. The texture or material index for a sub-mesh is probably in the sub-mesh header (unknown fields) **[H]**.

### 6.4 Animations (embedded) **[V]**
Two descriptor tables, at `0x8C5335F8` (494 records) and `0x8C558D68` (53 records), with the **MK4 PC record shape** `{u32 data_ptr, u32 frames, u32 node_count<<16 | flags}`. Skeleton sizes: 18 nodes (457), 24 (25), 6 (6), 4/20 (2 each), 9/13 (1 each). MK4 PC has the same 18/24 split. In **544 of 546** consecutive data blocks, `size == 4 × nodes × frames` holds exactly, so frames are stored **uncompressed** (MK4 PC compresses 571 of 612 and has a bit-stream decoder; Gold does not seem to). Frame layout: 3 floats (root translation) followed by `nodes-3` packed dwords, probably joint rotations **[H]**.

### 6.5 KAT **[V] directory, [H] codec**
`u32 count`, then `count × 44-byte` entries `{u32 type(=1), u32 offset, u32 size, u32 sample_rate, u32 0, u32 fmt(=4), …}`. Data starts at `4+44*count`, verified on all 25 files. `fmt=4` is probably AICA 4-bit ADPCM (Yamaha). The codec has to be confirmed with a decode-and-listen test against Flycast output.

---

## 7. Engine structure (current knowledge)

```
Shinobi boot (0x8C010000) ─► game main (not located)
   ├─ Platform layer  code\system\dc\  (DCDRAW.cpp → Kamui/PowerVR; gdFs file I/O; per* input; VMU backup)
   ├─ Game layer      code\game\        (DISPLAY, Mkbgnd = backgrounds, Mkladder = tower, Particle)
   ├─ Script VM       wordcode streams in .text + handler tables in data (§8)
   ├─ Animation       547 descriptors, raw frames, 18-node standard skeleton
   ├─ Assets          GEO/IMG per character and arena, loaded from GD-ROM by name (strings "*.img", "ch_*.kat")
   ├─ Audio           AICA driver (AUDIO64.DRV / MANATEE.DRV), KAT banks, CDDA music, ADX streams
   └─ Video           CRI Sofdec (SFD)
```

Gold has no FILESYS.DAT. Files are opened by name through `gdFs` (`MyFileGetSize`, `MyFileRead` wrappers) **[O]**.

---

## 8. Combat systems identified so far

- **Fight script VM** **[O]/[H]**: script streams in the code region (for example around `0x8C106300`) are 32-bit words with an **opcode in the top byte and a 24-bit inline field**. Pointers to animation descriptors are interleaved with them, e.g. `0x4F00001F, 0x8C533C04, 0x12000060`. This is the model mk4decomp and open-mk4 document for MK4 (`fight_script_vm.c`: top-byte opcode, packed word cursor, wait opcodes that park the actor). **The opcode numbering is not MK4 PC's**: in Gold, `0x4F` takes a descriptor pointer, while MK4 PC's 0x4F (`native_release`) takes none. The handler table and per-opcode semantics have to be derived from the SH-4 handlers.
- **Roster** **[V]**: 23 sound-bank characters plus Goro, with move or voice banks per character. Hidden-feature strings: `KODE 33: BIG HEAD MODE ACTIVE`, `ACCESS DENIED`.
- **Modes** **[O]** (strings): Arcade ladder (`Mkladder.cpp`), VS, **Team** (`Team 1 Choose Character`), **Practice** (`PRACTICE MENU`, `Practice Info`), weapons (`WEAPON_G.GEO`), high scores saved to VMU.
- Not yet located: per-player state block, hit detection, damage tables, AI. mk4decomp gives the shapes to look for: a 0xE8-byte node pool, the `+0x54/0x58/0x5c` position, the `+0x74` move_state, and the 0x320-byte per-player blocks. These are **search patterns, not facts**, for Gold.

---

## 9. Tools: what works and what needs adaptation

| Tool | Status for MK Gold |
|---|---|
| **Own `tools/gdi_extract.py`** | Works. Lists and extracts the GDI ISO9660 read-only and dumps IP.BIN. |
| **Own `tools/bin2elf.py`** | Works. Lets Ghidra (and REA) import the raw image with correct base and processor. |
| **Own `tools/mkg_assets.py`** | Works: `img2png` (149/149), `geo-check`, `kat-list`, `anim-table`. |
| **Own `tools/tracking.py`** | Works. Function tracker with IDENTIFIED / RECONSTRUCTED / VERIFIED kept separate. |
| **Ghidra 12.1.2** (+ `ExportInventory.java`, `DecompileList.java` from Manhunt 2) | Works for SH-4. Needs a function-seeding pass (coverage about 37 %). |
| **Ghidra FID DB from Katana SDK** (`build_dc_fidb.py`, AltoRetrato) | **Needs an SDK** (Shinobi 1.43, Kamui 1.10, CRI 5.5x libraries) to build signatures. This is the fastest way to tag about half the binary as `sdk`. The SDK is not on this machine and we do not download it. |
| **dc-re-ghidra** | Not cloned. Its Dreamcast memory-map and register labelling script is worth evaluating; check its license first. |
| **REA** | Not yet run on this target. SH-4 decompilation would go through its Ghidra backend; admission of an SH-4 ELF is untested. Next step: `npx rea-agents setup` against the Ghidra install, then open `ORIGINAL/1ST_READ.elf`. Used as in Manhunt 2: inventory, function dossiers, value tracing. |
| **Flycast 2.2.0** | Runs the game. GDB server: the config keys exist, the server itself is unconfirmed in this build. AltoRetrato reports the Flycast GDB stub is incomplete. Plan: test once, and if it is missing build from source with `-DENABLE_GDB_SERVER=ON`. Also usable for RAM dumps (save states) as an oracle. |
| **Ghidra P-code emulator** (`EmulatorHelper`) | **Recommended oracle** for function-level tests. It runs original SH-4 functions with chosen inputs headless and needs no emulator. Unicorn has no SH-4 support. |
| **mkggeotool** (ermaccer) | Agrees with our GEO decode: vertex = normal, position, uv as floats, one strip per sub-mesh. Limitations: it reads sequentially and ignores block offsets and types, so it only works for character models and not arenas or UI. |
| **img2bmp / bmp2img** (ermaccer) | Same format as our decode. Usable as-is. |
| **gditools3 / GD-ROM Explorer** | Not needed (own extractor). Kept as a cross-check. |
| **ImHex** | Not installed. Patterns for `.GEO/.IMG/.KAT` worth writing from docs/formats. |
| **mk4decomp tools** (`geo_mesh.py`, `anim_pack.py`, …) | **Not directly usable**: they target MK4 PC formats (fixed-point GEO with embedded RLE textures, AP0/AP1). Their *method and invariants* transfer. |
| **open-mk4 script decoder** | Not usable directly (x86 PE input, different opcode numbering). Its **opcode taxonomy** (119 names) is a useful dictionary when naming Gold handlers. No LICENSE file in the repo, so we read it as reference only and copy no code. |
| **dcrecomp** | See §10. GPL-2.0, alpha. |

---

## 10. Static recompilation: evaluation

| Option | Pros | Cons |
|---|---|---|
| **A. Reconstructed decompilation** (our UMK3 / Manhunt 2 method) | Readable, moddable code. Floats and arbitrary limits can be changed. Matches the project goal (mods, HD, netcode). mk4decomp gives a head start on the engine model. | Slow. About 1.45 MB of code minus SDK. |
| **B. Static recompilation (dcrecomp-style)** | Fast path to something that runs. | Generated C keeps the SH-4 register model and the 16 MB memory image. It still needs a PowerVR TA, AICA, GD-ROM and Maple HAL, which is emulator-like work. It cannot be shipped as our source (generated from the copyrighted binary, and dcrecomp is **GPL-2.0**, which would bind the port). Alpha status, no conformance harness. Generated code is not moddable. |

**Decision (recommended): A as the product, plus a *non-shipped* behavioural oracle.**
- Port architecture: reconstructed C/C++ only. **No recompiled code in the product.**
- SDK functions (Shinobi, Kamui, Ninja, CRI, AICA) are **replaced** by the platform layer (SDL2 / OpenGL / own audio, FFmpeg or similar for MPEG-1 SFD video), not decompiled.
- Oracle = original SH-4 code executed through Ghidra's emulator for single functions, plus Flycast RAM snapshots for whole-frame state. This replaces the x86 DLL oracle used for Manhunt 2.
- dcrecomp is kept as a **reference** for TA and AICA behaviour only, not linked or copied (GPL-2.0).

---

## 11. Technical difficulties and dependencies

1. **Function coverage**: Ghidra reaches about 37 % of the code. Seeding from pointer tables and prologues is mandatory before any statistics mean anything.
2. **SDK classification without an SDK**: without Katana SDK libraries there is no FID DB. Fallback: string xrefs (CRI and Shinobi error strings name their functions) and manual tagging. This is a dependency on the user if they want FID.
3. **Script VM**: the gameplay logic is data (wordcode) plus native handlers. Opcode semantics have to come from the SH-4 handlers. MK4 numbering cannot be reused.
4. **Animation channel encoding**: the 15 packed dwords per frame are not decoded yet. They are needed for any renderer.
5. **Arena and UI GEO block types** (2, 128, others) are not decoded.
6. **Audio**: KAT ADPCM codec to confirm. CDDA music is easy (WAV). ADX and Sofdec are proprietary codecs: decode with existing open implementations (ADX is well documented; SFD is MPEG-1 + ADX), keep originals untouched.
7. **Rendering semantics**: PowerVR specifics (per-pixel translucency sorting, modifier volumes for shadows, fog tables, the 640×480 interlaced/VGA modes) have to be identified in `DCDRAW.cpp` code before deciding how the original-graphics mode is reproduced faithfully.
8. **Verification**: Flycast GDB availability in the installed build is unknown. The Ghidra emulator does not cover hardware access (TA, AICA), so only pure game-logic functions are oracle-testable at first. That is fine: those are the ones that matter for fidelity and netcode.
9. **Legal model** (same as UMK3 / Manhunt 2): no assets, no binaries and no generated code in the repo. `.gitignore` enforces it.

---

## 12. Roadmap by phase

| Phase | Goal | Exit criterion (measurable) |
|---|---|---|
| **0. Audit** (this document) | Inventory, formats, strategy | Done: disc inventory, 4 formats decoded and validated, MK4 cross-reference, tracker in place. |
| **1. Static-analysis base** | Full function coverage; SDK tagged; strings, xrefs and data tables named | ≥95 % of the code region inside functions; every function categorised `game`/`sdk`; main loop and frame tick located. |
| **2. Oracle and test harness** | Ghidra-emulator runner plus a Flycast GDB or state-snapshot capture | One reconstructed function passes a randomized comparison against the original (first `verified`). |
| **3. Data layer** | Complete GEO (all block types), animation channels, KAT codec, SFD/CDDA handling; open-format exporters (glTF, PNG, WAV) | Every disc asset round-trips to an open format; a character renders in a static pose from extracted data. |
| **4. Combat core decomp** | Script VM + handlers, per-player state, collision, damage, AI, using mk4decomp as the map | A scripted move sequence produces identical state frame by frame against the oracle. |
| **5. Native runtime** | SDL2 platform, OpenGL renderer (original mode), input, audio, VMU-compatible saves | A full fight playable natively with original-mode graphics, fixed 60 Hz logic. |
| **6. Modernisation** | Widescreen, high resolution, HD texture and model override, enhanced lighting mode | Original vs enhanced toggle; logic stays bit-identical between modes. |
| **7. Modding API** | Mod packages (override folders + manifest), move and parameter editing in open formats | A sample mod replaces a texture, a model and a move parameter without touching originals. |
| **8. Online** | Rollback netcode research, then lobby, friends and ranking services | Determinism test: two instances, same inputs, identical state hash for N frames. Only then rollback. |

Rollback note **[H]**: MK4's engine is a fixed 60 Hz tick whose state lives in globals and node pools. If Gold's game state is similarly confined to known RAM regions, snapshot and restore is feasible. This is decided in Phase 4, once the state layout is known.
