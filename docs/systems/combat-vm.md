# Combat (fight-script) virtual machine

Tags: **[V]** verified (oracle test, or exhaustive check over the binary) · **[R]** read in the SH-4
code by hand · **[O]** observed · **[H]** hypothesis.
Opcode database: [vm-opcodes.tsv](vm-opcodes.tsv). Disassembler: `tools/mkg_vm.py`.

## Summary

Gold runs the **same fight-script VM as MK4 PC**: a wordcode interpreter whose program counter
lives in a node field and whose state is a block of pseudo-registers in RAM. The opcode
**numbering is MK4's** (Phase 0 claimed otherwise; that claim was wrong, see "Corrections").
Gold extends the table to 120 slots and widens the roster-select table from 16 to 24 entries.

## Machine model [R]

| Element | Gold address | Notes |
|---|---|---|
| Pseudo-registers | `0x8C2F3100–0x8C2F3150` | 21 dwords. Named by address (`R3120` …) until roles are proven. |
| Pause flag | `0x8C2F3074` | Tested after almost every call (3,078 literal refs). Non-zero stops the current chain for this frame. |
| Pseudo-stack pointer | `0x8C2F30CC` | Holds a word index. Push: `sp++; *(sp*4) = R3128`. Pop restores. |
| Current node | `R3120` (packed) | The actor/task node the VM is running for. |
| Script PC | `node[+0x48]` (packed word index) | Same offset as MK4 PC (`baseSel[+0x48]`). |
| Wait flag | `node[+0x84]` | Wait opcodes set it to 1 and install themselves as the node callback `node[+0x08]`. MK4: same offsets. |
| Condition flags | `R3128` | Bit 0 and bit 2 select branch-taken. Predicates write them. |
| Packed pointer | `p = (a & 0xFFFFFF) >> 2`, `a = ((p & 0xFFFFFF) << 2) \| 0x8C000000` | Verified in reconstructed code (oracle). |

Functional correspondences with MK4 PC, established by matching a whole function
(`VM_FetchWord` ≡ `ScaledIterStep_0045c020`, instruction for instruction):
`R3120 ≈ g_baseSel (0x542060)`, `R3110 ≈ g_eventQueueTotal (0x542050)`, `R3130 ≈ g_walkCallback (0x54206C)`.
The register block is **not** a uniform shift of MK4's layout, so other registers must be matched
one by one.

## Entry, dispatch, fetch [R]

| Function | Address | Behaviour |
|---|---|---|
| `VM_RunScriptAt` | `0x8C0DC920` | `R3110 = node[+0x48] = r4 >> 2` (byte address → word index), then dispatch. Called from about 400 sites, each passing a **script byte address** in `r4`. |
| `VM_Dispatch` | `0x8C0DC960` | Push R3128. `fetch`. Return if paused. `R3134 = word`, `R3130 = word >> 24`, handler = `*(0x8C322268 + 4*op)`. Pop R3128. `jsr handler`. |
| `VM_FetchWord` | `0x8C0E08E0` | `pc = node[+0x48]; R3110 = pc; R3130 = *unpack(pc); node[+0x48] = R3110 = pc + 1`. |
| `VM_FetchFloat` | `0x8C0E0940` | Same, moved through the FPU (`fmov.s`). |
| `VM_OptionalClipOperand` | `0x8C0E0860` | `R3130 = (word >> 8) & 0xFF`. If it is 2, fetch one word into `node(R311C)[+0x24]` (the clip/animation slot). |
| `VM_SplitInline12_12` | `0x8C0E09A0` | `R3130 = word & 0xFFF` (low 12 bits), `R3134 = (word >> 12) & 0xFFF`. |

Handlers either chain back into `VM_Dispatch` (continue), or install themselves and pause (wait),
or end the stream. A wait resumes at the next word on a later frame.

## Opcode table [V]

`0x8C322268`, 120 slots (`0x00–0x77`), slot `0x31` = NULL. Nine slots point at the dispatcher itself
(nop): `00 0B 15 18 21 23 57 66 67`.

**MK4 numbering agreement:** the nine nop slots and the null `0x31` are exactly the `nop*` and
`invalid` entries of the MK4 PC opcode list (open-mk4 taxonomy, 119 names). Independently, the
operand count per opcode, derived from Gold's own handler code, equals MK4's count for
**118 of 120 slots**. The two exceptions:

- `0x08`: Gold takes its clip operand only when the inline low byte is 0 (MK4 lists 1).
- `0x3C`: the inline select table has 24 entries in Gold, 16 in MK4.

mk4decomp's "49-entry table" is the part before the `0x31` hole.

MK4 names appear only as **reference labels** (`mk4:<name>`) in disassembler output. They are read at
run time from a local open-mk4 checkout (`REFERENCE/open-mk4`), because that repo has no licence; they
are **not stored** in this repo or in `vm-opcodes.tsv`. They are not Gold names until each handler's
behaviour is read.

## Instruction encoding [R]/[V]

```
31      24 23                                0
+--------+-----------------------------------+
| opcode |   inline field (24 bits)          |   + N operand words
+--------+-----------------------------------+
```

Operand rules, each established in the Gold handler:

| Rule | Opcodes | Source |
|---|---|---|
| Fixed N words = number of `jsr` to the word/float fetch | 37 opcodes (see TSV) | VmHandlers.java (call sites, not pool loads) |
| `+1` word iff `(w >> 8) & 0xFF == 2` (clip → node(R311C)+0x24) | 46, 47, 48, 49, 68 | 0x8C0E0860 |
| `+1` word iff `(w & 0xFF) == 0` | 08 | handler 0x8C0DD5C0 |
| 4 words read through `pc`, then `pc += 4` | 59 | handler 0x8C0DEFA0 |
| native fn + branch target | 43, 36 | handlers |
| 24 packed targets, `pc = table[node[+0x34]]` | 3C | handler 0x8C0DF8A0 + measured on all 14 uses |

Operand kinds:
- **packed pointer to an animation descriptor** (clip). Opcodes 01 02 09 0C 0E 0F 11 46 47 48 49 68 71 carry
  them (604 uses in decoded streams).
- **packed jump target** (33; last operand of branches 2F 36 3D 42 43 44 45 6F; all 24 of 3C).
- **native code address** = `operand & 0xFFFFFF | 0x8C000000` (32 tail, 35 call, 36/43/55 first operand).
- **float** (58 5A 5C 5D 5F 63 65 6C 6D 70).
- plain words (counts, ids).

## Control flow [R]

| Flow | Opcodes | Behaviour |
|---|---|---|
| end | 30, 31, 32, 3E, 3F | `30` calls `0x8C088300` (return to continuation); `32` tail-calls a native; `3E` parks (re-installs itself every frame, never advances pc); `3F` sets `node[+0x74]=0x200B`, runs natives, ends in `0x8C101780`. |
| jump | 33 | `pc = operand`. |
| select | 3C | `pc = mem[pc + node[+0x34]]`, 24-entry inline table. `+0x34` is a per-node index (the roster slot in MK4 [H]). |
| branch | 2F 36 3D 42 43 44 45 6F | Evaluate a predicate (native or flags in R3128/R314C). If taken, `pc = last operand`. Otherwise skip it. |
| wait | e.g. 01–09, 10, 17, 34, 46–48, 4A–4D, 54, 68–6A, 71 | Install the handler as node callback, set `node[+0x84]=1`, set the pause flag, resume later at the next word. |
| next | the rest | Do work, re-dispatch. |

Loop markers (MK4: `0x3A` marker / `0x3B` repeat) are present in Gold streams (`3A000002 … 3B000000`).
Their counter location is not read yet.

## Script streams [V]

- Seeds: the `r4` literal loaded before each `jsr` to `0x8C0DC920` (`mkg_vm.entry_seeds`), giving
  **623 entries**, all in the data area `0x8C2D0000–0x8C33B954`.
- Closure over jump/branch/select targets: **739 streams**, 4,190 decoded instructions at **3,978 distinct addresses** (streams share tails).
- **738 / 739 streams decode cleanly** to an end/jump/select (`python -I tools/mkg_vm.py scan`).
  The one failure starts on data: its seed is an `r4` value for a different call.
- Cross-check: 31 addresses are both an instruction start and an operand of another stream. All are
  words of 0x3C select tables also reached as nop-decoded starts from one seed (documented, not a
  count error).
- Opcodes observed in streams: 97 of the 110 non-nop opcodes. Never seen statically:
  `0A 13 17 1A 1B 1C 43 50 54 5D 6F 70 72` (they may be reached only from native-built streams).

**Correction to Phase 0:** the words around `0x8C106300` (`12000055 4F00001F <anim ptr> …`) are **not**
a script stream: `0x4F` takes no operand in Gold. They are a data table with an unknown role.

## What is NOT known yet
- Semantics of most handlers beyond operand use and flow (what each native does to the node).
- Exact meaning of R3128 bits, R314C, and the node fields the handlers touch (+0x24, +0x28, +0x34, +0x38, +0x44, +0x48, +0x4C, +0x5C, +0x68, +0x74, +0x78, +0x7C, +0x84; full list in the TSV).
- How native code builds or patches streams (12 opcodes never seen in static streams).
- Character identity of each stream (map seeds → callers → character tables).
- **Nothing in this VM is oracle-verified yet** except the small node accessors. Next step: emulate
  `VM_FetchWord` and a short stream end-to-end in the P-code oracle (docs/reverse-engineering/dynamic-analysis.md).
