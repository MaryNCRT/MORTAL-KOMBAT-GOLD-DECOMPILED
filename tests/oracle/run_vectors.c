/* run_vectors.c - replays oracle vectors recorded from the ORIGINAL SH-4 code
 * (tools/ghidra/EmuOracle.java) against the reconstructed C functions.
 *
 * Usage: run_vectors <func_hex> <vectors.tsv>
 * Exit 0 only if every trial matches; prints the first mismatches otherwise.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mkg_mem.h"

uint8_t mkg_ram[MKG_RAM_SIZE];

void NodeLink3C_Load74_8c137ec0(void);
void NodeLink3C_Load7C_8c137f00(void);
void AnimUnpackRot10_11_11_8c0692a0(void);

static const struct { uint32_t addr; void (*fn)(void); } registry[] = {
    {0x8C137EC0u, NodeLink3C_Load74_8c137ec0},
    {0x8C137F00u, NodeLink3C_Load7C_8c137f00},
    {0x8C0692A0u, AnimUnpackRot10_11_11_8c0692a0},
};

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: run_vectors <func_hex> <vectors.tsv>\n"); return 2; }
    uint32_t want = (uint32_t)strtoul(argv[1], NULL, 16);
    void (*fn)(void) = NULL;
    for (size_t i = 0; i < sizeof registry / sizeof registry[0]; i++)
        if (registry[i].addr == want) fn = registry[i].fn;
    if (!fn) { fprintf(stderr, "function %08x not registered\n", want); return 2; }
    FILE *f = fopen(argv[2], "r");
    if (!f) { perror(argv[2]); return 2; }
    char line[8192];
    int trials = 0, bad = 0;
    while (fgets(line, sizeof line, f)) {
        if (line[0] != 'w') continue;
        if (strstr(line, "FAULT")) { fprintf(stderr, "oracle trial faulted: %s", line); bad++; continue; }
        memset(mkg_ram, 0, sizeof mkg_ram);
        char *bar = strchr(line, '|');
        *bar = 0;
        for (char *t = strtok(line + 2, ","); t; t = strtok(NULL, ",")) {
            uint32_t a, v;
            if (sscanf(t, " %x=%x", &a, &v) == 2) MKG_U32(a) = v;
        }
        fn();
        char *rs = bar + 1;
        while (*rs == ' ' || *rs == 'r') rs++;
        for (char *t = strtok(rs, ","); t; t = strtok(NULL, ",")) {
            uint32_t a, v;
            if (sscanf(t, " %x=%x", &a, &v) == 2 && MKG_U32(a) != v) {
                if (bad < 5) fprintf(stderr, "trial %d: [%08x] = %08x, original %08x\n", trials, a, MKG_U32(a), v);
                bad++;
            }
        }
        trials++;
    }
    fclose(f);
    printf("%08x: %d trials, %d mismatches\n", want, trials, bad);
    return (bad == 0 && trials > 0) ? 0 : 1;
}
