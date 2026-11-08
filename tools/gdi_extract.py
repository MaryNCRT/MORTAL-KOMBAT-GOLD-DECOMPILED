"""Read-only GD-ROM (GDI) ISO9660 lister/extractor.

Reads tracks 3 (HD area start, LBA 45000) and the last data track as one
logical 2048-byte-sector volume. Never writes to the source tracks.

Usage:
    python -I tools/gdi_extract.py <file.gdi> list
    python -I tools/gdi_extract.py <file.gdi> extract <outdir>
    python -I tools/gdi_extract.py <file.gdi> ip <outfile>     # dump IP.BIN (first 16 sectors of track 3)
"""
import os, struct, sys

class Track:
    def __init__(self, num, lba, ttype, ssize, path):
        self.num, self.lba, self.type, self.ssize, self.path = num, lba, ttype, ssize, path
        self.nsect = os.path.getsize(path) // ssize

class GDI:
    def __init__(self, gdi):
        base = os.path.dirname(os.path.abspath(gdi))
        lines = open(gdi, encoding="utf-8").read().splitlines()
        self.tracks = []
        for ln in lines[1:]:
            if not ln.strip():
                continue
            p1 = ln.split('"')
            pre = p1[0].split()
            num, lba, ttype, ssize = map(int, pre[:4])
            self.tracks.append(Track(num, lba, ttype, ssize, os.path.join(base, p1[1])))
        self.fh = {}

    def read_sector(self, lba):
        for t in reversed(self.tracks):
            if t.type == 4 and t.lba <= lba < t.lba + t.nsect:
                f = self.fh.get(t.num) or open(t.path, "rb")
                self.fh[t.num] = f
                f.seek((lba - t.lba) * t.ssize + (16 if t.ssize == 2352 else 0))
                return f.read(2048)
        # Track 53 in GDI is positioned so that its first sector == its lba; data beyond is fine
        raise IOError("LBA %d not in a data track" % lba)

    def read(self, lba, size):
        out = bytearray()
        n = (size + 2047) // 2048
        for i in range(n):
            out += self.read_sector(lba + i)
        return bytes(out[:size])

def walk(g, lba, size, path, out):
    data = g.read(lba, size)
    i = 0
    while i < len(data):
        rl = data[i]
        if rl == 0:
            i = (i // 2048 + 1) * 2048
            continue
        ext = struct.unpack_from("<I", data, i + 2)[0]
        ln = struct.unpack_from("<I", data, i + 10)[0]
        flags = data[i + 25]
        nl = data[i + 32]
        name = data[i + 33:i + 33 + nl]
        i += rl
        if name in (b"\x00", b"\x01"):
            continue
        n = name.decode("ascii", "replace").split(";")[0]
        full = path + "/" + n
        if flags & 2:
            walk(g, ext, ln, full, out)
        else:
            out.append((full, ext, ln))

def listing(g):
    pvd = g.read_sector(45000 + 16)
    assert pvd[1:6] == b"CD001", pvd[:8]
    root = pvd[156:156 + 34]
    rlba = struct.unpack_from("<I", root, 2)[0]
    rlen = struct.unpack_from("<I", root, 10)[0]
    out = []
    walk(g, rlba, rlen, "", out)
    return pvd, out

if __name__ == "__main__":
    g = GDI(sys.argv[1])
    cmd = sys.argv[2]
    if cmd == "ip":
        open(sys.argv[3], "wb").write(g.read(45000, 16 * 2048))
        sys.exit()
    pvd, files = listing(g)
    if cmd == "list":
        print("volume_id\t" + pvd[40:72].decode().strip())
        for f, lba, ln in files:
            print("%s\t%d\t%d" % (f, lba, ln))
    elif cmd == "extract":
        od = sys.argv[3]
        for f, lba, ln in files:
            dst = os.path.join(od, f.lstrip("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as o:
                rem, cur = ln, lba
                while rem > 0:
                    chunk = min(rem, 2048 * 512)
                    o.write(g.read(cur, chunk))
                    cur += chunk // 2048
                    rem -= chunk
        print("extracted %d files" % len(files))
