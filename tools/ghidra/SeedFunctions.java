// Ghidra headless script: SH-4 function discovery for MK Gold's 1ST_READ.BIN.
//
// Two evidence sources, recorded separately (bookmark category "MKG-seed"):
//   ptr       a 4-aligned dword anywhere in the image holds the address, and the
//             target looks like a function start (see acceptStart)          -> confirmed
//   prologue  32-aligned address in the game-code band, not covered, preceded by
//             rts+delay slot / nop padding / tail jump, not read as data       -> probable
//
// Output: <out_dir>/seeded.tsv  (addr, source, created|existing|failed)
//
//   analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis \
//       -scriptPath tools\ghidra -postScript SeedFunctions.java <out_dir> <game_lo> <game_hi> <code_hi>
//
//@category MKG

import java.io.File;
import java.io.PrintWriter;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;

public class SeedFunctions extends GhidraScript {

    long base = 0x8C010000L, gameLo, gameHi, codeHi;
    Memory mem;

    int hw(long a) throws Exception {
        return mem.getShort(toAddr(a)) & 0xFFFF;
    }

    static boolean isPrologue(int w) {
        if ((w & 0xFF0F) == 0x2F06) return true;              // mov.l Rm,@-r15
        if (w == 0x4F22 || w == 0x4F12 || w == 0x4F02) return true; // sts.l pr/macl/mach,@-r15
        if (w == 0x4F52 || w == 0x4F62) return true;          // sts.l fpul/fpscr,@-r15
        if ((w & 0xFF00) == 0x7F00 && (w & 0x80) != 0) return true; // add #-n,r15
        if ((w & 0xFF0F) == 0xFF0B) return true;              // fmov.s FRm,@-r15
        return false;
    }

    boolean readAsData(Address a) {
        for (Reference r : getReferencesTo(a)) {
            if (r.getReferenceType().isData()) return true;
        }
        return false;
    }

    boolean afterBoundary(long a) throws Exception {
        long p = a - 2;
        int pad = 0;
        while (p > a - 32 && hw(p) == 0x0009) { p -= 2; pad++; }   // nop padding
        int w4 = hw(p - 2);                       // instruction before the delay slot
        if (w4 == 0x000B || w4 == 0x002B) return true;              // rts / rte
        if ((w4 & 0xF0FF) == 0x402B) return true;                   // jmp @Rn (tail call)
        if ((w4 & 0xF000) == 0xA000) return true;                   // bra (tail)
        return pad >= 2;
    }

    boolean tryCreate(Address a, String src, PrintWriter out) {
        if (getFunctionAt(a) != null) { out.println(a + "\t" + src + "\texisting"); return false; }
        if (getInstructionAt(a) == null) {
            if (getDataAt(a) != null && getDataAt(a).isDefined()) {
                out.println(a + "\t" + src + "\tfailed-data"); return false;
            }
            DisassembleCommand dc = new DisassembleCommand(a, null, true);
            if (!dc.applyTo(currentProgram, monitor) || getInstructionAt(a) == null) {
                out.println(a + "\t" + src + "\tfailed-disasm"); return false;
            }
        }
        Function f = createFunction(a, null);
        if (f == null || f.getBody().getNumAddresses() < 4) {
            out.println(a + "\t" + src + "\tfailed-create"); return false;
        }
        createBookmark(a, "MKG-seed", src);
        out.println(a + "\t" + src + "\tcreated");
        return true;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File dir = new File(args[0]);
        dir.mkdirs();
        gameLo = Long.parseLong(args[1], 16);
        gameHi = Long.parseLong(args[2], 16);
        codeHi = Long.parseLong(args[3], 16);
        mem = currentProgram.getMemory();
        long end = base + mem.getBlocks()[0].getSize();
        int nPtr = 0, nPro = 0;
        try (PrintWriter out = new PrintWriter(new File(dir, "seeded.tsv"), "UTF-8")) {
            out.println("addr\tsource\tresult");
            // Pass 1: code pointers stored in memory.
            for (long p = base; p + 4 <= end && !monitor.isCancelled(); p += 4) {
                long v = mem.getInt(toAddr(p)) & 0xFFFFFFFFL;
                if (v < base || v >= codeHi || (v & 1) != 0) continue;
                Address tgt = toAddr(v);
                if (getFunctionAt(tgt) != null) continue;
                Function cont = getFunctionContaining(tgt);
                if (cont != null) continue;            // interior label (jump table / branch)
                boolean game = v >= gameLo && v < gameHi;
                if (game ? (v % 32 != 0) : !isPrologue(hw(v))) continue;
                if (readAsData(tgt)) continue;
                if (tryCreate(tgt, "ptr@" + Long.toHexString(p), out)) nPtr++;
            }
            // Pass 2: 32-aligned starts in the game band.
            for (long a = gameLo; a < gameHi && !monitor.isCancelled(); a += 32) {
                Address at = toAddr(a);
                if (getFunctionContaining(at) != null) continue;
                if (getDataAt(at) != null && getDataAt(at).isDefined()) continue;
                if (readAsData(at)) continue;
                int w = hw(a);
                if (w == 0x0009 || w == 0x0000) continue;
                if (!afterBoundary(a)) continue;
                if (tryCreate(at, "prologue" + (isPrologue(w) ? "+push" : ""), out)) nPro++;
            }
        }
        analyzeChanges(currentProgram);   // follow calls out of the new functions
        println("seeded from pointers: " + nPtr + "   from prologue scan: " + nPro
                + "   functions now: " + currentProgram.getFunctionManager().getFunctionCount());
    }
}
