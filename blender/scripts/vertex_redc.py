import bpy
import sys

def load_model(filepath):
    # Import the model (assuming it's an OBJ file; adjust if needed)
    bpy.ops.import_scene.obj(filepath=filepath)

def reduce_vertices(obj, distance):
    # Select the object and enter edit mode
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Select all geometry
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Merge vertices by distance
    bpy.ops.mesh.remove_doubles(threshold=distance)
    
    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

def save_model(filepath):
    # Export the modified model (assuming OBJ format; adjust if needed)
    bpy.ops.export_scene.obj(filepath=filepath)

def main(model_path, output_path, distance):
    # Clear existing objects
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()
    
    # Load, process, and save the model
    load_model(model_path)
    obj = bpy.context.selected_objects[0]  # Assumes the model is the only selected object
    reduce_vertices(obj, distance)
    save_model(output_path)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: blender -b -P script.py -- <model_path> <output_path> <distance>")
        sys.exit(1)

    model_path = sys.argv[1]
    output_path = sys.argv[2]
    distance = float(sys.argv[3])
    
    main(model_path, output_path, distance)
