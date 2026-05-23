from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import sys
import fitz  # PyMuPDF
import uuid
import logging
from typing import Dict

from .utils import extract_text_from_pdf, make_cache_key, get_cached, set_cached
from typing import Optional
from pydantic import BaseModel

# Add current dir to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ai_agents import score_skills, audit_and_rewrite, structure_cv, generate_cover_letter
from pdf_templates import build_corporate, build_tech_modern, build_minimal_slate, build_cover_letter

app = FastAPI(title="CV Optimizer API")

# Simple in-memory job store for background tasks (id -> status/result)
JOBS: Dict[str, dict] = {}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

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

frontend_dist = os.path.join(base_dir, "frontend_dist")

@app.get("/")
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CV Optimizer API is running. Build the frontend to see the UI."}

class OptimizeRequest(BaseModel):
    job_description: str
    user_instructions: Optional[str] = ""


class CoverLetterRequest(BaseModel):
    job_description: str
    full_name: str
    target_company: str
    target_role: str
    key_achievement: str
    tone: str = "Professional"
    additional_notes: str = ""

@app.post("/analyze")
async def analyze_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_description: str = Form(...),
    user_instructions: str = Form("")
):
    """Enqueue analysis job and return a job id. Clients should poll /status and /result."""
    content = await file.read()

    cache_key = make_cache_key(content, job_description)
    cached = get_cached(cache_key)
    if cached:
        logger.info("Returning cached analysis result")
        return {"job_id": None, "status": "completed", "result": cached}

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "queued", "stage": "queued", "progress": 0, "result": None, "error": None, "cancel": False, "raw_text": None}
    logger.info(f"Queued job {job_id}")
    background_tasks.add_task(_run_analysis, job_id, content, job_description, user_instructions)
    return {"job_id": job_id, "status": "queued"}


def _run_analysis(job_id: str, content: bytes, job_description: str, user_instructions: str):
    try:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["stage"] = "extracting"
        JOBS[job_id]["progress"] = 5
        logger.info(f"Job {job_id} running")

        raw_text = extract_text_from_pdf(content)
        if not raw_text.strip():
            raise RuntimeError("Could not extract text from PDF (empty after OCR)")

        JOBS[job_id]["raw_text"] = raw_text

        if JOBS[job_id].get("cancel"):
            JOBS[job_id]["status"] = "canceled"
            JOBS[job_id]["stage"] = "canceled"
            logger.info(f"Job {job_id} canceled after extraction")
            return

        JOBS[job_id]["stage"] = "scoring"
        JOBS[job_id]["progress"] = 30
        scores = score_skills(raw_text, job_description)

        if JOBS[job_id].get("cancel"):
            JOBS[job_id]["status"] = "canceled"
            JOBS[job_id]["stage"] = "canceled"
            logger.info(f"Job {job_id} canceled after scoring")
            return

        JOBS[job_id]["stage"] = "auditing_rewriting"
        JOBS[job_id]["progress"] = 60
        audit, rewrite = audit_and_rewrite(raw_text, job_description, user_instructions)

        if JOBS[job_id].get("cancel"):
            JOBS[job_id]["status"] = "canceled"
            JOBS[job_id]["stage"] = "canceled"
            logger.info(f"Job {job_id} canceled after auditing")
            return

        JOBS[job_id]["stage"] = "structuring"
        JOBS[job_id]["progress"] = 85
        cv_data = structure_cv(raw_text, rewrite)

        result = {"scores": scores, "audit": audit, "rewrite": rewrite, "cv_data": cv_data}
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["stage"] = "completed"
        JOBS[job_id]["progress"] = 100
        JOBS[job_id]["result"] = result

        # Cache result for future identical requests
        cache_key = make_cache_key(content, job_description)
        set_cached(cache_key, result)
        logger.info(f"Job {job_id} completed and cached")
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["stage"] = "failed"
        JOBS[job_id]["error"] = str(e)

@app.post("/generate")
async def generate_pdf(template_id: str, cv_data: dict):
    try:
        templates = {
            "corporate": build_corporate,
            "tech": build_tech_modern,
            "minimal": build_minimal_slate
        }
        
        if template_id not in templates:
            raise HTTPException(status_code=400, detail="Invalid template ID")
            
        pdf_bytes = templates[template_id](cv_data)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=optimised_cv_{template_id}.pdf"}
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cover-letter")
async def generate_cover_letter_endpoint(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    full_name: str = Form(...),
    target_company: str = Form(...),
    target_role: str = Form(...),
    key_achievement: str = Form(...),
    tone: str = Form("Professional"),
    additional_notes: str = Form(""),
):
    content = await file.read()
    cache_key = make_cache_key(
        content,
        job_description,
        full_name,
        target_company,
        target_role,
        key_achievement,
        tone,
        additional_notes,
        "cover-letter",
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
        "full_name": full_name,
        "target_company": target_company,
        "target_role": target_role,
        "tone": tone,
    }
    set_cached(cache_key, result)
    return result


@app.post("/cover-letter-pdf")
async def cover_letter_pdf(
    cover_letter: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    target_company: str = Form(""),
    target_role: str = Form(""),
):
    pdf_bytes = build_cover_letter({
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
    return {"job_id": job_id, "status": job["status"], "stage": job.get("stage"), "progress": job.get("progress", 0), "error": job.get("error")}


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
    job["cancel"] = True
    job["stage"] = "canceling"
    job["status"] = "canceling"
    return {"job_id": job_id, "status": "canceling"}


@app.post("/structure")
async def rebuild_structure(job_id: str = Form(...), rewrite_text: str = Form(...)):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        # Use stored raw_text to rebuild structured cv_data
        raw = job.get("raw_text", "")
        cv_data = structure_cv(raw, rewrite_text)
        # update job result cv_data
        if job.get("result"):
            job["result"]["cv_data"] = cv_data
        job["stage"] = "structuring"
        return {"cv_data": cv_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files (assets, js, css) if the directory exists
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
