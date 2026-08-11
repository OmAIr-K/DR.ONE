import subprocess
import tkinter as tk
from tkinter import filedialog
import os

def run_instant_meshes(input_mesh, output_mesh, vertices_count, remesh_type):
    """
    Run Instant Meshes on the input_mesh to create a low-poly quad mesh and save it as output_mesh.
    
    Parameters:
    - input_mesh: Path to the input mesh file.
    - output_mesh: Path to save the output mesh file.
    - vertices_count: Desired vertex count for the output mesh.
    - remesh_type: Type of remeshing, e.g., 6 for quad (rosy=4, posy=4), 12 for triangle (rosy=6, posy=6).
    """
    # Construct the command for Instant Meshes
    command = [
        'InstantMeshes',
        input_mesh,
        '--output', output_mesh,
        '--vertices', str(vertices_count),
        '--rosy', str(remesh_type),  # Ensure quads are used
        '--posy', str(remesh_type),  # Ensure quads are used
        '--dominant'
    ]
    
    # Run the command
    subprocess.run(command, check=True)

def select_file():
    """
    Open a file dialog to select the input mesh file.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(title="Select Input Mesh File", filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")])
    return file_path

# Example usage
input_mesh = select_file()

if input_mesh:
    input_directory = os.path.dirname(input_mesh)  # Get the directory of the input file
    output_mesh = os.path.join(input_directory, "low_poly_model500.obj")  # Construct the output file path
    remesh_type = 4  # quad: (rosy, posy) -> (4, 4); triangle: (rosy, posy) -> (6, 6)
    vertices_count = 1000  # Adjust as needed
    
    run_instant_meshes(input_mesh, output_mesh, vertices_count, remesh_type)
else:
    print("No file selected.")
