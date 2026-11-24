"""
pdf_templates.py — CV and cover-letter PDFs using fpdf2.

Three CV templates share the same helpers so they behave the same way:
  * real bullet dots with a hanging indent (wrapped lines align with the text)
  * left-aligned text (no justified "rivers")
  * "Company · Period" lines that drop empty parts instead of leaving "Company |"
  * a role's header is kept together with its first bullet across page breaks
  * proper top margin on every page
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from fpdf import FPDF, XPos, YPos

# ── Text helpers ──────────────────────────────────────────────────────────────

_MAP = {
    "•": "-", "▸": ">", "►": ">", "‣": "-", "⁃": "-",
    "★": "*", "☆": "*", "✓": "", "✔": "", "✗": "", "✘": "",
    "–": "-", "—": "-", "―": "-", "‒": "-", "−": "-",
    "→": "->", "←": "<-", "⇒": "=>", "➔": "->",
    "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "‚": ",",
    "…": "...", " ": " ", " ": " ", " ": " ", "​": "",
    "≈": "~", "≠": "!=", "≥": ">=", "≤": "<=",
    # Letters with no Unicode decomposition
    "Ł": "L", "ł": "l", "Đ": "D", "đ": "d", "Œ": "OE", "œ": "oe",
    "ı": "i", "Ħ": "H", "ħ": "h", "Ŧ": "T", "ŧ": "t",
}


def _s(text) -> str:
    """Make text safe for the built-in latin-1 fonts, keeping accents where possible."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    for char, repl in _MAP.items():
        text = text.replace(char, repl)
    out = []
    for ch in text:
        try:
            ch.encode("latin-1")
            out.append(ch)
        except UnicodeEncodeError:
            # ł → l, ș → s, … ; anything else is dropped rather than shown as "?"
            base = unicodedata.normalize("NFKD", ch).encode("latin-1", "ignore").decode("latin-1")
            out.append(base)
    return "".join(out)


def _join(*parts, sep: str = "  ·  ") -> str:
    """Join non-empty parts: ('ACME', '') -> 'ACME' (no dangling separator)."""
    return sep.join(_s(p).strip() for p in parts if p and str(p).strip())


def _bullet_text(b) -> str:
    return re.sub(r"^\s*[-*•▸►]\s*", "", str(b or "")).strip()


def _list(cv: dict, key: str) -> list:
    val = cv.get(key) or []
    return val if isinstance(val, list) else []


def _has_room(pdf: FPDF, needed_mm: float) -> bool:
    return pdf.get_y() + needed_mm <= pdf.h - pdf.b_margin


def _bullet(pdf: FPDF, x: float, width: float, text: str, line_h: float, dot_rgb=(60, 60, 60)) -> None:
    """A round bullet with a hanging indent."""
    if not text:
        return
    if not _has_room(pdf, line_h):
        pdf.add_page()
    y = pdf.get_y()
    pdf.set_fill_color(*dot_rgb)
    pdf.ellipse(x + 0.6, y + line_h / 2 - 0.7, 1.4, 1.4, style="F")
    pdf.set_xy(x + 4.5, y)
    pdf.multi_cell(width - 4.5, line_h, _s(text), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _new_pdf(cls=FPDF, margins=(18, 16, 18), bottom=16) -> FPDF:
    pdf = cls(format="A4")
    pdf.set_margins(*margins)
    pdf.set_auto_page_break(auto=True, margin=bottom)
    pdf.set_title("Curriculum Vitae")
    return pdf


def _contact_items(cv: dict) -> list[str]:
    return [cv.get(k) for k in ("email", "phone", "location", "linkedin") if cv.get(k)]


# ── TEMPLATE 1: EXECUTIVE (corporate) ────────────────────────────────────────

def build_corporate(cv_data: dict) -> bytes:
    NAVY, GOLD, INK, GREY = (17, 45, 78), (194, 144, 28), (30, 30, 30), (95, 95, 95)
    pdf = _new_pdf()
    pdf.add_page()
    W = pdf.w

    # Header band
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, W, 34, "F")
    pdf.set_fill_color(*GOLD)
    pdf.rect(0, 34, W, 1.4, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(18, 8)
    pdf.cell(0, 10, _s(cv_data.get("name") or "Your Name"))
    if cv_data.get("current_title"):
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(200, 214, 232)
        pdf.set_xy(18, 19)
        pdf.cell(0, 7, _s(cv_data["current_title"]))

    pdf.set_y(39)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 5, _join(*_contact_items(cv_data), sep="   |   "), align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    def section(title: str) -> None:
        if not _has_room(pdf, 22):
            pdf.add_page()
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*GOLD)
        pdf.set_line_width(0.6)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 14, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(*INK)

    if cv_data.get("summary"):
        section("Professional Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.4, _s(cv_data["summary"]), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    if _list(cv_data, "skills"):
        section("Core Skills")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.4, _join(*cv_data["skills"], sep="   ·   "), align="L",
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    if _list(cv_data, "experience"):
        section("Professional Experience")
        for exp in cv_data["experience"]:
            if not isinstance(exp, dict):
                continue
            if not _has_room(pdf, 18):
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(0, 5.6, _s(exp.get("title")), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            meta = _join(exp.get("company"), exp.get("period"))
            if meta:
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(*GREY)
                pdf.cell(0, 5, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*INK)
            for b in exp.get("bullets") or []:
                _bullet(pdf, pdf.l_margin + 1, pdf.epw - 1, _bullet_text(b), 5.3, NAVY)
            pdf.ln(3)

    if _list(cv_data, "education"):
        section("Education")
        for edu in cv_data["education"]:
            if not isinstance(edu, dict):
                continue
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(0, 5.6, _s(edu.get("degree")), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            meta = _join(edu.get("institution"), edu.get("year"))
            if meta:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*GREY)
                pdf.cell(0, 5, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2.5)

    return bytes(pdf.output())


# ── TEMPLATE 2: MODERN (tech) ─────────────────────────────────────────────────

def build_tech_modern(cv_data: dict) -> bytes:
    ACCENT, DARK, INK, GREY = (79, 70, 229), (24, 24, 48), (32, 32, 40), (110, 110, 125)
    CHIP_BG = (237, 236, 253)
    pdf = _new_pdf()
    pdf.add_page()
    W = pdf.w

    # Header: name/title left, contact stacked right
    pdf.set_fill_color(*DARK)
    pdf.rect(0, 0, W, 38, "F")
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 38, W, 1.6, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(18, 9)
    pdf.cell(110, 10, _s(cv_data.get("name") or "Your Name"))
    if cv_data.get("current_title"):
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(180, 176, 250)
        pdf.set_xy(18, 20)
        pdf.cell(110, 7, _s(cv_data["current_title"]))
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(215, 215, 230)
    y = 9
    for item in _contact_items(cv_data)[:4]:
        pdf.set_xy(W - 18 - 70, y)
        pdf.cell(70, 5, _s(item), align="R")
        y += 5
    pdf.set_y(47)

    def section(title: str) -> None:
        if not _has_room(pdf, 22):
            pdf.add_page()
        y0 = pdf.get_y()
        pdf.set_fill_color(*ACCENT)
        pdf.rect(pdf.l_margin, y0 + 1.2, 2.2, 4.6, "F")
        pdf.set_xy(pdf.l_margin + 5, y0)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.5)
        pdf.set_text_color(*INK)

    if cv_data.get("summary"):
        section("Profile")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.4, _s(cv_data["summary"]), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    skills = [_s(s).strip() for s in _list(cv_data, "skills") if str(s).strip()]
    if skills:
        section("Skills")
        pdf.set_font("Helvetica", "", 9)
        x, y = pdf.l_margin, pdf.get_y()
        h, pad, gap = 6.2, 2.6, 2.2
        right = W - pdf.r_margin
        for s in skills:
            w = min(pdf.get_string_width(s) + 2 * pad, right - pdf.l_margin)
            if x + w > right:
                x, y = pdf.l_margin, y + h + gap
            pdf.set_fill_color(*CHIP_BG)
            pdf.rect(x, y, w, h, style="F", round_corners=True, corner_radius=1.6)
            pdf.set_text_color(*ACCENT)
            pdf.set_xy(x, y)
            pdf.cell(w, h, s, align="C")
            x += w + gap
        pdf.set_y(y + h + 6)
        pdf.set_text_color(*INK)

    if _list(cv_data, "experience"):
        section("Experience")
        for exp in cv_data["experience"]:
            if not isinstance(exp, dict):
                continue
            if not _has_room(pdf, 18):
                pdf.add_page()
            period = _s(exp.get("period")).strip()
            pdf.set_font("Helvetica", "I", 9)
            period_w = pdf.get_string_width(period) + 2 if period else 0
            y0 = pdf.get_y()
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(pdf.epw - period_w - 4, 5.6, _s(exp.get("title")), align="L",
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y_after = pdf.get_y()
            if period:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*GREY)
                pdf.set_xy(W - pdf.r_margin - period_w, y0)
                pdf.cell(period_w, 5.6, period, align="R")
                pdf.set_y(y_after)
            if exp.get("company"):
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.set_text_color(*ACCENT)
                pdf.cell(0, 5, _s(exp["company"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 9.8)
            pdf.set_text_color(*INK)
            for b in exp.get("bullets") or []:
                _bullet(pdf, pdf.l_margin + 1, pdf.epw - 1, _bullet_text(b), 5.2, ACCENT)
            pdf.ln(3.5)

    if _list(cv_data, "education"):
        section("Education")
        for edu in cv_data["education"]:
            if not isinstance(edu, dict):
                continue
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(0, 5.6, _s(edu.get("degree")), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            meta = _join(edu.get("institution"), edu.get("year"))
            if meta:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*GREY)
                pdf.cell(0, 5, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2.5)

    return bytes(pdf.output())


# ── TEMPLATE 3: MINIMAL (sidebar) ─────────────────────────────────────────────

def build_minimal_slate(cv_data: dict) -> bytes:
    SB = 64           # sidebar width (mm)
    SIDE, LIGHT, ACCENT = (40, 48, 64), (205, 215, 230), (125, 180, 240)
    INK, GREY = (30, 30, 36), (100, 100, 110)
    MX = SB + 10      # main column x

    class SlatePDF(FPDF):
        def header(self):
            # Sidebar background on every page
            self.set_fill_color(*SIDE)
            self.rect(0, 0, SB, self.h, "F")

    pdf = _new_pdf(SlatePDF, margins=(MX, 16, 14))
    pdf.add_page()
    W = pdf.w
    MW = W - MX - pdf.r_margin

    # ── Main column first (it controls page count), sidebar afterwards ───────
    def section(title: str) -> None:
        if not _has_room(pdf, 22):
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(*SIDE)
        pdf.cell(MW, 6, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*ACCENT)
        pdf.set_line_width(0.5)
        pdf.line(MX, pdf.get_y(), MX + MW, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(*INK)

    pdf.set_y(16)
    if cv_data.get("summary"):
        section("Profile")
        pdf.set_font("Helvetica", "", 9.8)
        pdf.multi_cell(MW, 5.3, _s(cv_data["summary"]), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    if _list(cv_data, "experience"):
        section("Experience")
        for exp in cv_data["experience"]:
            if not isinstance(exp, dict):
                continue
            if not _has_room(pdf, 18):
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*INK)
            pdf.multi_cell(MW, 5.5, _s(exp.get("title")), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            meta = _join(exp.get("company"), exp.get("period"))
            if meta:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*GREY)
                pdf.cell(MW, 5, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.8)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*INK)
            for b in exp.get("bullets") or []:
                _bullet(pdf, MX, MW, _bullet_text(b), 5.0, SIDE)
            pdf.ln(3)

    if _list(cv_data, "education"):
        section("Education")
        for edu in cv_data["education"]:
            if not isinstance(edu, dict):
                continue
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*INK)
            pdf.multi_cell(MW, 5.5, _s(edu.get("degree")), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            meta = _join(edu.get("institution"), edu.get("year"))
            if meta:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*GREY)
                pdf.cell(MW, 5, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2.5)

    # ── Sidebar on page 1 ─────────────────────────────────────────────────────
    last_page = pdf.page
    pdf.page = 1
    pdf.set_auto_page_break(False)
    pdf.set_left_margin(8)
    SW = SB - 16

    pdf.set_xy(8, 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(SW, 7.5, _s(cv_data.get("name") or "Your Name"), align="L",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if cv_data.get("current_title"):
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*ACCENT)
        pdf.multi_cell(SW, 4.8, _s(cv_data["current_title"]), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def sb_heading(title: str) -> None:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*ACCENT)
        pdf.cell(SW, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*ACCENT)
        pdf.set_line_width(0.3)
        pdf.line(8, pdf.get_y(), 8 + 10, pdf.get_y())
        pdf.ln(2)

    contact = _contact_items(cv_data)
    if contact:
        sb_heading("CONTACT")
        pdf.set_font("Helvetica", "", 8.2)
        pdf.set_text_color(*LIGHT)
        for val in contact:
            pdf.multi_cell(SW, 4.6, _s(val), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.8)

    skills = _list(cv_data, "skills")
    if skills:
        sb_heading("SKILLS")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*LIGHT)
        for skill in skills:
            if pdf.get_y() > pdf.h - 20:
                break  # sidebar is page-1 only; stop rather than overflow
            _bullet(pdf, 8, SW, _bullet_text(skill), 4.7, ACCENT)

    pdf.page = last_page
    return bytes(pdf.output())


# ── COVER LETTER ──────────────────────────────────────────────────────────────

_PREAMBLE_RE = re.compile(
    r"^\s*(?:sure|certainly|of course|okay|ok)?[!,.\s]*"
    r"(?:here(?:'s| is)|below is|i(?:'ve| have) (?:written|drafted|prepared))\b[^\n]*\n+",
    re.IGNORECASE,
)
_TRAILER_RE = re.compile(
    r"\n+\s*(?:note|notes|p\.?s\.?|i hope this|feel free|let me know|this (?:cover )?letter)\b[\s\S]*$",
    re.IGNORECASE,
)


def clean_cover_letter(text: str, full_name: str = "") -> str:
    """
    Strip model chatter ("Here is a cover letter for …:", trailing notes),
    placeholder lines like "[Your Name]", and a trailing signature block —
    the PDF adds its own sign-off with the candidate's name.
    """
    out = (text or "").strip()
    out = _PREAMBLE_RE.sub("", out, count=1).strip()
    out = _TRAILER_RE.sub("", out).strip()
    out = re.sub(r"^\s*\[[^\]\n]{1,40}\]\s*$", "", out, flags=re.MULTILINE)  # [Your Name], [Date]…
    lines = out.splitlines()
    # Remove trailing sign-off lines: name, "Best regards," etc.
    sign_offs = ("sincerely", "best regards", "kind regards", "regards", "best", "thank you",
                 "yours sincerely", "yours faithfully", "warm regards", "warmly", "cheers")
    name_norm = re.sub(r"\W+", "", (full_name or "").lower())
    while lines:
        last = lines[-1].strip()
        norm = re.sub(r"\W+", "", last.lower())
        if not last or (name_norm and norm == name_norm) or last.lower().rstrip(",.!") in sign_offs:
            lines.pop()
        else:
            break
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def build_cover_letter(letter_data: dict) -> bytes:
    ACCENT, INK, GREY = (79, 70, 229), (30, 30, 36), (100, 100, 110)
    pdf = _new_pdf(margins=(22, 20, 22), bottom=20)
    pdf.set_title("Cover Letter")
    pdf.add_page()
    W = pdf.w
    name = letter_data.get("full_name") or ""

    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 0, W, 3, "F")
    pdf.set_xy(22, 18)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*INK)
    pdf.cell(0, 9, _s(name or "Your Name"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    contact = _join(letter_data.get("email"), letter_data.get("phone"),
                    letter_data.get("location"), letter_data.get("linkedin"), sep="   |   ")
    if contact:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 5, contact, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(225, 225, 232)
    pdf.set_line_width(0.3)
    pdf.ln(5)
    pdf.line(22, pdf.get_y(), W - 22, pdf.get_y())
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5.5, datetime.now().strftime("%d %B %Y"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    recipient = _join(letter_data.get("target_role"), letter_data.get("target_company"), sep=", ")
    if recipient:
        pdf.set_text_color(*INK)
        pdf.cell(0, 5.5, f"Re: {recipient}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    body = clean_cover_letter(letter_data.get("cover_letter", ""), name)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*INK)
    for para in [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]:
        pdf.multi_cell(0, 6, _s(" ".join(para.split("\n")) if not para.lower().startswith("dear") else para),
                       align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3.5)

    pdf.ln(2)
    pdf.cell(0, 6, "Kind regards,", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 6, _s(name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())
