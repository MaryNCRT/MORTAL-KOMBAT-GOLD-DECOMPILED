# External references (pinned, read-only)

Cloned shallow into `REFERENCE/` (not versioned). Never edited, never vendored into
the port. Update a pin only deliberately, and record the new commit here.

| Repo | Pinned commit | Date | License | Role in this project |
|---|---|---|---|---|
| [nathan-casabieille/mk4decomp](https://github.com/nathan-casabieille/mk4decomp) | `af8800788f704be1e3c85a0e3cbf5688f112c426` | 2026-09-16 | MIT (author contributions; game rights excluded) | **Permanent technical reference** for engine architecture, combat FSM, scenegraph, animation and script VM semantics. See [mk4-to-mkg.md](../cross-reference/mk4-to-mkg.md). |
| [corepunch/open-mk4](https://github.com/corepunch/open-mk4) | `85a515a9016204231e0c7f38f78c8dd95cf15d2d` | 2026-11-01 | **No LICENSE file** (all rights reserved by default) | Reference only: script-VM research notes and opcode taxonomy. No code reuse. |
| [alexbeavs-ps1-ports/mortal-kombat-4-recomp](https://github.com/alexbeavs-ps1-ports/mortal-kombat-4-recomp) | `e1892e2a9034cb5753081ae0a0c2596d76cedac4` | 2026-09-30 | GPL-3.0 | PS1 static recomp built on psxrecomp. Example of the recomp approach; not used for Gold data. |
| [ermaccer/MortalKombat.Tools](https://github.com/ermaccer/MortalKombat.Tools) | `35980deb85ccc924225dc80aed5ef2d2c6939813` | 2021-06-20 | none stated | Gold IMG/GEO tools (img2bmp, bmp2img, mkggeotool), cross-checked against our decode. |
| [sp00nznet/dcrecomp](https://github.com/sp00nznet/dcrecomp) | `3c60e6f03cbbaaabeaa1f3165247ed3120f23c3e` | 2026-10-20 | **GPL-2.0** | SH-4 → C recomp evaluation and PowerVR TA / AICA behaviour reference. Do not link or copy. |
| [AltoRetrato/Dreamcast-Disassembly-Debugging-and-Decompilation-Diaries](https://github.com/AltoRetrato/Dreamcast-Disassembly-Debugging-and-Decompilation-Diaries) | `fc101701cdf439ea82da1aab2acb8a3a61b0a1d4` | 2026-02-13 | no LICENSE file | Ghidra FIDB from Katana SDK (`build_dc_fidb.py`), Flycast GDB workflow. |

Article: *Unreleased Mortal Kombat 4 Dreamcast — reverse engineering* (VincentNL, ermaccer),
sega-dreamcast-info.com. Describes the **MK4 DC prototype** (not Gold).

Not cloned yet: flycast (local 2.2.0 release in use), ImHex (not installed),
dc-re-ghidra, gditools3 (own extractor in use), Dreamcast docs (Kochise/dreamcast-docs).

## Tools tested in Phase 1

| Tool | Version | Result |
|---|---|---|
| REA (`E:ea-rea-agents-6.3.0`, `node scripts/rea.mjs`) | 6.3.0 | Rejects `1ST_READ.elf` with "unsupported ELF architecture". The Windows Ghidra provider admits x86/x86-64 PE only. Kept for the native port binaries. |
| Flycast (`Dreamcast/flycast.exe`) | 2.2.0 release | No GDB RSP stub compiled in (tested; see dynamic-analysis.md). |
| Ghidra P-code emulator (`EmulatorHelper`) | 12.1.2 | Works for SH-4 incl. FPU; used as the oracle. |
| open-mk4 opcode taxonomy | `85a515a` | Used as **reference labels** only (`mk4:<name>`); Gold operand rules come from Gold handlers. |
