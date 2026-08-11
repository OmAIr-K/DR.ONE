import bpy
import math
import os

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
    start_height = min(pos[2] for pos in takeoff_positions) - 10.0  # Slightly below the lowest drone
    end_height = max(pos[2] for pos in final_positions) + 10.0  # Slightly above the highest drone

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

# Parameters

speed = 4.0  # Speed of drones
duration = 100  # Duration of takeoff to vertex in frames
pause_duration = 200  # Frames to pause at vertex
radius = 150.0
camera_duration = 700  # Duration of the animation in frames
obj_name = os.environ.get("DRONE_TEST_OBJECT", "arabic_pot")


# Get the target object
obj = bpy.data.objects.get(obj_name)
if obj is None:
    raise ValueError(f"Object with name '{obj_name}' not found")

# Retrieve the number of drones from the object's vertices
num_drones = len(obj.data.vertices)
start_z = 0.0  # Initial Z position
 # Final Z position (1.5 times current height)

# Gather drone objects and their materials
drone_objects = [(bpy.data.objects[f"Drone_{i+1}"], bpy.data.objects[f"Drone_{i+1}"].data.materials) for i in range(num_drones)]

# Set the scene frame to 0 to ensure correct positions
bpy.context.scene.frame_set(0)

# Extract the takeoff positions from the drone objects
takeoff_positions = [drone[0].matrix_world.translation.copy() for drone in drone_objects]
# Get the vertex positions from the object
vertex_positions = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]

center_position = calculate_grid_center(takeoff_positions)
move_object_to_base(obj, takeoff_positions, center_position)
target_height = center_position[2] + obj.dimensions.z * 1.5 
animate_object_movement(obj, start_z, target_height, duration, speed, pause_duration)

# Create the camera with the updated parameters
create_camera_360_view(obj, radius, camera_duration, takeoff_positions, vertex_positions)
