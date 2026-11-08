/* node_link.c - small node-field accessors from the 0x8C137Exx cluster.
 *
 * Reconstructed by reading the SH-4 disassembly (OUTPUT/vm2.txt). Names describe the
 * mechanics only; what the fields MEAN is not established. Do not rename to a role
 * without evidence.
 *
 * Both functions:
 *     n1    = unpack(R3120)          ; node addressed by pseudo-register 0x8C2F3120
 *     R3104 = n1[+0x3C]              ; a packed link stored in that node
 *     R3130 = unpack(R3104)[+FIELD]  ; read FIELD of the linked node
 * The SH-4 code computes unpack(x) as ((x << 8) >> 6 logical) | 0x8C000000, which equals
 * ((x & 0xFFFFFF) << 2) | 0x8C000000.
 */
#include "mkg_mem.h"

/* 0x8C137EC0 (42 bytes). FIELD = +0x74 (MK4 PC: +0x74 is move_state on player nodes [H]). */
void NodeLink3C_Load74_8c137ec0(void)
{
    R3104 = MKG_U32(mkg_unpack(R3120) + 0x3C);
    R3130 = MKG_U32(mkg_unpack(R3104) + 0x74);
}

/* 0x8C137F00 (42 bytes). FIELD = +0x7C. */
void NodeLink3C_Load7C_8c137f00(void)
{
    R3104 = MKG_U32(mkg_unpack(R3120) + 0x3C);
    R3130 = MKG_U32(mkg_unpack(R3104) + 0x7C);
}
