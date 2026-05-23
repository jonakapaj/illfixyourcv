"""
ai_agents.py — Ollama-powered AI agents for CV analysis and optimisation.

Three agents:
  1. skill_scorer   → rates CV vs job description (0-100 per skill)
  2. cv_auditor     → identifies gaps and rewrites key sections (STAR method)
  3. cv_structurer  → converts raw text into structured JSON for PDF rendering
    4. cover_letter   → drafts a tailored cover letter from CV + user details
"""

import json
# pyrefly: ignore [missing-import]
import ollama


def _compact_text(text: str, limit: int) -> str:
    """Normalize whitespace and cap long inputs to keep prompts responsive."""
    return " ".join(text.split())[:limit]


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
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 4000)}\n\nCV:\n{_compact_text(cv_text, 6000)}"
    )
    response = ollama.generate(model="llama3", prompt=prompt, options={"num_predict": 128})
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
    prompt = (
        "You are a senior technical recruiter and expert CV writer.\n"
        "Do TWO things in one response to reduce latency:\n"
        "1) Audit the CV against the job description and identify EXACTLY 3 gaps.\n"
        "2) Rewrite the CV's key sections using those gaps and the user instructions.\n\n"
        "Rules for the audit:\n"
        "- Give each gap a short title\n"
        "- Explain why it matters for THIS role\n"
        "- Give one concrete fix\n\n"
        "Rules for the rewrite:\n"
        "- Use the STAR method for experience bullets\n"
        "- Include at least one metric or quantified outcome in every bullet\n"
        "- Match keywords naturally without stuffing\n"
        "- Output clearly labelled sections: SUMMARY, SKILLS, EXPERIENCE, EDUCATION\n\n"
        "Return ONLY valid JSON with exactly these keys: audit, rewrite.\n"
        "The audit value should be a plain string. The rewrite value should be a plain string.\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 4000)}\n\n"
        f"CANDIDATE CV:\n{_compact_text(cv_text, 6000)}\n\n"
        f"USER INSTRUCTIONS:\n{user_instructions or 'Improve overall quality and relevance to the role.'}"
    )
    response = ollama.generate(model="llama3", prompt=prompt, options={"num_predict": 512})
    raw = response["response"].strip()

    try:
        parsed = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        return parsed.get("audit", raw), parsed.get("rewrite", raw)
    except Exception:
        audit_sep = "REWRITE:"
        if audit_sep in raw:
            left, right = raw.split(audit_sep, 1)
            return left.replace("AUDIT:", "").strip(), right.strip()
        return raw, raw


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
        f"ORIGINAL CV:\n{_compact_text(original_cv_text, 3000)}\n\n"
        f"OPTIMISED REWRITE:\n{_compact_text(rewrite_text, 3000)}"
    )
    response = ollama.generate(model="llama3", prompt=prompt, options={"num_predict": 256})
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


# ── Agent 4: Cover Letter Generator ─────────────────────────────────────────

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
    """
    Draft a tailored cover letter using the candidate CV and required self-inputs.
    Returns plain text and falls back to a concise template if the model output is malformed.
    """
    prompt = (
        "You are an expert career writer. Write a tailored cover letter using the candidate's CV and the user's details.\n"
        "Rules:\n"
        "- Write 3 to 5 short paragraphs, around 250 to 400 words.\n"
        "- Keep it specific, credible, and tailored to the target role and company.\n"
        "- Do not invent experience or achievements that are not supported by the CV or user notes.\n"
        "- Mention the candidate's key achievement naturally.\n"
        "- Use a clear opening, middle evidence, and a concise closing.\n"
        "- Return ONLY the cover letter text with no markdown, title, or bullet points.\n\n"
        f"TARGET ROLE: {target_role}\n"
        f"TARGET COMPANY: {target_company}\n"
        f"CANDIDATE NAME: {full_name}\n"
        f"TONE: {tone}\n"
        f"KEY ACHIEVEMENT: {key_achievement}\n"
        f"ADDITIONAL NOTES: {additional_notes or 'None'}\n\n"
        f"JOB DESCRIPTION:\n{_compact_text(job_desc, 3500)}\n\n"
        f"CANDIDATE CV:\n{_compact_text(cv_text, 5000)}"
    )
    response = ollama.generate(model="llama3", prompt=prompt, options={"num_predict": 512})
    raw = response["response"].strip()

    # Remove accidental fences or label prefixes if the model adds them.
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if raw.lower().startswith("cover letter:"):
        raw = raw.split(":", 1)[-1].strip()

    if raw:
        return raw

    return (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to express my interest in the {target_role} position at {target_company}. "
        f"My background, as reflected in my CV, aligns well with the responsibilities of this role, and "
        f"my key achievement, {key_achievement}, demonstrates the kind of impact I aim to bring.\n\n"
        f"I would welcome the opportunity to discuss how my experience can contribute to your team.\n\n"
        f"Sincerely,\n{full_name}"
    )
