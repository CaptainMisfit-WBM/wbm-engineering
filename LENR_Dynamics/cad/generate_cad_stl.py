#!/usr/bin/env python3
"""
================================================================================
CM-OFE 3D CAD STL MESH GENERATOR (generate_cad_stl.py)
================================================================================
Author: Digital Misfit / Captain Misfit (WBM Research)
Generates physical 3D STL binary CAD geometry for:
1. cmofe_reactor_cell.stl (Micro-capillary reaction vessel with cooling jacket)
2. cmofe_electrode_assembly.stl (2.4 THz SPP excitation electrode housing)
================================================================================
"""

import os
import math
import struct

def write_binary_stl(filename: str, header_str: str, triangles: list):
    """
    Writes a list of triangles to a binary STL file.
    Each triangle is ((nx, ny, nz), (v1x, v1y, v1z), (v2x, v2y, v2z), (v3x, v3y, v3z))
    """
    with open(filename, 'wb') as f:
        # 80-byte header
        header = header_str.encode('ascii')[:80].ljust(80, b'\0')
        f.write(header)
        
        # 4-byte triangle count
        f.write(struct.pack('<I', len(triangles)))
        
        # Write triangles
        for tri in triangles:
            norm, v1, v2, v3 = tri
            # Pack 12 floats + 1 uint16 (attribute byte count = 0)
            data = struct.pack(
                '<12fH',
                norm[0], norm[1], norm[2],
                v1[0], v1[1], v1[2],
                v2[0], v2[1], v2[2],
                v3[0], v3[1], v3[2],
                0
            )
            f.write(data)
    print(f"Generated STL mesh: {filename} ({len(triangles)} triangles, {os.path.getsize(filename)} bytes)")

def compute_normal(v1, v2, v3):
    ax, ay, az = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
    bx, by, bz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
    nx = ay*bz - az*by
    ny = az*bx - ax*bz
    nz = ax*by - ay*bx
    l = math.sqrt(nx*nx + ny*ny + nz*nz)
    if l > 1e-9:
        return (nx/l, ny/l, nz/l)
    return (0.0, 0.0, 1.0)

def generate_cylinder_mesh(radius: float, height: float, num_segments: int = 32, center_offset=(0,0,0)):
    """
    Generates a 3D cylinder mesh (top disc, bottom disc, side walls).
    """
    cx, cy, cz = center_offset
    triangles = []
    
    # Vertices for top and bottom circles
    top_verts = []
    bot_verts = []
    
    z_bot = cz - height / 2.0
    z_top = cz + height / 2.0
    
    for i in range(num_segments):
        theta = 2.0 * math.pi * i / num_segments
        x = cx + radius * math.cos(theta)
        y = cy + radius * math.sin(theta)
        top_verts.append((x, y, z_top))
        bot_verts.append((x, y, z_bot))
        
    top_center = (cx, cy, z_top)
    bot_center = (cx, cy, z_bot)
    
    for i in range(num_segments):
        i_next = (i + 1) % num_segments
        
        # Top disc
        v1, v2, v3 = top_center, top_verts[i], top_verts[i_next]
        triangles.append((compute_normal(v1, v2, v3), v1, v2, v3))
        
        # Bottom disc
        v1, v2, v3 = bot_center, bot_verts[i_next], bot_verts[i]
        triangles.append((compute_normal(v1, v2, v3), v1, v2, v3))
        
        # Side quad (2 triangles)
        # Tri 1
        v1, v2, v3 = bot_verts[i], top_verts[i], top_verts[i_next]
        triangles.append((compute_normal(v1, v2, v3), v1, v2, v3))
        
        # Tri 2
        v1, v2, v3 = bot_verts[i], top_verts[i_next], bot_verts[i_next]
        triangles.append((compute_normal(v1, v2, v3), v1, v2, v3))
        
    return triangles

def build_cmofe_reactor_cell_mesh():
    """
    Builds reaction chamber with outer cooling jacket (R=25mm, H=80mm)
    and central flange rings (R=35mm, H=10mm).
    """
    tris = []
    # Main outer body
    tris.extend(generate_cylinder_mesh(radius=25.0, height=80.0, num_segments=48, center_offset=(0,0,0)))
    # Top flange ring
    tris.extend(generate_cylinder_mesh(radius=35.0, height=10.0, num_segments=48, center_offset=(0,0,35.0)))
    # Bottom flange ring
    tris.extend(generate_cylinder_mesh(radius=35.0, height=10.0, num_segments=48, center_offset=(0,0,-35.0)))
    return tris

def build_cmofe_electrode_housing_mesh():
    """
    Builds 2.4 THz SPP electrode array mount housing (R=18mm, H=40mm).
    """
    tris = []
    # Base electrode housing
    tris.extend(generate_cylinder_mesh(radius=18.0, height=40.0, num_segments=36, center_offset=(0,0,0)))
    # Micro-strip coupler stem
    tris.extend(generate_cylinder_mesh(radius=8.0, height=20.0, num_segments=24, center_offset=(0,0,25.0)))
    return tris

if __name__ == "__main__":
    cad_dir = os.path.dirname(os.path.abspath(__file__))
    
    reactor_stl = os.path.join(cad_dir, "cmofe_reactor_cell.stl")
    electrode_stl = os.path.join(cad_dir, "cmofe_electrode_housing.stl")
    
    tris_reactor = build_cmofe_reactor_cell_mesh()
    write_binary_stl(reactor_stl, "CM-OFE Micro-Capillary Reaction Vessel CAD STL", tris_reactor)
    
    tris_electrode = build_cmofe_electrode_housing_mesh()
    write_binary_stl(electrode_stl, "CM-OFE 2.4 THz SPP Electrode Housing CAD STL", tris_electrode)
