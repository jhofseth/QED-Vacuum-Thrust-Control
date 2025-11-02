# extensions/unity_exporter.py
# This module provides scripts for exporting FreeCAD models (.fcstd) to Unity-compatible formats (e.g., OBJ)
# for VR threat modeling. It uses FreeCAD's Python API to load, process, and export models.
# Usage: python unity_exporter.py --input path/to/model.fcstd --output path/to/export.obj
# Requires FreeCAD installed and added to PYTHONPATH (e.g., sys.path.append('/usr/lib/freecad/lib')).

import sys
import argparse
import os

# Add FreeCAD to path (adjust based on installation)
freecad_path = '/usr/lib/freecad/lib'  # Example for Linux; change for Windows/Mac
if freecad_path not in sys.path:
    sys.path.append(freecad_path)

try:
    import FreeCAD
    import Mesh
except ImportError:
    print("Error: FreeCAD not found. Install FreeCAD and add to PYTHONPATH.")
    sys.exit(1)

def export_to_obj(input_fcstd, output_obj, part_name=None):
    """
    Export FreeCAD model to OBJ format.
    
    Parameters:
    input_fcstd (str): Path to .fcstd file
    output_obj (str): Path for exported .obj
    part_name (str, optional): Specific part to export; default all
    
    Returns:
    bool: Success status
    """
    try:
        # Open document
        doc = FreeCAD.openDocument(input_fcstd)
        
        # Get objects
        objects = doc.Objects if part_name is None else [doc.getObject(part_name)]
        if not objects:
            print(f"Error: No objects found or part '{part_name}' not found.")
            return False
        
        # Export as mesh to OBJ
        Mesh.export(objects, output_obj)
        
        print(f"Successfully exported to {output_obj}")
        FreeCAD.closeDocument(doc.Name)
        return True
    
    except Exception as e:
        print(f"Export failed: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Export FreeCAD models to OBJ for Unity VR threat modeling.")
    parser.add_argument("--input", type=str, required=True, help="Path to .fcstd file")
    parser.add_argument("--output", type=str, required=True, help="Path for exported .obj file")
    parser.add_argument("--part", type=str, default=None, help="Specific part name to export (optional)")
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)
    
    export_to_obj(args.input, args.output, args.part)

if __name__ == "__main__":
    main()
