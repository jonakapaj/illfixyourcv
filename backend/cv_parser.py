"""
cv_parser.py — turn the rewrite text into the cv_data dict used by the PDF templates,
without an LLM call.

The rewrite prompt asks for four labelled sections (PROFESSIONAL SUMMARY, CORE
SKILLS, PROFESSIONAL EXPERIENCE, EDUCATION), so the structure is predictable.
Parsing it directly takes milliseconds instead of a ~30 s model call. If the
text doesn't parse into something usable, parse_rewrite() returns None and the
caller falls back to the LLM structurer.
"""

from __future__ import annotations

import re

_SECTIONS = {
    "summary": ("professional summary", "summary", "profile", "about me", "personal statement"),
    "skills": ("core skills", "skills", "key skills", "technical skills", "core competencies", "competencies"),
    "experience": ("professional experience", "experience", "work experience", "employment history", "work history"),
    "education": ("education", "education and training", "academic background", "qualifications"),
    "other": ("projects", "certifications", "languages", "interests", "references", "awards", "volunteering"),
}

_BULLET_RE = re.compile(r"^\s*(?:[-*•·▪►▸]|\d+[.)])\s+")
_YEAR = r"(?:19|20)\d{2}"
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE = rf"(?:{_MONTH}\s+)?{_YEAR}"
_PERIOD_RE = re.compile(
    rf"\(?\s*({_DATE}\s*(?:[-–—]|to)\s*(?:{_DATE}|present|current|now|today)|{_DATE}|expected\s+{_YEAR})\s*\)?",
    re.IGNORECASE,
)

# Chatter models add around the actual document.
_PREAMBLE_RE = re.compile(r"^\s*(?:sure|certainly|okay)?[!,.\s]*(?:here(?:'s| is)|below is)\b[^\n]*\n+", re.IGNORECASE)
_TRAILER_RE = re.compile(r"\n+\s*(?:\**\s*)?(?:note|notes|i(?:'ve| have) (?:kept|made|added|rephrased|tailored)|"
                         r"this (?:cv|resume|rewrite|version))\b[\s\S]*$", re.IGNORECASE)


def clean_rewrite(text: str) -> str:
    """Remove 'Here is the rewritten CV…' preambles and trailing 'Note: …' paragraphs."""
    out = _PREAMBLE_RE.sub("", (text or "").strip(), count=1)
    out = _TRAILER_RE.sub("", out)
    return out.strip()


def _plain(line: str) -> str:
    """Strip markdown emphasis/headers and surrounding punctuation."""
    s = re.sub(r"^#+\s*", "", line.strip())
    s = s.replace("**", "").replace("__", "")
    return s.strip().strip(":").strip()


def _section_of(line: str) -> str | None:
    p = _plain(line).lower()
    if not p or len(p) > 40 or _BULLET_RE.match(line):
        return None
    for key, names in _SECTIONS.items():
        if p in names:
            return key
    return None


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        key = _section_of(line)
        if key:
            current = key
            sections.setdefault(key, [])
            continue
        if current:
            sections[current].append(line.rstrip())
    return sections


def _bullet_body(line: str) -> str:
    return _plain(_BULLET_RE.sub("", line))


def _parse_role_header(line: str) -> dict:
    """'Backend Developer, Nordlicht Software (2021 – present)' → title/company/period."""
    text = _plain(line)
    period = ""
    m = None
    for m in _PERIOD_RE.finditer(text):
        pass  # keep the last date-looking match
    if m:
        period = m.group(1).strip()
        text = (text[:m.start()] + text[m.end():]).strip(" ,|-–—()")
    parts = [p.strip(" ,|-–—") for p in re.split(r"\s+\|\s+|\s+[-–—]\s+|,\s+|\s+at\s+|\s+@\s+", text) if p.strip(" ,|-–—")]
    title = parts[0] if parts else text
    company = ", ".join(parts[1:]) if len(parts) > 1 else ""
    return {"title": title, "company": company, "period": period.replace("--", "–")}


def _is_role_header(line: str, next_lines: list[str]) -> bool:
    raw = line.strip()
    if not raw or _BULLET_RE.match(raw):
        return False
    bold = raw.startswith("**") or raw.startswith("#")
    has_date = bool(_PERIOD_RE.search(raw))
    followed_by_bullets = any(_BULLET_RE.match(n) for n in next_lines[:3] if n.strip())
    return (bold or has_date) and followed_by_bullets and len(_plain(raw)) <= 140


def _parse_experience(lines: list[str]) -> list[dict]:
    roles: list[dict] = []
    current: dict | None = None
    pending: list[str] = []  # plain lines between a header and its bullets (e.g. company on its own line)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if _is_role_header(line, lines[i + 1:]) or (current is None and not _BULLET_RE.match(line)):
            if current is not None and not current["bullets"] and pending is not None and not _BULLET_RE.match(line):
                # Second header line, e.g. "Nordlicht Software | 2021 – present"
                extra = _parse_role_header(line)
                current["company"] = current["company"] or extra["title"]
                current["period"] = current["period"] or extra["period"]
                continue
            current = {**_parse_role_header(line), "bullets": []}
            roles.append(current)
            continue
        if current is None:
            continue
        body = _bullet_body(line)
        if not body:
            continue
        if _BULLET_RE.match(line):
            current["bullets"].append(body)
        elif current["bullets"]:
            current["bullets"][-1] += " " + body  # wrapped bullet continuation
        else:
            extra = _parse_role_header(line)
            current["company"] = current["company"] or extra["title"]
            current["period"] = current["period"] or extra["period"]
    return [r for r in roles if r["title"]]


def _parse_education(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        body = _bullet_body(line) if _BULLET_RE.match(line) else _plain(line)
        if not body:
            continue
        year_m = list(re.finditer(rf"(?:expected\s+)?{_YEAR}", body, re.IGNORECASE))
        year = year_m[-1].group(0) if year_m else ""
        rest = body.replace(year, "").strip(" ,|-–—()") if year else body
        parts = [p.strip() for p in re.split(r",\s+|\s+\|\s+|\s+[-–—]\s+", rest) if p.strip()]
        if not parts:
            continue
        if out and not year and len(parts) == 1 and not out[-1]["institution"]:
            out[-1]["institution"] = parts[0]  # institution on its own line
            continue
        if out and len(body) > 60 and not year and out[-1]["degree"]:
            continue  # coursework/notes line; skip
        if re.match(r"(relevant\s+)?(coursework|courses|modules|projects?|thesis|gpa|grade|honou?rs)\b", parts[0], re.I):
            continue  # detail under a degree, not a degree of its own
        out.append({"degree": parts[0], "institution": ", ".join(parts[1:]), "year": year})
    return out


def _parse_skills(lines: list[str]) -> list[str]:
    skills: list[str] = []
    for line in lines:
        body = _bullet_body(line) if _BULLET_RE.match(line) else _plain(line)
        if not body:
            continue
        if ":" in body and len(body.split(":", 1)[0]) < 30:
            label, desc = (p.strip() for p in body.split(":", 1))
            items = [p.strip() for p in re.split(r",\s*", desc) if p.strip()]
            # "Languages: Python, Go" is a list → use the items;
            # "React: experienced in building …" is a description → use the label.
            is_list = len(items) >= 2 and all(len(p.split()) <= 3 for p in items)
            body = desc if is_list else label
        for item in re.split(r",\s*|\s*[|;•·]\s*", body):
            item = re.sub(r"\s*\([^)]*\)\s*$", "", item).strip(" .-")  # drop "(caching and …)" notes
            if item and len(item) <= 40 and len(item.split()) <= 5 and item.lower() not in {s.lower() for s in skills}:
                skills.append(item)
    return skills[:20]


def parse_rewrite(rewrite_text: str) -> dict | None:
    """
    Parse the rewrite into {summary, skills, experience, education}.
    Returns None if the text doesn't contain enough structure to trust.
    """
    sections = _split_sections(clean_rewrite(rewrite_text))
    summary = " ".join(_plain(ln) for ln in sections.get("summary", []) if ln.strip()).strip()
    experience = _parse_experience(sections.get("experience", []))
    if not summary or not experience:
        return None
    return {
        "summary": summary,
        "skills": _parse_skills(sections.get("skills", [])),
        "experience": experience,
        "education": _parse_education(sections.get("education", [])),
    }
