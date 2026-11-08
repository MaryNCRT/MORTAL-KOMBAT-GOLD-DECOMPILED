"""MK Gold fight-script VM: opcode database + standalone disassembler.

Everything here was derived from the Gold SH-4 code (docs/systems/combat-vm.md):
  dispatcher 0x8C0DC960, opcode = word >> 24, handler = table[0x8C322268 + 4*op] (120 slots),
  fetch 0x8C0E08E0 (word at unpack(pc); pc++), float fetch 0x8C0E0940,
  script PC = packed word index at node+0x48, packed = (addr & 0xFFFFFF) >> 2.
MK4 PC names (open-mk4 taxonomy) are REFERENCE LABELS ONLY, shown as "mk4:<name>";
numbering agreement is evidenced (all 9 nop slots + the 0x31 hole match), semantics are not
assumed beyond what the Gold handler shows.

Usage:
    python -I tools/mkg_vm.py ops [--tsv]                       # opcode database
    python -I tools/mkg_vm.py dis <1ST_READ.BIN> <addr> [max]   # disassemble one script stream
    python -I tools/mkg_vm.py scan <1ST_READ.BIN> [out.tsv]     # find + decode all script streams
"""
import struct
import sys

LOAD = 0x8C010000
TABLE = 0x8C322268
DISPATCH = 0x8C0DC960
GAME_LO, GAME_HI = 0x8C05D6E0, 0x8C16E800
CODE_LO, CODE_HI = 0x8C010000, 0x8C17A000

# Gold handler addresses (table dump, verified by tools/ghidra/VmHandlers.java output).
HANDLERS = [
    0x8c0dc960, 0x8c0dd1a0, 0x8c0dd740, 0x8c0de360, 0x8c0ddde0, 0x8c0de160, 0x8c0dd3c0, 0x8c0dd4c0,
    0x8c0dd5c0, 0x8c0dd2c0, 0x8c0ddfe0, 0x8c0dc960, 0x8c0de0a0, 0x8c0de120, 0x8c0de520, 0x8c0de5a0,
    0x8c0de640, 0x8c0de760, 0x8c0de820, 0x8c0de880, 0x8c0de8e0, 0x8c0dc960, 0x8c0e0280, 0x8c0ddee0,
    0x8c0dc960, 0x8c0dd860, 0x8c0dda60, 0x8c0ddac0, 0x8c0ddb00, 0x8c0de040, 0x8c0df4e0, 0x8c0dca60,
    0x8c0dca00, 0x8c0dc960, 0x8c0df3e0, 0x8c0dc960, 0x8c0dcea0, 0x8c0dcca0, 0x8c0dcc40, 0x8c0dcbe0,
    0x8c0df3a0, 0x8c0df360, 0x8c0dcac0, 0x8c0dcb80, 0x8c0dcb20, 0x8c0dcd60, 0x8c0dcda0, 0x8c0dcde0,
    0x8c0dcee0, 0x00000000, 0x8c0dcfa0, 0x8c0df740, 0x8c0dcf00, 0x8c0dd0c0, 0x8c0df9c0, 0x8c0dcfe0,
    0x8c0df2c0, 0x8c0df320, 0x8c0df7a0, 0x8c0df800, 0x8c0df8a0, 0x8c0df900, 0x8c0df960, 0x8c1016a0,
    0x8c0dd120, 0x8c0df480, 0x8c0dfa40, 0x8c0dfaa0, 0x8c0dfb00, 0x8c0dfb60, 0x8c0dfe20, 0x8c0dff20,
    0x8c0e0020, 0x8c0e0120, 0x8c0e0180, 0x8c0e02c0, 0x8c0e03a0, 0x8c0de260, 0x8c0deb80, 0x8c0deac0,
    0x8c0debc0, 0x8c0de9a0, 0x8c0dea00, 0x8c0de940, 0x8c0dec60, 0x8c0ded40, 0x8c0deb20, 0x8c0dc960,
    0x8c0def00, 0x8c0defa0, 0x8c0df020, 0x8c0df0c0, 0x8c0df260, 0x8c0df200, 0x8c0dea60, 0x8c0df080,
    0x8c0df5e0, 0x8c0df700, 0x8c0df620, 0x8c0df680, 0x8c0df6c0, 0x8c0dee60, 0x8c0dc960, 0x8c0dc960,
    0x8c0dfd20, 0x8c0dfc60, 0x8c0de460, 0x8c0dcd00, 0x8c0df140, 0x8c0dee20, 0x8c0df100, 0x8c0dce40,
    0x8c0df540, 0x8c0e0480, 0x8c0e09e0, 0x8c0e0a20, 0x8c0e0ac0, 0x8c0e0b20, 0x8c0e0ba0, 0x8c0e0c20,
]

# Direct operand-fetch call sites per handler (word fetch + float fetch), from VmHandlers.java.
FETCHES = {
    0x01: 1, 0x02: 1, 0x08: 1, 0x09: 1, 0x0c: 1, 0x0e: 1, 0x0f: 1, 0x11: 1, 0x17: 1, 0x1a: 1,
    0x1b: 1, 0x1f: 1, 0x2f: 1, 0x32: 1, 0x33: 1, 0x35: 1, 0x36: 2, 0x38: 1, 0x3d: 1, 0x40: 2,
    0x42: 1, 0x43: 1, 0x44: 1, 0x50: 1, 0x55: 2, 0x58: 3, 0x5a: 1, 0x5c: 1, 0x5d: 2, 0x5f: 1,
    0x63: 1, 0x65: 3, 0x6c: 1, 0x6d: 1, 0x6f: 1, 0x70: 1, 0x71: 1,
}
FLOAT_OPS = {0x58, 0x5a, 0x5c, 0x5d, 0x5f, 0x63, 0x65, 0x6c, 0x6d, 0x70}

# Operand-count corrections established by READING the Gold handler (not by MK4):
COUNT_FROM_READING = {
    0x43: (2, "fetch 1 (native fn, called) + branch-or-skip helper 0x8C0DFA40 consumes 1"),
    0x59: (4, "passes pc to 0x8C139400 then pc += 4"),
    0x45: (1, "every path ends in fetch+dispatch (skip) or jump via 0x8C0DF740 (take)"),
    0x3c: (24, "pc = mem[pc + node[+0x34]]; inline table measured at 24 packed targets in all 14 uses (MK4: 16)"),
}
PREFIXED = {0x46, 0x47, 0x48, 0x49, 0x68}   # via 0x8C0E0860: +1 word if ((w >> 8) & 0xFF) == 2
UNRESOLVED = {}
END = {0x30: "calls 0x8C088300, no re-dispatch", 0x31: "null slot", 0x32: "calls native operand, no re-dispatch",
       0x3e: "re-installs itself as node callback (+0x08), sets +0x84, R310C=0x3C, pause; never advances pc",
       0x3f: "sets node[+0x74]=0x200B, runs natives, ends in native 0x8C101780; no fetch, no re-dispatch"}
# Operand present only when the inline low byte is 0 (handler: extu.b; tst; bf -> skip fetch). Read in Gold.
OPTIONAL_LOW0 = {0x08}
JUMP = {0x33}                                   # pc = operand (packed)
BRANCH_LAST = {0x2f, 0x3d, 0x42, 0x44, 0x45, 0x6f, 0x36, 0x43}   # last operand = target if condition true
NATIVE_FIRST = {0x32, 0x35, 0x36, 0x43, 0x55}   # first operand = native code address (and 0xFFFFFF | 0x8C000000)

# MK4 PC reference labels and operand counts are NOT stored in this repo (open-mk4 has no licence).
# They are read as plain data from a local pinned checkout when present (REFERENCE/open-mk4,
# commit 85a515a, tools/mk4_asm.py), only to label output and report agreement - never to decode.
def _load_mk4_reference():
    import ast
    import os
    import re
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "REFERENCE", "open-mk4", "tools", "mk4_asm.py")
    try:
        txt = open(path, encoding="utf-8").read()
        names = re.search(r"NAMES = '''(.*?)'''", txt, re.S).group(1).split()
        counts = ast.literal_eval(re.search(r"COUNTS = (\{.*?\})", txt, re.S).group(1))
        return names, counts
    except (OSError, AttributeError, ValueError, SyntaxError):
        return [], {}


MK4_REF, MK4_COUNTS = _load_mk4_reference()


ANIM_TABLES = [(0x8C5335F8, 494), (0x8C558D68, 53)]


def anim_index(v):
    """Packed pointer to an animation descriptor -> global index (table 1 then table 2), else None."""
    if v >> 24:
        return None
    a = unpack(v)
    base = 0
    for t, n in ANIM_TABLES:
        if t <= a < t + 12 * n and (a - t) % 12 == 0:
            return base + (a - t) // 12
        base += n
    return None


def unpack(p):
    return ((p & 0xFFFFFF) << 2) | 0x8C000000


def pack(a):
    return (a & 0xFFFFFF) >> 2


def opinfo(op):
    h = HANDLERS[op] if op < len(HANDLERS) else 0
    nop = h == DISPATCH
    if op in COUNT_FROM_READING:
        count, how = COUNT_FROM_READING[op][0], "read"
    elif op in PREFIXED:
        count, how = "prefixed", "read"
    elif op in OPTIONAL_LOW0:
        count, how = "low0", "read"
    elif op in UNRESOLVED:
        count, how = "?", "unresolved"
    else:
        count, how = (0 if nop else FETCHES.get(op, 0)), "fetch-sites"
    if op in END or h == 0:
        flow = "end"
    elif op in JUMP:
        flow = "jump"
    elif op == 0x3c:
        flow = "select"
    elif op in BRANCH_LAST:
        flow = "branch"
    else:
        flow = "next"
    mk4 = MK4_COUNTS.get(op, 0) if MK4_REF else None
    if mk4 is None:
        agree = "n/a"
    elif count == "prefixed":
        agree = "yes" if mk4 == -1 else "no"
    elif count == "low0":
        agree = "partial"
    elif count == "?":
        agree = "open"
    else:
        agree = "yes" if count == mk4 else "no"
    return {"op": op, "handler": h, "nop": nop, "count": count, "how": how, "flow": flow,
            "float": op in FLOAT_OPS, "native_first": op in NATIVE_FIRST,
            "mk4": MK4_REF[op] if op < len(MK4_REF) else "-", "mk4_count": mk4, "agree_mk4": agree}


class Image:
    def __init__(self, path):
        self.d = open(path, "rb").read()

    def u32(self, a):
        o = a - LOAD
        if o < 0 or o + 4 > len(self.d):
            raise IndexError(hex(a))
        return struct.unpack_from("<I", self.d, o)[0]


def decode_one(img, addr):
    """Decode one instruction at byte address addr. Returns dict or raises ValueError."""
    w = img.u32(addr)
    op = w >> 24
    if op >= len(HANDLERS) or HANDLERS[op] == 0:
        raise ValueError("invalid opcode %02x at %08x" % (op, addr))
    info = opinfo(op)
    n = info["count"]
    if n == "prefixed":
        n = 1 if ((w >> 8) & 0xFF) == 2 else 0
    elif n == "low0":
        n = 1 if (w & 0xFF) == 0 else 0
    if n == "?":
        raise ValueError("opcode %02x at %08x has an unresolved operand format" % (op, addr))
    ops = [img.u32(addr + 4 * (k + 1)) for k in range(n)]
    return {"addr": addr, "word": w, "op": op, "inline": w & 0xFFFFFF, "operands": ops,
            "size": 4 * (1 + n), "info": info}


def targets(ins):
    i = ins["info"]
    if i["flow"] == "select":
        return [unpack(v) for v in ins["operands"]]
    if i["flow"] in ("jump", "branch") and ins["operands"]:
        return [unpack(ins["operands"][-1])]
    return []


def decode_stream(img, start, max_ins=4096):
    """Linear decode from start until an end/jump/select or an error; returns (instrs, stop_reason)."""
    out, a = [], start
    for _ in range(max_ins):
        try:
            ins = decode_one(img, a)
        except (ValueError, IndexError) as e:
            return out, "error: %s" % e
        out.append(ins)
        a += ins["size"]
        if ins["info"]["flow"] in ("end", "jump", "select"):
            return out, ins["info"]["flow"]
    return out, "limit"


def fmt(ins):
    i = ins["info"]
    s = "%08x  %08x  op_%02x" % (ins["addr"], ins["word"], ins["op"])
    if ins["inline"]:
        s += " #%06x" % ins["inline"]
    ops = []
    for k, v in enumerate(ins["operands"]):
        if k == 0 and i["native_first"]:
            ops.append("native:%08x" % ((v & 0xFFFFFF) | 0x8C000000))   # handlers: and 0xFFFFFF | 0x8C000000
        elif anim_index(v) is not None:
            ops.append("anim[%d]" % anim_index(v))
        elif i["flow"] in ("jump", "branch") and k == len(ins["operands"]) - 1:
            ops.append("->%08x" % unpack(v))
        elif i["float"]:
            ops.append("%g" % struct.unpack("<f", struct.pack("<I", v))[0])
        else:
            ops.append("%08x" % v)
    if ops:
        s += "  " + ", ".join(ops)
    return s + "   ; mk4:%s" % i["mk4"]


def plausible_entry(img, a, min_ins=2):
    ins, why = decode_stream(img, a, 512)
    if why.startswith("error") or why == "limit" or len(ins) < min_ins:
        return False
    if all(x["info"]["nop"] for x in ins[:-1]):
        return False
    for x in ins:
        for t in targets(x):
            if not (CODE_LO <= t < CODE_HI):
                return False
    return True


ENTRY = 0x8C0DC920          # run-script entry: pc = r4 >> 2 ; node[+0x48] = pc ; dispatch
DATA_LO, DATA_HI = 0x8C2D0000, 0x8C33B954   # script streams found here (see combat-vm.md)


def entry_seeds(img):
    """Script starts = the r4 literal loaded right before a `jsr` to the run-script entry 0x8C0DC920."""
    lo, hi = GAME_LO, GAME_HI
    h = struct.unpack("<%dH" % ((hi - lo) // 2), img.d[lo - LOAD:hi - LOAD])

    def pool(i, reg):
        w = h[i]
        if (w & 0xF000) == 0xD000 and ((w >> 8) & 0xF) == reg:     # mov.l @(disp,pc),Rreg
            ea = ((lo + i * 2 + 4) & ~3) + (w & 0xFF) * 4
            return img.u32(ea)
        return None

    seeds = {}
    for i, w in enumerate(h):
        if (w & 0xF0FF) == 0x400B:                                   # jsr @Rn
            n = (w >> 8) & 0xF
            if not any(pool(j, n) == ENTRY for j in range(max(0, i - 16), i)):
                continue
            for j in list(range(max(0, i - 16), i)) + [i + 1]:
                v = pool(j, 4)
                if v is not None and DATA_LO <= v < DATA_HI:
                    seeds[v] = lo + i * 2
    return seeds


def scan(img):
    """Seeds from calls to the run-script entry, then closure over jump/branch targets."""
    seeds = entry_seeds(img)
    streams, todo = {}, list(seeds)
    while todo:
        a = todo.pop()
        if a in streams:
            continue
        ins, why = decode_stream(img, a)
        streams[a] = (ins, why)
        for x in ins:
            for t in targets(x):
                if t not in streams and DATA_LO <= t < DATA_HI:
                    todo.append(t)
    return seeds, streams


if __name__ == "__main__":
    a = sys.argv
    cmd = a[1] if len(a) > 1 else ""
    if cmd == "ops":
        tsv = "--tsv" in a
        if tsv:
            print("op\thandler\toperands\thow\tflow\tfloat\tnative_first\tmk4_ref\tmk4_count\tagree_mk4")
        for op in range(len(HANDLERS)):
            i = opinfo(op)
            if tsv:
                print("%02x\t%08x\t%s\t%s\t%s\t%d\t%d\t%s\t%s\t%s" % (op, i["handler"], i["count"], i["how"], i["flow"],
                      i["float"], i["native_first"], i["mk4"], i["mk4_count"], i["agree_mk4"]))
            else:
                print("op_%02x handler=%08x operands=%-8s flow=%-6s mk4:%s" % (op, i["handler"], i["count"], i["flow"], i["mk4"]))
    elif cmd == "dis":
        img = Image(a[2])
        ins, why = decode_stream(img, int(a[3], 16), int(a[4]) if len(a) > 4 else 4096)
        for x in ins:
            print(fmt(x))
        print("; stop:", why)
    elif cmd == "scan":
        img = Image(a[2])
        seeds, streams = scan(img)
        good = sum(1 for s in streams.values() if not s[1].startswith("error"))
        nins = sum(len(s[0]) for s in streams.values())
        print("seeds %d  streams %d  ending cleanly %d  instructions %d" % (len(seeds), len(streams), good, nins))
        if len(a) > 3:
            with open(a[3], "w") as f:
                f.write("start\tseed_ref\tinstructions\tstop\n")
                for s in sorted(streams):
                    f.write("%08x\t%s\t%d\t%s\n" % (s, ("%08x" % seeds[s]) if s in seeds else "target",
                                                    len(streams[s][0]), streams[s][1]))
    else:
        print(__doc__)
