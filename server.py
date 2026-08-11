"""
FastAPI backend for DR.ONE — image upload → SF3D → Blender drone video.

Run:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from definitions import RENDER_DIR, UPLOAD_DIR, BLENDER_EXECUTABLE, BGD_BLEND_PATH
from pipeline_service import JobResult, JobStatus, run_full_pipeline, save_upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("drone.server")

app = FastAPI(
    title="DR.ONE API",
    description="Upload a 2D image, generate a 3D drone-show visualization video.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (single-process localhost use)
_jobs: Dict[str, JobResult] = {}
_lock = threading.Lock()

ALLOWED_CONTENT = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/bmp",
    "image/gif",
    "application/octet-stream",
}


def _set_job(job: JobResult) -> None:
    with _lock:
        _jobs[job.job_id] = job


def _get_job(job_id: str) -> JobResult:
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


def _execute_pipeline(job_id: str, image_path: str) -> None:
    job = _get_job(job_id)
    job.status = JobStatus.PREPROCESSING
    job.message = "Preparing uploaded image…"
    job.progress = 5
    _set_job(job)

    def on_progress(stage: str, message: str) -> None:
        current = _get_job(job_id)
        current.logs.append(f"[{stage}] {message}")
        # Soft progress bumps during long stages
        if stage == "sf3d" and current.progress < 40:
            current.progress = min(40, current.progress + 1)
            current.message = message[:200]
        elif stage == "blender" and current.progress < 95:
            current.progress = min(95, max(55, current.progress + 1))
            current.message = message[:200]
        _set_job(current)

    result = run_full_pipeline(image_path, job=job, on_progress=on_progress)
    _set_job(result)


@app.get("/api/health")
def health():
    blender_ok = bool(BLENDER_EXECUTABLE) and os.path.isfile(BLENDER_EXECUTABLE)
    bgd_ok = os.path.isfile(BGD_BLEND_PATH.replace("/", os.sep))
    return {
        "status": "ok" if blender_ok and bgd_ok else "degraded",
        "service": "DR.ONE",
        "blender_found": blender_ok,
        "blender_path": BLENDER_EXECUTABLE,
        "background_found": bgd_ok,
        "background_path": BGD_BLEND_PATH,
    }


@app.post("/api/process")
async def process_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content_type = (file.content_type or "").lower()
    ext = os.path.splitext(file.filename)[1].lower()
    if content_type not in ALLOWED_CONTENT and ext not in {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif",
    }:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a PNG, JPG, WEBP, BMP, or GIF.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload")

    job_id, saved_path, stem = save_upload(data, file.filename)
    job = JobResult(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Queued for processing",
        image_name=stem,
        progress=0,
    )
    _set_job(job)
    background_tasks.add_task(_execute_pipeline, job_id, saved_path)

    return {
        "job_id": job_id,
        "image_name": stem,
        "status": job.status.value,
        "message": job.message,
    }


@app.get("/api/status/{job_id}")
def job_status(job_id: str):
    job = _get_job(job_id)
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "message": job.message,
        "progress": job.progress,
        "image_name": job.image_name,
        "video_url": job.video_url,
        "mesh_path": job.mesh_path,
        "error": job.error,
        "logs": job.logs[-40:],
    }


@app.get("/api/videos/{stem}/{filename}")
def get_video(stem: str, filename: str):
    # Prevent path traversal
    if ".." in stem or ".." in filename or "/" in stem or "\\" in stem:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = os.path.join(RENDER_DIR, stem, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=filename,
        headers={"Accept-Ranges": "bytes"},
    )


@app.get("/api/jobs")
def list_jobs():
    with _lock:
        jobs = list(_jobs.values())
    return [
        {
            "job_id": j.job_id,
            "status": j.status.value,
            "progress": j.progress,
            "image_name": j.image_name,
            "video_url": j.video_url,
        }
        for j in jobs
    ]


# Serve built frontend if present (production / single-port mode)
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
