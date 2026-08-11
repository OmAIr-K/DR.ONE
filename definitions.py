import os
import shutil
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass


def _discover_blender() -> Optional[str]:
    """Resolve Blender executable from env, PATH, or common install locations."""
    env_path = os.environ.get("DRONE_BLENDER_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    which = shutil.which("blender")
    if which:
        return which

    candidates = [
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]


# Project roots
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_DIR = os.path.join(ROOT_DIR, "blender")
RENDER_DIR = os.path.join(BLEND_DIR, "animations")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
INPUT_DIR = os.path.join(ROOT_DIR, "input")

# Blender executable — override with DRONE_BLENDER_PATH
BLENDER_EXECUTABLE = _discover_blender()

# Night-sky background used by the drone visualization
BGD_BLEND_PATH = os.path.join(
    BLEND_DIR, "assets", "scenes", "night_sky", "night_env1.blend"
).replace("\\", "/")

# Object name appended from the night-sky .blend library
BGD_OBJECT_NAME = os.environ.get("DRONE_BGD_OBJECT", "Water")

# SF3D / Blender scripts
RUN_SCRIPT = os.path.join(ROOT_DIR, "run.py")
BLENDER_SCRIPT = os.path.join(BLEND_DIR, "scripts", "updated_render.py")

# Ensure runtime directories exist
for _path in (OUTPUT_DIR, UPLOAD_DIR, RENDER_DIR, INPUT_DIR):
    os.makedirs(_path, exist_ok=True)
