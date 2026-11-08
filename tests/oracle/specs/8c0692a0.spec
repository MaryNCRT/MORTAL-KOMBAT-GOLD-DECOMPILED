# FUN_8c0692a0: unpack one packed joint-rotation word (10:11:11) into 3 floats (radians)
func   8c0692a0
keep   8c2f7160
keep   8c2f715c
u32    8c2f3130
packed 8c2f310c 8c800000 10000
out    8c2f3130
out    8c2f3134
outp   8c2f310c 0
outp   8c2f310c 4
outp   8c2f310c 8
