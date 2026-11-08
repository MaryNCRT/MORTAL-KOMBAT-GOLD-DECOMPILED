"""Animation + fight-script VM tests.

- Python rotation model vs ORIGINAL-code oracle vectors (bit-exact IEEE single).
- VM decoder rules on synthetic streams (no game data).
- Disc/binary tests run only when ORIGINAL/1ST_READ.BIN exists locally.

    python -I -m unittest discover -s tests -v
"""
import os
import struct
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import mkg_anim  # noqa: E402
import mkg_vm  # noqa: E402

BIN = os.path.join(ROOT, "ORIGINAL", "1ST_READ.BIN")
VEC = os.path.join(ROOT, "tests", "oracle", "vectors", "8c0692a0.tsv")


def parse_vectors(path):
    out = []
    for line in open(path):
        if not line.startswith("w "):
            continue
        w, r = line[2:].split("|")[:2]
        wd = dict((int(a, 16), int(b, 16)) for a, b in (t.split("=") for t in w.strip().strip(",").split(",")))
        rd = dict((int(a, 16), int(b, 16)) for a, b in (t.split("=") for t in r.strip()[2:].strip(",").split(",")))
        out.append((wd, rd))
    return out


class RotationOracle(unittest.TestCase):
    def test_python_model_matches_original_code(self):
        vecs = parse_vectors(VEC)
        self.assertGreaterEqual(len(vecs), 1000)
        for wd, rd in vecs:
            w = wd[0x8C2F3130]
            dst = mkg_vm.unpack(wd[0x8C2F310C])
            self.assertEqual(mkg_anim.unpack_rotation_bits(w), (rd[dst], rd[dst + 4], rd[dst + 8]))

    def test_scale_constants(self):
        import math
        self.assertAlmostEqual(mkg_anim.f32(mkg_anim.K2048_BITS), 2 * math.pi / 2048, places=9)
        self.assertAlmostEqual(mkg_anim.f32(mkg_anim.K1024_BITS), 2 * math.pi / 1024, places=9)


class FakeImage(mkg_vm.Image):
    def __init__(self, base, words):
        self.d = b"\0" * (base - mkg_vm.LOAD) + struct.pack("<%dI" % len(words), *words)


class VmDecoder(unittest.TestCase):
    BASE = 0x8C300000

    def dec(self, words):
        return mkg_vm.decode_stream(FakeImage(self.BASE, words), self.BASE)

    def test_table_shape(self):
        self.assertEqual(len(mkg_vm.HANDLERS), 120)
        self.assertEqual(mkg_vm.HANDLERS[0x31], 0)
        nops = [op for op, h in enumerate(mkg_vm.HANDLERS) if h == mkg_vm.DISPATCH]
        self.assertEqual(nops, [0x00, 0x0B, 0x15, 0x18, 0x21, 0x23, 0x57, 0x66, 0x67])
        # with a local open-mk4 checkout: every Gold nop slot carries an MK4 'nop*' reference label
        if mkg_vm.MK4_REF:
            self.assertTrue(all(mkg_vm.MK4_REF[o].startswith("nop") for o in nops))

    def test_end_and_operands(self):
        ins, why = self.dec([0x0F000000, mkg_vm.pack(0x8C5335F8), 0x32000000, 0x8C07EC00])
        self.assertEqual(why, "end")
        self.assertEqual([x["op"] for x in ins], [0x0F, 0x32])
        self.assertEqual(mkg_vm.anim_index(ins[0]["operands"][0]), 0)

    def test_prefixed_clip(self):
        ins, _ = self.dec([0x47000244, mkg_vm.pack(0x8C533B98), 0x47000044, 0x30000000])
        self.assertEqual([len(x["operands"]) for x in ins], [1, 0, 0])

    def test_optional_low_byte_clip(self):
        ins, _ = self.dec([0x08000000, 0x00123456, 0x08000001, 0x30000000])
        self.assertEqual([len(x["operands"]) for x in ins], [1, 0, 0])

    def test_jump_and_branch_targets(self):
        tgt = self.BASE + 0x40
        ins, why = self.dec([0x42000000, mkg_vm.pack(tgt), 0x33000000, mkg_vm.pack(tgt)])
        self.assertEqual(why, "jump")
        self.assertEqual(mkg_vm.targets(ins[0]), [tgt])
        self.assertEqual(mkg_vm.targets(ins[1]), [tgt])

    def test_select_has_24_targets(self):
        words = [0x3C000000] + [mkg_vm.pack(self.BASE + 0x100 + 4 * k) for k in range(24)]
        ins, why = self.dec(words)
        self.assertEqual(why, "select")
        self.assertEqual(len(mkg_vm.targets(ins[0])), 24)

    def test_invalid_slot_rejected(self):
        _, why = self.dec([0x31000000])
        self.assertTrue(why.startswith("error"))


@unittest.skipUnless(os.path.isfile(BIN), "1ST_READ.BIN not available locally")
class OnBinary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img = mkg_vm.Image(BIN)

    def test_handler_table_matches_binary(self):
        for op, h in enumerate(mkg_vm.HANDLERS):
            self.assertEqual(self.img.u32(mkg_vm.TABLE + 4 * op), h, "op %02x" % op)

    def test_script_streams_decode(self):
        seeds, streams = mkg_vm.scan(self.img)
        clean = sum(1 for ins, why in streams.values() if not why.startswith("error"))
        self.assertGreaterEqual(len(seeds), 600)
        self.assertGreaterEqual(clean / len(streams), 0.99)

    def test_animation_descriptors(self):
        descs = mkg_anim.descriptors(self.img.d)
        self.assertEqual(len(descs), 547)
        uniq = sorted({(d["data"], d["frames"], d["nodes"]) for d in descs})
        exact = sum(1 for a, b in zip(uniq, uniq[1:]) if b[0] - a[0] == 4 * a[1] * a[2])
        self.assertGreaterEqual(exact, 544)

    def test_frame_decodes_in_range(self):
        import math
        d = mkg_anim.descriptors(self.img.d)[0]
        root, joints = mkg_anim.frame(self.img.d, d, 0)
        self.assertEqual(len(joints), d["nodes"] - 3)
        for j in joints:
            self.assertTrue(all(0.0 <= x < 2 * math.pi for x in j))


if __name__ == "__main__":
    unittest.main()
