# AI Career Sentinel / CV Optimizer

Local-first CV optimization and cover letter generation using local LLMs (defaults to Ollama `llama3.2:3b`; set `OLLAMA_MODEL=llama3` for the larger model). Contains a Streamlit dashboard, a FastAPI backend with background job queue, and a React (Vite) frontend.

---

## 🚀 Key Features

- **Multi-Agent CV Audit & Rewrite**: Evaluates skill alignment, identifies gaps, provides roadmaps, and rewrites CVs using the STAR method.
- **Grounded Output**: The rewrite and cover letter are told which job requirements the CV lacks, then fact-checked (`grounding.py`); invented skills or numbers trigger one repair pass, and anything left is shown to the user. Skill scores are capped when the model can't quote evidence from the CV.
- **Asynchronous Task Queue**: Background worker for long-running LLM tasks with status polling and cancellation.
- **Cover Letter Generator**: Builds customized cover letters (text or PDF) matching CV and job details.
- **PDF Generation**: Exports print-ready CVs using `corporate`, `tech`, or `minimal` templates.
- **OCR Fallback**: Automated text extraction fallback for scanned PDFs via Tesseract OCR + Pillow.
- **Response Caching**: Local file-based caching for identical CV, job description and instructions.

---

## 📁 Directory Structure

- `app.py`: Streamlit dashboard for fast local iteration.
- `build.py`: Compiles React assets and packages the app into a single executable.
- `backend/`:
  - `main.py`: FastAPI server routes and background task worker.
  - `ai_agents.py`: LLM agent logic (scoring, auditing, rewriting).
  - `pdf_templates.py`: PDF rendering code for CV templates and cover letters.
  - `grounding.py`: Deterministic checks that generated text only uses facts from the CV.
  - `cv_parser.py`: Parses the rewrite into PDF-ready `cv_data` without an LLM call (LLM structurer is only a fallback).
  - `utils.py`: Text extraction, OCR, and hashing cache helpers.
  - `tests/`: Unit tests (`venv/bin/python -m unittest discover backend/tests`).
- `frontend/`: React + Vite SPA.

---

## ⚙️ Quickstart & Development

### 1. Prerequisites
- Python 3.10+
- Node.js & npm
- Ollama service running with `llama3.2:3b` pulled (`ollama pull llama3.2:3b`)
- *Optional*: System-level Tesseract (`brew install tesseract`) for scanned PDF support

### 2. Installation
```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Running Services
- **Streamlit UI**: `PYTHONPATH=backend streamlit run app.py`
- **FastAPI API**: `uvicorn backend.main:app --reload --port 8000` *(Docs at `/docs`)*
- **React Frontend**: `cd frontend && npm install && npm run dev`

---

## 📦 Production Bundle

To compile the React SPA and bundle the backend + frontend into a single executable:
```bash
python build.py
```
The standalone binary will be created at `backend/dist/CV_Optimizer`. Run it directly to start the server at [http://localhost:8000](http://localhost:8000).

---

## 🔌 API Reference

### CV Analysis & Jobs
* **`POST /analyze`** (Multipart): Submit `file` (PDF), `job_description`, and optional `user_instructions`. Returns `job_id`.
* **`GET /status/{job_id}`**: Poll progress status (`queued`, `running`, `completed`, `failed`, `canceled`), stage info, and `partial` results (`scores`, then `audit`) as soon as each step finishes.
* **`GET /result/{job_id}`**: Retrieve final `scores`, `audit`, `rewrite`, `cv_data`, and `grounding` (`{numbers, terms}` the rewrite uses that the CV doesn't contain).
* **`POST /cancel/{job_id}`**: Cancel a running analysis.
* **`POST /structure`** (Form): Re-parse CV JSON structure from manual rewrite text.

### PDF Exports & Cover Letters
* **`POST /generate?template_id={corporate|tech|minimal}`** (JSON body: `cv_data`): Generates a PDF resume stream.
* **`POST /cover-letter`** (Multipart): Generates cover letter text using CV PDF, job details, and optional `tone`.
* **`POST /cover-letter-pdf`** (Form): Generates a styled cover letter PDF attachment.

---

## 🔧 Environment Variables

- `OLLAMA_MODEL`: Target Ollama model name (default: `llama3.2:3b`; `llama3` is slower but writes slightly better).
- `OLLAMA_KEEP_ALIVE`: How long the model stays loaded between calls (default: `30m`).
- `OLLAMA_NUM_CTX`: Context window per request (default: `4096`; Ollama's own default of 2048 truncates long CVs).
- `SERVE_FRONTEND`: Set to `1`, `true`, or `yes` to serve the static frontend via FastAPI.

---

## 🧪 Evaluation

`eval/run_eval.py` runs the real agents against four fixed CV / job-description pairs (`eval/cases.py`) and scores the output with rule-based checks, with no LLM judging another LLM:

- **No invented achievements**: every number in the rewrite and cover letter must appear in the original CV, no skill the CV lacks (but the JD asks for) may be claimed, and every employer and institution in the structured CV must exist in the original.
- **Format**: required audit and rewrite sections, a valid `cv_data` schema, name and email copied correctly, cover letter length and signature.
- **Scoring sanity**: 6 integer scores in the 0-100 range that aren't the fallback defaults; strong-fit CVs must score above weak-fit ones.
- **Latency** per agent.

```bash
venv/bin/python eval/run_eval.py                       # all cases (needs Ollama running)
venv/bin/python eval/run_eval.py --case pm_no_metrics  # a single case
```

Results go to `eval/results/<timestamp>.json` (full outputs) and `eval/results/latest.md` (summary).
