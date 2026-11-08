// Ghidra headless script: characterise every handler of the fight-script VM opcode table.
//
// For each table slot: ensure a function exists at the handler, then record
//   - operand fetches  : calls to the word fetch (0x8C0E08E0) / float fetch (0x8C0E0940)
//   - continues        : calls/jumps back to the dispatcher (0x8C0DC960)
//   - pause tests      : reads of the pause flag 0x8C2F3074
//   - node fields      : "add #0x40,Rm ; mov.l ..,@(d,Rm)" style accesses -> 0x40+d (and plain @(d,Rm))
//   - pseudo-registers : 0x8C2F30xx/31xx literals read
//   - callees          : every other call target
// and dump each handler's disassembly to <out_dir>/handlers.asm.
//
//   analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis \
//       -scriptPath tools\ghidra -postScript VmHandlers.java <out_dir> <table_hex> <count>
//
//@category MKG

import java.io.File;
import java.io.PrintWriter;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.TreeSet;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;

public class VmHandlers extends GhidraScript {

    static final long FETCH = 0x8C0E08E0L, FETCHF = 0x8C0E0940L, DISPATCH = 0x8C0DC960L, PAUSE = 0x8C2F3074L;

    long u32(Address a) throws Exception {
        return currentProgram.getMemory().getInt(a) & 0xFFFFFFFFL;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File dir = new File(args[0]);
        dir.mkdirs();
        long table = Long.parseLong(args[1], 16);
        int count = Integer.parseInt(args[2]);
        try (PrintWriter tsv = new PrintWriter(new File(dir, "handlers.tsv"), "UTF-8");
             PrintWriter asm = new PrintWriter(new File(dir, "handlers.asm"), "UTF-8")) {
            tsv.println("op\thandler\tbytes\tfetch\tfetchf\tcontinues\tpause_tests\tnode_fields\tpregs\tcallees");
            for (int op = 0; op < count; op++) {
                long h = u32(toAddr(table + 4L * op));
                if (h == 0) { tsv.println(String.format("%02x\t0\t\t\t\t\t\t\t\t", op)); continue; }
                Address ha = toAddr(h);
                if (getInstructionAt(ha) == null) new DisassembleCommand(ha, null, true).applyTo(currentProgram, monitor);
                Function f = getFunctionAt(ha);
                if (f == null) f = createFunction(ha, null);
                if (f == null) { tsv.println(String.format("%02x\t%08x\tFAILED", op, h)); continue; }
                int fetch = 0, fetchf = 0, cont = 0, pause = 0;
                Set<String> fields = new TreeSet<>(), pregs = new TreeSet<>(), callees = new LinkedHashSet<>();
                asm.println(String.format("\n==== op %02x  handler %08x  (%d bytes)", op, h, f.getBody().getNumAddresses()));
                InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
                Instruction prev = null;
                while (it.hasNext()) {
                    Instruction in = it.next();
                    StringBuilder line = new StringBuilder(in.getAddress() + "  " + in);
                    for (Reference r : in.getReferencesFrom()) {
                        if (r.getReferenceType().isCall() || r.getReferenceType().isJump()) {
                            // count real call sites (a pool value loaded once can be called twice)
                            long t = r.getToAddress().getOffset();
                            if (t == FETCH) fetch++;
                            else if (t == FETCHF) fetchf++;
                            else if (t == DISPATCH) cont++;
                        }
                        if (r.getReferenceType().isData()) {
                            try {
                                long v = u32(r.getToAddress());
                                if (v == FETCH || v == FETCHF || v == DISPATCH) { }
                                else if (v == PAUSE) pause++;
                                else if (v >= 0x8C2F3000L && v < 0x8C2F3200L) pregs.add(Long.toHexString(v).substring(4));
                                else if (v >= 0x8C010000L && v < 0x8C17A000L && getFunctionAt(toAddr(v)) != null)
                                    callees.add(Long.toHexString(v));
                                line.append("   ; =0x").append(Long.toHexString(v));
                            } catch (Exception e) { }
                        }
                    }
                    String m = in.getMnemonicString();
                    String s = in.toString();
                    // node-field access: displacement form @(0xNN,rM), with "add #0x40,rM" just before
                    int at = s.indexOf("@(0x");
                    if (at >= 0 && (m.startsWith("mov.l") || m.startsWith("fmov"))) {
                        try {
                            int disp = Integer.parseInt(s.substring(at + 4, s.indexOf(',', at)), 16);
                            boolean plus40 = prev != null && prev.toString().startsWith("add 0x40")
                                    || (prev != null && prev.toString().contains("#0x40"));
                            fields.add(Integer.toHexString(disp + (plus40 ? 0x40 : 0)) + (plus40 ? "" : "?"));
                        } catch (Exception e) { }
                    }
                    asm.println(line);
                    prev = in;
                }
                tsv.println(String.format("%02x\t%08x\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%s", op, h,
                        f.getBody().getNumAddresses(), fetch, fetchf, cont, pause,
                        String.join(",", fields), String.join(",", pregs), String.join(",", callees)));
            }
        }
        println("done");
    }
}
