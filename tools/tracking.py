"""Function tracking for the MK Gold decomp: decomp/functions.tsv + progress report.

One row per function of 1ST_READ.BIN (SH-4, loaded at 0x8C010000):

    addr            entry address (hex, no 0x)
    size            body size in bytes (from Ghidra)
    category        game | sdk | unclassified
                      sdk = Katana SDK / middleware linked into the binary
                      (Shinobi, Kamui, Ninja, CRI ADX/Sofdec, AICA audio64, libc)
    name            our name (empty until known; never a guess without evidence)
    research        none | identified          (purpose known, evidence in docs)
    reconstruction  none | readable | replaced | dropped
                      readable = clean C/C++ in decomp/ that mirrors the original
                      replaced = intentionally reimplemented by the port (runtime/)
    verification    none | verified
                      verified = proven equivalent by a reproducible test
                      (tests/oracle) against the original. Compiling is NOT verification.
    file            source file that holds it
    evidence        short pointer to the proof (doc section, address, test name)

The three state columns are independent so IDENTIFIED / RECONSTRUCTED / VERIFIED
are always reported separately.

Usage:
    python -I tools/tracking.py init      # (re)build from OUTPUT/inventory/functions.tsv, keeping states
    python -I tools/tracking.py set <addr> key=value ...
    python -I tools/tracking.py report
"""
import csv
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TRACK = os.path.join(ROOT, "decomp", "functions.tsv")
INVENTORY = os.path.join(ROOT, "OUTPUT", "inventory", "functions.tsv")
FIELDS = ["addr", "size", "category", "name", "research", "reconstruction",
          "verification", "file", "evidence"]
CHOICES = {
    "category": ("game", "sdk", "unclassified"),
    "research": ("none", "identified"),
    "reconstruction": ("none", "readable", "replaced", "dropped"),
    "verification": ("none", "verified"),
}


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def save(rows):
    os.makedirs(os.path.dirname(TRACK), exist_ok=True)
    with open(TRACK, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def init():
    old = {r["addr"]: r for r in load(TRACK)} if os.path.exists(TRACK) else {}
    rows = []
    for g in load(INVENTORY):
        a = g["addr"].lower()
        r = old.get(a) or {"addr": a, "category": "unclassified", "name": "",
                           "research": "none", "reconstruction": "none",
                           "verification": "none", "file": "", "evidence": ""}
        r["size"] = g["bytes"]
        rows.append({k: r.get(k, "") for k in FIELDS})
    kept = set(old) - {r["addr"] for r in rows}
    for a in sorted(kept):  # never silently drop a tracked function
        rows.append(old[a])
    rows.sort(key=lambda r: int(r["addr"], 16))
    save(rows)
    print("tracked functions:", len(rows), "(kept %d not in inventory)" % len(kept))


def set_fields(addr, pairs):
    rows = load(TRACK)
    addr = addr.lower().replace("0x", "")
    for r in rows:
        if r["addr"] == addr:
            for p in pairs:
                k, v = p.split("=", 1)
                if k not in FIELDS:
                    sys.exit("unknown field " + k)
                if k in CHOICES and v not in CHOICES[k]:
                    sys.exit("%s must be one of %s" % (k, CHOICES[k]))
                if k == "verification" and v == "verified" and r["reconstruction"] == "none":
                    sys.exit("cannot verify a function that has no reconstruction")
                r[k] = v
            save(rows)
            return
    sys.exit("address not tracked: " + addr)


def report():
    rows = load(TRACK)
    total = sum(int(r["size"] or 0) for r in rows)
    def part(pred):
        sel = [r for r in rows if pred(r)]
        b = sum(int(r["size"] or 0) for r in sel)
        return len(sel), b, 100.0 * b / total if total else 0
    print("functions tracked: %d (%d bytes)" % (len(rows), total))
    for label, pred in [
        ("IDENTIFIED", lambda r: r["research"] == "identified"),
        ("RECONSTRUCTED", lambda r: r["reconstruction"] in ("readable", "replaced")),
        ("VERIFIED", lambda r: r["verification"] == "verified"),
        ("sdk", lambda r: r["category"] == "sdk"),
        ("unclassified", lambda r: r["category"] == "unclassified"),
    ]:
        n, b, p = part(pred)
        print("  %-14s %5d functions  %8d bytes  %6.2f %%" % (label, n, b, p))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        init()
    elif cmd == "set":
        set_fields(sys.argv[2], sys.argv[3:])
    elif cmd == "report":
        report()
    else:
        print(__doc__)
