# AI Career Sentinel / CV Optimizer

> Local-first CV optimisation: Streamlit UI + optional SPA frontend, FastAPI backend, and single-file build.

Overview
- Streamlit app for quick local CV optimisation (`app.py`).
- Optional React + Vite frontend (in `frontend/`) served as static assets by a FastAPI backend (`backend/main.py`).
- Build tooling to bundle backend + frontend into a single executable using PyInstaller (`build.py`, `backend/CV_Optimizer.spec`).

Quickstart (development)

Prerequisites:
- Python 3.10+ and a POSIX shell (macOS/Linux)
- Node.js + npm (for the frontend)
- Optional: `pyinstaller` if you plan to create the single-file bundle

1) Create a virtual environment and install backend deps:

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

2) Run the Streamlit app (fast local iteration):

```bash
source venv/bin/activate
streamlit run app.py
```

3) Run the backend API (serves the SPA when built):

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

4) Frontend development (React + Vite):

```bash
cd frontend
npm install
npm run dev
```

Build & bundle (production)

- Build the frontend static assets:

```bash
cd frontend
npm run build
```

- The repository includes `build.py` which automates copying the built frontend into `backend/frontend_dist` and running PyInstaller to bundle the backend into a single executable.

```bash
# from project root
python build.py
```

API endpoints
- `POST /analyze` — multipart: `file` (PDF), `job_description`, `user_instructions` — returns `scores`, `audit`, `rewrite`, `cv_data`.
- `POST /generate` — JSON body: `template_id`, `cv_data` — returns a PDF response.

Notes & troubleshooting
- PDF text extraction uses PyMuPDF (`fitz`). If text extraction fails, check that the uploaded PDF contains selectable text (not scanned images) or add OCR beforehand.
- If you see import errors for local modules, ensure your working directory is the project root so `backend` and `app.py` can import `ai_agents` and `pdf_templates`.
- For packaging with PyInstaller: make sure `pyinstaller` is installed in the active environment and that `npm run build` completed successfully.

Project layout (high level)
- `app.py` — Streamlit UI for local usage
- `backend/` — FastAPI app, PyInstaller spec, and bundled static `frontend_dist`
- `frontend/` — React + Vite SPA source and configs
- `build.py` — convenience script to build frontend + run PyInstaller
- `backend/requirements.txt` — Python dependencies for the backend
- `scratch/test_api.py` — small smoke test for the API

Contributing
- Open a branch, make small commits with clear messages, and open a PR describing the change.

License
- Add your chosen license file at the project root (e.g. `LICENSE`).
