# extensions/unity_exporter.py
# This module provides scripts for exporting FreeCAD models (.fcstd) to Unity-compatible formats (e.g., OBJ)
# for VR threat modeling. It uses FreeCAD's Python API to load, process, and export models.
# Usage: python unity_exporter.py --input path/to/model.fcstd --output path/to/export.obj
# Requires FreeCAD installed and added to PYTHONPATH (e.g., sys.path.append('/usr/lib/freecad/lib')).

import sys
import argparse
import os
import platform

# Add FreeCAD to path (adjust based on installation and platform)
def get_freecad_path():
    """Determine FreeCAD library path based on platform."""
    system = platform.system()
    if system == "Linux":
        return '/usr/lib/freecad/lib'
    elif system == "Windows":
        # Common Windows installation paths
        possible_paths = [
            'C:/Program Files/FreeCAD 0.21/bin',
            'C:/Program Files/FreeCAD/bin',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    elif system == "Darwin":  # macOS
        return '/Applications/FreeCAD.app/Contents/Resources/lib'
    return None

freecad_path = get_freecad_path()
if freecad_path and freecad_path not in sys.path:
    sys.path.append(freecad_path)

try:
    import FreeCAD
    import Mesh
except ImportError as e:
    print("Error: FreeCAD not found. Install FreeCAD and add to PYTHONPATH.")
    print(f"Tried path: {freecad_path}")
    print(f"Import error: {e}")
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
    doc = None
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_obj)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Open document
        doc = FreeCAD.openDocument(input_fcstd)
        
        # Get objects
        if part_name is None:
            objects = doc.Objects
        else:
            obj = doc.getObject(part_name)
            if obj is None:
                print(f"Error: Part '{part_name}' not found in document.")
                print(f"Available objects: {[o.Name for o in doc.Objects]}")
                return False
            objects = [obj]
        
        if not objects:
            print("Error: No objects found in document.")
            return False
        
        # Filter to only mesh-exportable objects
        exportable_objects = [obj for obj in objects if hasattr(obj, 'Shape')]
        
        if not exportable_objects:
            print("Error: No exportable objects with Shape attribute found.")
            return False
        
        # Export as mesh to OBJ
        Mesh.export(exportable_objects, output_obj)
        
        print(f"Successfully exported {len(exportable_objects)} object(s) to {output_obj}")
        return True
    
    except Exception as e:
        print(f"Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure document is closed even if export fails
        if doc is not None:
            try:
                FreeCAD.closeDocument(doc.Name)
            except Exception as e:
                print(f"Warning: Could not close document: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Export FreeCAD models to OBJ for Unity VR threat modeling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python unity_exporter.py --input model.fcstd --output model.obj
  python unity_exporter.py --input model.fcstd --output model.obj --part "Body"
        """
    )
    parser.add_argument("--input", type=str, required=True, help="Path to .fcstd file")
    parser.add_argument("--output", type=str, required=True, help="Path for exported .obj file")
    parser.add_argument("--part", type=str, default=None, help="Specific part name to export (optional)")
    
    args = parser.parse_args()
    
    # Validate input path
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        sys.exit(1)
    
    # Validate input file extension
    if not args.input.lower().endswith('.fcstd'):
        print(f"Warning: Input file {args.input} does not have .fcstd extension.")
    
    # Validate output file extension
    if not args.output.lower().endswith('.obj'):
        print(f"Warning: Output file {args.output} does not have .obj extension.")
    
    # Perform export
    success = export_to_obj(args.input, args.output, args.part)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
