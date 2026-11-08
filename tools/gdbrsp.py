"""Minimal GDB Remote Serial Protocol client for Flycast's SH-4 GDB stub.

No gdb binary needed (the local gdb is x86-only). Read-only by default:
it can query status, read registers and memory, set/clear breakpoints,
continue/step, and dump RAM to a file for state comparison.

Usage:
    python -I tools/gdbrsp.py probe [host:port]                 # '?' + registers + 64 bytes at 0x8C010000
    python -I tools/gdbrsp.py dump <addr> <len> <out> [host:port]
    python -I tools/gdbrsp.py regs [host:port]
"""
import socket
import sys


class RSP:
    def __init__(self, host="127.0.0.1", port=3263, timeout=10):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)

    def _send(self, payload):
        ck = sum(payload.encode()) & 0xFF
        self.s.sendall(("$%s#%02x" % (payload, ck)).encode())
        ack = self.s.recv(1)
        if ack != b"+":
            raise IOError("no ack: %r" % ack)

    def _recv(self):
        buf = b""
        while True:
            c = self.s.recv(1)
            if not c:
                raise IOError("connection closed")
            if c == b"$":
                break
        while not buf.endswith(b"#") :
            buf += self.s.recv(1)
        self.s.recv(2)  # checksum
        self.s.sendall(b"+")
        return buf[:-1].decode(errors="replace")

    def cmd(self, payload):
        self._send(payload)
        return self._recv()

    def read_mem(self, addr, length, chunk=0x400):
        out = bytearray()
        while length > 0:
            n = min(chunk, length)
            r = self.cmd("m%x,%x" % (addr, n))
            if r.startswith("E") or not r:
                raise IOError("read error at %08x: %s" % (addr, r))
            out += bytes.fromhex(r)
            addr += n
            length -= n
        return bytes(out)


def hostport(args, i):
    if len(args) > i:
        h, p = args[i].split(":")
        return h, int(p)
    return "127.0.0.1", 3263


if __name__ == "__main__":
    a = sys.argv
    cmd = a[1] if len(a) > 1 else ""
    if cmd == "probe":
        r = RSP(*hostport(a, 2))
        print("supported:", r.cmd("qSupported"))
        print("halt reason:", r.cmd("?"))
        g = r.cmd("g")
        print("g packet: %d hex chars" % len(g))
        print("mem 8c010000:", r.read_mem(0x8C010000, 64).hex())
    elif cmd == "regs":
        r = RSP(*hostport(a, 2))
        g = r.cmd("g")
        regs = [int.from_bytes(bytes.fromhex(g[i:i + 8]), "little") for i in range(0, len(g), 8)]
        for i, v in enumerate(regs[:24]):
            print("reg%-2d %08x" % (i, v))
    elif cmd == "dump":
        r = RSP(*hostport(a, 5))
        data = r.read_mem(int(a[2], 16), int(a[3], 16))
        open(a[4], "wb").write(data)
        print("wrote", len(data), "bytes")
    else:
        print(__doc__)
