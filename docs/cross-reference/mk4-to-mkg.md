# MK4 → MK Gold: cross-reference

What existing Mortal Kombat 4 work can speed up MK Gold, and how far it can be trusted.
Function-level detail: [function-mapping.csv](function-mapping.csv). Engine side by
side: [engine-comparison.md](engine-comparison.md). Formats: [asset-formats.md](asset-formats.md).

Tags: **[V]** verified on Gold data/binary · **[O]** observed · **[H]** hypothesis.

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

## Three different targets: do not mix them

| | MK4 PC (1998) | MK4 Dreamcast prototype | MK Gold Dreamcast (1999) |
|---|---|---|---|
| Binary | `MK4.EXE`, PE32 x86, MSVC 5.0 SP3 | SH-4 executable, does not boot | `1ST_READ.BIN`, SH-4, Katana SDK (Shinobi 1.43, Kamui 1.10) |
| Developer | Eurocom (port of the N64/PSX code base, per mk4decomp) | Eurocom for Midway | Eurocom (`EUROCOM TEAM` in credits) |
| Archive | `FILESYS.DAT`, hashed full paths | `.GEO` containers like PC | Plain ISO9660 files on the GD-ROM |
| Geometry | `.geo`: s16 fixed-point vertices, embedded RLE-16 textures | `.GEO` with PC structure, 15-bit RLE textures, 30–80 % more vertices than Gold | `.GEO` float strips + separate `.IMG` raw ARGB1555 |
| Animation | `.AP0/.AP1`, 571/612 bit-packed | unknown | embedded in the executable, raw |
| Math | 16.16 fixed point, BAM angles, sine LUT | unknown | IEEE float (SH-4 FPU) in meshes and root motion |
| Source language | reconstructed as C | unknown | C++ (`.\code\game\*.cpp` strings) |
| Public RE | mk4decomp (byte-matching, MIT), open-mk4 | sega-dreamcast-info.com article (VincentNL, ermaccer) | ermaccer MortalKombat.Tools (img2bmp, bmp2img, mkggeotool) |

The prototype facts come from the sega-dreamcast-info.com article only. **We do not have
that build.** Its formats must never be assumed for Gold. Two points from the article are
consistent with our Gold data: textures are raw RGB555 in Gold **[V]**, and Gold models
are lighter **[O]**.

## Verified shared lineage (evidence for reusing MK4 knowledge)

1. **Asset naming.** The same `xx_geo / xx_a_geo / xx_g_geo / xx_m_geo / xx_e_geo` scheme and the
   same arena basenames (`tomb_geo`, `well_geo`, `wind_geo`, `forest_g`, `ice_pit_`, `lair_geo`,
   `theatre_`, `shaolin_`) appear in MK4 PC (mk4decomp) and in Gold's disc listing **[V]**.
2. **`0.1v` magic and field-relative offsets.** Both games' GEO start with `0.1v`, and both encode
   block data offsets relative to the field that holds them **[V]**. Record sizes differ
   (16 B on PC, 32 B on Gold).
3. **Same skeleton split.** Scorpion has 37 GEO blocks in both games **[V]**.
4. **Animation descriptor schema.** `{data, frames, nodes<<16|flags}`, 18-node standard skeleton
   with a 24-node minority, in both games **[V]** (Gold: 457 × 18, 25 × 24; PC: 575 × 18, 25 × 24).
5. **Packed-pointer pseudo-register idiom.** `(addr & 0xFFFFFF) >> 2` cursors in globals, unpacked
   with `<< 2 | base`, appear in decompiled Gold script-entry helpers `0x8C11E880..960` **[O]**.
   This is the exact idiom mk4decomp documents for MK4 PC's node indices.
6. **Wordcode fight scripts.** 32-bit words with the opcode in the top byte, carrying animation
   references, appear in Gold `.text` (e.g. `0x8C106300`) **[O]**. MK4 PC: `fight_script_vm.c`.

So Gold is a later, float-based Dreamcast revision of the **same engine and data model**,
not a different engine. Addresses, opcode numbers, struct offsets and the numeric
representation **do differ** and must be re-derived on SH-4.

## What we can reuse, by category

### Reuse directly as knowledge (high value, low risk)
- **Engine model**: two tracks per tick (menu FSM + fight tick), fixed 60 Hz logic with a
  catch-up loop, entity groups (players / arena / HUD), ping-pong event queue,
  cooperative task-FSM with "wait" opcodes that park an actor. These shapes tell us
  *what to look for* in Gold. (mk4decomp `combat_fsm.md`, `node_struct.md`)
- **Animation semantics**: descriptor → frame pointer = `data + nodes*frame`; nodes are
  grouped per joint; the skeleton is a runtime-built node tree. (`architecture.md`)
- **Script-VM semantics**: wait/park/resume, loop/repeat markers, clip binding,
  native tails. The open-mk4 opcode *taxonomy* (119 names) is a vocabulary for naming
  Gold handlers once their behaviour is read. (`open-mk4/docs/research/retail-vm.md`)
- **Combat geometry**: horizontal distance `sqrt(dx²+dz²)` driving reaction tiers,
  midpoint for the camera, a ± facing vector. Expect the same logic in float.
- **Per-player state**: four player slots and per-player state blocks with a health
  value. Gold has Team mode, so slot usage may differ.

### Needs adaptation
- **GEO decoding**: same concepts (field-relative block table, strips, per-part blocks),
  different binary layout (32-byte records, float vertices with normal and UV, textures
  split into IMG). Our decoder already implements the Gold layout.
- **Animation decoding**: Gold is uncompressed but packs joint channels differently
  (3 floats + packed dwords). The MK4 BAM / 16.16 dual-format insight is a lead for the
  packed dwords.
- **Function mapping**: every MK4 function is a *search target*. Use its role, callers
  and globals to find the SH-4 counterpart; record evidence in `function-mapping.csv`.
- **Method**: mk4decomp's "measure first" loop (trace which opcodes and handlers actually
  run) maps onto Flycast RAM snapshots plus the Ghidra emulator.

### Investigate from zero
- Everything Dreamcast-specific: Kamui/PowerVR rendering (`DCDRAW.cpp`), GD-ROM I/O,
  Maple input, VMU saves, AICA audio, KAT banks, CDDA, ADX streams, Sofdec movies.
- Gold-only content: new characters (Baraka, Mileena, Kung Lao, Cyrax, Kitana, Sektor),
  weapons and Team mode, `Mkladder.cpp`, Particle system, Kode cheats.
- Script opcode numbering and handler semantics (numbering verified **different**).
- Arena GEO block types and UI/2D blocks.

## Script VM: what we know in Gold {#script-vm}

- Entry helpers `0x8C11E880`, `0x8C11E8E0`, `0x8C11E960`: cursor = `(addr & 0xFFFFFF) >> 2`, plus a
  base; fetch `*(((cursor & mask) << 2) | base)`; call through a pointer. B and C then test a
  global (pause flag?) and call a continuation **[O]** (Ghidra output in
  `OUTPUT/vm_candidates.c`).
- Candidate handler table `0x8C32AF14`: 114 code pointers into `0x8C11xxxx–0x8C12xxxx`, used as
  `base+4` by the helpers' literal pools **[O]/[H]**.
- MK4 PC table: 49 entries at `0x4e8970` (mk4decomp). The sizes differ, consistent with a
  different numbering.

## Recommended next steps (cross-reference specific)
1. Seed the remaining functions (pointer tables + prologues), then find the main loop.
2. Decompile the handler set behind `0x8C32AF14` and name each opcode from its behaviour.
3. Find the per-player tick by searching float `fsqrt` code reading two actor positions.
4. Decode one character's skeleton binding (GEO blocks ↔ animation nodes) and render a pose.

## Reference repository

mk4decomp is a **permanent technical reference** for this project, pinned at commit
`af8800788f704be1e3c85a0e3cbf5688f112c426` in `REFERENCE/mk4decomp` (MIT, author contributions only).
Policy: read and cite, never vendor its code into the port. Any adapted formula carries
attribution (MIT notice) and a Gold-side verification test. See
[../reverse-engineering/REFERENCES.md](../reverse-engineering/REFERENCES.md).
