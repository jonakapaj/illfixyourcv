"""
Offline evaluation of the CV agents against fixed CV / job-description pairs.

Runs the real agents in backend/ai_agents.py (against the local Ollama model)
and scores their output with deterministic checks; no LLM-as-judge.

Checks
  score_skills   6 skills, integer 0-100, not the fallback defaults;
                 strong-fit cases must score higher on average than weak-fit ones
  audit_cv       all three required sections present
  rewrite_cv     required sections present; NO INVENTED ACHIEVEMENTS:
                   - every number in the rewrite must appear in the original CV
                   - no skill the CV lacks (case "missing_skills") is claimed
  structure_cv   valid schema; name/email copied from the CV;
                 every employer / institution exists in the original CV
  cover_letter   word count in 230-370; ends with the candidate's name;
                 same "no invented numbers / skills" checks as the rewrite

Usage (from repo root, Ollama running):
  venv/bin/python eval/run_eval.py                 # all cases
  venv/bin/python eval/run_eval.py --case pm_no_metrics --skip-cover-letter

Writes eval/results/<timestamp>.json (full outputs + check details) and
eval/results/latest.md (summary table).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ai_agents  # noqa: E402
from cases import CASES  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"

AUDIT_SECTIONS = ["EXECUTIVE SUMMARY", "CRITICAL GAPS", "ALIGNMENT MATRIX"]
REWRITE_SECTIONS = ["PROFESSIONAL SUMMARY", "CORE SKILLS", "PROFESSIONAL EXPERIENCE", "EDUCATION"]
DEFAULT_SCORES = {
    "Technical Skills": 50, "Communication": 50, "Experience Fit": 50,
    "Tools & Frameworks": 50, "Domain Knowledge": 50, "Problem Solving": 50,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


_LIST_MARKER_RE = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)


def numbers_in(text: str) -> set[str]:
    """Numeric tokens, normalised so '11,500' == '11500'. List markers ('1. ', '2) ') are ignored."""
    text = _LIST_MARKER_RE.sub("", text or "")
    return {tok.replace(",", "") for tok in _NUM_RE.findall(text)}


def ungrounded_numbers(output: str, source: str) -> list[str]:
    """Numbers in output that do not occur anywhere in the source CV."""
    src = numbers_in(source)
    return sorted(n for n in numbers_in(output) if n not in src)


def _snippet(text: str, start: int, end: int, pad: int = 50) -> str:
    s = " ".join(text[max(0, start - pad): end + pad].split())
    return f"…{s}…"


def claimed_missing_skills(output: str, missing: list[str]) -> list[dict]:
    hits = []
    for skill in missing:
        m = re.search(rf"(?<![\w.]){re.escape(skill)}(?![\w])", output or "", flags=re.IGNORECASE)
        if m:
            hits.append({"skill": skill, "context": _snippet(output, m.start(), m.end())})
    return hits


def has_sections(text: str, sections: list[str]) -> list[str]:
    up = (text or "").upper()
    return [s for s in sections if s not in up]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def matches_known(value: str, known: list[str]) -> bool:
    v = _norm(value)
    if not v:
        return True  # empty field is not an invention
    return any(_norm(k) in v or v in _norm(k) for k in known)


def check(name: str, passed: bool, detail=None) -> dict:
    return {"check": name, "pass": bool(passed), "detail": detail}


def timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, round(time.perf_counter() - t0, 1)


# ── Per-case evaluation ───────────────────────────────────────────────────────

def evaluate_case(case: dict, skip_cover_letter: bool) -> dict:
    cv, jd = case["cv"], case["jd"]
    checks: list[dict] = []
    latency: dict[str, float] = {}
    outputs: dict = {}

    # 1. Scoring
    scores, latency["score_skills"] = timed(ai_agents.score_skills, cv, jd)
    outputs["scores"] = scores
    vals = list(scores.values())
    checks.append(check("scores: 6 skills", len(scores) == 6, len(scores)))
    checks.append(check("scores: ints in 0-100",
                        all(isinstance(v, int) and 0 <= v <= 100 for v in vals)))
    checks.append(check("scores: not fallback defaults", scores != DEFAULT_SCORES))

    # 2. Audit
    audit, latency["audit_cv"] = timed(ai_agents.audit_cv, cv, jd)
    outputs["audit"] = audit
    missing = has_sections(audit, AUDIT_SECTIONS)
    checks.append(check("audit: all sections present", not missing, missing or None))

    # 3. Rewrite
    rewrite, latency["rewrite_cv"] = timed(ai_agents.rewrite_cv, cv, jd, "")
    outputs["rewrite"] = rewrite
    missing = has_sections(rewrite, REWRITE_SECTIONS)
    checks.append(check("rewrite: all sections present", not missing, missing or None))
    bad_nums = ungrounded_numbers(rewrite, cv)
    checks.append(check("rewrite: no invented numbers", not bad_nums, bad_nums or None))
    bad_skills = claimed_missing_skills(rewrite, case["missing_skills"])
    checks.append(check("rewrite: no invented skills", not bad_skills, bad_skills or None))

    # 4. Structure
    cv_data, latency["structure_cv"] = timed(ai_agents.structure_cv, cv, rewrite)
    outputs["cv_data"] = cv_data
    schema_ok = isinstance(cv_data, dict) and all(
        k in cv_data for k in ("name", "email", "summary", "skills", "experience", "education"))
    checks.append(check("structure: schema keys present", schema_ok))
    name_ok = _norm(cv_data.get("name", "")) == _norm(case["full_name"])
    email_ok = (cv_data.get("email") or "").strip().lower() in cv.lower() and bool(cv_data.get("email"))
    checks.append(check("structure: name & email from CV", name_ok and email_ok,
                        {"name": cv_data.get("name"), "email": cv_data.get("email")}))
    exp = cv_data.get("experience") or []
    edu = cv_data.get("education") or []
    fake_emp = [e.get("company") for e in exp if isinstance(e, dict)
                and not matches_known(e.get("company", ""), case["employers"])]
    fake_edu = [e.get("institution") for e in edu if isinstance(e, dict)
                and not matches_known(e.get("institution", ""), case["institutions"])]
    checks.append(check("structure: no invented employers", not fake_emp, fake_emp or None))
    checks.append(check("structure: no invented institutions", not fake_edu, fake_edu or None))
    checks.append(check("structure: all employers kept",
                        len(exp) >= len(case["employers"]), f"{len(exp)}/{len(case['employers'])}"))

    # 5. Cover letter
    if not skip_cover_letter:
        letter, latency["cover_letter"] = timed(
            ai_agents.generate_cover_letter, cv, jd, case["full_name"],
            case["target_company"], case["target_role"], case["key_achievement"],
        )
        outputs["cover_letter"] = letter
        words = len(letter.split())
        checks.append(check("cover letter: 230-370 words", 230 <= words <= 370, words))
        last_line = letter.strip().splitlines()[-1] if letter.strip() else ""
        checks.append(check("cover letter: signed with name",
                            _norm(case["full_name"]) in _norm(last_line), last_line))
        # The target company/role are given to the model, so they are allowed sources too.
        allowed = cv + case["target_role"] + case["target_company"]
        bad_nums = ungrounded_numbers(letter, allowed)
        checks.append(check("cover letter: no invented numbers", not bad_nums, bad_nums or None))
        bad_skills = claimed_missing_skills(letter, case["missing_skills"])
        checks.append(check("cover letter: no invented skills", not bad_skills, bad_skills or None))

    return {
        "id": case["id"],
        "expected_fit": case["expected_fit"],
        "avg_score": round(sum(vals) / len(vals), 1) if vals else None,
        "latency_s": latency,
        "checks": checks,
        "passed": sum(c["pass"] for c in checks),
        "total": len(checks),
        "outputs": outputs,
    }


# ── Reporting ─────────────────────────────────────────────────────────────────

def cross_case_checks(results: list[dict]) -> list[dict]:
    strong = [r["avg_score"] for r in results if r["expected_fit"] == "strong" and r["avg_score"] is not None]
    weak = [r["avg_score"] for r in results if r["expected_fit"] == "weak" and r["avg_score"] is not None]
    if not strong or not weak:
        return []
    ok = min(strong) > max(weak)
    return [check("ranking: strong-fit CVs score above weak-fit CVs", ok,
                  {"strong": strong, "weak": weak})]


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        f"# CV agent eval — {report['timestamp']}",
        "",
        f"Model: `{report['model']}` · cases: {len(report['cases'])} · "
        f"checks passed: **{report['passed']}/{report['total']}** · "
        f"invented-content checks passed: **{report['grounding_passed']}/{report['grounding_total']}**",
        "",
        "| Case | Fit | Avg score | Checks | Latency (s) |",
        "|---|---|---|---|---|",
    ]
    for r in report["cases"]:
        lat = sum(r["latency_s"].values())
        lines.append(f"| {r['id']} | {r['expected_fit']} | {r['avg_score']} | "
                     f"{r['passed']}/{r['total']} | {lat:.0f} |")
    lines += ["", "## Failed checks", ""]
    any_fail = False
    for r in report["cases"]:
        for c in r["checks"]:
            if not c["pass"]:
                any_fail = True
                lines.append(f"- **{r['id']}** — {c['check']}: `{json.dumps(c['detail'], ensure_ascii=False)}`")
    for c in report["cross_case"]:
        if not c["pass"]:
            any_fail = True
            lines.append(f"- **cross-case** — {c['check']}: `{json.dumps(c['detail'])}`")
    if not any_fail:
        lines.append("None.")
    lines += ["", "## Mean latency per agent (s)", ""]
    agents = sorted({a for r in report["cases"] for a in r["latency_s"]})
    for a in agents:
        xs = [r["latency_s"][a] for r in report["cases"] if a in r["latency_s"]]
        lines.append(f"- {a}: {sum(xs) / len(xs):.1f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", help="run only this case id (repeatable)")
    ap.add_argument("--skip-cover-letter", action="store_true")
    args = ap.parse_args()

    cases = [c for c in CASES if not args.case or c["id"] in args.case]
    if not cases:
        print("No matching cases.", file=sys.stderr)
        return 2

    model = ai_agents._resolve_model_name()
    print(f"Model: {model} · {len(cases)} case(s)")
    results = []
    for case in cases:
        print(f"\n▶ {case['id']}", flush=True)
        r = evaluate_case(case, args.skip_cover_letter)
        for c in r["checks"]:
            mark = "PASS" if c["pass"] else "FAIL"
            extra = "" if c["pass"] or c["detail"] is None else f"  {json.dumps(c['detail'], ensure_ascii=False)[:160]}"
            print(f"  [{mark}] {c['check']}{extra}")
        print(f"  avg score {r['avg_score']} · latency {r['latency_s']}")
        results.append(r)

    cross = cross_case_checks(results)
    for c in cross:
        print(f"\n[{'PASS' if c['pass'] else 'FAIL'}] {c['check']}  {json.dumps(c['detail'])}")

    all_checks = [c for r in results for c in r["checks"]] + cross
    grounding = [c for c in all_checks if "invented" in c["check"]]
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report = {
        "timestamp": ts,
        "model": model,
        "passed": sum(c["pass"] for c in all_checks),
        "total": len(all_checks),
        "grounding_passed": sum(c["pass"] for c in grounding),
        "grounding_total": len(grounding),
        "cross_case": cross,
        "cases": results,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{ts}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, RESULTS_DIR / "latest.md")
    print(f"\nPassed {report['passed']}/{report['total']} checks "
          f"(invented-content: {report['grounding_passed']}/{report['grounding_total']})")
    print(f"Report: {RESULTS_DIR / 'latest.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
