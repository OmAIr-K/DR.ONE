const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const browseBtn = document.getElementById("browse-btn");
const previewPanel = document.getElementById("preview-panel");
const previewImage = document.getElementById("preview-image");
const fileNameEl = document.getElementById("file-name");
const processBtn = document.getElementById("process-btn");
const resetBtn = document.getElementById("reset-btn");
const statusPanel = document.getElementById("status-panel");
const statusPhase = document.getElementById("status-phase");
const statusPct = document.getElementById("status-pct");
const statusMessage = document.getElementById("status-message");
const progressBar = document.getElementById("progress-bar");
const progressFill = document.getElementById("progress-fill");
const logOutput = document.getElementById("log-output");
const resultPanel = document.getElementById("result-panel");
const resultVideo = document.getElementById("result-video");
const downloadLink = document.getElementById("download-link");
const againBtn = document.getElementById("again-btn");

let selectedFile = null;
let objectUrl = null;
let pollTimer = null;

const PHASE_LABELS = {
  queued: "Queued",
  preprocessing: "Preparing",
  generating_mesh: "Building 3D mesh",
  rendering: "Rendering visualization",
  completed: "Complete",
  failed: "Failed",
};

function revokePreview() {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }
}

function setSelectedFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    alert("Please select a valid image file.");
    return;
  }
  selectedFile = file;
  revokePreview();
  objectUrl = URL.createObjectURL(file);
  previewImage.src = objectUrl;
  fileNameEl.textContent = file.name;
  dropzone.hidden = true;
  previewPanel.hidden = false;
  statusPanel.hidden = true;
  resultPanel.hidden = true;
  statusPanel.classList.remove("is-error");
  processBtn.disabled = false;
}

function resetUI() {
  selectedFile = null;
  revokePreview();
  fileInput.value = "";
  dropzone.hidden = false;
  previewPanel.hidden = true;
  statusPanel.hidden = true;
  resultPanel.hidden = true;
  statusPanel.classList.remove("is-error");
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  resultVideo.removeAttribute("src");
  resultVideo.load();
}

function updateProgress(data) {
  const pct = Math.max(0, Math.min(100, data.progress ?? 0));
  statusPhase.textContent = PHASE_LABELS[data.status] || data.status;
  statusPct.textContent = `${pct}%`;
  statusMessage.textContent = data.message || "";
  progressFill.style.width = `${pct}%`;
  progressBar.setAttribute("aria-valuenow", String(pct));
  if (Array.isArray(data.logs)) {
    logOutput.textContent = data.logs.join("\n");
  }
}

async function pollStatus(jobId) {
  const res = await fetch(`/api/status/${jobId}`);
  if (!res.ok) {
    throw new Error(`Status check failed (${res.status})`);
  }
  return res.json();
}

async function startProcessing() {
  if (!selectedFile) return;

  processBtn.disabled = true;
  statusPanel.hidden = false;
  resultPanel.hidden = true;
  statusPanel.classList.remove("is-error");
  updateProgress({
    status: "queued",
    progress: 0,
    message: "Uploading image…",
    logs: [],
  });

  const form = new FormData();
  form.append("file", selectedFile, selectedFile.name);

  let jobId;
  try {
    const res = await fetch("/api/process", {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed (${res.status})`);
    }
    const payload = await res.json();
    jobId = payload.job_id;
    updateProgress({
      status: payload.status,
      progress: 5,
      message: payload.message,
      logs: [`Job ${jobId} created`],
    });
  } catch (err) {
    statusPanel.classList.add("is-error");
    updateProgress({
      status: "failed",
      progress: 0,
      message: err.message,
      logs: [err.message],
    });
    processBtn.disabled = false;
    return;
  }

  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const data = await pollStatus(jobId);
      updateProgress(data);

      if (data.status === "completed") {
        clearInterval(pollTimer);
        pollTimer = null;
        const videoUrl = data.video_url;
        resultVideo.src = videoUrl;
        downloadLink.href = videoUrl;
        downloadLink.download = `${data.image_name || "visualization"}.mp4`;
        resultPanel.hidden = false;
        processBtn.disabled = false;
      } else if (data.status === "failed") {
        clearInterval(pollTimer);
        pollTimer = null;
        statusPanel.classList.add("is-error");
        processBtn.disabled = false;
      }
    } catch (err) {
      clearInterval(pollTimer);
      pollTimer = null;
      statusPanel.classList.add("is-error");
      updateProgress({
        status: "failed",
        progress: 0,
        message: err.message,
        logs: [err.message],
      });
      processBtn.disabled = false;
    }
  }, 2000);
}

browseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});

dropzone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) setSelectedFile(file);
});

["dragenter", "dragover"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("is-dragover");
  });
});

["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("is-dragover");
  });
});

dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer?.files?.[0];
  if (file) setSelectedFile(file);
});

processBtn.addEventListener("click", startProcessing);
resetBtn.addEventListener("click", resetUI);
againBtn.addEventListener("click", resetUI);

// Health ping so the UI fails fast if the API is down
fetch("/api/health")
  .then((r) => {
    if (!r.ok) throw new Error("API unavailable");
  })
  .catch(() => {
    statusPanel.hidden = false;
    statusPanel.classList.add("is-error");
    updateProgress({
      status: "failed",
      progress: 0,
      message:
        "Cannot reach the API. Start the backend with: uvicorn server:app --port 8000",
      logs: ["Backend not reachable on the Vite proxy (/api → :8000)"],
    });
  });
