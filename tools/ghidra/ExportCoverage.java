// Ghidra headless script: function inventory with evidence source + byte coverage.
//
//   functions.tsv : addr, bytes, source (flow | ptr | prologue | prologue+push), callers, callees, name
//   coverage.tsv  : per band, bytes in function bodies / instructions outside functions /
//                   defined data / undefined
//
//   analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis -readOnly \
//       -scriptPath tools\ghidra -postScript ExportCoverage.java <out_dir>
//
//@category MKG

import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Bookmark;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;

public class ExportCoverage extends GhidraScript {

    @Override
    public void run() throws Exception {
        File dir = new File(getScriptArgs()[0]);
        dir.mkdirs();
        try (PrintWriter out = new PrintWriter(new File(dir, "functions.tsv"), "UTF-8")) {
            out.println("addr\tbytes\tsource\tcallers\tcallees\tname");
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext() && !monitor.isCancelled()) {
                Function f = it.next();
                String src = "flow";
                for (Bookmark b : currentProgram.getBookmarkManager().getBookmarks(f.getEntryPoint())) {
                    if (b.getCategory().equals("MKG-seed")) {
                        src = b.getComment().startsWith("ptr") ? "ptr" : b.getComment();
                    }
                }
                out.println(f.getEntryPoint() + "\t" + f.getBody().getNumAddresses() + "\t" + src + "\t"
                        + f.getCallingFunctions(monitor).size() + "\t"
                        + f.getCalledFunctions(monitor).size() + "\t" + f.getName());
            }
        }
        long[][] bands = {
            {0x8C010000L, 0x8C05D6E0L}, {0x8C05D6E0L, 0x8C16E800L}, {0x8C16E800L, 0x8C17A000L}};
        String[] names = {"sdk_low", "game", "sdk_high"};
        try (PrintWriter out = new PrintWriter(new File(dir, "coverage.tsv"), "UTF-8")) {
            out.println("band\tstart\tend\tin_functions\tinsn_outside_functions\tdefined_data\tundefined");
            for (int i = 0; i < bands.length; i++) {
                long inF = 0, insOut = 0, data = 0, undef = 0;
                Address a = toAddr(bands[i][0]);
                Address e = toAddr(bands[i][1]);
                while (a.compareTo(e) < 0 && !monitor.isCancelled()) {
                    CodeUnit cu = currentProgram.getListing().getCodeUnitAt(a);
                    long len = cu == null ? 1 : cu.getLength();
                    if (cu instanceof Instruction) {
                        if (getFunctionContaining(a) != null) inF += len; else insOut += len;
                    } else if (cu instanceof Data && ((Data) cu).isDefined()) {
                        data += len;
                    } else {
                        undef += len;
                    }
                    a = a.add(len);
                }
                out.println(names[i] + "\t" + Long.toHexString(bands[i][0]) + "\t" + Long.toHexString(bands[i][1])
                        + "\t" + inF + "\t" + insOut + "\t" + data + "\t" + undef);
            }
        }
        println("exported");
    }
}
