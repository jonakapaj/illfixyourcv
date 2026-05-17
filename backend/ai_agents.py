"""
ai_agents.py — Ollama-powered AI agents for CV analysis and optimisation.

Three agents:
  1. skill_scorer   → rates CV vs job description (0-100 per skill)
  2. cv_auditor     → identifies gaps and rewrites key sections (STAR method)
  3. cv_structurer  → converts raw text into structured JSON for PDF rendering
"""

import json
# pyrefly: ignore [missing-import]
import ollama


# ── Agent 1: Skill Scorer ─────────────────────────────────────────────────────

def score_skills(cv_text: str, job_desc: str) -> dict:
    """
    Rate the candidate's CV against the job description for 6 skill areas.
    Returns a dict like {"Python": 85, "Django": 70, ...}.
    Falls back to neutral 50s if the model returns malformed JSON.
    """
    prompt = (
        "You are evaluating how well a candidate's CV matches a job description.\n"
        "Score the candidate 0-100 for each skill area listed below.\n"
        "Base scores on EVIDENCE in the CV — not assumptions.\n"
        "Return ONLY a valid JSON object, no text before or after it.\n"
        'Example: {"Python": 85, "Django": 70, "Frontend": 40, '
        '"Databases": 75, "APIs": 80, "Soft Skills": 65}\n\n'
        f"JOB DESCRIPTION:\n{job_desc}\n\nCV:\n{cv_text}"
    )
    response = ollama.generate(model="llama3", prompt=prompt)
    try:
        res = response["response"].strip()
        return json.loads(res[res.find("{"):res.rfind("}") + 1])
    except Exception:
        return {
            "Python": 50, "Django": 50, "Frontend": 50,
            "Databases": 50, "APIs": 50, "Soft Skills": 50,
        }


# ── Agent 2: CV Auditor + Rewriter ───────────────────────────────────────────

def audit_and_rewrite(cv_text: str, job_desc: str, user_instructions: str = "") -> tuple[str, str]:
    """
    Two-step agent:
      Step A — Audit: identify 3 specific gaps between the CV and the job.
      Step B — Rewrite: produce improved CV sections using the STAR method.
    Returns (audit_report, rewritten_sections).
    """
    # Step A: Audit
    audit_prompt = (
        "You are a senior technical recruiter with 15 years of experience hiring software engineers.\n"
        "Your task: audit the CV below against the job description and identify EXACTLY 3 gaps.\n"
        "For each gap:\n"
        "  - Give it a short title (e.g. 'Missing Quantified Impact')\n"
        "  - Explain why it matters for THIS specific role\n"
        "  - Give one concrete fix the candidate can make\n"
        "Be direct, specific, and actionable. No fluff.\n\n"
        f"JOB DESCRIPTION:\n{job_desc}\n\n"
        f"CANDIDATE CV:\n{cv_text}"
    )
    audit_report = ollama.generate(model="llama3", prompt=audit_prompt)["response"]

    # Step B: Rewrite
    rewrite_prompt = (
        "You are an expert CV writer specialising in software engineering roles.\n"
        "Using the audit findings and user instructions below, rewrite the CV's key sections.\n\n"
        "Rules:\n"
        "- Use the STAR method (Situation->Task->Action->Result) for all experience bullets\n"
        "- Every bullet must include at least one metric or quantified outcome\n"
        "- Match keywords from the job description naturally — do NOT keyword-stuff\n"
        "- Rewrite the Professional Summary to open with the candidate's strongest selling point\n"
        "- Output clearly labelled sections: SUMMARY, SKILLS, EXPERIENCE, EDUCATION\n\n"
        f"AUDIT FINDINGS:\n{audit_report}\n\n"
        f"USER INSTRUCTIONS:\n{user_instructions or 'Improve overall quality and relevance to the role.'}\n\n"
        "Write the improved sections now:"
    )
    rewritten = ollama.generate(model="llama3", prompt=rewrite_prompt)["response"]
    return audit_report, rewritten


# ── Agent 3: CV Structurer ────────────────────────────────────────────────────

def structure_cv(original_cv_text: str, rewrite_text: str) -> dict:
    """
    Extract a structured JSON CV from the original CV and the AI rewrite.
    Contact details come from the original; content comes from the rewrite.
    Falls back to a minimal skeleton if JSON parsing fails.
    """
    prompt = (
        "You are a data extraction assistant. Produce a single valid JSON object from the two texts below.\n"
        "IMPORTANT RULES:\n"
        "- Use the ORIGINAL CV for: name, email, phone, location, linkedin, current_title\n"
        "- Use the REWRITE for: summary, experience bullets, skills list\n"
        "- If a field is missing, use an empty string or empty array\n"
        "- Return ONLY the JSON — no markdown, no explanation, no code fences\n\n"
        "Required JSON schema:\n"
        '{"name":"","email":"","phone":"","location":"","linkedin":"",'
        '"current_title":"","summary":"","skills":[],'
        '"experience":[{"title":"","company":"","period":"","bullets":[]}],'
        '"education":[{"degree":"","institution":"","year":""}]}\n\n'
        f"ORIGINAL CV:\n{original_cv_text[:3000]}\n\n"
        f"OPTIMISED REWRITE:\n{rewrite_text[:3000]}"
    )
    response = ollama.generate(model="llama3", prompt=prompt)
    raw = response["response"].strip()

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception:
        return {
            "name": "Candidate", "email": "", "phone": "",
            "location": "", "linkedin": "",
            "current_title": "Software Engineer",
            "summary": rewrite_text[:500],
            "skills": [], "experience": [], "education": [],
        }
