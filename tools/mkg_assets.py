"""Read-only inspectors for Mortal Kombat Gold (Dreamcast) data files.

Every layout here was checked against the retail disc; see docs/formats/.
Nothing is written next to the source files.

Usage:
    python -I tools/mkg_assets.py img2png <file.IMG> <out_dir>     # ARGB1555 linear -> PNG (needs Pillow+numpy)
    python -I tools/mkg_assets.py geo-check <disc_dir>             # validate GEO block layout on every file
    python -I tools/mkg_assets.py kat-list <file.KAT>              # list sound-bank entries
    python -I tools/mkg_assets.py anim-table <1ST_READ.BIN>        # dump the animation descriptor tables
"""
import glob
import os
import struct
import sys

LOAD_BASE = 0x8C010000

# Animation descriptor tables found in 1ST_READ.BIN (Rev 1, SHA-256 0518524820d8...).
# Same record shape as MK4 PC's table at 0x004ffdec: {data ptr, frames, nodes<<16 | flags}.
ANIM_TABLES = [(0x8C5335F8, 494), (0x8C558D68, 53)]


def img_entries(d):
    magic, size, count, _ = struct.unpack_from("<4sIII", d, 0)
    if magic != b"0.1v":
        raise ValueError("not a 0.1v container")
    # Each surface = 32-byte sub-header {u16 w, u16 h, 28 bytes zero} + w*h ARGB1555 pixels.
    off = 0x20
    out = []
    for _ in range(count):
        w, h = struct.unpack_from("<HH", d, off)
        out.append((w, h, off + 32))
        off += 32 + w * h * 2
    if off != size:
        raise ValueError("IMG size mismatch: computed 0x%x, header 0x%x" % (off, size))
    return out


def cmd_img2png(path, outdir):
    import numpy as np
    from PIL import Image
    d = open(path, "rb").read()
    if len(d) < 0x20:
        print("%s: empty container (%d bytes)" % (path, len(d)))
        return
    os.makedirs(outdir, exist_ok=True)
    for i, (w, h, off) in enumerate(img_entries(d)):
        p = np.frombuffer(d, dtype="<u2", offset=off, count=w * h).astype(np.uint32)
        rgba = np.stack([((p >> 10) & 31) * 255 // 31, ((p >> 5) & 31) * 255 // 31,
                         (p & 31) * 255 // 31, (p >> 15) * 255], -1).astype(np.uint8)
        dst = os.path.join(outdir, "%s_%d.png" % (os.path.splitext(os.path.basename(path))[0], i))
        Image.fromarray(rgba.reshape(h, w, 4), "RGBA").save(dst)
        print(dst, w, h)


def geo_blocks(d):
    _, size, count, _ = struct.unpack_from("<4sIII", d, 0)
    blocks = []
    for i in range(count):
        e = 0x20 + i * 32
        btype, nsub, rel = struct.unpack_from("<HHi", d, e)
        blocks.append((btype, nsub, e + 4 + rel))
    return size, blocks


def cmd_geo_check(disc):
    ok, bad = 0, []
    for f in sorted(glob.glob(os.path.join(disc, "*.GEO"))):
        d = open(f, "rb").read()
        if len(d) < 0x20:
            bad.append((os.path.basename(f), "empty"))
            continue
        size, blocks = geo_blocks(d)
        if size != len(d) or any(b[0] != 1 for b in blocks):
            bad.append((os.path.basename(f), "types=%s" % sorted({b[0] for b in blocks})))
            continue
        ends = []
        for _, nsub, p in blocks:
            for _ in range(nsub):
                nv = struct.unpack_from("<H", d, p + 6)[0]
                p += 32 + nv * 32
            ends.append(p)
        if all(ends[i] == blocks[i + 1][2] for i in range(len(blocks) - 1)) and ends[-1] <= len(d):
            ok += 1
        else:
            bad.append((os.path.basename(f), "non-contiguous"))
    print("type-1 (strip mesh) files validated:", ok)
    for b in bad:
        print("  not validated:", *b)


def cmd_kat_list(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 0)[0]
    print("entries", n, "header", 4 + n * 44)
    for i in range(n):
        e = struct.unpack_from("<11I", d, 4 + i * 44)
        print("%3d off=0x%06x size=%6d rate=%5d f4=%d f5=%d" % (i, e[1], e[2], e[3], e[4], e[5]))


def cmd_anim_table(path):
    d = open(path, "rb").read()
    recs = []
    for base, count in ANIM_TABLES:
        for i in range(count):
            p, frames, nf = struct.unpack_from("<III", d, base - LOAD_BASE + i * 12)
            recs.append((base + i * 12, p, frames, nf >> 16, nf & 0xFFFF))
    uniq = sorted({(r[1], r[2], r[3]) for r in recs})
    good = sum(1 for a, b in zip(uniq, uniq[1:]) if b[0] - a[0] == 4 * a[2] * a[1])
    print("records %d, unique data blocks %d, size==4*nodes*frames for %d of %d gaps"
          % (len(recs), len(uniq), good, len(uniq) - 1))
    print("desc_addr\tdata\tframes\tnodes\tflags")
    for r in recs:
        print("%08x\t%08x\t%d\t%d\t%d" % r)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "img2png":
        cmd_img2png(sys.argv[2], sys.argv[3])
    elif c == "geo-check":
        cmd_geo_check(sys.argv[2])
    elif c == "kat-list":
        cmd_kat_list(sys.argv[2])
    elif c == "anim-table":
        cmd_anim_table(sys.argv[2])
    else:
        print(__doc__)
