from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import sys
import fitz  # PyMuPDF
from typing import Optional
from pydantic import BaseModel

# Add current dir to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ai_agents import score_skills, audit_and_rewrite, structure_cv
from pdf_templates import build_corporate, build_tech_modern, build_minimal_slate

app = FastAPI(title="CV Optimizer API")

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

@app.post("/analyze")
async def analyze_cv(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    user_instructions: str = Form("")
):
    try:
        # 1. Read PDF content
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        # Ensure each page text is a string to satisfy type checkers
        raw_text = "".join(str(page.get_text()) for page in doc)
        
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        # 2. Run Agents
        scores = score_skills(raw_text, job_description)
        audit, rewrite = audit_and_rewrite(raw_text, job_description, user_instructions)
        cv_data = structure_cv(raw_text, rewrite)

        return {
            "scores": scores,
            "audit": audit,
            "rewrite": rewrite,
            "cv_data": cv_data
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

# Mount static files (assets, js, css) if the directory exists
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
