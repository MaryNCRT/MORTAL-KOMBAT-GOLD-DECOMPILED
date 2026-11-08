/* mkg_mem.h - memory model shared by reconstructed MK Gold code and the oracle tests.
 *
 * The original engine keeps its working state in a block of "pseudo-registers"
 * (globals at 0x8C2F3xxx) and addresses data through PACKED pointers:
 *     packed   = (addr & 0x00FFFFFF) >> 2
 *     unpacked = ((packed & 0x00FFFFFF) << 2) | 0x8C000000
 * (seen verbatim in SH-4 code, e.g. 0x8C11E880 and 0x8C137E60; same idiom as MK4 PC).
 *
 * Reconstructed code addresses original memory through MKG_U32(va), backed by a
 * 16 MiB array that mirrors Dreamcast main RAM (0x8C000000..0x8CFFFFFF).
 * This keeps original addresses visible while the data layout is still being
 * recovered; it is a decomp-stage model, not the final port's memory layout.
 */
#ifndef MKG_MEM_H
#define MKG_MEM_H
#include <stdint.h>

#define MKG_RAM_BASE 0x8C000000u
#define MKG_RAM_SIZE 0x01000000u

extern uint8_t mkg_ram[MKG_RAM_SIZE];

static inline uint32_t *mkg_u32p(uint32_t va) {
    return (uint32_t *)(mkg_ram + ((va - MKG_RAM_BASE) & (MKG_RAM_SIZE - 1)));
}
#define MKG_U32(va) (*mkg_u32p((uint32_t)(va)))

static inline uint32_t mkg_unpack(uint32_t p) { return ((p & 0x00FFFFFFu) << 2) | MKG_RAM_BASE; }
static inline uint32_t mkg_pack(uint32_t va) { return (va & 0x00FFFFFFu) >> 2; }

/* Pseudo-register block (0x8C2F3100..0x8C2F3150). Names are ADDRESS-BASED on purpose:
 * roles are not established yet (see docs/systems/combat-vm.md). */
#define R3104 MKG_U32(0x8C2F3104u)
#define R3108 MKG_U32(0x8C2F3108u)
#define R3120 MKG_U32(0x8C2F3120u)
#define R3130 MKG_U32(0x8C2F3130u)
#define R3134 MKG_U32(0x8C2F3134u)
#define MKG_PAUSE_FLAG MKG_U32(0x8C2F3074u)   /* tested after most calls; role [H] */

#endif
