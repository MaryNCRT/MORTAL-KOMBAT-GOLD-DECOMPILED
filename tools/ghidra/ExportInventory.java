// Ghidra headless script: dumps the inventory of the analyzed program.
//
//   functions.tsv : addr, name, bytes, n_callers, n_callees, signature
//   strings.tsv   : addr, n_xrefs, functions referencing it, text
//
//   analyzeHeadless OUTPUTghidra MKG -process 1ST_READ.elf -noanalysis \
//       -scriptPath OUTPUT\tools -postScript ExportInventory.java <out_dir>
//
//@category MKG

import java.io.File;
import java.io.PrintWriter;
import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;

public class ExportInventory extends GhidraScript {

    private static String clean(String s) {
        return s.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ');
    }

    @Override
    public void run() throws Exception {
        File dir = new File(getScriptArgs()[0]);
        dir.mkdirs();

        int nf = 0;
        try (PrintWriter out = new PrintWriter(new File(dir, "functions.tsv"), "UTF-8")) {
            out.println("addr\tname\tbytes\tcallers\tcallees\tsignature");
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                out.println(f.getEntryPoint() + "\t" + f.getName() + "\t"
                        + f.getBody().getNumAddresses() + "\t"
                        + f.getCallingFunctions(monitor).size() + "\t"
                        + f.getCalledFunctions(monitor).size() + "\t"
                        + clean(f.getPrototypeString(false, false)));
                nf++;
            }
        }

        int ns = 0;
        try (PrintWriter out = new PrintWriter(new File(dir, "strings.tsv"), "UTF-8")) {
            out.println("addr\txrefs\tfunctions\ttext");
            DataIterator di = currentProgram.getListing().getDefinedData(true);
            while (di.hasNext() && !monitor.isCancelled()) {
                Data d = di.next();
                if (!d.hasStringValue()) {
                    continue;
                }
                Set<String> fns = new LinkedHashSet<>();
                int n = 0;
                for (Reference r : getReferencesTo(d.getAddress())) {
                    n++;
                    Function f = getFunctionContaining(r.getFromAddress());
                    if (f != null) {
                        fns.add(f.getEntryPoint().toString());
                    }
                }
                out.println(d.getAddress() + "\t" + n + "\t" + String.join(",", fns) + "\t"
                        + clean(String.valueOf(d.getValue())));
                ns++;
            }
        }
        println("functions: " + nf + "   strings: " + ns);
    }
}
