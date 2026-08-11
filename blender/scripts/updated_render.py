import bpy
import math
import random
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from definitions import (
    BGD_OBJECT_NAME,
    OUTPUT_DIR,
    RENDER_DIR,
    bgd_path_for_blender,
)


def parse_args():
    """Parse args after Blender's `--` separator."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    default_bgd = bgd_path_for_blender()
    args = {
        "input_image": None,
        "mesh_path": None,
        "bgd_path": default_bgd,
        "bgd_object": BGD_OBJECT_NAME,
        "render_name": None,
    }

    flag_map = {
        "--input_image": "input_image",
        "--mesh_path": "mesh_path",
        "--bgd_path": "bgd_path",
        "--bgd_object": "bgd_object",
        "--render_name": "render_name",
    }

    i = 0
    while i < len(argv):
        key = argv[i]
        if key in flag_map and i + 1 < len(argv):
            args[flag_map[key]] = argv[i + 1]
            i += 2
        else:
            i += 1

    return args


def find_mesh_file(input_image_path, mesh_path=None):
    if mesh_path:
        if not os.path.isfile(mesh_path):
            raise FileNotFoundError(f"Mesh not found: {mesh_path}")
        return mesh_path

    if not input_image_path:
        raise ValueError("Either --mesh_path or --input_image is required.")

    output_folder_name = os.path.splitext(os.path.basename(input_image_path))[0]
    mesh_filepath = os.path.join(OUTPUT_DIR, output_folder_name, "mesh.glb")
    if not os.path.isfile(mesh_filepath):
        raise FileNotFoundError(f"Expected mesh not found at {mesh_filepath}")
    return mesh_filepath


def clear_scene():
    bpy.ops.object.select_all(action='DESELECT')

    # Select all objects in the scene
    bpy.ops.object.select_all(action='SELECT')

    # Delete all selected objects
    bpy.ops.object.delete()

    # Optionally, clear all collections as well
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)

def import_object(filepath):
    """
    Import an object from a given file path.
    
    :param filepath: The file path to the 3D model
    :return: The imported object
    """
    imported_object = None
    try:

        if filepath.endswith('.obj'):
            bpy.ops.wm.obj_import(filepath=filepath)
        elif filepath.endswith('.fbx'):
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif filepath.endswith('.glb') or filepath.endswith('.gltf'):
            bpy.ops.import_scene.gltf(filepath=filepath)
        else:
            raise ValueError("Unsupported file format")
    except Exception as exc:
        raise FileNotFoundError(f"File not found at {filepath}") from exc
    
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
           
def create_glowing_sphere(location, radius=1, glow_color=(1, 1, 1), emission_strength=10):
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
        sphere, mat = create_glowing_sphere(location=(x, y, z), radius=0.2, glow_color=(0.2, 0.8, 1), emission_strength=10)
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
        
        #animate_rgb_flicker(mat, start_frame=0, end_frame=return_frame, flicker_speed=20)

def move_object_to_base(obj, drone_positions, center_position):
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
        center_position[2]   # Z component
    ) 
    
    # Set the object's location to the center of the drone grid
    obj.location = new_center_position
    return center_position

def create_camera_360_view(obj, radius, duration, takeoff_positions, final_positions):
    """
    Creates a camera that orbits around the grid center for a 360-degree view,
    starting from a downward perspective on the drones' takeoff positions and 
    gradually focusing on the object as the drones move.

    :param obj: The target object the camera will eventually focus on.
    :param radius: The radius of the camera's orbit.
    :param duration: The duration of the 360-degree rotation in frames.
    :param takeoff_positions: The initial positions of the drones on the grid.
    :param final_positions: The final positions of the drones forming the object shape.
    """
    

    # Calculate the center of the drone grid
    grid_center =  calculate_grid_center(takeoff_positions)

    # Calculate the center height at the beginning and end of the animation
    start_height = min(pos[2] for pos in takeoff_positions) + 10.0  # Slightly below the lowest drone
    end_height = max(pos[2] for pos in final_positions.values()) + 10.0  # Slightly above the highest drone

    # Create a new camera
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "360_Camera"

    # Set the initial position of the camera
    camera.location = (grid_center[0] + radius, grid_center[1], start_height)

    # Add a constraint to keep the camera pointed at the object
    constraint = camera.constraints.new(type='TRACK_TO')
    constraint.target = obj
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    # Insert keyframes for the camera's orbit and vertical movement
    for frame in range(0, duration + 1):
        # Calculate the angle for this frame (for orbiting)
        angle = 2 * math.pi * frame / duration
        
        # Update camera's horizontal location (orbit)
        camera.location.x = grid_center[0] + radius * math.cos(angle)
        camera.location.y = grid_center[1] + radius * math.sin(angle)
        
        # Move the camera's vertical location from start_height to end_height
        camera.location.z = start_height + (end_height - start_height) * (frame / duration)

        # Insert keyframe for the camera's location
        camera.keyframe_insert(data_path="location", frame=frame)

        # Optional: Adjust the camera's rotation to look at the object
        # This may help create a more dynamic effect
        camera.rotation_euler[0] = math.radians(45)  # Look slightly down at the start
        camera.rotation_euler[2] = angle  # Adjust rotation based on the angle

        # Insert keyframe for the camera's rotation
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Ensure linear interpolation for smooth movement
    for fcurve in camera.animation_data.action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = 'LINEAR'
            
            
def animate_object_movement(obj, start_z, target_height, duration, speed, pause_duration):
    """
    Animates the movement of the object in the Z direction from start_z to target_height.

    :param obj: The target object to animate.
    :param start_z: The starting Z location of the object.
    :param target_height: The target Z height for the object.
    :param duration: The duration of the animation in frames.
    :param speed: The speed at which the object should move.
    """
    # Set the initial Z position
    obj.location.z = start_z
    obj.keyframe_insert(data_path="location", frame=0)
    
    
    # Set the final Z position
    end_frame = int(duration * (speed // 2))
    obj.location.z = target_height
    obj.keyframe_insert(data_path="location", frame=end_frame)
    
    bpy.context.scene.frame_set(end_frame + pause_duration)
    obj.keyframe_insert(data_path="location", frame=end_frame + pause_duration)
    
    
    return_frame = end_frame + pause_duration + duration
    obj.location.z = start_z
    obj.keyframe_insert(data_path="location", frame=return_frame)

    # Calculate the final Z position based on speed
    # The target height moves upwards according to the speed over the duration
    #final_z = start_z + speed * (duration / 24)  # Assume 24 FPS for duration

    # Ensure linear interpolation for smooth movement
    for fcurve in obj.animation_data.action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = 'LINEAR'
            
def append_bgd(bgd_filepath, object_name=BGD_OBJECT_NAME):
    if not bgd_filepath:
        print("No background path provided; skipping night-sky append.")
        return
    bgd_filepath = str(bgd_filepath).replace("\\", "/")
    if not os.path.isfile(bgd_filepath):
        raise FileNotFoundError(f"Background blend not found: {bgd_filepath}")
    directory = bgd_filepath + "/Object/"
    bpy.ops.wm.append(
        filepath=directory + object_name,
        directory=directory,
        filename=object_name,
    )
    
    
def render_video(render_filepath):
    # Set render settings
    bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
    bpy.context.scene.render.ffmpeg.format = 'MPEG4'
    bpy.context.scene.render.ffmpeg.codec = 'H264'
    bpy.context.scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    bpy.context.scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
    bpy.context.scene.render.filepath = render_filepath + '.mp4'

    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = duration + pause_duration + 200  # Add extra frames for landing, if needed

    # Render the animation to the specified file
    bpy.ops.render.render(animation=True, write_still=False)
    scene_filepath = render_filepath + '.gltf' #Change this according to the export format.
    # Export the scene as a GLTF file
    bpy.ops.export_scene.gltf(filepath=scene_filepath, export_format='GLB')
    


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
radius = 150.0
camera_duration = 700  # Duration of the animation in frames
start_z = 0.0  # Initial Z position
cli = parse_args()
input_image_path = cli["input_image"]
mesh_filepath = find_mesh_file(input_image_path, cli["mesh_path"])
clear_scene()
obj = import_object(mesh_filepath)

if obj is None:
    raise Exception(f"3D object not found at '{mesh_filepath}'.")

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

center_position = calculate_grid_center(takeoff_positions)
move_object_to_base(obj, takeoff_positions, center_position)
target_height = center_position[2] + obj.dimensions.z * 1.5 
animate_object_movement(obj, start_z, target_height, duration, speed, pause_duration)

# Create the camera with the updated parameters
create_camera_360_view(obj, radius, camera_duration, takeoff_positions, vertex_positions)

bpy.context.scene.camera = bpy.data.objects['360_Camera']

if cli["bgd_path"]:
    append_bgd(cli["bgd_path"], cli["bgd_object"])
else:
    print("Skipping background append (DRONE_BGD_PATH / night_sky asset not set).")

# Render Video
if cli["render_name"]:
    render_video_name = cli["render_name"]
elif input_image_path:
    render_video_name = os.path.splitext(os.path.basename(input_image_path))[0]
else:
    render_video_name = os.path.splitext(os.path.basename(mesh_filepath))[0]

render_path = os.path.join(RENDER_DIR, render_video_name)
os.makedirs(render_path, exist_ok=True)
render_filepath = os.path.join(render_path, render_video_name)

render_video(render_filepath)

