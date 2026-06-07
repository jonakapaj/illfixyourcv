"""
ai_agents.py — Ollama-powered AI agents for CV analysis and optimisation.

Four agents:
  1. score_skills  → rates CV vs job description (0-100, dynamic skills from JD)
  2. audit_cv      → executive summary, 3 gaps, roadmap, alignment matrix
  3. rewrite_cv    → optimised CV sections using STAR method
  4. structure_cv  → converts rewrite into structured JSON for PDF rendering
  5. cover_letter  → tailored 3-paragraph cover letter

audit_cv and rewrite_cv are independent and are run in parallel by main.py
together with score_skills, cutting wall-clock time roughly in half.
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
# pyrefly: ignore [missing-import]
import ollama


DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

_NO_THINK_SYSTEM = (
    "Return only the requested output. No explanations, no markdown wrappers, no preamble."
)


# ── Response helpers ──────────────────────────────────────────────────────────

def _extract_response_text(response: object) -> str:
    if isinstance(response, dict):
        return str(response.get("response", "")).strip()
    attr_text = getattr(response, "response", None)
    if isinstance(attr_text, str):
        return attr_text.strip()
    return str(response).strip()


def _strip_reasoning_wrappers(text: str) -> str:
    """Remove <think>…</think> blocks and markdown code fences."""
    out = (text or "").strip()
    out = re.sub(r"<think>[\s\S]*?</think>", "", out, flags=re.IGNORECASE).strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if out.startswith("Here is the output in JSON format:"):
        out = out.split(":", 1)[-1].strip()
    return out


def _find_first_json_object(text: str) -> str:
    left, right = text.find("{"), text.rfind("}")
    if left == -1 or right == -1 or right <= left:
        return ""
    return text[left:right + 1]


def _compact_text(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


# ── Model resolution ──────────────────────────────────────────────────────────

def _available_model_names() -> list[str]:
    try:
        listing = ollama.list()
    except Exception:
        return []
    models: list[object] = []
    if isinstance(listing, dict):
        raw = listing.get("models", [])
        if isinstance(raw, list):
            models = raw
    else:
        raw = getattr(listing, "models", [])
        if isinstance(raw, list):
            models = raw
    names: list[str] = []
    for m in models:
        name = (m.get("name") or m.get("model")) if isinstance(m, dict) else (
            getattr(m, "name", None) or getattr(m, "model", None))
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


_resolved_model_cache: str | None = None

def _resolve_model_name() -> str:
    global _resolved_model_cache
    if _resolved_model_cache:
        return _resolved_model_cache
    wanted = DEFAULT_OLLAMA_MODEL.strip()
    installed = _available_model_names()
    if not installed:
        return wanted
    if wanted in installed:
        _resolved_model_cache = wanted
        return wanted
    base = wanted.split(":", 1)[0].lower()
    for name in installed:
        if name.split(":", 1)[0].lower() == base:
            _resolved_model_cache = name
            return name
    for name in installed:
        if base in name.lower():
            _resolved_model_cache = name
            return name
    _resolved_model_cache = wanted
    return wanted


# ── Core generation ───────────────────────────────────────────────────────────

def _generate_text(
    prompt: str,
    num_predict: int = 700,
    temperature: float = 0.25,
    no_think: bool = True,
) -> str:
    model = _resolve_model_name()
    options = {"num_predict": num_predict, "temperature": temperature, "top_p": 0.9}
    kwargs: dict = {"model": model, "prompt": prompt, "options": options}
    if no_think:
        kwargs["system"] = _NO_THINK_SYSTEM
    try:
        return _strip_reasoning_wrappers(_extract_response_text(ollama.generate(**kwargs)))
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "status code: 404" in msg:
            for fallback in _available_model_names():
                if fallback != model:
                    kwargs["model"] = fallback
                    return _strip_reasoning_wrappers(_extract_response_text(ollama.generate(**kwargs)))
        raise


def _generate_json(prompt: str, num_predict: int = 300) -> dict:
    model = _resolve_model_name()
    options = {"num_predict": num_predict, "temperature": 0.05, "top_p": 0.9}
    try:
        response = ollama.generate(
            model=model, prompt=prompt, system=_NO_THINK_SYSTEM,
            format="json", options=options,
        )
        text = _strip_reasoning_wrappers(_extract_response_text(response))
        return json.loads(text)
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "status code: 404" in msg:
            for fallback in _available_model_names():
                if fallback == model:
                    continue
                try:
                    response = ollama.generate(
                        model=fallback, prompt=prompt, system=_NO_THINK_SYSTEM,
                        format="json", options=options,
                    )
                    return json.loads(_strip_reasoning_wrappers(_extract_response_text(response)))
                except Exception:
                    continue
        # Last resort: free-text then extract
        text = _generate_text(prompt, num_predict=num_predict, temperature=0.05)
        payload = _find_first_json_object(text)
        if payload:
            return json.loads(payload)
        raise ValueError("Model did not return valid JSON")


# ── Agent 1: Skill Scorer ─────────────────────────────────────────────────────

def score_skills(cv_text: str, job_desc: str) -> dict:
    """
    Dynamically extracts 6 key skills from the JD and scores the CV against them.
    Returns {skill_name: 0-100}.
    """
    prompt = (
        "Analyze the job description and CV below.\n"
        "Step 1: Identify the 6 most important skill/competency requirements from the job description.\n"
        "Step 2: Score the CV 0-100 for each skill based ONLY on explicit evidence in the CV.\n\n"
        "Scoring: 85-100=strong evidence, 65-84=clear evidence, 45-64=partial, 20-44=minimal, 0-19=none.\n\n"
        "Return ONLY a JSON object with exactly 6 keys (2-4 word skill names) and integer scores.\n"
        'Example: {"Python Development": 80, "REST APIs": 65, "SQL Databases": 70, '
        '"Unit Testing": 45, "Cloud Deployment": 30, "Agile Workflow": 60}\n\n'
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 2500)}\n\n"
        f"CV:\n{_compact_text(cv_text, 4000)}"
    )
    _default = {
        "Technical Skills": 50, "Communication": 50, "Experience Fit": 50,
        "Tools & Frameworks": 50, "Domain Knowledge": 50, "Problem Solving": 50,
    }
    try:
        parsed = _generate_json(prompt, num_predict=200)
        out: dict = {}
        for key, raw in parsed.items():
            if not isinstance(key, str) or not key.strip():
                continue
            try:
                score = int(float(raw)) if isinstance(raw, (int, float, str)) else 50
                out[key.strip()] = max(0, min(100, score))
            except Exception:
                continue
        return out if len(out) >= 4 else _default
    except Exception:
        return _default


# ── Agent 2a: CV Auditor ──────────────────────────────────────────────────────

def audit_cv(cv_text: str, job_desc: str) -> str:
    """
    Produces an audit report: executive summary, 3 gaps, improvement roadmap,
    and an alignment matrix built from the actual JD requirements.
    Runs independently — can be parallelised with rewrite_cv.
    """
    prompt = (
        "You are a senior hiring manager reviewing a candidate's CV for a specific role.\n"
        "Write a structured audit report with these four sections in order:\n\n"
        "EXECUTIVE SUMMARY\n"
        "5 sentences evaluating the candidate's overall fit. Be specific — reference actual JD requirements and CV content.\n\n"
        "AUDIT FINDINGS — 3 CRITICAL GAPS\n"
        "For each gap:\n"
        "  Gap: [name]\n"
        "  Evidence From CV: [what the CV does or does not show]\n"
        "  Why It Matters: [importance for this specific role]\n"
        "  How To Fix: [concrete improvement action]\n\n"
        "IMPROVEMENT ROADMAP\n"
        "5 prioritised, actionable bullet points.\n\n"
        "ALIGNMENT MATRIX\n"
        "Markdown table with columns: Requirement | CV Evidence | Gap Level | Fix\n"
        "One row per key JD requirement (minimum 6 rows). Base requirements on the ACTUAL job description.\n\n"
        "Rules: plain text only, no JSON, no markdown code fences.\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 3000)}\n\n"
        f"CV:\n{_compact_text(cv_text, 5000)}"
    )
    return _generate_text(prompt, num_predict=900, temperature=0.2, no_think=False)


# ── Agent 2b: CV Rewriter ─────────────────────────────────────────────────────

def rewrite_cv(cv_text: str, job_desc: str, user_instructions: str = "") -> str:
    """
    Produces an optimised CV with STAR-method bullets, ATS-friendly formatting.
    Runs independently — can be parallelised with audit_cv.
    """
    prompt = (
        "You are an expert CV writer. Rewrite the candidate's CV optimised for the target role.\n"
        "Include these clearly labeled sections:\n\n"
        "PROFESSIONAL SUMMARY\n"
        "3-4 sentences, keyword-rich for this role, highlighting top strengths. No generic phrases.\n\n"
        "CORE SKILLS\n"
        "8-12 relevant skills with brief context. Include skills from the JD that the candidate demonstrably has.\n\n"
        "PROFESSIONAL EXPERIENCE\n"
        "Each role: title, company, dates, then 3-4 impact bullets.\n"
        "Each bullet: Action → Task → Result, with at least one metric where possible.\n"
        "Rewrite weak or vague bullets to be specific and impactful.\n\n"
        "EDUCATION\n"
        "Degree, institution, year, relevant coursework or projects.\n\n"
        "Rules:\n"
        "- Base all content on the original CV — do not invent achievements.\n"
        "- Tailor language and keywords to the specific role and JD.\n"
        "- ATS-friendly: no tables, no columns, no graphics.\n"
        "- Plain text only, no markdown code fences.\n\n"
        f"USER INSTRUCTIONS: {user_instructions or 'Improve overall quality and relevance.'}\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 2500)}\n\n"
        f"ORIGINAL CV:\n{_compact_text(cv_text, 5000)}"
    )
    return _generate_text(prompt, num_predict=850, temperature=0.2, no_think=False)


# ── Compatibility wrapper ─────────────────────────────────────────────────────

def audit_and_rewrite(cv_text: str, job_desc: str, user_instructions: str = "") -> tuple[str, str]:
    """Run audit and rewrite in parallel and return (audit, rewrite)."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_audit = ex.submit(audit_cv, cv_text, job_desc)
        f_rewrite = ex.submit(rewrite_cv, cv_text, job_desc, user_instructions)
        audit = f_audit.result()
        rewrite = f_rewrite.result()
    return audit, rewrite


# ── Agent 3: CV Structurer ────────────────────────────────────────────────────

def structure_cv(original_cv_text: str, rewrite_text: str) -> dict:
    """
    Extract contact details from original and content from rewrite into a JSON schema
    suitable for PDF rendering.
    """
    prompt = (
        "Extract structured data from the two texts and return a single JSON object.\n"
        "Rules:\n"
        "- Contact fields (name, email, phone, location, linkedin, current_title): from ORIGINAL CV only.\n"
        "- Content fields (summary, skills, experience, education): from OPTIMISED REWRITE.\n"
        "- Include ALL experience and education entries.\n"
        "- Missing fields: use empty string or empty array.\n"
        "- Return ONLY the JSON object.\n\n"
        "Schema:\n"
        '{"name":"","email":"","phone":"","location":"","linkedin":"",'
        '"current_title":"","summary":"","skills":[],'
        '"experience":[{"title":"","company":"","period":"","bullets":[]}],'
        '"education":[{"degree":"","institution":"","year":""}]}\n\n'
        f"ORIGINAL CV:\n{_compact_text(original_cv_text, 2500)}\n\n"
        f"OPTIMISED REWRITE:\n{_compact_text(rewrite_text, 3500)}"
    )
    try:
        parsed = _generate_json(prompt, num_predict=750)
        if parsed.get("name") or parsed.get("experience") or parsed.get("summary"):
            return parsed
    except Exception:
        pass
    # Fallback via text
    raw = _generate_text(prompt, num_predict=750, temperature=0.05, no_think=True)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        payload = _find_first_json_object(raw)
        if payload:
            return json.loads(payload)
    except Exception:
        pass
    return {
        "name": "Candidate", "email": "", "phone": "", "location": "", "linkedin": "",
        "current_title": "Professional", "summary": rewrite_text[:400],
        "skills": [], "experience": [], "education": [],
    }


# ── Agent 4: Cover Letter ─────────────────────────────────────────────────────

def generate_cover_letter(
    cv_text: str,
    job_desc: str,
    full_name: str,
    target_company: str,
    target_role: str,
    key_achievement: str,
    tone: str = "Professional",
    additional_notes: str = "",
) -> str:
    """Draft a tailored 3-paragraph cover letter (260-340 words)."""
    tone_guide = {
        "Professional": "formal and polished, confident but not boastful",
        "Warm": "friendly and personable while remaining professional",
        "Confident": "assertive and self-assured, emphasising clear value",
        "Direct": "concise and to the point, no filler phrases",
    }.get(tone, "professional and clear")

    prompt = (
        f"Write a cover letter for {full_name} applying to {target_role} at {target_company}.\n\n"
        "Three paragraphs:\n"
        "1. Opening (~80 words): Why this specific role and company. Reference something from the JD. "
        "Do NOT start with 'I am writing to...'.\n"
        "2. Evidence (~130 words): 2-3 specific examples from the CV addressing the JD requirements. "
        "Mention the key achievement naturally.\n"
        "3. Closing (~60 words): Enthusiasm, availability, what you bring.\n\n"
        f"Tone: {tone_guide}. Target 260-340 words total.\n"
        "No bullet points, no headers, no markdown. End with the candidate's name on a new line.\n"
        "Only reference experience visible in the CV.\n\n"
        f"KEY ACHIEVEMENT: {key_achievement}\n"
        f"ADDITIONAL CONTEXT: {additional_notes or 'None.'}\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 2500)}\n\n"
        f"CV:\n{_compact_text(cv_text, 4000)}"
    )
    raw = _generate_text(prompt, num_predict=600, temperature=0.3, no_think=False)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if raw and len(raw.split()) > 80:
        return raw.strip()
    return (
        f"The {target_role} position at {target_company} stands out to me because of the opportunity "
        f"to contribute meaningfully in this area — it aligns closely with the direction I have been "
        f"building my career.\n\n"
        f"My background maps directly to your requirements. {key_achievement}. "
        f"This reflects the kind of impact-driven approach I apply consistently — combining technical "
        f"depth with a focus on measurable outcomes that matter to the business.\n\n"
        f"I would welcome the chance to discuss how my experience can contribute to your team. "
        f"I am available at your convenience and look forward to the conversation.\n\n"
        f"{full_name}"
    )
