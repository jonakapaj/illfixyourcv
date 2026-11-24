"""
grounding.py — deterministic checks that generated text only uses facts from the CV.

Used in two places:
  * ai_agents.py, to steer the rewrite / cover letter and repair them after generation
  * eval/run_eval.py, to measure how often the model still invents content

No LLM calls here: everything is plain string matching, so results are
reproducible and cheap.
"""

from __future__ import annotations

import re

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")

# Tokens that look like named skills/tools: PostgreSQL, Next.js, C#, CI/CD, dbt, AWS…
_TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[.+#/-][A-Za-z0-9+#]+)*[+#]*")

# Capitalised words that are almost never a skill claim.
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on",
    "or", "our", "the", "to", "we", "with", "you", "your", "will", "this", "that", "who", "what",
    "requirements", "required", "responsibilities", "nice", "have", "plus", "bonus", "preferred",
    "experience", "experienced", "years", "year", "strong", "solid", "good", "great", "excellent",
    "ability", "able", "knowledge", "skills", "skill", "team", "teams", "role", "job", "position",
    "company", "candidate", "about", "us", "looking", "join", "work", "working", "build", "building",
    "ideally", "similar", "including", "etc", "e.g", "i.e", "junior", "senior", "lead", "mid",
    "engineer", "developer", "manager", "designer", "analyst", "intern", "remote", "hybrid", "onsite",
    "full", "time", "part", "contract", "benefits", "salary", "daily", "eye", "comfortable",
    "familiarity", "familiar", "understanding", "proven", "track", "record", "minimum", "must",
    "data", "tools", "tooling", "systems", "platform", "products", "product", "users", "customers",
}


_LIST_MARKER_RE = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)


def numbers_in(text: str) -> set[str]:
    """Numeric tokens, normalised so '11,500' == '11500'. List markers ('1. ', '2) ') are ignored."""
    text = _LIST_MARKER_RE.sub("", text or "")
    return {tok.replace(",", "") for tok in _NUM_RE.findall(text)}


def ungrounded_numbers(output: str, source: str) -> list[str]:
    """Numbers in `output` that never occur in `source`."""
    src = numbers_in(source)
    return sorted(n for n in numbers_in(output) if n not in src)


def _contains(text: str, term: str) -> bool:
    """Whole-word, case-insensitive match (so 'Go' does not match 'good')."""
    return re.search(rf"(?<![\w.]){re.escape(term)}(?![\w])", text or "", flags=re.IGNORECASE) is not None


def _in_cv(cv_text: str, term: str) -> bool:
    """Lenient match for the CV side: 'SQL' counts as present if the CV says 'PostgreSQL'."""
    return term.lower() in (cv_text or "").lower()


def _looks_generic(tok: str) -> bool:
    low = tok.lower()
    return low in _STOP or low.endswith(("ing", "ed", "ly", "tion", "tions", "ment", "ness", "ity"))


def job_terms(job_desc: str) -> list[str]:
    """
    Skill-like terms from a job description:
      * tokens with internal capitals, digits or symbols: PostgreSQL, Next.js, C#, CI/CD, AWS
      * short vowel-less lowercase tokens: dbt, npm
      * other capitalised words that are not generic English: Kubernetes, Kafka, Jira
    The first line is skipped when it looks like a title ("Acme — Backend Engineer").
    """
    lines = [ln for ln in (job_desc or "").splitlines() if ln.strip()]
    if len(lines) > 1 and len(lines[0].split()) <= 12 and not lines[0].rstrip().endswith((".", ":")):
        lines = lines[1:]
    terms: dict[str, str] = {}
    for line in lines:
        body = re.sub(r"^\s*(?:[-*•·▪]|\d+[.)])\s*", "", line)
        for m in _TERM_RE.finditer(body):
            tok = m.group(0).strip(".-/")
            if len(tok) < 2 or tok.lower() in _STOP:
                continue
            techy = (
                any(c in tok for c in ".+#/") or any(ch.isdigit() for ch in tok)
                or (tok.isupper() and len(tok) >= 2)
                or any(ch.isupper() for ch in tok[1:])
                or (tok.islower() and len(tok) <= 5 and not re.search(r"[aeiouy]", tok))
            )
            named = tok[0].isupper() and not _looks_generic(tok)
            if techy or named:
                terms.setdefault(tok.lower(), tok)
    return list(terms.values())


def missing_job_terms(cv_text: str, job_desc: str) -> list[str]:
    """Job-description terms that the CV never mentions: things the CV must not claim."""
    return [t for t in job_terms(job_desc) if not _in_cv(cv_text, t)]


def unsupported_terms(output: str, cv_text: str, job_desc: str, allowed: str = "") -> list[str]:
    """Terms the JD asks for, the CV lacks, and the output nonetheless mentions."""
    return [t for t in missing_job_terms(cv_text + "\n" + allowed, job_desc) if _contains(output, t)]


def grounding_report(output: str, cv_text: str, job_desc: str, allowed: str = "") -> dict:
    """{'numbers': [...], 'terms': [...]} of content in `output` not backed by the CV."""
    source = cv_text + "\n" + allowed
    return {
        "numbers": ungrounded_numbers(output, source),
        "terms": unsupported_terms(output, cv_text, job_desc, allowed),
    }


def is_clean(report: dict) -> bool:
    return not report.get("numbers") and not report.get("terms")
