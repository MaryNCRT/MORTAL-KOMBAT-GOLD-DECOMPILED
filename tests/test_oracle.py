"""Reconstructed C vs ORIGINAL SH-4 behaviour (vectors recorded by tools/ghidra/EmuOracle.java).

Compiles tests/oracle/run_vectors.c with every decomp/**/*.c and replays each vector file.
Skipped when no C compiler is found. Recording NEW vectors needs Ghidra (tools/ghidra/oracle.ps1);
replaying them does not.
"""
import glob
import os
import shutil
import subprocess
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CC = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")


@unittest.skipUnless(CC, "no C compiler")
class OracleReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
        cls.exe = os.path.join(ROOT, "build", "run_vectors")
        srcs = [os.path.join(ROOT, "tests", "oracle", "run_vectors.c")] + \
            sorted(glob.glob(os.path.join(ROOT, "decomp", "**", "*.c"), recursive=True))
        subprocess.run([CC, "-std=c11", "-O2", "-Wall", "-ffp-contract=off",
                        "-I" + os.path.join(ROOT, "decomp", "include"), "-o", cls.exe] + srcs, check=True)

    def test_vectors(self):
        files = sorted(glob.glob(os.path.join(ROOT, "tests", "oracle", "vectors", "*.tsv")))
        self.assertTrue(files)
        for f in files:
            func = os.path.splitext(os.path.basename(f))[0]
            with self.subTest(func=func):
                r = subprocess.run([self.exe, func, f], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
