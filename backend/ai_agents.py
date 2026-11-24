"""
ai_agents.py — Ollama-powered AI agents for CV analysis and optimisation.

Five agents:
  1. score_skills          → rates CV vs job description (0-100, 6 requirements taken from the JD)
  2. audit_cv              → executive summary, 3 gaps, roadmap, alignment matrix
  3. rewrite_cv            → optimised CV sections using the STAR method
  4. structure_cv          → converts the rewrite into structured JSON for PDF rendering
  5. generate_cover_letter → tailored 3-paragraph cover letter

Grounding: the rewrite and the cover letter are told which job requirements the
CV does not show, then checked with grounding.py. If they still contain numbers
or skills that are not in the CV, one repair pass removes them. Scores are
capped when the model cannot quote evidence from the CV.

backend/main.py runs score → audit → rewrite → structure sequentially, because a
local Ollama instance serves one generation at a time. audit_cv and rewrite_cv do
not depend on each other; audit_and_rewrite() runs them in a thread pool and is
used by the Streamlit app (app.py).
"""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor

# pyrefly: ignore [missing-import]
import ollama

from cv_parser import clean_rewrite, parse_rewrite
from grounding import grounding_report, is_clean, missing_job_terms
from pdf_templates import clean_cover_letter

logger = logging.getLogger("ai_agents")

# llama3.2:3b is ~2-3x faster than llama3 (8B) on a laptop; set OLLAMA_MODEL=llama3 for the larger model.
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

_NO_THINK_SYSTEM = (
    "Return only the requested output. No explanations, no markdown wrappers, no preamble."
)

# Score given to a requirement when the model cannot quote supporting CV text.
_NO_EVIDENCE_CAP = 20

# Keep the model loaded between pipeline steps (reloading llama3 costs seconds per call).
KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
# Ollama's default context (2048 tokens) silently truncates our longer prompts.
NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))


# ── Response helpers ──────────────────────────────────────────────────────────

def _extract_response_text(response: object) -> str:
    if isinstance(response, dict):
        return str(response.get("response", "")).strip()
    attr_text = getattr(response, "response", None)
    if isinstance(attr_text, str):
        return attr_text.strip()
    return str(response).strip()


def _strip_reasoning_wrappers(text: str) -> str:
    """Remove <think>…</think> blocks, markdown code fences and common preambles."""
    out = (text or "").strip()
    out = re.sub(r"<think>[\s\S]*?</think>", "", out, flags=re.IGNORECASE).strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    out = re.sub(r"^(here is|here's)[^\n:]*:\s*", "", out, flags=re.IGNORECASE).strip()
    return out


def _find_first_json_object(text: str) -> str:
    left, right = text.find("{"), text.rfind("}")
    if left == -1 or right == -1 or right <= left:
        return ""
    return text[left:right + 1]


def _compact_text(text: str, limit: int) -> str:
    return " ".join((text or "").split())[:limit]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# ── Model resolution ──────────────────────────────────────────────────────────

def _available_model_names() -> list[str]:
    try:
        listing = ollama.list()
    except Exception:
        return []
    raw = listing.get("models", []) if isinstance(listing, dict) else getattr(listing, "models", [])
    names: list[str] = []
    for m in raw if isinstance(raw, list) else []:
        name = (m.get("name") or m.get("model")) if isinstance(m, dict) else (
            getattr(m, "name", None) or getattr(m, "model", None))
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


_resolved_model_cache: str | None = None


def _resolve_model_name() -> str:
    """Map OLLAMA_MODEL to an installed tag (e.g. 'llama3' → 'llama3:latest')."""
    global _resolved_model_cache
    if _resolved_model_cache:
        return _resolved_model_cache
    wanted = DEFAULT_OLLAMA_MODEL.strip()
    installed = _available_model_names()
    if not installed:
        return wanted  # Ollama not reachable yet; don't cache so we retry next call
    base = wanted.split(":", 1)[0].lower()
    match = (
        next((n for n in installed if n == wanted), None)
        or next((n for n in installed if n.split(":", 1)[0].lower() == base), None)
        or next((n for n in installed if base in n.lower()), None)
        or wanted
    )
    _resolved_model_cache = match
    return match


# ── Core generation ───────────────────────────────────────────────────────────

def _is_missing_model(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "not found" in msg or "status code: 404" in msg


def _call(prompt: str, options: dict, system: str | None, fmt: str | None) -> str:
    """One generation, falling back to any installed model if the configured one is missing."""
    model = _resolve_model_name()
    kwargs: dict = {"model": model, "prompt": prompt, "keep_alive": KEEP_ALIVE,
                    "options": {"num_ctx": NUM_CTX, **options}}
    if system:
        kwargs["system"] = system
    if fmt:
        kwargs["format"] = fmt
    try:
        return _strip_reasoning_wrappers(_extract_response_text(ollama.generate(**kwargs)))
    except Exception as exc:
        if not _is_missing_model(exc):
            raise
        for fallback in _available_model_names():
            if fallback == model:
                continue
            try:
                kwargs["model"] = fallback
                return _strip_reasoning_wrappers(_extract_response_text(ollama.generate(**kwargs)))
            except Exception:
                continue
        raise


def warm_up() -> None:
    """Load the model into memory so the first real request doesn't pay the load time."""
    try:
        ollama.generate(model=_resolve_model_name(), prompt="", keep_alive=KEEP_ALIVE)
        logger.info("Model %s loaded", _resolve_model_name())
    except Exception as exc:
        logger.warning("Model warm-up failed: %s", exc)


def _generate_text(prompt: str, num_predict: int = 700, temperature: float = 0.25, no_think: bool = True) -> str:
    options = {"num_predict": num_predict, "temperature": temperature, "top_p": 0.9}
    return _call(prompt, options, _NO_THINK_SYSTEM if no_think else None, None)


def _generate_json(prompt: str, num_predict: int = 300) -> dict:
    options = {"num_predict": num_predict, "temperature": 0.05, "top_p": 0.9}
    try:
        return json.loads(_call(prompt, options, _NO_THINK_SYSTEM, "json"))
    except Exception as exc:
        logger.info("JSON mode failed (%s); retrying as free text", exc)
    payload = _find_first_json_object(_call(prompt, options, _NO_THINK_SYSTEM, None))
    if payload:
        return json.loads(payload)
    raise ValueError("Model did not return valid JSON")


def _missing_block(cv_text: str, job_desc: str) -> tuple[list[str], str]:
    """Prompt section listing JD requirements the CV does not show."""
    missing = missing_job_terms(cv_text, job_desc)
    if not missing:
        return missing, ""
    return missing, (
        "NOT IN THE CV — the job asks for these, but the CV never mentions them. "
        "Do NOT claim, list or imply experience with any of them anywhere: "
        + ", ".join(missing) + "\n\n"
    )


def _repair(text: str, report: dict, kind: str, num_predict: int) -> str:
    """Ask the model to remove unsupported numbers/terms, changing nothing else."""
    items = []
    if report.get("terms"):
        items.append("these skills/tools, which the candidate does not have: " + ", ".join(report["terms"]))
    if report.get("numbers"):
        items.append("these numbers, which do not appear in the original CV: " + ", ".join(report["numbers"]))
    prompt = (
        f"The {kind} below contains claims that are not supported by the candidate's real CV.\n"
        "Remove or rephrase every sentence or bullet that uses " + "; and ".join(items) + ".\n"
        "Do not add anything new. Keep all other wording, sections and formatting exactly as they are.\n"
        f"Return the full corrected {kind} only.\n\n"
        f"{kind.upper()}:\n{text}"
    )
    return _generate_text(prompt, num_predict=num_predict, temperature=0.05, no_think=True)


def _ground(text: str, cv_text: str, job_desc: str, kind: str, num_predict: int, allowed: str = "") -> str:
    """Check `text` against the CV and run one repair pass if it invents content."""
    report = grounding_report(text, cv_text, job_desc, allowed)
    if is_clean(report):
        return text
    logger.info("%s: repairing unsupported content %s", kind, report)
    try:
        repaired = _repair(text, report, kind, num_predict)
    except Exception as exc:
        logger.warning("%s repair failed: %s", kind, exc)
        return text
    # Keep the repair only if it is a real improvement and didn't truncate the text.
    after = grounding_report(repaired, cv_text, job_desc, allowed)
    size = lambda r: len(r["numbers"]) + len(r["terms"])  # noqa: E731
    if repaired and len(repaired) > 0.6 * len(text) and size(after) < size(report):
        return repaired
    return text


# ── Agent 1: Skill Scorer ─────────────────────────────────────────────────────

_DEFAULT_SCORES = {
    "Technical Skills": 50, "Communication": 50, "Experience Fit": 50,
    "Tools & Frameworks": 50, "Domain Knowledge": 50, "Problem Solving": 50,
}


def score_skills(cv_text: str, job_desc: str) -> dict:
    """
    Extracts the 6 most important requirements from the JD and scores the CV
    against each. The model must quote CV evidence; a score whose quote is not
    actually in the CV is capped at _NO_EVIDENCE_CAP. Returns {requirement: 0-100}.
    """
    prompt = (
        "Read the JOB DESCRIPTION and pick its 6 most important requirements, using the job's own wording "
        "(2-4 words each). Only use requirements that are written in this job description.\n"
        "For each, copy a short exact quote (max 12 words) from the CV that proves it, or \"\" if there is none, "
        "and score 0-100 from that evidence only:\n"
        "85-100 strong and specific, 65-84 clear, 45-64 partial or indirect, 20-44 minimal, 0-19 none.\n\n"
        'Return JSON: {"requirements": [{"name": "<requirement>", "evidence": "<quote from CV or empty>", '
        '"score": <int>}, ... 6 items]}\n\n'
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 2500)}\n\n"
        f"CV:\n{_compact_text(cv_text, 4000)}"
    )
    try:
        parsed = _generate_json(prompt, num_predict=420)
    except Exception as exc:
        logger.warning("score_skills failed: %s", exc)
        return dict(_DEFAULT_SCORES)

    items = parsed.get("requirements") if isinstance(parsed, dict) else None
    if not isinstance(items, list):  # tolerate the old flat {"skill": score} shape
        items = [{"name": k, "score": v, "evidence": None} for k, v in (parsed or {}).items()]

    cv_words = set(_norm(cv_text).split())

    def _evidence_ok(quote: str) -> bool:
        # Most of the quoted words must really appear in the CV (allows small paraphrases).
        words = [w for w in _norm(quote).split() if len(w) > 2]
        return bool(words) and sum(w in cv_words for w in words) / len(words) >= 0.75

    out: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name in out:
            continue
        try:
            score = max(0, min(100, int(float(item.get("score", 0)))))
        except (TypeError, ValueError):
            continue
        evidence = item.get("evidence")
        if evidence is not None and not _evidence_ok(str(evidence)):
            score = min(score, _NO_EVIDENCE_CAP)
        out[name] = score
        if len(out) == 6:
            break
    return out if len(out) >= 4 else dict(_DEFAULT_SCORES)


# ── Agent 2: CV Auditor ───────────────────────────────────────────────────────

def audit_cv(cv_text: str, job_desc: str) -> str:
    """
    Short audit report: 2-sentence summary, the 3 most critical gaps with a fix
    for each, and an alignment table built from the actual JD requirements.
    Kept deliberately compact: output length is what makes local models slow.
    Does not depend on rewrite_cv.
    """
    prompt = (
        "You are a senior hiring manager reviewing a candidate's CV for a specific role.\n"
        "Write a SHORT audit with exactly these three sections:\n\n"
        "EXECUTIVE SUMMARY\n"
        "2 sentences on overall fit, naming real JD requirements and CV content.\n\n"
        "3 CRITICAL GAPS\n"
        "For each gap, three lines:\n"
        "Gap: <name>\n"
        "Evidence: <what the CV shows or lacks, one sentence>\n"
        "Fix: <one concrete action>\n\n"
        "ALIGNMENT MATRIX\n"
        "Markdown table: Requirement | CV Evidence | Gap Level (Low/Medium/High)\n"
        "6 rows, one per key JD requirement, cells under 8 words.\n\n"
        "Rules: plain text, no preamble, no closing remarks. Never say the CV shows something it does not.\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 3000)}\n\n"
        f"CV:\n{_compact_text(cv_text, 5000)}"
    )
    return _generate_text(prompt, num_predict=520, temperature=0.2, no_think=True)


# ── Agent 3: CV Rewriter ──────────────────────────────────────────────────────

def rewrite_cv(cv_text: str, job_desc: str, user_instructions: str = "") -> str:
    """
    Produces an optimised CV with STAR-method bullets, ATS-friendly formatting.
    Only facts from the original CV are allowed; see _ground().
    Does not depend on audit_cv.
    """
    _, missing = _missing_block(cv_text, job_desc)
    prompt = (
        "You are an expert CV writer. Rewrite the candidate's CV for the target role.\n"
        "Include these clearly labeled sections:\n\n"
        "PROFESSIONAL SUMMARY\n"
        "3-4 sentences, keyword-rich for this role, highlighting real strengths. No generic phrases.\n\n"
        "CORE SKILLS\n"
        "8-12 skills the CV actually shows, ordered by relevance to the job.\n\n"
        "PROFESSIONAL EXPERIENCE\n"
        "Each role: title, company, dates, then 3-4 impact bullets.\n"
        "Each bullet: action → task → result. Keep every metric that is in the original; "
        "if the original has no number, describe the result in words.\n\n"
        "EDUCATION\n"
        "Degree, institution, year, relevant coursework or projects.\n\n"
        "HARD RULES (breaking them makes the CV dishonest):\n"
        "- Use only facts from the ORIGINAL CV. Never invent achievements, employers, dates, certifications or skills.\n"
        "- Never add a number, percentage, count or duration that is not in the original CV.\n"
        "- Use the job's keywords only where the CV genuinely supports them.\n"
        "- ATS-friendly plain text: no tables, no columns, no markdown code fences.\n"
        "- Output only the CV: no introduction, no notes or explanations after it.\n\n"
        f"{missing}"
        f"USER INSTRUCTIONS: {user_instructions or 'Improve overall quality and relevance.'}\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 2500)}\n\n"
        f"ORIGINAL CV:\n{_compact_text(cv_text, 5000)}"
    )
    text = clean_rewrite(_generate_text(prompt, num_predict=1000, temperature=0.2, no_think=True))
    return clean_rewrite(_ground(text, cv_text, job_desc, "CV", num_predict=1000))


# ── Compatibility wrapper ─────────────────────────────────────────────────────

def audit_and_rewrite(cv_text: str, job_desc: str, user_instructions: str = "") -> tuple[str, str]:
    """Run audit and rewrite in parallel and return (audit, rewrite)."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_audit = ex.submit(audit_cv, cv_text, job_desc)
        f_rewrite = ex.submit(rewrite_cv, cv_text, job_desc, user_instructions)
        return f_audit.result(), f_rewrite.result()


# ── Agent 4: CV Structurer ────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"\+?\d[\d ()/-]{7,}\d")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", re.IGNORECASE)


def contact_from_cv(cv_text: str) -> dict:
    """Contact details read straight from the CV text (more reliable than the model)."""
    out = {}
    for key, rx in (("email", _EMAIL_RE), ("phone", _PHONE_RE), ("linkedin", _LINKEDIN_RE)):
        m = rx.search(cv_text or "")
        if m:
            out[key] = m.group(0).strip()
    first = next((ln.strip() for ln in (cv_text or "").splitlines() if ln.strip()), "")
    if first and len(first.split()) <= 5 and not any(ch.isdigit() or ch == "@" for ch in first):
        out["name"] = first
    return out


def _finish_cv_data(data: dict, original_cv_text: str) -> dict:
    for key, value in contact_from_cv(original_cv_text).items():
        data[key] = value
    for key in ("name", "email", "phone", "location", "linkedin", "current_title", "summary"):
        data.setdefault(key, "")
    if not data.get("current_title") and data.get("experience"):
        data["current_title"] = data["experience"][0].get("title", "")
    for key in ("skills", "experience", "education"):
        if not isinstance(data.get(key), list):
            data[key] = []
    return data


def structure_cv(original_cv_text: str, rewrite_text: str) -> dict:
    """
    Build the cv_data used for PDF rendering: contact details from the original CV,
    content from the rewrite. Parses the rewrite directly (instant); only falls back
    to the LLM when the rewrite doesn't have the expected sections.
    """
    parsed = parse_rewrite(rewrite_text)
    if parsed:
        return _finish_cv_data(parsed, original_cv_text)
    logger.info("Rewrite didn't parse; structuring with the LLM")
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
    data: dict | None = None
    try:
        parsed = _generate_json(prompt, num_predict=750)
        if isinstance(parsed, dict) and (parsed.get("name") or parsed.get("experience") or parsed.get("summary")):
            data = parsed
    except Exception as exc:
        logger.warning("structure_cv failed: %s", exc)
    if data is None:
        data = {
            "name": "Candidate", "email": "", "phone": "", "location": "", "linkedin": "",
            "current_title": "Professional", "summary": rewrite_text[:400],
            "skills": [], "experience": [], "education": [],
        }
    return _finish_cv_data(data, original_cv_text)


# ── Agent 5: Cover Letter ─────────────────────────────────────────────────────

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
    """Draft a tailored 3-paragraph cover letter (260-340 words), grounded in the CV."""
    tone_guide = {
        "Professional": "formal and polished, confident but not boastful",
        "Warm": "friendly and personable while remaining professional",
        "Confident": "assertive and self-assured, emphasising clear value",
        "Direct": "concise and to the point, no filler phrases",
    }.get(tone, "professional and clear")
    _, missing = _missing_block(cv_text, job_desc)

    prompt = (
        f"Write a cover letter for {full_name} applying to {target_role} at {target_company}.\n\n"
        "Three paragraphs:\n"
        "1. Opening (~80 words): Why this specific role and company. Reference something from the JD. "
        "Do NOT start with 'I am writing to...'.\n"
        "2. Evidence (~130 words): 2-3 specific examples from the CV addressing the JD requirements. "
        "Mention the key achievement naturally.\n"
        "3. Closing (~60 words): Enthusiasm, availability, what you bring.\n\n"
        f"Tone: {tone_guide}. Target 260-340 words total.\n"
        "No bullet points, no headers, no markdown. End with the candidate's name on its own line.\n"
        "Only reference experience visible in the CV or the key achievement. Never add numbers that are not there.\n\n"
        f"{missing}"
        f"KEY ACHIEVEMENT: {key_achievement}\n"
        f"ADDITIONAL CONTEXT: {additional_notes or 'None.'}\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 2500)}\n\n"
        f"CV:\n{_compact_text(cv_text, 4000)}"
    )
    raw = _generate_text(prompt, num_predict=650, temperature=0.3, no_think=False).strip()
    if len(raw.split()) <= 80:
        raw = (
            f"The {target_role} position at {target_company} stands out to me because it aligns closely "
            f"with the direction I have been building my career in.\n\n"
            f"My background maps directly to your requirements. {key_achievement.rstrip('.')}. "
            f"This reflects the impact-driven approach I bring to my work, combining technical depth "
            f"with a focus on outcomes that matter to the business.\n\n"
            f"I would welcome the chance to discuss how my experience can contribute to your team. "
            f"I am available at your convenience and look forward to the conversation.\n\n"
            f"{full_name}"
        )
    allowed = "\n".join([key_achievement, additional_notes, target_company, target_role, full_name])
    letter = _ground(raw, cv_text, job_desc, "cover letter", num_predict=700, allowed=allowed)

    # Drop chatter like "Here is a cover letter for …:" and any model-written
    # sign-off, then add one consistent sign-off with the candidate's name.
    body = clean_cover_letter(letter, full_name)
    return f"{body}\n\nKind regards,\n{full_name}"
