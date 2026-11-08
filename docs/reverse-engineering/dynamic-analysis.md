# Dynamic analysis: capabilities tested (Phase 1)

Every line says whether it was **tested**, and how. Nothing here is assumed from documentation alone.

## Summary

| Capability | Status | Evidence |
|---|---|---|
| Ghidra P-code emulation of original SH-4 functions | **Works** | `tools/ghidra/EmuOracle.java`: 200 + 200 + 1,000 trials completed at the return address, including FPU code. |
| Oracle vectors replayed against reconstructed C | **Works** | `tests/test_oracle.py` (gcc 16.1, `-ffp-contract=off`). 3 functions, 0 mismatches. Negative control (swapped vectors) fails as expected. |
| Flycast 2.2.0 GDB server | **Not available** | The release binary has no RSP stub (no `qSupported`/`PacketSize`/`$T05`/`qXfer` strings). With `Debug.GDBEnabled=yes` in an isolated copy, nothing listens on 3263. |
| REA 6.3.0 on the SH-4 ELF | **Rejected by REA** | `rea analyze ... --provider ghidra` → `target_unavailable: unsupported ELF architecture`. |
| Memory / register snapshots from a running game | **Not yet** | Needs a GDB-enabled Flycast build or save-state parsing (below). |

## 1. Ghidra P-code oracle (primary verification path)

```
tests/oracle/specs/<func>.spec   ->  tools/ghidra/oracle.ps1 <func> [trials] [seed]
                                 ->  tests/oracle/vectors/<func>.tsv   (versioned)
decomp/**/*.c + tests/oracle/run_vectors.c  ->  python -I -m unittest tests.test_oracle
```

- The script runs the **original** function in Ghidra's emulator, with `PR` set to a magic return
  address and a breakpoint on it. Inputs are randomized per spec: packed pointers, chained node
  links, random fields, random globals, and constants copied from the image (`keep`). It records
  every input write and the requested outputs.
- Replay needs no Ghidra: the C harness models RAM as 16 MiB at `0x8C000000` (`decomp/include/mkg_mem.h`),
  applies the writes, calls the reconstruction and compares.
- Determinism: fixed seeds are recorded in the TSV header.
- Limits:
  - Functions that touch hardware registers (PVR, AICA, GD-ROM, Maple) cannot run unmodified.
  - Functions that call other functions run those callees too. This is fine for pure engine code;
    for anything that reaches SDK code it needs stubs.
  - `EmulatorHelper` is deprecated in Ghidra 12 (it still works). The newer `PcodeEmulator` API is the
    migration path.
- Reproduce: `powershell -File tools\ghidra\oracle.ps1 8c0692a0 1000 3`.

## 2. Flycast

- Installed: Flycast 2.2.0 (mingw x86_64 release) in `Dreamcast/`. It is not modified. The test used an
  isolated copy, `OUTPUT/flycast-gdb/` (own `emu.cfg` with `GDBEnabled = yes`, `GDBWaitForConnection = yes`).
- Result: the game window starts, but no TCP listener belongs to the process and port 3263 refuses
  connections. A byte search of the binary finds none of the RSP protocol strings, so the stub is
  compiled out of this release (`ENABLE_GDB_SERVER` off).
- Client ready: `tools/gdbrsp.py` (minimal RSP client: `?`, `g`, `m`, `qSupported`, RAM dump).
  It needs no gdb binary (the local gdb is x86-only).
- To enable: build Flycast from source with `-DENABLE_GDB_SERVER=ON`. This is documented by AltoRetrato
  (MSYS2, Ninja). He also reports the stub as incomplete (e.g. `until` missing), so only use
  `m`/`g`/`Z0`/`c`. **This is a user decision**, since it means installing a toolchain and building a
  third-party program.
- Alternative without GDB [not tested]: Flycast save states contain main RAM. Parsing that format gives
  frame snapshots for state comparison, with no breakpoints.

## 3. REA

- REA 6.3.0 (local checkout, `node scripts/rea.mjs`) with `GHIDRA_INSTALL_DIR` set to Ghidra 12.1.2.
- The SH-4 ELF is refused at admission: `unsupported ELF architecture`. The Windows Ghidra provider admits
  only x86/x86-64 PE ("P0" scope in REA's docs).
- Where REA still fits: analysing and comparing **our native port binaries** (x86-64 PE) later, and
  value-tracing and evidence bundles on them. SH-4 analysis stays in Ghidra with our own scripts.

## 4. SH-4 debugging needs, mapped to tools

| Need | Tool now | Later |
|---|---|---|
| Run one function with inputs | P-code oracle | — |
| Breakpoints / single step in the real game | — | GDB-enabled Flycast build |
| Memory snapshot at a frame | — | GDB `m` dump via `tools/gdbrsp.py`, or save-state parsing |
| Register snapshot | P-code (per function) | GDB `g` |
| State comparison (original vs port) | per-function vectors | frame snapshots → diff tool |
