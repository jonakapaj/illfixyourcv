import logging
import os
import sys
import time
import uuid
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

# Make sibling modules importable both as `backend.main` (uvicorn) and as a
# plain script (`python main.py`, PyInstaller bundle).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_agents import (  # noqa: E402
    _resolve_model_name, audit_cv, contact_from_cv, generate_cover_letter, rewrite_cv, score_skills, structure_cv, warm_up,
)
from grounding import grounding_report  # noqa: E402
from pdf_templates import build_corporate, build_cover_letter, build_minimal_slate, build_tech_modern  # noqa: E402
from utils import extract_text_from_pdf, get_cached, make_cache_key, set_cached  # noqa: E402

app = FastAPI(title="CV Optimizer API")

# Bump when prompts or the result shape change, so stale cached results are ignored.
ANALYSIS_CACHE_VERSION = "analysis-v6-grounded"

# In-memory job store (id -> status/result). Old finished jobs are pruned.
JOBS: Dict[str, dict] = {}
MAX_FINISHED_JOBS = 50

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")


@app.on_event("startup")
def _load_model_in_background() -> None:
    # Load the model while the user is still pasting the job ad.
    import threading
    threading.Thread(target=warm_up, daemon=True).start()


# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine the base directory depending on if we are running from a PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running in a bundle; use getattr to avoid static type checkers complaining about _MEIPASS
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    # Running in normal Python environment
    base_dir = os.path.dirname(os.path.abspath(__file__))

repo_root = os.path.dirname(base_dir)
frontend_dist_candidates = [
    os.path.join(repo_root, "frontend", "dist"),
    os.path.join(base_dir, "frontend_dist"),
]


def _resolve_frontend_dist() -> str:
    for candidate in frontend_dist_candidates:
        if os.path.exists(os.path.join(candidate, "index.html")):
            return candidate
    return frontend_dist_candidates[-1]


frontend_dist = _resolve_frontend_dist()


def _should_serve_frontend() -> bool:
    if getattr(sys, 'frozen', False):
        return True
    return os.getenv('SERVE_FRONTEND', '').lower() in {'1', 'true', 'yes'}

@app.get("/")
async def root():
    if not _should_serve_frontend():
        return {"message": "CV Optimizer API is running."}
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CV Optimizer API is running. Build the frontend to see the UI."}

def _new_job(**extra) -> str:
    _prune_jobs()
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "queued", "stage": "queued", "progress": 0, "result": None,
        "error": None, "cancel": False, "raw_text": None, "created": time.time(), "partial": {}, **extra,
    }
    return job_id


def _prune_jobs() -> None:
    finished = [jid for jid, j in JOBS.items() if j["status"] in {"completed", "failed", "canceled"}]
    finished.sort(key=lambda jid: JOBS[jid].get("created", 0))
    for jid in finished[:-MAX_FINISHED_JOBS]:
        JOBS.pop(jid, None)


@app.post("/analyze")
async def analyze_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_description: str = Form(...),
    user_instructions: str = Form(""),
):
    """Enqueue an analysis job and return its id. Clients poll /status and /result."""
    content = await file.read()

    cache_key = make_cache_key(content, job_description, user_instructions, ANALYSIS_CACHE_VERSION)
    cached = get_cached(cache_key)
    if cached:
        logger.info("Returning cached analysis result")
        # Register a finished job so /structure (Apply edits) also works for cached results.
        job_id = _new_job(status="completed", stage="completed", progress=100, result=cached,
                          raw_text=extract_text_from_pdf(content), job_description=job_description)
        return {"job_id": job_id, "status": "completed", "result": cached}

    job_id = _new_job(job_description=job_description)
    logger.info("Queued job %s", job_id)
    background_tasks.add_task(_run_analysis, job_id, content, job_description, user_instructions, cache_key)
    return {"job_id": job_id, "status": "queued"}


@app.get("/health")
def health():
    """Backend status and the model in use (shown in the UI header)."""
    return {"status": "ok", "model": _resolve_model_name()}


class _Canceled(Exception):
    pass


def _run_analysis(job_id: str, content: bytes, job_description: str, user_instructions: str, cache_key: str):
    job = JOBS[job_id]

    def stage(name: str, progress: int) -> None:
        if job.get("cancel"):
            raise _Canceled()
        job.update(status="running", stage=name, progress=progress)
        logger.info("Job %s: %s", job_id, name)

    try:
        stage("extracting", 5)
        raw_text = extract_text_from_pdf(content)
        if not raw_text.strip():
            raise RuntimeError("Could not extract text from PDF (empty after OCR)")
        job["raw_text"] = raw_text

        stage("scoring", 15)
        scores = score_skills(raw_text, job_description)
        job["partial"]["scores"] = scores  # shown in the UI while the rest runs

        stage("auditing", 35)
        audit = audit_cv(raw_text, job_description)
        job["partial"]["audit"] = audit

        stage("rewriting", 60)
        rewrite = rewrite_cv(raw_text, job_description, user_instructions)

        stage("structuring", 95)
        cv_data = structure_cv(raw_text, rewrite)

        result = {
            "scores": scores,
            "audit": audit,
            "rewrite": rewrite,
            "cv_data": cv_data,
            # What the rewrite still says that the CV doesn't back up (shown to the user).
            "grounding": grounding_report(rewrite, raw_text, job_description),
        }
        job.update(status="completed", stage="completed", progress=100, result=result)

        # Only cache real results, not fallback defaults.
        scores_are_default = list(scores.values()) == [50] * 6
        if audit.strip() and rewrite.strip() and not scores_are_default:
            set_cached(cache_key, result)
            logger.info("Job %s completed and cached", job_id)
        else:
            logger.warning("Job %s completed with fallback/empty content; not cached", job_id)
    except _Canceled:
        job.update(status="canceled", stage="canceled")
        logger.info("Job %s canceled", job_id)
    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        job.update(status="failed", stage="failed", error=str(e))


TEMPLATES = {"corporate": build_corporate, "tech": build_tech_modern, "minimal": build_minimal_slate}


@app.post("/generate")
def generate_pdf(template_id: str, cv_data: dict):
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=400, detail="Invalid template ID")
    try:
        pdf_bytes = TEMPLATES[template_id](cv_data)
    except Exception as e:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=str(e))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=optimised_cv_{template_id}.pdf"},
    )


@app.post("/cover-letter")
def generate_cover_letter_endpoint(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    full_name: str = Form(...),
    target_company: str = Form(...),
    target_role: str = Form(...),
    key_achievement: str = Form(...),
    tone: str = Form("Professional"),
    additional_notes: str = Form(""),
):
    content = file.file.read()
    cache_key = make_cache_key(
        content,
        job_description,
        full_name,
        target_company,
        target_role,
        key_achievement,
        tone,
        additional_notes,
        "cover-letter-v3",
    )
    cached = get_cached(cache_key)
    if cached:
        return cached

    raw_text = extract_text_from_pdf(content)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    cover_letter = generate_cover_letter(
        raw_text,
        job_description,
        full_name,
        target_company,
        target_role,
        key_achievement,
        tone=tone,
        additional_notes=additional_notes,
    )

    result = {
        "cover_letter": cover_letter,
        "contact": {k: v for k, v in contact_from_cv(raw_text).items() if k != "name"},
        "full_name": full_name,
        "target_company": target_company,
        "target_role": target_role,
        "tone": tone,
    }
    set_cached(cache_key, result)
    return result


@app.post("/cover-letter-pdf")
def cover_letter_pdf(
    cover_letter: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    linkedin: str = Form(""),
    target_company: str = Form(""),
    target_role: str = Form(""),
):
    pdf_bytes = build_cover_letter({
        "linkedin": linkedin,
        "cover_letter": cover_letter,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "location": location,
        "target_company": target_company,
        "target_role": target_role,
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cover_letter.pdf"},
    )


@app.get("/status/{job_id}")
async def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id, "status": job["status"], "stage": job.get("stage"),
        "progress": job.get("progress", 0), "error": job.get("error"),
        "partial": job.get("partial") or {},
    }


@app.get("/result/{job_id}")
async def job_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Job not completed: {job['status']}")
    return job["result"]


@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in {"completed", "failed", "canceled"}:
        return {"job_id": job_id, "status": job["status"]}
    job.update(cancel=True, stage="canceling", status="canceling")
    return {"job_id": job_id, "status": "canceling"}


@app.post("/structure")
def rebuild_structure(job_id: str = Form(...), rewrite_text: str = Form(...)):
    """Re-structure an edited rewrite into cv_data for the PDF."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. Re-run the analysis.")
    raw_text = job.get("raw_text") or ""
    try:
        cv_data = structure_cv(raw_text, rewrite_text)
    except Exception as e:
        logger.exception("Re-structuring failed")
        raise HTTPException(status_code=500, detail=str(e))
    grounding = grounding_report(rewrite_text, raw_text, job.get("job_description") or "")
    if job.get("result"):
        job["result"].update(cv_data=cv_data, rewrite=rewrite_text, grounding=grounding)
    return {"cv_data": cv_data, "grounding": grounding}

# Mount static files only for bundled or explicitly enabled frontend serving.
if _should_serve_frontend() and os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
