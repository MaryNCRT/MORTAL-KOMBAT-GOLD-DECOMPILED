/* anim_rot.c - packed joint-rotation decoder (animation frames).
 *
 * 0x8C0692A0 (114 bytes). Reconstructed from the SH-4 disassembly (OUTPUT/anim1.txt).
 * Input : R3130 = one packed frame dword (fields 10:11:11, see docs/systems/animation-engine.md)
 *         R310C = packed pointer to a float[3] destination
 * Output: dst[0] = (w        & 0x7FF) * K2048     K2048 = *(float*)0x8C2F7160 = 0x3B490FDB = 2*pi/2048
 *         dst[1] = ((w >> 11) & 0x7FF) * K2048
 *         dst[2] = (w >> 22)           * K1024     K1024 = *(float*)0x8C2F715C = 0x3BC90FDB = 2*pi/1024
 *         R3134 = bits(dst[1]), R3130 = bits(dst[2])   (pseudo-register side effects kept)
 * The constants are read from memory exactly as the original does (they live in initialised data).
 * Float semantics: SH-4 single precision, `float FPUL` = signed int -> float, one fmul each.
 */
#include <string.h>
#include "mkg_mem.h"

static float f32_at(uint32_t va) { float f; memcpy(&f, mkg_u32p(va), 4); return f; }
static void put_f32(uint32_t va, float f) { memcpy(mkg_u32p(va), &f, 4); }
static uint32_t bits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }

void AnimUnpackRot10_11_11_8c0692a0(void)
{
    const uint32_t w = R3130;
    const uint32_t dst = mkg_unpack(MKG_U32(0x8C2F310Cu));

    float a = (float)(int32_t)(w & 0x7FFu) * f32_at(0x8C2F7160u);
    put_f32(dst + 0, a);
    float b = (float)(int32_t)((w >> 11) & 0x7FFu) * f32_at(0x8C2F7160u);
    put_f32(dst + 4, b);
    R3134 = bits(b);
    float c = (float)(int32_t)(w >> 22) * f32_at(0x8C2F715Cu);
    put_f32(dst + 8, c);
    R3130 = bits(c);
}
