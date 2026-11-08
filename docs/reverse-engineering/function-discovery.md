# SH-4 function discovery (Phase 1)

Tags: **[V]** verified · **[O]** observed · **[H]** hypothesis.
Function count is **not** code coverage. Both are reported separately below.

## Inputs
- Ghidra 12.1.2, program `1ST_READ.elf` (`tools/bin2elf.py`), `SuperH4:LE:32:default`, base `0x8C010000`.
- Phase 0 baseline: 4,220 functions from Ghidra's auto-analysis (recursive descent from `entry`).

## SH-4 code conventions observed in this binary [O]

| Aspect | Observation |
|---|---|
| Calling convention | Hitachi/GCC SH ABI: args r4–r7, return r0, `pr` = return address; callee-saved r8–r14; r15 = stack; FPU args fr4–fr11. |
| Prologue | `mov.l r14,@-r15` / `mov.l r8..r13,@-r15` (`0x2Fm6`), `sts.l pr,@-r15` (`0x4F22`), `add #-n,r15` (`0x7Fnn`), `fmov.s frN,@-r15`; frame pointer set with `mov r15,r14` (often in a branch delay slot). |
| Epilogue | `mov r14,r15; lds.l @r15+,pr; mov.l @r15+,r14...; rts` with a register pop in the delay slot. |
| Calls | Nearly every call is indirect: `mov.l @(disp,pc),rN; jsr @rN` with the target in a literal pool after the function. Ghidra resolves these as long as the pool value is a constant. |
| Literal pools | Directly after each function's `rts`, then `nop` (`0x0009`) padding up to the next 32-byte boundary. |
| Alignment | **Game band: every function starts on a 32-byte boundary** (2,423 of 2,423 consecutive functions in Phase 0). SDK bands: 2- or 4-byte alignment. |
| Game-code style | The engine is translated code. Its state lives in a block of **pseudo-registers** (globals `0x8C2F3100–0x8C2F3150`, plus a pause flag at `0x8C2F3074` tested after most calls) and in **packed pointers** (`(addr & 0xFFFFFF) >> 2`). Control flow chains through tiny functions that set pseudo-registers and call or tail-call the next. |
| Indirect flow | Code pointers stored in data tables (`0x8C31DADC`, `0x8C322AC4`, `0x8C32AF14`, `0x8C32B0EC`, …) and inside script wordcode (native call targets). Recursive descent misses these. |

## Band boundaries [H, strongly supported]

| Band | Range | Evidence |
|---|---|---|
| `sdk_low` | `0x8C010000–0x8C05D6E0` | Functions are not 32-aligned. CRI error/version strings are referenced from `0x8C010144–0x8C022EE8`, Kamui strings from `0x8C02B14C–0x8C02B1DC`. |
| `game` | `0x8C05D6E0–0x8C16E800` | Longest run of 32-aligned functions (`0x8C05D6E0`…`0x8C16E760`). Game-text strings (menus, Kode, VMU messages) are referenced from `0x8C066820–0x8C162920`. |
| `sdk_high` | `0x8C16E800–0x8C17A000` | Alignment drops again. The audio-driver host strings (`_ac*`, `amInit`) are referenced from `0x8C1712D2–0x8C1746DA`, plus Shinobi. |

The band is recorded in `decomp/functions.tsv`. It is a location fact, not a category
decision: `category` (game/sdk) still requires per-function evidence.

## Discovery pass: `tools/ghidra/SeedFunctions.java`

1. **Pointer seeds** (`ptr`): every 4-aligned dword in the image whose value points into the
   code range, at a target that is not already inside a function. It must be 32-aligned in the
   game band or start with a prologue elsewhere, and must not be read as data by PC-relative
   loads. Classified as **confirmed**: the address is stored as a code pointer.
2. **Boundary scan** (`prologue`): every 32-aligned address in the game band that is not
   covered, not defined data and not a literal-pool target, and that directly follows `rts`/`rte`,
   a tail `jmp`/`bra` plus delay slot, or `nop` padding. Classified as **probable**.
3. `analyzeChanges` after each pass. A second run created nothing new (fixed point).

Reproduce:
```powershell
analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis -scriptPath tools\ghidra `
    -postScript SeedFunctions.java OUTPUT\seed1 8c05d6e0 8c16e800 8c17a000
analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis -readOnly -scriptPath tools\ghidra `
    -postScript ExportCoverage.java OUTPUT\inventory_p1
```

## Results [V] (measured by ExportCoverage.java and tracking.py)

| | Phase 0 | Phase 1 |
|---|---|---|
| Functions | 4,220 | **6,660** (6,554 after seeding + 106 VM handlers created by VmHandlers.java) |
| from flow analysis (confirmed) | 4,220 | 4,465 (incl. callees reached from seeded functions and the 106 handlers) |
| from code pointers (confirmed) | — | 393 |
| from boundary scan (probable) | — | 1,802 |

Per band (function starts):

| Band | Confirmed | Probable |
|---|---|---|
| sdk_low | 1,576 (160,616 B) | 0 |
| game | 3,030 (412,742 B) | 1,802 (191,648 B) |
| sdk_high | 252 (28,744 B) | 0 |

**Byte coverage** (`OUTPUT/inventory_p1/coverage.tsv`):

| Band | Size | In functions | Instructions outside functions | Defined data | Undefined |
|---|---|---|---|---|---|
| sdk_low | 317,152 | 160,616 (51 %) | 35,606 | 38,402 | 82,528 |
| game | 1,118,496 | 604,390 (54 %) | 166,712 | 226,356 | 121,038 |
| sdk_high | 47,104 | 28,700 (61 %) | 1,674 | 4,664 | 12,066 |

What the remainder is:
- **Defined data in the game band** (226 KB): mostly literal pools (every function has one)
  and pointer tables.
- **Instructions outside functions** (175 KB): code Ghidra disassembled while following
  jumps but did not assign to a function (tail-call targets, interior labels, wordcode
  that happens to decode as SH-4).
- **Script wordcode is interleaved with code in `.text`** (e.g. `0x8C106200–0x8C10631C`), so
  some of the "undefined" or "instructions outside functions" bytes are fight scripts, not
  code. Separating them needs the script-stream map (docs/systems/combat-vm.md).

Not yet done:
- SDK identification (needs a Katana SDK for FID or manual string-xref tagging).
- Interrupt and exception vectors: the SH-4 VBR and handler setup live in the Shinobi startup
  (`sdk_low`) and are not traced yet.
- Classifying the 175 KB of loose instructions (function vs script vs mis-decoded data).
