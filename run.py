import argparse
import os

import rembg
import torch
from PIL import Image
from tqdm import tqdm

from sf3d.system import SF3D
from sf3d.utils import remove_background, resize_foreground

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "image", type=str, nargs="+", help="Path to input image(s) or folder."
    )
    parser.add_argument(
        "--device",
        default="cuda:0",
        type=str,
        help="Device to use. If no CUDA-compatible device is found, the baking will fail. Default: 'cuda:0'",
    )
    parser.add_argument(
        "--pretrained-model",
        default="stabilityai/stable-fast-3d",
        type=str,
        help="Path to the pretrained model. Could be either a huggingface model id is or a local path. Default: 'stabilityai/stable-fast-3d'",
    )
    parser.add_argument(
        "--foreground-ratio",
        default=0.85,
        type=float,
        help="Ratio of the foreground size to the image size. Only used when --no-remove-bg is not specified. Default: 0.85",
    )
    parser.add_argument(
        "--output-dir",
        default="output/",
        type=str,
        help="Output directory to save the results. Default: 'output/'",
    )
    parser.add_argument(
        "--texture-resolution",
        default=1024,
        type=int,
        help="Texture atlas resolution. Default: 1024",
    )
    parser.add_argument(
        "--remesh_option",
        choices=["none", "triangle", "quad"],
        default="none",
        help="Remeshing option",
    )
    parser.add_argument(
        "--batch_size", default=1, type=int, help="Batch size for inference"
    )
    args = parser.parse_args()

    # Ensure args.device contains cuda
    if "cuda" not in args.device:
        raise ValueError(
            "CUDA device is required for baking and hence running the method."
        )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available. Stable Fast 3D requires a CUDA-capable GPU "
            "for texture baking."
        )

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    device = args.device
    model = SF3D.from_pretrained(
        args.pretrained_model,
        config_name="config.yaml",
        weight_name="model.safetensors",
    )
    model.to(device)
    model.eval()

    rembg_session = rembg.new_session()
    images = []
    output_names = []

    def handle_image(image_path, output_folder_name):
        image = remove_background(
            Image.open(image_path).convert("RGBA"), rembg_session
        )
        image = resize_foreground(image, args.foreground_ratio)

        os.makedirs(os.path.join(output_dir, output_folder_name), exist_ok=True)
        image.save(
            os.path.join(output_dir, output_folder_name, output_folder_name + ".png")
        )
        images.append(image)
        output_names.append(output_folder_name)

    for image_path in args.image:
        if os.path.isdir(image_path):
            image_paths = [
                os.path.join(image_path, f)
                for f in os.listdir(image_path)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
            ]
            for nested_path in image_paths:
                image_name = os.path.basename(nested_path)
                output_folder_name = os.path.splitext(image_name)[0]
                handle_image(nested_path, output_folder_name)
        else:
            image_name = os.path.basename(image_path)
            output_folder_name = os.path.splitext(image_name)[0]
            handle_image(image_path, output_folder_name)

    if not images:
        raise FileNotFoundError("No valid input images found.")

    for i in tqdm(range(0, len(images), args.batch_size)):
        batch_images = images[i : i + args.batch_size]
        batch_names = output_names[i : i + args.batch_size]
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                mesh, glob_dict = model.run_image(
                    batch_images,
                    bake_resolution=args.texture_resolution,
                    remesh=args.remesh_option,
                )
        print("Peak Memory:", torch.cuda.max_memory_allocated() / 1024 / 1024, "MB")

        if len(batch_images) == 1:
            out_mesh_path = os.path.join(output_dir, batch_names[0], "mesh.glb")
            mesh.export(out_mesh_path, include_normals=True)
        else:
            for j in range(len(mesh)):
                out_mesh_path = os.path.join(output_dir, batch_names[j], "mesh.glb")
                mesh[j].export(out_mesh_path, include_normals=True)
