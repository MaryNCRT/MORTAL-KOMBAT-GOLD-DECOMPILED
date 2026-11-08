"""Full structural parser for MK Gold `0.1v` GEO files (all block kinds).

Layout verified on all 148 non-empty GEO files of the retail disc: header,
block records and payloads tile every file exactly (see docs/formats/geo-extended.md).

Block record (32 bytes at 0x20 + 32*i), kind chosen by flag bit 0x80:

    mesh   (flags & 0x80 == 0):  u16 flags, u16 n_sub, s32 rel @+4  -> payload = &rel + rel
    sprite (flags & 0x80 != 0):  u16 flags, u16 aux, u16 w, u16 h, s16 x0, s16 y0,
                                 s32 rel @+12 -> payload = &rel + rel,
                                 float fw, fh, fright, fbottom @+16

Payload = n_sub (sprite: 1) x [32-byte sub-header {u16 h[16]: n_vert = h[3], h[5] = mode}
          + n_vert x 32-byte vertex {float nx,ny,nz, x,y,z, u,v}]
"""
import struct
from collections import namedtuple

Vertex = namedtuple("Vertex", "nx ny nz x y z u v")
SubMesh = namedtuple("SubMesh", "offset header vertices")
Block = namedtuple("Block", "index record_offset flags kind n_sub payload_offset payload_end sprite submeshes")
Sprite = namedtuple("Sprite", "aux w h x0 y0 fw fh fright fbottom")

HEADER_SIZE = 0x20
RECORD_SIZE = 0x20
SUB_HEADER_SIZE = 0x20
VERTEX_SIZE = 0x20


class GeoError(ValueError):
    pass


def parse_geo(data):
    if len(data) < 12 or data[:4] != b"0.1v":
        raise GeoError("not a 0.1v container")
    size, count = struct.unpack_from("<II", data, 4)
    if size != len(data):
        raise GeoError("header size %d != file size %d" % (size, len(data)))
    blocks = []
    for i in range(count):
        ro = HEADER_SIZE + i * RECORD_SIZE
        flags, second = struct.unpack_from("<HH", data, ro)
        sprite = None
        if flags & 0x80:
            w, h, x0, y0 = struct.unpack_from("<HHhh", data, ro + 4)
            rel = struct.unpack_from("<i", data, ro + 12)[0]
            payload = ro + 12 + rel
            fw, fh, fr, fb = struct.unpack_from("<4f", data, ro + 16)
            sprite = Sprite(second, w, h, x0, y0, fw, fh, fr, fb)
            n_sub, kind = 1, "sprite"
        else:
            rel = struct.unpack_from("<i", data, ro + 4)[0]
            payload = ro + 4 + rel
            n_sub, kind = second, "mesh"
        subs, p = [], payload
        for _ in range(n_sub):
            if p + SUB_HEADER_SIZE > len(data):
                raise GeoError("block %d: sub-header past end of file" % i)
            hdr = struct.unpack_from("<16H", data, p)
            nv = hdr[3]
            end = p + SUB_HEADER_SIZE + nv * VERTEX_SIZE
            if end > len(data):
                raise GeoError("block %d: vertices past end of file" % i)
            verts = [Vertex(*struct.unpack_from("<8f", data, p + SUB_HEADER_SIZE + k * VERTEX_SIZE))
                     for k in range(nv)]
            subs.append(SubMesh(p, hdr, verts))
            p = end
        blocks.append(Block(i, ro, flags, kind, n_sub, payload, p, sprite, subs))
    return blocks


def check_tiling(data, blocks):
    """True if header + records + payloads cover the file exactly, with no gap or overlap."""
    spans = sorted((b.payload_offset, b.payload_end) for b in blocks)
    pos = HEADER_SIZE + RECORD_SIZE * len(blocks)
    for a, e in spans:
        if a != pos:
            return False
        pos = e
    return pos == len(data)


def strip_triangles(n):
    """Triangle indices for one strip of n vertices (alternating winding, degenerates dropped
    later by the caller if positions coincide)."""
    tris = []
    for i in range(n - 2):
        tris.append((i, i + 1, i + 2) if i % 2 == 0 else (i, i + 2, i + 1))
    return tris
