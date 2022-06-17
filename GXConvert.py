#!/usr/bin/env python

# Copyright (c) 2022 Christopher Dellman
# 
# This program is free software: you can redistribute it and/or modify  
# it under the terms of the GNU General Public License as published by  
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path, PurePath
from plyfile import PlyData, PlyElement
from struct import *

import argparse
import sys

def process(fileName, binPath, sourcePath, headerPath):
    plydata = PlyData.read(fileName)
    objname = Path(fileName).stem
    
    num_vert = len(plydata["vertex"])
    num_faces = len(plydata["face"])*3
    
    hasVtx = False
    hasNorm = False
    hasUv = False
    hasColor = False
    hasColorAlpha = False
    
    offsetVtx = 0
    offsetNorm = 0
    offsetUv = 0
    offsetColor = 0
    offsetColorAlpha = 0
    
    sizeVtx = (3*4)
    sizeNorm = (3*4)
    sizeUv = (2*4)
    sizeColor = (3*1)
    sizeColorAlpha = (1*1)
    
    sizeOfElems = 0
    for prop in plydata.elements[0].properties:
        name = prop.name
        if name == "x" or name == "y" or name == "z":
            hasVtx = True
        elif name == "nx" or name == "ny" or name == "nz":
            hasNorm = True
        elif name == "s" or name == "t":
            hasUv = True
        elif name == "red" or name == "green" or name == "blue":
            hasColor = True
        elif name == "alpha":
            hasColorAlpha = True

    if hasVtx:
        offsetVtx = sizeOfElems
        sizeOfElems += sizeVtx
    if hasNorm:
        offsetNorm = sizeOfElems
        sizeOfElems += sizeNorm
    if hasUv:
        offsetUv = sizeOfElems
        sizeOfElems += sizeUv
    if hasColor:
        offsetColor = sizeOfElems
        sizeOfElems += sizeColor
    if hasColorAlpha:
        offsetColorAlpha = sizeOfElems
        sizeOfElems += sizeColorAlpha
    
    print(f"Name:{objname} Vertices:{num_vert} Faces:{num_faces}")
    print(f"HasVtx:{hasVtx} HasNorm:{hasNorm} HasUv:{hasUv}")
    print(f"HasColor:{hasColor} HasColorAlpha:{hasColorAlpha}")
    
    if not hasVtx:
        raise ValueError("PLY contains no vertex info")
    
    #Create the packed binary model file
    binPath = PurePath(binPath,f"{objname}.mdl")
    print(f"Packing binary model {binPath} ...")
    with open(binPath, "wb") as f:
        for i in range(num_vert):
            #Pack vertex info
            x = plydata["vertex"]["x"][i]
            y = plydata["vertex"]["y"][i]
            z = plydata["vertex"]["z"][i]
            packedarr = pack(">3f", x, y, z)
            
            if hasNorm:            
                nx = plydata["vertex"]["nx"][i]
                ny = plydata["vertex"]["ny"][i]
                nz = plydata["vertex"]["nz"][i]
                packedarr += pack(">3f", nx, ny, nz)
            
            if hasUv:
                s = plydata["vertex"]["s"]
                t = plydata["vertex"]["t"]
                packedarr += pack(">2f", s, t)
            
            if hasColor:
                r = plydata["vertex"]["red"][i]
                g = plydata["vertex"]["green"][i]
                b = plydata["vertex"]["blue"][i]
                packedarr += pack("3B", r, g, b)
                
            if hasColorAlpha:
                a = plydata["vertex"]["alpha"][i]
                packedarr += pack("B", a)
            
            f.write(packedarr)
    
    sourcePath = PurePath(sourcePath,f"draw_{objname}.c")
    print(f"Generating C file {sourcePath} ...")
    #Create the C file loading the binary model
    with open(sourcePath, "w") as f:
        f.write(f"#include <ogc/gx.h>\n")
        f.write(f'#include "{objname}_mdl.h"\n')
        
        #Define Vertex index array
        if num_vert > 255:
            f.write('static const u16 vtxArr[] = {')
        else:
            f.write('static const u8 vtxArr[] = {')
        
        for i in range(len(plydata["face"])):      
            for j in range(3):
                f.write(f'{plydata["face"][i][0][j]},') #Heyyyy trailing commas are legal EXACTLY for this reason
        f.write('};\n')
        
        f.write(f"void draw_{objname}(void) {{\n")
        f.write("GX_ClearVtxDesc();\n")
        
        if hasVtx:
            f.write(f"GX_SetArray(GX_VA_POS, (void*){objname}_mdl+{offsetVtx}, {sizeOfElems});\n")
        if hasNorm:            
            f.write(f"GX_SetArray(GX_VA_NRM, (void*){objname}_mdl+{offsetNorm}, {sizeOfElems});\n")
        if hasUv:
            f.write(f"GX_SetArray(GX_VA_TEX0, (void*){objname}_mdl+{offsetUv}, {sizeOfElems});\n")
        #Alpha is part of the color stride if it exists
        if hasColor:
            f.write(f"GX_SetArray(GX_VA_CLR0, (void*){objname}_mdl+{offsetColor}, {sizeOfElems});\n")

        if num_vert > 255:
            if hasVtx:
                f.write("GX_SetVtxDesc(GX_VA_POS, GX_INDEX16);\n")
            if hasNorm:
                f.write("GX_SetVtxDesc(GX_VA_NRM, GX_INDEX16);\n")
            if hasUv:
                f.write("GX_SetVtxDesc(GX_VA_TEX0, GX_INDEX16);\n")
            if hasColor:
                f.write("GX_SetVtxDesc(GX_VA_CLR0, GX_INDEX16);\n")
        else:
            if hasVtx:
                f.write("GX_SetVtxDesc(GX_VA_POS, GX_INDEX8);\n")
            if hasNorm:
                f.write("GX_SetVtxDesc(GX_VA_NRM, GX_INDEX8);\n")
            if hasUv:
                f.write("GX_SetVtxDesc(GX_VA_TEX0, GX_INDEX8);\n")
            if hasColor:
                f.write("GX_SetVtxDesc(GX_VA_CLR0, GX_INDEX8);\n")
        
        if hasVtx:
            f.write("GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_POS, GX_POS_XYZ, GX_F32, 0);\n")
        if hasNorm:
            f.write("GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_NRM, GX_NRM_XYZ, GX_F32, 0);\n")
        if hasUv:
            f.write("GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_TEX0, GX_TEX_ST, GX_F32, 0);\n")
        if hasColor:
            if hasColorAlpha:
                f.write("GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_CLR0, GX_CLR_RGBA, GX_RGBA8, 0);\n")
            else:
                f.write("GX_SetVtxAttrFmt(GX_VTXFMT0, GX_VA_CLR0, GX_CLR_RGB, GX_RGB8, 0);\n")
                
        f.write(f'GX_Begin(GX_TRIANGLES, GX_VTXFMT0, {num_faces});\n')
        f.write(f'for(size_t i = 0; i<{num_faces}; i++){{\n')
        if num_vert > 255:
            if hasVtx:
                f.write(f'\tGX_Position1x16(vtxArr[i]);\n')
            if hasNorm:
                f.write(f'\tGX_Normal1x16(vtxArr[i]);\n')
            if hasUv:
                f.write(f'\tGX_TexCoord1x16(vtxArr[i]);\n')
            if hasColor:
                f.write(f'\tGX_Color1x16(vtxArr[i]);\n')
        else:
            if hasVtx:
                f.write(f'\tGX_Position1x8(vtxArr[i]);\n')
            if hasNorm:
                f.write(f'\tGX_Normal1x8(vtxArr[i]);\n')
            if hasUv:
                f.write(f'\tGX_TexCoord1x8(vtxArr[i]);\n')
            if hasColor:
                f.write(f'\tGX_Color1x8(vtxArr[i]);\n')
            
        f.write('}\n')
        f.write('GX_End();\n')
        f.write('}\n')
    
    headerPath = PurePath(headerPath,f"draw_{objname}.h")
    print(f"Generating H file {headerPath} ...")
    with open(headerPath, "w") as f:
        f.write(f"#pragma once\n")
        f.write(f"void draw_{objname}(void);\n")    

def main():
    parser = argparse.ArgumentParser(description='PLYtoGX Converter')
    parser.add_argument('-b', default=".", help='Output path for binary blob')
    parser.add_argument('-s', default=".", help='Output path for generated C file')
    parser.add_argument('-e', default=".", help='Output path for generated H file')    
    parser.add_argument('FILE', help='PLY file to process')    

    args = parser.parse_args()
    print("PLYtoGX v1.0")
    process(args.FILE, args.b, args.s, args.e)

if __name__ == "__main__":
    main()
