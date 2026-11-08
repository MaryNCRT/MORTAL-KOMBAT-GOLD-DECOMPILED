# CLAUDE.md — MK Gold (Dreamcast) decomp / native PC port

Native Windows + Linux reimplementation of *Mortal Kombat Gold* (Sega Dreamcast, USA Rev 1),
built from reverse engineering of the original `1ST_READ.BIN` (SH-4). Same method as our
UMK3 and Manhunt 2 projects. Not an emulator front end, not an ISO patch.

**Language:** repo content (code, comments, docs, commits) in English.

## Rules
- **Understand, then reconstruct, then modernise.** No mass reconstruction before the
  inventory and the oracle exist (see docs/reverse-engineering/AUDIT.md §12).
- **Never modify** `ISO/`, `Dreamcast/Roms/`, `ORIGINAL/`. Work on copies in `EXTRACTED/`, `OUTPUT/`.
- **Never invent** functions, structs or results. Tag claims [V]/[O]/[H]; only [V] may be built on.
- **Tracker** `decomp/functions.tsv` via `tools/tracking.py`. IDENTIFIED / RECONSTRUCTED /
  VERIFIED are separate columns. `verified` needs a reproducible oracle test; compiling is not verification.
- **Architecture A:** hand-reconstructed C/C++ only in the product. SDK (Shinobi, Kamui, Ninja,
  CRI, AICA) is *replaced* by the platform layer, not decompiled. No recompiled code in the product.
- **Oracle:** Ghidra P-code emulator (single functions) + Flycast (state snapshots / GDB).
- **Determinism:** game logic must reproduce SH-4 single-precision float results bit for bit.
- **Legal:** zero assets, binaries or generated code in the repo (`.gitignore`). The user supplies the disc.
- **References** in `REFERENCE/` are read-only and pinned (docs/reverse-engineering/REFERENCES.md).
  mk4decomp is the permanent technical reference; GPL/unlicensed repos are knowledge only.
- Run Python on extracted or downloaded data with `python -I`.

## Toolchain
- Ghidra 12.1.2: `E:\MANHUNT 2 DESCOMP\tools\ghidra_12.1.2_PUBLIC` (JDK 21 `C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot`).
  Project `OUTPUT/ghidra/MKG`, program `1ST_READ.elf` (SuperH4:LE:32:default, base 0x8C010000).
  Scripts in `tools/ghidra/` (ExportInventory, DecompileList). Call `analyzeHeadless.bat` from PowerShell (path has spaces).
- REA (`E:\rea-rea-agents-6.3.0`, `npx rea-agents`): inventory, dossiers, value tracing, on the ELF wrapper.
- Flycast 2.2.0 in `Dreamcast/`. Ollama for local assistance.
- Port stack (later): C/C++, CMake, SDL2, OpenGL first.

## Key tools
`tools/gdi_extract.py` · `tools/bin2elf.py` · `tools/mkg_assets.py` · `tools/tracking.py`

State of the project: `PROGRESS.md`.
