import bpy

def remove_loose_parts(obj):
    """ Remove loose parts from the selected mesh object. """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete_loose()
    bpy.ops.object.mode_set(mode='OBJECT')

def decimate_mesh(obj, target_vertex_count):
    """ Reduce the number of vertices of the mesh to approximately the target_vertex_count. """
    # Calculate the desired ratio
    original_vertex_count = len(obj.data.vertices)
    target_ratio = target_vertex_count / original_vertex_count
    
    # Add and configure the Decimate modifier
    decimate_modifier = obj.modifiers.new(name='Decimate', type='DECIMATE')
    decimate_modifier.ratio = target_ratio
    
    # Apply the Decimate modifier
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier='Decimate')

def remesh_uniform(obj, voxel_size):
    """ Apply a Remesh modifier to distribute vertices uniformly using voxels. """
    # Add and configure the Remesh modifier
    remesh_modifier = obj.modifiers.new(name='Remesh', type='REMESH')
    remesh_modifier.mode = 'VOXEL'
    remesh_modifier.voxel_size = voxel_size
    
    # Apply the Remesh modifier
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier='Remesh')

def main(target_vertex_count, voxel_size):
    # Ensure we're in object mode and select the active object
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Iterate over all selected objects
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            remove_loose_parts(obj)
            decimate_mesh(obj, target_vertex_count)
            remesh_uniform(obj, voxel_size)
    
    # Recalculate normals for improved shading
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')

# Set your desired vertex count and voxel size here
target_vertex_count = 1000
voxel_size = 0.05  # Adjust the voxel size as needed

# Run the script
main(target_vertex_count, voxel_size)
