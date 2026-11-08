"""Wrap the raw Dreamcast 1ST_READ.BIN in a minimal SH-4 ELF32 (little endian).

The bytes are copied unchanged; the ELF only declares where they load
(0x8C010000, the address the BIOS jumps to) so that Ghidra's ELF loader
and REA's native-executable admission accept the image. The source is
never modified.

Usage: python -I tools/bin2elf.py <1ST_READ.BIN> <out.elf> [base_hex]
"""
import struct, sys

src, dst = sys.argv[1], sys.argv[2]
base = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x8C010000
code = open(src, "rb").read()
EHS, PHS, SHS = 52, 32, 40
off = 0x1000
shstr = b"\x00.text\x00.shstrtab\x00"
shstr_off = off + len(code)
sh_off = (shstr_off + len(shstr) + 3) & ~3
eh = struct.pack("<4sBBBB8sHHIIIIIHHHHHH", b"\x7fELF", 1, 1, 1, 0, b"\0" * 8,
                 2, 42, 1, base, EHS, sh_off, 0x9, EHS, PHS, 1, SHS, 3, 2)  # EM_SH=42, EF_SH4=9
ph = struct.pack("<IIIIIIII", 1, off, base, base, len(code), len(code), 7, 0x20)
sh = [b"\0" * SHS,
      struct.pack("<IIIIIIIIII", 1, 1, 7, base, off, len(code), 0, 0, 32, 0),
      struct.pack("<IIIIIIIIII", 7, 3, 0, 0, shstr_off, len(shstr), 0, 0, 1, 0)]
with open(dst, "wb") as o:
    o.write(eh + ph)
    o.write(b"\0" * (off - EHS - PHS))
    o.write(code + shstr)
    o.write(b"\0" * (sh_off - shstr_off - len(shstr)))
    o.write(b"".join(sh))
print("wrote %s: %d code bytes at 0x%08X" % (dst, len(code), base))
