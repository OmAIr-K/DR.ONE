"""
CLI entry point: select an image via dialog and run the full pipeline.
Prefer the web UI (`npm run dev` + `uvicorn server:app`) for interactive use.
"""

from __future__ import annotations

import os
import sys

from tkinter import Tk, filedialog

from definitions import RENDER_DIR
from pipeline_service import run_full_pipeline


def select_image() -> str:
    root = Tk()
    root.withdraw()
    root.update()
    file_path = filedialog.askopenfilename(
        title="Select an Image",
        filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.webp")],
    )
    root.destroy()
    return file_path


def main() -> int:
    input_image_path = select_image()
    if not input_image_path:
        print("No file selected.")
        return 1

    print(f"Selected Image: {input_image_path}")
    result = run_full_pipeline(input_image_path)
    if result.status.value != "completed":
        print(f"Pipeline failed: {result.error}")
        return 1

    video_path = result.video_path or os.path.join(
        RENDER_DIR, result.image_name, f"{result.image_name}.mp4"
    )
    print(f"Video ready: {video_path}")
    try:
        os.startfile(video_path)  # type: ignore[attr-defined]
    except Exception as exc:
        print(f"Could not open video automatically: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
