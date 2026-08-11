"""
Legacy helper: append the night-sky background object into the open Blender scene.

Prefer the full pipeline via updated_render.py / pipeline_service.py.
"""

import os
import sys

import bpy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from definitions import BGD_OBJECT_NAME, bgd_path_for_blender


def append_bgd(bgd_filepath=None, object_name=BGD_OBJECT_NAME):
    bgd_filepath = bgd_filepath or bgd_path_for_blender()
    if not bgd_filepath:
        raise FileNotFoundError(
            "No background .blend found. Set DRONE_BGD_PATH or add a file under "
            "blender/assets/scenes/night_sky/."
        )
    bgd_filepath = str(bgd_filepath).replace("\\", "/")
    if not os.path.isfile(bgd_filepath):
        raise FileNotFoundError(f"Background blend not found: {bgd_filepath}")
    directory = bgd_filepath + "/Object/"
    bpy.ops.wm.append(
        filepath=directory + object_name,
        directory=directory,
        filename=object_name,
    )


if __name__ == "__main__":
    append_bgd()
