"""GEO parser tests.

Synthetic fixtures (built here, no game data) cover every block kind seen on the disc:
mesh blocks with flags 0x000/0x001/0x002/0x004/0x040/0x200 and sprite blocks with flags
0x080/0x180/0x280/0x380/0x480. Disc tests run only when EXTRACTED/disc exists locally.

    python -I -m unittest discover -s tests -v
"""
import glob
import os
import struct
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import mkg_geo  # noqa: E402


def read(path):
    with open(path, "rb") as f:
        return f.read()

DISC = os.path.join(ROOT, "EXTRACTED", "disc")


def vertex(i):
    return struct.pack("<8f", 0.0, 1.0, 0.0, float(i), float(i * 2), 0.5, i / 8.0, 1 - i / 8.0)


def sub(nverts, mode=0):
    h = [0] * 16
    h[3] = nverts
    h[5] = mode
    return struct.pack("<16H", *h) + b"".join(vertex(i) for i in range(nverts))


def build(blocks):
    """blocks: list of ('mesh', flags, [(nverts, mode), ...]) or ('sprite', flags, aux, w, h, x0, y0, uv)."""
    n = len(blocks)
    payloads, recs = [], []
    pos = 0x20 + 0x20 * n
    for i, b in enumerate(blocks):
        ro = 0x20 + 0x20 * i
        if b[0] == "mesh":
            _, flags, subs = b
            pl = b"".join(sub(nv, m) for nv, m in subs)
            rec = struct.pack("<HHi", flags, len(subs), pos - (ro + 4)) + b"\0" * 24
        else:
            _, flags, aux, w, h, x0, y0, uv = b
            hdr = [0] * 16
            hdr[3] = 4
            hdr[5] = flags >> 8
            pl = struct.pack("<16H", *hdr) + b"".join(
                struct.pack("<8f", 0, 0, 0, 0, 0, 0, u, v) for u, v in uv)
            rec = struct.pack("<HHHHhhi4f", flags, aux, w, h, x0, y0, pos - (ro + 12),
                              float(w), float(h), float(w + x0), float(h + y0))
        assert len(rec) == 32
        recs.append(rec)
        payloads.append(pl)
        pos += len(pl)
    body = b"".join(recs) + b"".join(payloads)
    size = 0x20 + len(body)
    return b"0.1v" + struct.pack("<II", size, n) + b"\0" * 20 + body


UV = [(0, 0.5), (0, 0), (0.25, 0.5), (0.25, 0)]


class SyntheticGeo(unittest.TestCase):
    def check(self, data):
        blocks = mkg_geo.parse_geo(data)
        self.assertTrue(mkg_geo.check_tiling(data, blocks))
        return blocks

    def test_mesh_flag_kinds(self):
        for flags in (0x000, 0x001, 0x002, 0x004, 0x040, 0x200):
            with self.subTest(flags=hex(flags)):
                b = self.check(build([("mesh", flags, [(5, 0), (3, 2)])]))
                self.assertEqual(b[0].kind, "mesh")
                self.assertEqual([len(s.vertices) for s in b[0].submeshes], [5, 3])
                self.assertEqual(b[0].submeshes[1].header[5], 2)
                self.assertAlmostEqual(b[0].submeshes[0].vertices[4].x, 4.0)

    def test_sprite_flag_kinds(self):
        for flags in (0x080, 0x180, 0x280, 0x380, 0x480):
            with self.subTest(flags=hex(flags)):
                b = self.check(build([("sprite", flags, 0x100, 120, 60, -60, -30, UV)]))[0]
                self.assertEqual(b.kind, "sprite")
                self.assertEqual((b.sprite.w, b.sprite.h, b.sprite.x0, b.sprite.y0), (120, 60, -60, -30))
                self.assertEqual(b.sprite.fright, 60.0)
                self.assertEqual(b.submeshes[0].header[5], flags >> 8)
                self.assertEqual(len(b.submeshes[0].vertices), 4)

    def test_mixed_file(self):
        data = build([("mesh", 0x001, [(4, 0)]), ("sprite", 0x280, 1, 10, 10, -5, -5, UV),
                      ("mesh", 0x200, [(6, 2), (3, 0)])])
        self.assertEqual([b.kind for b in self.check(data)], ["mesh", "sprite", "mesh"])

    def test_rejects_bad_size(self):
        data = bytearray(build([("mesh", 0, [(3, 0)])]))
        data += b"\0"
        with self.assertRaises(mkg_geo.GeoError):
            mkg_geo.parse_geo(bytes(data))

    def test_detects_gap(self):
        data = bytearray(build([("mesh", 0, [(3, 0)])]))
        struct.pack_into("<I", data, 4, len(data) + 32)
        data += b"\0" * 32
        blocks = mkg_geo.parse_geo(bytes(data))
        self.assertFalse(mkg_geo.check_tiling(bytes(data), blocks))

    def test_strip_winding(self):
        self.assertEqual(mkg_geo.strip_triangles(5), [(0, 1, 2), (1, 3, 2), (2, 3, 4)])


@unittest.skipUnless(os.path.isdir(DISC), "retail disc not extracted locally")
class DiscGeo(unittest.TestCase):
    def test_every_geo_tiles(self):
        n = 0
        for f in sorted(glob.glob(os.path.join(DISC, "*.GEO"))):
            d = read(f)
            if len(d) < 0x20:
                continue
            with self.subTest(f=os.path.basename(f)):
                self.assertTrue(mkg_geo.check_tiling(d, mkg_geo.parse_geo(d)))
            n += 1
        self.assertEqual(n, 148)

    def test_sprite_quads_are_atlas_rectangles(self):
        # w/h is the on-screen size; UVs select an axis-aligned atlas region (not the same size:
        # VS_SC spans 233 texels for w=234, CY_FAT block 2 spans 37x26 texels for 450x324).
        n = 0
        for f in sorted(glob.glob(os.path.join(DISC, "*.GEO"))):
            d = read(f)
            if len(d) < 0x20:
                continue
            for b in mkg_geo.parse_geo(d):
                if b.kind != "sprite":
                    continue
                v = b.submeshes[0].vertices
                self.assertEqual(len(v), 4)
                self.assertTrue(all(0.0 <= x.u <= 1.0 and 0.0 <= x.v <= 1.0 for x in v))
                self.assertLessEqual(len({x.u for x in v}), 2)
                self.assertLessEqual(len({x.v for x in v}), 2)
                self.assertTrue(all(x.x == x.y == x.z == 0.0 for x in v))
                n += 1
        self.assertEqual(n, 1076)


if __name__ == "__main__":
    unittest.main()
