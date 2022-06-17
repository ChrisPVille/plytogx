#include <ogc/gx.h>
#include "triangle_mdl.h"
static const u8 vtxArr[] = {0,1,2,2,1,3,3,1,0,2,3,0,};
void draw_triangle(void) {
GX_ClearVtxDesc();
GX_SetArray(GX_VA_POS, (void*)triangle_mdl+0, 12);
GX_SetVtxDesc(GX_VA_POS, GX_INDEX8);
GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_POS, GX_POS_XYZ, GX_F32, 0);
GX_Begin(GX_TRIANGLES, GX_VTXFMT0, 12);
for(size_t i = 0; i<12; i++){
	GX_Position1x8(vtxArr[i]);
}
GX_End();
}
