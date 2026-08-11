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
        return os.path.normpath(env_path)

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
    return None


def _discover_background(blend_dir: str) -> Optional[str]:
    """
    Resolve night-sky .blend path.

    Priority:
      1. DRONE_BGD_PATH env (absolute or repo-relative)
      2. First existing candidate under blender/assets/scenes/night_sky/
    """
    env_path = os.environ.get("DRONE_BGD_PATH", "").strip().strip('"')
    if env_path:
        if not os.path.isabs(env_path):
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), env_path)
        env_path = os.path.normpath(env_path)
        if os.path.isfile(env_path):
            return env_path

    night_sky = os.path.join(blend_dir, "assets", "scenes", "night_sky")
    candidates = [
        os.path.join(night_sky, "night_env1.blend"),
        os.path.join(night_sky, "night_env.blend"),
    ]
    # Also pick any other .blend in that folder (skip .blend1 backups)
    if os.path.isdir(night_sky):
        for name in sorted(os.listdir(night_sky)):
            if name.lower().endswith(".blend") and not name.lower().endswith(".blend1"):
                candidates.append(os.path.join(night_sky, name))

    seen = set()
    for path in candidates:
        path = os.path.normpath(path)
        if path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path):
            return path
    return None


# Project roots
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_DIR = os.path.join(ROOT_DIR, "blender")
RENDER_DIR = os.path.join(BLEND_DIR, "animations")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
INPUT_DIR = os.path.join(ROOT_DIR, "input")

# Blender executable — override with DRONE_BLENDER_PATH
BLENDER_EXECUTABLE = _discover_blender()

# Night-sky background — override with DRONE_BGD_PATH (no machine-specific hardcode)
BGD_BLEND_PATH = _discover_background(BLEND_DIR)

# Object name appended from the night-sky .blend library
BGD_OBJECT_NAME = os.environ.get("DRONE_BGD_OBJECT", "Water")


def bgd_path_for_blender() -> Optional[str]:
    """Forward-slash path suitable for Blender library append."""
    if not BGD_BLEND_PATH:
        return None
    return BGD_BLEND_PATH.replace("\\", "/")


def bgd_relative() -> Optional[str]:
    """Repo-relative path for logs / health (portable)."""
    if not BGD_BLEND_PATH:
        return None
    try:
        return os.path.relpath(BGD_BLEND_PATH, ROOT_DIR).replace("\\", "/")
    except ValueError:
        return BGD_BLEND_PATH.replace("\\", "/")


# SF3D / Blender scripts
RUN_SCRIPT = os.path.join(ROOT_DIR, "run.py")
BLENDER_SCRIPT = os.path.join(BLEND_DIR, "scripts", "updated_render.py")

# Ensure runtime directories exist
for _path in (OUTPUT_DIR, UPLOAD_DIR, RENDER_DIR, INPUT_DIR):
    os.makedirs(_path, exist_ok=True)
