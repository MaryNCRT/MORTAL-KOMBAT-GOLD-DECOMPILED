# PROGRESS.md — MK Gold decomp / PC port

**Last update:** 2026-11-08 · **Phase:** 0 (audit) complete → Phase 1 (static-analysis base) next.

## Where everything is

| Path | What |
|---|---|
| Repo | https://github.com/MaryNCRT/MORTAL-KOMBAT-GOLD-DECOMPILED (`main`). Only code and docs are versioned. |
| `ISO/` | Original GDI (53 tracks). **Read-only.** |
| `Dreamcast/` | Flycast 2.2.0 + identical copy of the GDI in `Roms/`. Do not modify. |
| `EXTRACTED/disc/` | 375 files extracted from the disc; `EXTRACTED/IP.BIN`. |
| `ORIGINAL/` | `1ST_READ.BIN` (SHA-256 `05185248…1e37a`) + `1ST_READ.elf` wrapper. |
| `OUTPUT/` | Ghidra project, inventories (`functions.tsv` 4220, `strings.tsv`, `iso_files.tsv`, `anim_descriptors.tsv`), PNG textures, decompiler output. |
| `REFERENCE/` | Pinned community repos (read-only). |
| `docs/` | Audit, formats, cross-reference. |

## Status (measured)

| Metric | Value |
|---|---|
| Functions found by Ghidra | 4,220 (540,894 B; about 37 % of the ~1.45 MB code region) |
| IDENTIFIED / RECONSTRUCTED / VERIFIED | 4 / 0 / 0 (`python -I tools/tracking.py report`) |
| Formats decoded and validated | IMG 149/149 · GEO type-1 57 files · KAT 25/25 directories · animation descriptors 547 (544/546 size-checked) |

## Done in Phase 0
- Disc structure, full file inventory, IP.BIN (T-9701N V1.006 1999-09-09).
- Executable: memory map, SDK versions, C++ source paths, Ghidra import and auto-analysis.
- Formats: `0.1v` container, IMG (ARGB1555 linear), GEO type 1 (float strips), KAT directory,
  embedded animation tables.
- MK4 cross-reference: shared lineage proven (naming, `0.1v`, 37-block Scorpion, animation
  descriptor schema, packed pointers, wordcode scripts). mk4decomp pinned as permanent reference.
- Tooling: GDI extractor, ELF wrapper, asset inspectors, function tracker.

## Next (Phase 1)
1. Function seeding: code pointers from data tables + SH-4 prologue scan → re-analyse (`CreateFunctions.java` from Manhunt 2).
2. Tag SDK code (CRI/Shinobi error-string xrefs; FIDB only if the user supplies a Katana SDK).
3. Locate main loop, frame tick, script VM interpreter and handler set behind `0x8C32AF14`.
4. Run REA on `ORIGINAL/1ST_READ.elf` (first SH-4 test).
5. Check whether Flycast 2.2.0 exposes the GDB server; otherwise plan a source build with GDB.
6. Build the Ghidra-emulator oracle runner (`tests/oracle/`).

## Decisions
- Architecture A (reconstructed decomp) for the product. Static recomp rejected for shipping
  (GPL-2.0 dcrecomp, unmoddable output, needs full HAL). See AUDIT §10.
- Repo docs in English (UMK3 / Manhunt 2 convention).
