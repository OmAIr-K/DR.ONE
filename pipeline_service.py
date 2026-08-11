"""
Shared image → SF3D mesh → Blender drone visualization pipeline.

Used by the FastAPI server and can also replace the Tkinter flow in
executable_pipeline.py.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from definitions import (
    BGD_BLEND_PATH,
    BGD_OBJECT_NAME,
    BLENDER_EXECUTABLE,
    BLENDER_SCRIPT,
    OUTPUT_DIR,
    RENDER_DIR,
    RUN_SCRIPT,
    UPLOAD_DIR,
    bgd_path_for_blender,
    bgd_relative,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, str], None]


class JobStatus(str, Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    GENERATING_MESH = "generating_mesh"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobResult:
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = "Waiting to start"
    image_name: str = ""
    mesh_path: Optional[str] = None
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    error: Optional[str] = None
    progress: int = 0  # 0–100
    logs: list[str] = field(default_factory=list)


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stem)
    return cleaned or f"image_{uuid.uuid4().hex[:8]}"


def _run_logged(
    cmd: list[str],
    stage: str,
    on_progress: Optional[ProgressCallback] = None,
) -> None:
    logger.info("[%s] Running: %s", stage, " ".join(cmd))
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=os.path.dirname(RUN_SCRIPT),
    )
    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if line:
            logger.info("[%s] %s", stage, line)
            if on_progress:
                on_progress(stage, line)
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"{stage} failed with exit code {return_code}")


def run_sf3d(
    image_path: str,
    output_dir: str = OUTPUT_DIR,
    on_progress: Optional[ProgressCallback] = None,
) -> str:
    """Run Stable Fast 3D (run.py) and return path to mesh.glb."""
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    cmd = [
        sys.executable,
        RUN_SCRIPT,
        image_path,
        "--output-dir",
        output_dir if output_dir.endswith(os.sep) else output_dir + os.sep,
    ]
    _run_logged(cmd, "sf3d", on_progress)

    stem = Path(image_path).stem
    mesh_path = os.path.join(output_dir, stem, "mesh.glb")
    if not os.path.isfile(mesh_path):
        raise FileNotFoundError(f"Expected mesh not found at {mesh_path}")
    return mesh_path


def run_blender_render(
    image_path: str,
    mesh_path: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> str:
    """Run Blender visualization script; return path to rendered MP4."""
    if not BLENDER_EXECUTABLE or not os.path.isfile(BLENDER_EXECUTABLE):
        raise FileNotFoundError(
            f"Blender not found at '{BLENDER_EXECUTABLE}'. "
            "Set DRONE_BLENDER_PATH to your blender executable."
        )
    if not os.path.isfile(BLENDER_SCRIPT):
        raise FileNotFoundError(f"Blender script not found: {BLENDER_SCRIPT}")

    bgd = bgd_path_for_blender()
    if not bgd or not os.path.isfile(BGD_BLEND_PATH or ""):
        raise FileNotFoundError(
            "Night-sky background .blend not found. Place a file under "
            "blender/assets/scenes/night_sky/ (e.g. night_env1.blend) "
            "or set DRONE_BGD_PATH in .env."
        )

    stem = Path(image_path).stem
    if mesh_path is None:
        mesh_path = os.path.join(OUTPUT_DIR, stem, "mesh.glb")

    cmd = [
        BLENDER_EXECUTABLE,
        "--background",
        "--python",
        BLENDER_SCRIPT,
        "--",
        "--input_image",
        image_path,
        "--mesh_path",
        mesh_path,
        "--bgd_path",
        bgd,
        "--bgd_object",
        BGD_OBJECT_NAME,
        "--render_name",
        stem,
    ]
    logger.info("Using background asset: %s", bgd_relative())
    _run_logged(cmd, "blender", on_progress)

    video_path = os.path.join(RENDER_DIR, stem, f"{stem}.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Expected video not found at {video_path}")
    return video_path


def save_upload(file_bytes: bytes, original_filename: str) -> tuple[str, str, str]:
    """
    Persist an uploaded image under uploads/ and return
    (job_id, saved_path, safe_stem).
    """
    job_id = uuid.uuid4().hex
    stem = _safe_stem(original_filename)
    ext = Path(original_filename).suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}:
        ext = ".png"

    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    saved_path = os.path.join(job_dir, f"{stem}{ext}")
    with open(saved_path, "wb") as f:
        f.write(file_bytes)
    return job_id, saved_path, stem


def run_full_pipeline(
    image_path: str,
    job: Optional[JobResult] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> JobResult:
    """
    Full pipeline: SF3D mesh generation → Blender drone show → MP4.
    """
    if job is None:
        job = JobResult(job_id=uuid.uuid4().hex)

    stem = Path(image_path).stem
    job.image_name = stem

    def update(status: JobStatus, message: str, progress: int) -> None:
        job.status = status
        job.message = message
        job.progress = progress
        job.logs.append(f"[{status.value}] {message}")
        if on_progress:
            on_progress(status.value, message)

    try:
        update(JobStatus.GENERATING_MESH, "Generating 3D mesh with Stable Fast 3D…", 15)
        mesh_path = run_sf3d(image_path, on_progress=on_progress)
        job.mesh_path = mesh_path
        update(JobStatus.GENERATING_MESH, f"Mesh ready: {mesh_path}", 45)

        update(JobStatus.RENDERING, "Building Blender drone visualization & rendering video…", 55)
        video_path = run_blender_render(
            image_path,
            mesh_path=mesh_path,
            on_progress=on_progress,
        )
        job.video_path = video_path
        job.video_url = f"/api/videos/{stem}/{stem}.mp4"
        update(JobStatus.COMPLETED, "Visualization complete", 100)
    except Exception as exc:
        logger.exception("Pipeline failed for %s", image_path)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.message = f"Failed: {exc}"
        job.progress = job.progress or 0
        job.logs.append(f"[failed] {exc}")

    return job


def cleanup_job_upload(job_id: str) -> None:
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    if os.path.isdir(job_dir):
        shutil.rmtree(job_dir, ignore_errors=True)
