import bpy
import math
import random
import os
from bpy_extras.io_utils import ImportHelper


def get_filepath(image_path):
    # Assume input_image_path is the path to the input image
      # Update with the correct input image path

    # Extract the name of the input image (without the extension)
    image_name = os.path.splitext(os.path.basename(image_path))[0]

    # Determine the current working directory
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Navigate upwards to find the root directory containing the 'output' folder
    root_directory = current_directory
    while not os.path.isdir(os.path.join(root_directory, 'output')):
        root_directory = os.path.dirname(root_directory)
        if root_directory == '/':
            raise Exception("Root directory with 'output' folder not found.")

    # Define the output folder path within the root directory
    output_folder = os.path.join(root_directory, 'output')

    # Create a new directory under the output folder with the name of the input image
    output_dir = os.path.join(output_folder, input_image_name)
    os.makedirs(output_dir, exist_ok=True)

    # Define the file path for the 3D model inside the newly created directory
    filepath = os.path.join(output_dir, '3dmodel.obj')  # Update with the correct 3D model filename
    
    return filepath



class ImportObjectOperator(bpy.types.Operator, ImportHelper):
    """Operator to open a file browser and import a 3D object"""
    bl_idname = "import_scene.import_object"  # Unique identifier for buttons and menu items to reference
    bl_label = "Import 3D Object"  # Display name in the interface

    # ImportHelper mixin class uses this to define the filename and other properties
    filename_ext = ".obj;.fbx;.glb;.gltf"  # Supported file extensions

    filter_glob: bpy.props.StringProperty(
        default="*.obj;*.fbx;*.glb;*.gltf",
        options={'HIDDEN'},
    )

    def execute(self, context):
        filepath = self.filepath

        # Call the import_object function to import the selected file
        imported_object = import_object(filepath)

        if imported_object is None:
            self.report({'ERROR'}, f"Failed to import object from {filepath}")
            return {'CANCELLED'}

        # Perform any additional operations like reducing vertices, etc.
        reduce_vertex(imported_object, max_vertices=1000, merge_distance=0.01)

        # Return success
        return {'FINISHED'}


def import_object(filepath):
    """
    Import an object from a given file path.
    
    :param filepath: The file path to the 3D model
    :return: The imported object
    """
    imported_object = None
    
    if filepath.endswith('.obj'):
        bpy.ops.wm.obj_import(filepath=filepath)
    elif filepath.endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif filepath.endswith('.glb') or filepath.endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=filepath)
    else:
        raise ValueError("Unsupported file format")
    
    imported_object = bpy.context.selected_objects[-1]
    
    return imported_object


def remove_loose_parts(obj):
    """ Remove loose parts from the selected mesh object. """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete_loose()
    bpy.ops.object.mode_set(mode='OBJECT')

def decimate_mesh(obj):
    """ Reduce the number of vertices of the mesh to approximately the target_vertex_count. """
    # Calculate the desired ratio
#    original_vertex_count = len(obj.data.vertices)
#    target_ratio = target_vertex_count / original_vertex_count
    
    # Add and configure the Decimate modifier
    decimate_modifier = obj.modifiers.new(name='Decimate', type='DECIMATE')
    decimate_modifier.ratio = 0.2
    
     # Enable symmetry on all axes
    decimate_modifier.use_symmetry = True
    decimate_modifier.symmetry_axis = 'X'  # Set symmetry axis to X
    # decimate_modifier.symmetry_axis = 'Y'  # Uncomment for Y symmetry
    # decimate_modifier.symmetry_axis = 'Z'  # Uncomment for Z symmetry
    
    # Enable triangulation
    decimate_modifier.use_collapse_triangulate = True
    
    # Apply the Decimate modifier
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier='Decimate')
    
def merge_by_distance(obj, distance=0.01):
    """
    Merges vertices in the given object that are within a certain distance of each other.
    
    Parameters:
    - obj: The mesh object to apply the merge operation on.
    - distance: The distance threshold for merging vertices. Default is 0.0001.
    """
    # Ensure the object is selected and active
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')  # Switch to Edit mode
    
    # Select all vertices
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Perform the merge by distance
    #bpy.ops.mesh.merge(type='BY_DISTANCE', threshold=distance)
    bpy.ops.mesh.remove_doubles(threshold=distance)
    
    
    # Switch back to Object mode
    bpy.ops.object.mode_set(mode='OBJECT')


def check_vertex_count(obj, max_vertices):
    """ Check the number of vertices in the selected object.
        Used for making sure to keep reducing vertices until count is less than 1000 """
        
    obj_vertex_count = len(obj.data.vertices)
    if (obj_vertex_count > max_vertices):
        return True
    else:
        return False
    
def reduce_vertex(obj,max_vertices, distance):
    
    # Ensure we're in object mode and select the active object
    bpy.ops.object.mode_set(mode='OBJECT')
    if obj.type == 'MESH':
        while(check_vertex_count(obj, max_vertices)):
            remove_loose_parts(obj)
            decimate_mesh(obj)
            remove_loose_parts(obj)
            merge_by_distance(obj, distance)
            remove_loose_parts(obj)
        # Recalculate normals for improved shading    
        while(check_vertex_count(obj, max_vertices)):
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
           
def create_glowing_sphere(location, radius=1, glow_color=(1, 1, 1), emission_strength=5):
    """
    Create a sphere with a glowing effect in Blender.

    :param location: The location of the sphere (x, y, z)
    :param radius: The radius of the sphere
    :param glow_color: The initial color of the glow (R, G, B)
    :param emission_strength: The strength of the emission (glow effect)
    :return: The created sphere object
    """
    # Create a UV sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    sphere = bpy.context.active_object

    # Create a new material with an emission shader
    mat = bpy.data.materials.new(name="GlowMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()

    # Add Emission shader node
    emission_node = nodes.new(type='ShaderNodeEmission')
    emission_node.inputs['Color'].default_value = (*glow_color, 1)  # Set color
    emission_node.inputs['Strength'].default_value = emission_strength  # Set emission strength

    # Add Material Output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')

    # Link the emission node to the output node
    links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])

    # Assign the material to the sphere
    sphere.data.materials.append(mat)

    return sphere, mat


def animate_rgb_flicker(material, start_frame, end_frame, flicker_speed=20):
    """
    Animate the emission color to create a randomized RGB flickering effect.

    :param material: The material to animate
    :param start_frame: The frame to start the flicker animation
    :param end_frame: The frame to end the flicker animation
    :param flicker_speed: The base frequency of color change
    """
    emission_node = material.node_tree.nodes['Emission']
    
    current_frame = start_frame

    while current_frame < end_frame:
        # Randomize flicker timing and color
        random_flicker_frame = current_frame + random.randint(0, flicker_speed)
        random_color = (
            random.uniform(0, 1),  # Random red component
            random.uniform(0, 1),  # Random green component
            random.uniform(0, 1)   # Random blue component
        )
        
        # Set the random color to the emission node
        emission_node.inputs['Color'].default_value = (*random_color, 1)
        
        # Insert a keyframe for the color at the randomized frame
        emission_node.inputs['Color'].keyframe_insert(data_path="default_value", frame=random_flicker_frame)
        
        # Move to the next flicker frame
        current_frame += random.randint(flicker_speed // 2, flicker_speed)




def create_drone_grid(num_drones, spacing, start_position=(0, 0, 0)):
    """
    Create a grid of glowing sphere drone objects in Blender.

    :param num_drones: Number of drones to create
    :param spacing: Distance between drones in the grid
    :param start_position: Starting position of the grid (x, y, z)
    :return: List of created drone objects
    """
    grid_size = math.ceil(math.sqrt(num_drones))  # Create a square grid
    drone_objects = []
    start_positions = []
    for i in range(num_drones):
        x = start_position[0] + (i % grid_size) * spacing
        y = start_position[1] + (i // grid_size) * spacing
        z = start_position[2]
        start_positions.append((x, y, z))

        # Create a glowing sphere at the calculated position
        sphere, mat = create_glowing_sphere(location=(x, y, z), radius=0.2, glow_color=(0.2, 0.8, 1), emission_strength=20)
        sphere.name = f"Drone_{i+1}"

        drone_objects.append((sphere, mat))

    return drone_objects, start_positions


def assign_drones_to_vertices(obj, num_drones):
    """ Assign drones to the vertices of the object """
    #obj = bpy.data.objects[object_name]
    vertices = obj.data.vertices
    vertex_count = len(vertices)
    vertex_positions = [obj.matrix_world @ vertex.co for vertex in vertices]
    assignments = {}
    for i in range(num_drones):
        vertex_index = i % vertex_count
        assignments[i] = vertex_positions[vertex_index]
    
    return assignments

def calculate_grid_center(drone_positions):
    """
    Calculate the center of the grid based on drone positions.

    :param drone_objects: A list of tuples representing the positions of drones.
    :return: A tuple representing the center of the grid.
    """
    
    num_drones = len(drone_positions)
    if num_drones == 0:
        return (0.0, 0.0, 0.0)
    
    # Sum all positions
    sum_x = sum(pos[0] for pos in drone_positions)
    sum_y = sum(pos[1] for pos in drone_positions)
    sum_z = sum(pos[2] for pos in drone_positions)
    
    # Calculate the center
    center_x = sum_x / num_drones
    center_y = sum_y / num_drones
    center_z = sum_z / num_drones
    
    return (center_x, center_y, center_z)

def move_object_to_grid_center(obj, drone_positions):
    """
    Move the selected object to the center of the drone grid.

    :param obj: The object to move. 
    """
    
    # Calculate the center of the grid
    center_position = calculate_grid_center(drone_positions)
    
    obj_dimensions = obj.dimensions
    obj_height = obj_dimensions.z  # Height of the object along the Z axis
    
    # Offset the Z position by the object's height and the clearance space
    new_center_position = (
        center_position[0],  # X component
        center_position[1],  # Y component
        center_position[2] + obj_height*1.5 # Z component with offset
    ) 
    
    # Set the object's location to the center of the drone grid
    obj.location = new_center_position

def create_drone_flight_paths(drones, takeoff_positions, vertex_positions, speed, duration, pause_duration):
    """ Create flight paths for drones """
    for i, (drone, mat) in enumerate(drones):
        drone.location = takeoff_positions[i]
        drone.keyframe_insert(data_path="location", frame=0)
        
        end_frame = int(duration * (speed // 2))
        drone.location = vertex_positions[i]
        drone.keyframe_insert(data_path="location", frame=end_frame)
        
        bpy.context.scene.frame_set(end_frame + pause_duration)
        drone.keyframe_insert(data_path="location", frame=end_frame + pause_duration)
        
        return_frame = end_frame + pause_duration + duration
        drone.location = takeoff_positions[i]
        drone.keyframe_insert(data_path="location", frame=return_frame)
        
        animate_rgb_flicker(mat, start_frame=0, end_frame=return_frame, flicker_speed=20)

def create_camera_360_view(obj, radius, duration):
    """
    Creates a camera that orbits around the object for a 360-degree view.

    :param obj: The object around which the camera will orbit.
    :param radius: The radius of the camera's orbit.
    :param duration: The duration of the 360-degree rotation in frames.
    """
    # Create a new camera
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "360_Camera"

    # Position the camera at the starting location
    camera.location = (radius, 0, obj.location.z + 0.5 * obj.dimensions.z)
    
    # Set the camera to point at the object
    constraint = camera.constraints.new(type='TRACK_TO')
    constraint.target = obj
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    
    # Insert keyframes for the camera's rotation around the object
    for frame in range(0, duration + 1):
        angle = 2 * math.pi * frame / duration  # Calculate the angle for this frame
        camera.location.x = radius * math.cos(angle)
        camera.location.y = radius * math.sin(angle)
        
        # Insert a keyframe for the camera's location
        camera.keyframe_insert(data_path="location", frame=frame)
    
    # Ensure linear interpolation for smooth movement
    for fcurve in camera.animation_data.action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = 'LINEAR'



# Parameters
#num_drones = 500
max_vertices = 1000
merge_distance = 0.01
spacing = 3.0
start_position = (0, 0, 0)
speed = 4.0  # Speed of drones
duration = 100  # Duration of takeoff to vertex in frames
pause_duration = 200  # Frames to pause at vertex
scale_factor = (50.0,50.0,50.0)
camera_radius = 100.0 
#object_name = 'arabic_pot'

image_path = ""
# Legacy experiment script — pass mesh/output via env or edit these relatives.
filepath = os.environ.get(
    "DRONE_TEST_MESH",
    os.path.join(os.path.dirname(__file__), "..", "models", "plane_redc.obj"),
)
output_filepath = os.environ.get(
    "DRONE_TEST_OUTPUT",
    os.path.join(os.path.dirname(__file__), "..", "animations", "test_export.gltf"),
)
obj = import_object(filepath)

if obj == None:
    raise Exception(" 'None' type object returned. 3D Object at 'filepath' not found.")

bpy.ops.object.mode_set(mode='OBJECT')

for object in bpy.data.objects:
    if object == obj:
        continue  # Skip the imported object
    
    if object.animation_data:  # Check if the object has animation data
        object.animation_data_clear() 
    for material in bpy.data.materials:
        if material.animation_data:
            material.animation_data_clear()

    for action in bpy.data.actions:
        bpy.data.actions.remove(action)
        

reduce_vertex(obj, max_vertices, merge_distance)
vertices = obj.data.vertices
num_drones = len(vertices)
obj.scale = scale_factor
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Create the drone grid with glowing spheres
drone_objects, takeoff_positions = create_drone_grid(num_drones, spacing, start_position)
bpy.context.scene.frame_set(0)

bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

move_object_to_grid_center(obj, takeoff_positions)   
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Assign drones to vertices of the object (Assuming object is named 'jet_plane_redc2')
vertex_positions = assign_drones_to_vertices(obj, num_drones)

# Create the flight paths
create_drone_flight_paths(drone_objects, takeoff_positions, vertex_positions, speed, duration, pause_duration)

## Play animation
#bpy.context.scene.frame_start = 0
#bpy.context.scene.frame_end = duration + pause_duration + 100  # Add extra frames for landing, if needed
#bpy.ops.screen.animation_play()


# Hide the imported object from the final render
obj.hide_viewport = True
obj.hide_render = True

animation_time = duration + pause_duration + 100
# Create the camera and animate it to provide a 360-degree view
create_camera_360_view(obj, camera_radius, animation_time)

# Export the scene as a GLTF file
bpy.ops.export_scene.gltf(filepath=output_filepath, export_format='GLB')