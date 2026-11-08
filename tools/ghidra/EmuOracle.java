// Ghidra headless script: run an ORIGINAL SH-4 function under Ghidra's P-code emulator
// with randomized memory inputs and record input/output vectors (the oracle).
//
// Spec file (one directive per line, hex numbers without 0x):
//   func   <addr>                         function to run
//   packed <global> <region_lo> <span>    global := packed pointer ((a & 0xFFFFFF) >> 2) to a random
//                                         4-aligned address in [region_lo, region_lo+span)
//   chain  <global> <off> <region_lo> <span>
//                                         node = unpack(*global); *(node+off) := packed random address
//   rand   <global> <off>                 node = unpack(*global); *(node+off) := random u32
//          (global may be written as "*<global>+<off2>" to start from a second-level node)
//   u32    <global>                       global := random u32
//   keep   <addr>                         record the image's own value at addr as an input (constants)
//   out    <addr>                         record this u32 after the call
//   outp   <global> <off>                 record u32 at unpack(*global)+off after the call
//
// Output TSV: one line per trial: "w addr=val,... | r addr=val,..."
//
//   analyzeHeadless OUTPUT\ghidra MKG -process 1ST_READ.elf -noanalysis -readOnly \
//       -scriptPath tools\ghidra -postScript EmuOracle.java <spec> <out.tsv> <trials> <seed>
//
//@category MKG

import java.io.File;
import java.io.PrintWriter;
import java.math.BigInteger;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class EmuOracle extends GhidraScript {

    static final long RET = 0x8C00FFF0L;      // magic return address (outside the image)
    static final long STACK = 0x8CFF0000L;

    EmulatorHelper emu;

    long rd(long a) throws Exception {
        byte[] b = emu.readMemory(toAddr(a), 4);
        return (b[0] & 0xFFL) | (b[1] & 0xFFL) << 8 | (b[2] & 0xFFL) << 16 | (b[3] & 0xFFL) << 24;
    }

    void wr(long a, long v, Map<Long, Long> log) throws Exception {
        byte[] b = {(byte) v, (byte) (v >> 8), (byte) (v >> 16), (byte) (v >> 24)};
        emu.writeMemory(toAddr(a), b);
        log.put(a, v & 0xFFFFFFFFL);
    }

    static long unpack(long p) { return ((p & 0xFFFFFFL) << 2) | 0x8C000000L; }
    static long pack(long a) { return (a & 0xFFFFFFL) >> 2; }

    long node(String g) throws Exception {
        if (g.startsWith("*")) {
            String[] p = g.substring(1).split("\\+");
            return unpack(rd(unpack(rd(Long.parseLong(p[0], 16))) + Long.parseLong(p[1], 16)));
        }
        return unpack(rd(Long.parseLong(g, 16)));
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        List<String[]> spec = new ArrayList<>();
        for (String l : Files.readAllLines(new File(args[0]).toPath())) {
            l = l.trim();
            if (!l.isEmpty() && !l.startsWith("#")) spec.add(l.split("\\s+"));
        }
        int trials = Integer.parseInt(args[2]);
        Random rnd = new Random(Long.parseLong(args[3]));
        long func = 0;
        List<Long> outs = new ArrayList<>();
        for (String[] s : spec) {
            if (s[0].equals("func")) func = Long.parseLong(s[1], 16);
            if (s[0].equals("out")) outs.add(Long.parseLong(s[1], 16));
        }
        int okRuns = 0;
        try (PrintWriter out = new PrintWriter(new File(args[1]), "UTF-8")) {
            out.println("# oracle for " + Long.toHexString(func) + " trials=" + trials + " seed=" + args[3]);
            for (int t = 0; t < trials; t++) {
                emu = new EmulatorHelper(currentProgram);
                Map<Long, Long> w = new LinkedHashMap<>();
                for (String[] s : spec) {
                    switch (s[0]) {
                        case "packed": {
                            long lo = Long.parseLong(s[2], 16), span = Long.parseLong(s[3], 16);
                            wr(Long.parseLong(s[1], 16), pack(lo + (rnd.nextInt((int) (span / 4)) * 4L)), w);
                            break;
                        }
                        case "chain": {
                            long n = node(s[1]);
                            long lo = Long.parseLong(s[3], 16), span = Long.parseLong(s[4], 16);
                            wr(n + Long.parseLong(s[2], 16), pack(lo + (rnd.nextInt((int) (span / 4)) * 4L)), w);
                            break;
                        }
                        case "rand": {
                            long n = node(s[1]);
                            wr(n + Long.parseLong(s[2], 16), rnd.nextInt() & 0xFFFFFFFFL, w);
                            break;
                        }
                        case "u32":
                            wr(Long.parseLong(s[1], 16), rnd.nextInt() & 0xFFFFFFFFL, w);
                            break;
                        case "keep": {
                            long a = Long.parseLong(s[1], 16);
                            wr(a, rd(a), w);
                            break;
                        }
                        default:
                    }
                }
                emu.writeRegister("r15", BigInteger.valueOf(STACK));
                emu.writeRegister("pr", BigInteger.valueOf(RET));
                emu.writeRegister("pc", BigInteger.valueOf(func));
                Address stop = toAddr(RET);
                emu.setBreakpoint(stop);
                emu.run(monitor);   // stops at the breakpoint on the magic return address
                long pc = emu.readRegister("pc").longValue();
                StringBuilder sb = new StringBuilder("w ");
                for (Map.Entry<Long, Long> e : w.entrySet())
                    sb.append(Long.toHexString(e.getKey())).append('=').append(Long.toHexString(e.getValue())).append(',');
                sb.append(" | r ");
                for (long o : outs) sb.append(Long.toHexString(o)).append('=').append(Long.toHexString(rd(o))).append(',');
                for (String[] s : spec) {
                    if (s[0].equals("outp")) {
                        long o = unpack(rd(Long.parseLong(s[1], 16))) + Long.parseLong(s[2], 16);
                        sb.append(Long.toHexString(o)).append('=').append(Long.toHexString(rd(o))).append(',');
                    }
                }
                if (pc != RET) {
                    sb.append(" | FAULT pc=").append(Long.toHexString(pc)).append(' ').append(emu.getLastError());
                } else okRuns++;
                out.println(sb);
                emu.dispose();
            }
        }
        println("oracle runs completed at return address: " + okRuns + "/" + trials);
    }
}
