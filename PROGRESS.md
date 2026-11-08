# PROGRESS.md — MK Gold decomp / PC port

**Last update:** 2026-11-08 · **Phase:** 1 (SH-4 engine reconstruction) in progress.

## Where everything is

| Path | What |
|---|---|
| Repo | https://github.com/MaryNCRT/MORTAL-KOMBAT-GOLD-DECOMPILED (`main`). Only code and docs are versioned. |
| `ISO/` | Original GDI (53 tracks). **Read-only.** |
| `Dreamcast/` | Flycast 2.2.0 + identical copy of the GDI in `Roms/`. Do not modify. |
| `EXTRACTED/disc/` | 375 files extracted from the disc; `EXTRACTED/IP.BIN`. |
| `ORIGINAL/` | `1ST_READ.BIN` (SHA-256 `05185248…1e37a`) + `1ST_READ.elf` wrapper. |
| `OUTPUT/` | Ghidra project (`ghidra/MKG`), inventories (`inventory_p1/`), VM handler analysis (`vm/`), full decompilation (`decomp_all.c`), logs. |
| `OUTPUT/flycast-gdb/` | Isolated Flycast copy used for the GDB test (not the user's install). |
| `REFERENCE/` | Pinned community repos (read-only). |

## Status (measured)

| Metric | Value | Source |
|---|---|---|
| Functions | 6,660 (Phase 0: 4,220) | `tools/tracking.py report` |
| Confirmed / probable starts (game band) | 3,030 / 1,802 | discovery column |
| Game-band bytes inside functions | 604,390 of 1,118,496 (54 %) | `OUTPUT/inventory_p1/coverage.tsv` |
| IDENTIFIED / RECONSTRUCTED / VERIFIED | 125 / 3 / 3 | tracker |
| Oracle vectors | 1,400 trials over 3 functions, 0 mismatches | `tests/oracle/vectors/` |
| VM opcodes characterised | 120 / 120 slots (operand rule + flow), all from Gold handlers | `docs/systems/vm-opcodes.tsv` |
| Script streams decoded | 738 / 739 clean (623 entry seeds) | `tools/mkg_vm.py scan` |
| GEO files fully tiled | 148 / 148 (meshes + sprites) | `tools/mkg_assets.py geo-tile` |
| Automated tests | 22 passing | `python -I -m unittest discover -s tests` |

## Done in Phase 1
- **Function discovery**: band boundaries (SDK / game / SDK), pointer and prologue seeding,
  confirmed vs probable, byte coverage. → docs/reverse-engineering/function-discovery.md
- **Combat VM**: entry `0x8C0DC920`, dispatcher `0x8C0DC960`, fetch `0x8C0E08E0`, table `0x8C322268`
  (120 slots), pseudo-register model, wait mechanism, operand rules, control flow. The opcode numbering
  matches MK4 PC. Opcode DB + standalone disassembler. → docs/systems/combat-vm.md
- **Animation**: descriptor and frame layout. Packed rotation 10:11:11 decoded and **oracle-verified**
  (`0x8C0692A0`). Root-translation reader located. Link to VM clip operands. → docs/systems/animation-engine.md
- **GEO**: every block kind decoded (flag word; sprite records with 160-byte quad payloads).
  New parser + fixtures. → docs/formats/geo-extended.md
- **Dynamic analysis**: P-code oracle pipeline working end-to-end. Flycast 2.2.0 has no GDB stub
  (tested). REA rejects SH-4 (tested). → docs/reverse-engineering/dynamic-analysis.md
- **Corrections** to three Phase 0 claims (opcode numbering, script location, entry helpers), noted
  in AUDIT.md and mk4-to-mkg.md.

## Recommended next targets (Phase 1 continued)
1. **Oracle the VM core**: emulate `VM_FetchWord`, `VM_Dispatch` and a short real stream with stubbed
   natives; reconstruct the fetch/dispatch/wait core in C and verify it.
2. **Handler semantics**: read the ~40 most-used handlers (32, 05, 03, 34, 0F, 4A, 48, 27, 47, 12, 3F, 62)
   and the natives they call; name opcodes from Gold behaviour.
3. **Skeleton**: find the rig/hierarchy table, the Euler order (matrix builder after `0x8C0692A0`) and
   the GEO-block ↔ joint binding; render one pose from extracted data as the first visual check.
4. **Character ↔ script map**: tie the 623 entry seeds to their callers and to the roster
   (`select` index `node[+0x34]`, 24 slots).
5. **SDK tagging**: CRI and Shinobi string xrefs → `category=sdk` for `sdk_low`/`sdk_high`.
6. **Dynamic**: decide on a GDB-enabled Flycast build (user decision), or parse save states for RAM snapshots.

## Decisions
- Architecture A (reconstructed decomp) for the product; no recompiled code (AUDIT §10).
- Oracle = Ghidra P-code emulator; vectors are versioned, replay needs only a C compiler.
- Names stay address-based or mechanical until behaviour is proven. MK4 names are reference labels.
- Repo docs in English (UMK3 / Manhunt 2 convention).
