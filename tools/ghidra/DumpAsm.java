// Ghidra headless script: dump disassembly (with resolved PC-relative constants and
// callers) for address ranges, plus decompiled C for each function touched.
//
//   analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis -readOnly \
//       -scriptPath tools\ghidra -postScript DumpAsm.java <out.txt> <start:end> [<start:end> ...]
//
//@category MKG

import java.io.File;
import java.io.PrintWriter;
import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;

public class DumpAsm extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Set<Function> funcs = new LinkedHashSet<>();
        try (PrintWriter out = new PrintWriter(new File(args[0]), "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                String[] r = args[i].split(":");
                Address a = toAddr(Long.parseLong(r[0], 16));
                Address e = toAddr(Long.parseLong(r[1], 16));
                out.println("==== " + r[0] + " .. " + r[1]);
                while (a.compareTo(e) < 0) {
                    Function f = getFunctionAt(a);
                    if (f != null) {
                        funcs.add(f);
                        StringBuilder cs = new StringBuilder();
                        for (Function c : f.getCallingFunctions(monitor)) cs.append(c.getEntryPoint()).append(' ');
                        StringBuilder rs = new StringBuilder();
                        for (Reference ref : getReferencesTo(a)) rs.append(ref.getFromAddress()).append(' ');
                        out.println("\n---- FUNCTION " + a + "  callers: " + cs + " refs: " + rs);
                    }
                    CodeUnit cu = currentProgram.getListing().getCodeUnitAt(a);
                    if (cu == null) { a = a.add(2); continue; }
                    StringBuilder sb = new StringBuilder();
                    sb.append(a).append("  ").append(cu.toString());
                    if (cu instanceof Instruction) {
                        for (Reference ref : cu.getReferencesFrom()) {
                            sb.append("   ; -> ").append(ref.getToAddress());
                            if (ref.getReferenceType().isData()) {
                                try {
                                    long v = currentProgram.getMemory().getInt(ref.getToAddress()) & 0xFFFFFFFFL;
                                    sb.append(" = 0x").append(Long.toHexString(v));
                                    Function tf = getFunctionAt(toAddr(v));
                                    if (tf != null) sb.append(" <").append(tf.getName()).append(">");
                                } catch (Exception ex) { }
                            }
                        }
                    }
                    out.println(sb);
                    a = a.add(cu.getLength());
                }
            }
            DecompInterface di = new DecompInterface();
            di.openProgram(currentProgram);
            for (Function f : funcs) {
                DecompileResults res = di.decompileFunction(f, 60, monitor);
                out.println("\n/* ===== " + f.getEntryPoint() + " " + f.getName() + " ===== */");
                out.println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "/* decompile failed */");
            }
        }
    }
}
