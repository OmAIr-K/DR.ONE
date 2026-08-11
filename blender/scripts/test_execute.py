"""
Dev helper: print where a rendered video would be written for an input image.

Usage (from repo root, or with Blender --python):
  python blender/scripts/test_execute.py [image_name]
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from definitions import INPUT_DIR, RENDER_DIR

image_name = sys.argv[1] if len(sys.argv) > 1 else "car.png"
input_image_path = (
    image_name
    if os.path.isabs(image_name) or os.path.sep in image_name
    else os.path.join(INPUT_DIR, image_name)
)
render_video_name = os.path.splitext(os.path.basename(input_image_path))[0]
os.makedirs(os.path.join(RENDER_DIR, render_video_name), exist_ok=True)
render_path = os.path.join(RENDER_DIR, render_video_name, f"{render_video_name}.mp4")
print(render_path)
