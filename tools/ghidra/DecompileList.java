// Ghidra headless script: decompiles a list of functions into a .c file.
//
// Reads a text file with one function per line (format: "0xADDR name" or just
// the name) and writes the decompiled C in the given order, which is the
// difficulty order produced by the ranking script.
//
//   analyzeHeadless <proyecto> MH2 -process Manhunt2_nosecu.exe -noanalysis \
//       -scriptPath "E:\MK3 PROJECT\OUTPUT\tools" \
//       -postScript DecompileList.java <list.txt> <out.c>
//
//@category MKG

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.ArrayDataType;
import ghidra.program.model.data.CharDataType;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeConflictHandler;
import ghidra.program.model.data.StructureDataType;
import ghidra.program.model.data.DoubleDataType;
import ghidra.program.model.data.FloatDataType;
import ghidra.program.model.data.IntegerDataType;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.data.ShortDataType;
import ghidra.program.model.data.SignedByteDataType;
import ghidra.program.model.data.UnsignedIntegerDataType;
import ghidra.program.model.data.UnsignedShortDataType;
import ghidra.program.model.data.Undefined4DataType;
import ghidra.program.model.data.VoidDataType;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.ParameterImpl;
import ghidra.program.model.listing.ReturnParameterImpl;
import ghidra.program.model.listing.Variable;
import ghidra.program.model.symbol.SourceType;

public class DecompileList extends GhidraScript {

    /** Structs declared in structs.txt, by name. */
    private final Map<String, DataType> customTypes = new LinkedHashMap<>();

    /** Converts a type name from the signatures file into a DataType. */
    private DataType parseType(String t) {
        t = t.trim();
        // arrays: "char[64]"
        int arrLen = 0;
        int lb = t.indexOf('[');
        if (lb >= 0 && t.endsWith("]")) {
            arrLen = Integer.parseInt(t.substring(lb + 1, t.length() - 1).trim());
            t = t.substring(0, lb).trim();
        }
        int stars = 0;
        while (t.endsWith("*")) {
            stars++;
            t = t.substring(0, t.length() - 1).trim();
        }
        DataType base;
        // structs declarados en structs.txt
        if (customTypes.containsKey(t)) {
            base = customTypes.get(t);
            for (int i = 0; i < stars; i++) {
                base = new PointerDataType(base);
            }
            return arrLen > 0 ? new ArrayDataType(base, arrLen, base.getLength()) : base;
        }
        switch (t) {
            case "void":   base = VoidDataType.dataType; break;
            case "float":  base = FloatDataType.dataType; break;
            case "double": base = DoubleDataType.dataType; break;
            case "int":    base = IntegerDataType.dataType; break;
            case "uint":   base = UnsignedIntegerDataType.dataType; break;
            case "short":  base = ShortDataType.dataType; break;
            case "ushort": base = UnsignedShortDataType.dataType; break;
            case "char":   base = CharDataType.dataType; break;
            case "byte":   base = SignedByteDataType.dataType; break;
            default:       base = Undefined4DataType.dataType; break;
        }
        for (int i = 0; i < stars; i++) {
            base = new PointerDataType(base);
        }
        return arrLen > 0 ? new ArrayDataType(base, arrLen, base.getLength()) : base;
    }

    /**
     * Creates the structs declared in structs.txt and registers them in the program.
     * Done in two passes: first they are created empty (so a struct can refer to
     * one declared later), then the fields are filled in.
     */
    private int applyStructs(String path) throws Exception {
        List<String[]> pending = new ArrayList<>();   // {name, offset, type, field}
        StructureDataType cur = null;

        try (BufferedReader br = new BufferedReader(new FileReader(new File(path)))) {
            String line;
            while ((line = br.readLine()) != null) {
                String raw = line;
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                if (line.startsWith("struct ")) {
                    String[] p = line.split("\\s+");
                    int size = Integer.decode(p[2]);
                    cur = new StructureDataType(p[1], size);
                    customTypes.put(p[1], cur);
                } else if (cur != null && raw.startsWith(" ")) {
                    String[] p = line.split("\\s+");
                    if (p.length >= 3) {
                        pending.add(new String[] { cur.getName(), p[0], p[1], p[2] });
                    }
                }
            }
        }

        // second pass: every struct name is now resolvable
        for (String[] f : pending) {
            StructureDataType s = (StructureDataType) customTypes.get(f[0]);
            int off = Integer.decode(f[1]);
            DataType dt = parseType(f[2]);
            try {
                s.replaceAtOffset(off, dt, dt.getLength(), f[3], null);
            } catch (Exception e) {
                println("  campo rechazado " + f[0] + "." + f[3] + ": " + e.getMessage());
            }
        }

        int n = 0;
        for (Map.Entry<String, DataType> e : customTypes.entrySet()) {
            DataType added = currentProgram.getDataTypeManager()
                    .addDataType(e.getValue(), DataTypeConflictHandler.REPLACE_HANDLER);
            customTypes.put(e.getKey(), added);
            n++;
        }
        return n;
    }

    /**
     * Applies the signatures from the given file. This is the step that turns
     * `undefined4 *param_1` into `float *m`: without it the decompiler does not know
     * the data is floating point and emits unreadable bit manipulation.
     */
    private int applySignatures(String path, Map<String, Function> byName) throws Exception {
        int applied = 0;
        try (BufferedReader br = new BufferedReader(new FileReader(new File(path)))) {
            String line;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                String[] parts = line.split("\\|");
                if (parts.length < 2) {
                    continue;
                }
                String fname = parts[0].trim();
                Function f = byName.get(fname);
                if (f == null) {
                    println("  signature without function: " + fname);
                    continue;
                }
                DataType ret = parseType(parts[1]);
                List<Variable> params = new ArrayList<>();
                if (parts.length > 2 && !parts[2].trim().isEmpty()) {
                    for (String p : parts[2].split(",")) {
                        p = p.trim();
                        if (p.isEmpty()) {
                            continue;
                        }
                        int sp = Math.max(p.lastIndexOf(' '), p.lastIndexOf('*'));
                        String tname = p.substring(0, sp + 1).trim();
                        String pname = p.substring(sp + 1).trim();
                        if (tname.isEmpty()) {
                            tname = p;
                            pname = "arg" + (params.size() + 1);
                        }
                        params.add(new ParameterImpl(pname, parseType(tname), currentProgram));
                    }
                }
                f.updateFunction(null, new ReturnParameterImpl(ret, currentProgram),
                        params,
                        Function.FunctionUpdateType.DYNAMIC_STORAGE_FORMAL_PARAMS,
                        true, SourceType.USER_DEFINED);
                applied++;
            }
        }
        return applied;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: DecompileList <list.txt> <out.c>");
            return;
        }

        // index of functions by name and by address
        Map<String, Function> byName = new LinkedHashMap<>();
        Map<Long, Function> byAddr = new LinkedHashMap<>();
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext()) {
            Function f = it.next();
            byName.put(f.getName(), f);
            byAddr.put(f.getEntryPoint().getOffset(), f);
        }

        List<Function> targets = new ArrayList<>();
        List<String> missing = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(new File(args[0])))) {
            String line;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                String[] parts = line.split("\\s+");
                Function f = null;
                if (parts[0].startsWith("0x")) {
                    long a = Long.parseLong(parts[0].substring(2), 16);
                    f = byAddr.get(a);
                    if (f == null) {
                        // the function may not be defined yet: create it
                        Address addr = currentProgram.getAddressFactory()
                                .getDefaultAddressSpace().getAddress(a);
                        f = createFunction(addr, parts.length > 1 ? parts[1] : null);
                    }
                }
                if (f == null && parts.length > 1) {
                    f = byName.get(parts[1]);
                }
                if (f == null) {
                    f = byName.get(parts[0]);
                }
                if (f != null) {
                    targets.add(f);
                } else {
                    missing.add(line);
                }
            }
        }

        println("requested: " + targets.size() + "  not found: " + missing.size());
        for (String s : missing) {
            println("  NOT FOUND: " + s);
        }

        // Structs go first: signatures may refer to them.
        if (args.length >= 4 && !args[3].isEmpty() && new File(args[3]).exists()) {
            println("structs created: " + applyStructs(args[3]));
        }
        if (args.length >= 3 && !args[2].isEmpty() && new File(args[2]).exists()) {
            println("signatures applied: " + applySignatures(args[2], byName));
        }

        DecompInterface decomp = new DecompInterface();
        // Default options: grabFromToolAndProgram() needs a Tool, which does not
        // exist in headless mode.
        DecompileOptions opts = new DecompileOptions();
        opts.setMaxWidth(100);
        decomp.setOptions(opts);
        decomp.toggleCCode(true);
        decomp.toggleSyntaxTree(true);
        decomp.setSimplificationStyle("decompile");
        decomp.openProgram(currentProgram);

        int ok = 0, fail = 0;
        try (PrintWriter out = new PrintWriter(args[1], "UTF-8")) {
            out.println("/*");
            out.println(" * Decompiled with Ghidra (project-specific header).");
            out.println(" * Generated by OUTPUT/tools/DecompileList.java.");
            out.println(" * Starting point: types and names must be fixed by hand.");
            out.println(" */");
            out.println();
            for (Function f : targets) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults res = decomp.decompileFunction(f, 180, monitor);
                out.println("/* ================================================== */");
                out.println("/* " + f.getName() + "  @ " + f.getEntryPoint()
                        + "   (" + f.getBody().getNumAddresses() + " bytes) */");
                out.println("/* ================================================== */");
                if (res.decompileCompleted() && res.getDecompiledFunction() != null) {
                    out.println(res.getDecompiledFunction().getC());
                    ok++;
                    println("  ok   " + f.getName());
                } else {
                    out.println("/* FAILED: " + res.getErrorMessage() + " */");
                    fail++;
                    println("  FAILED " + f.getName() + ": " + res.getErrorMessage());
                }
                out.println();
            }
        } finally {
            decomp.dispose();
        }
        println("decompiled: " + ok + "   failed: " + fail);
        println("wrote " + args[1]);
    }
}
