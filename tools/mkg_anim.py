"""MK Gold animation data: descriptor tables + frame decoding (read-only).

Verified facts (docs/systems/animation-engine.md):
  descriptor  {u32 data_ptr, u32 frames, u32 (nodes << 16) | flags}  tables 0x8C5335F8 (494), 0x8C558D68 (53)
  frame       nodes x u32: [0..2] float root translation, [3..] packed joint rotations
  rotation    decoded by 0x8C0692A0 (oracle-verified):
                r0 = (w & 0x7FF)        * K2048
                r1 = ((w >> 11) & 0x7FF) * K2048
                r2 = (w >> 22)          * K1024
              K2048 = float 0x3B490FDB (2*pi/2048), K1024 = float 0x3BC90FDB (2*pi/1024), all IEEE single.
Which axis each component drives, and the joint hierarchy, are NOT established yet.

Usage:
    python -I tools/mkg_anim.py list  <1ST_READ.BIN>
    python -I tools/mkg_anim.py frame <1ST_READ.BIN> <anim_index> <frame>
"""
import struct
import sys

LOAD = 0x8C010000
TABLES = [(0x8C5335F8, 494), (0x8C558D68, 53)]
K2048_BITS = 0x3B490FDB
K1024_BITS = 0x3BC90FDB


def f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def f32_bits(x):
    """Round a Python float to IEEE single and return its bits."""
    return struct.unpack("<I", struct.pack("<f", x))[0]


def unpack_rotation_bits(w):
    """Bit-exact model of 0x8C0692A0. Returns the three IEEE single results as raw bits."""
    import numpy as np
    k11, k10 = np.float32(f32(K2048_BITS)), np.float32(f32(K1024_BITS))
    a = np.float32(np.int32(w & 0x7FF)) * k11
    b = np.float32(np.int32((w >> 11) & 0x7FF)) * k11
    c = np.float32(np.int32(w >> 22)) * k10
    return tuple(struct.unpack("<I", np.float32(x).tobytes())[0] for x in (a, b, c))


def descriptors(img):
    out = []
    for base, n in TABLES:
        for i in range(n):
            p, frames, nf = struct.unpack_from("<III", img, base - LOAD + 12 * i)
            out.append({"index": len(out), "desc": base + 12 * i, "data": p, "frames": frames,
                        "nodes": nf >> 16, "flags": nf & 0xFFFF})
    return out


def frame(img, desc, k):
    if not 0 <= k < desc["frames"]:
        raise IndexError("frame out of range")
    n = desc["nodes"]
    words = struct.unpack_from("<%dI" % n, img, desc["data"] - LOAD + 4 * n * k)
    root = tuple(f32(x) for x in words[:3])
    joints = [tuple(f32(b) for b in unpack_rotation_bits(w)) for w in words[3:]]
    return root, joints


if __name__ == "__main__":
    a = sys.argv
    if len(a) >= 3 and a[1] == "list":
        img = open(a[2], "rb").read()
        print("index\tdesc\tdata\tframes\tnodes\tflags")
        for d in descriptors(img):
            print("%d\t%08x\t%08x\t%d\t%d\t%d" % (d["index"], d["desc"], d["data"], d["frames"], d["nodes"], d["flags"]))
    elif len(a) >= 5 and a[1] == "frame":
        img = open(a[2], "rb").read()
        d = descriptors(img)[int(a[3])]
        root, joints = frame(img, d, int(a[4]))
        print("anim %d frame %s/%d nodes %d" % (d["index"], a[4], d["frames"], d["nodes"]))
        print("root translation: % .5f % .5f % .5f" % root)
        for i, j in enumerate(joints):
            print("joint %2d  r0=% .5f r1=% .5f r2=% .5f rad" % ((i,) + j))
    else:
        print(__doc__)
