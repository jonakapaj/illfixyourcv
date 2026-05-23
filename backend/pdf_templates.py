"""
pdf_templates.py — Three CV PDF templates using fpdf2.
"""
from fpdf import FPDF, XPos, YPos
from datetime import datetime


def _s(text):
    """Substitute common unicode chars with latin-1 equivalents, then encode safely."""
    if not isinstance(text, str):
        text = str(text)
    _MAP = {
        # Bullets & symbols
        "\u2022": "-",   # •
        "\u25b8": ">",   # ▸
        "\u25ba": ">",   # ►
        "\u2023": "-",   # ‣
        "\u2043": "-",   # ⁃
        "\u2605": "*",   # ★
        "\u2606": "*",   # ☆
        "\u2713": "OK",  # ✓
        "\u2714": "OK",  # ✔
        "\u2717": "X",   # ✗
        "\u2718": "X",   # ✘
        # Dashes & hyphens
        "\u2013": "-",   # –
        "\u2014": "-",   # —
        "\u2015": "-",   # ―
        "\u2012": "-",   # ‒
        # Arrows
        "\u2192": "->",  # →
        "\u2190": "<-",  # ←
        "\u21d2": "=>",  # ⇒
        "\u2794": "->",  # ➔
        # Quotes
        "\u201c": '"',   # "
        "\u201d": '"',   # "
        "\u2018": "'",   # '
        "\u2019": "'",   # '
        "\u201a": ",",   # ‚
        "\u00ab": "<<",  # «
        "\u00bb": ">>",  # »
        # Ellipsis & spaces
        "\u2026": "...", # …
        "\u00a0": " ",   # non-breaking space
        "\u2009": " ",   # thin space
        "\u200b": "",    # zero-width space
        # Math / misc
        "\u00d7": "x",   # ×
        "\u00f7": "/",   # ÷
        "\u00b7": ".",   # ·
        "\u2248": "~",   # ≈
        "\u2260": "!=",  # ≠
        "\u2265": ">=",  # ≥
        "\u2264": "<=",  # ≤
    }
    for char, repl in _MAP.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", "replace").decode("latin-1")


# ── TEMPLATE 1: CORPORATE CLASSIC ────────────────────────────────────────────
def build_corporate(cv_data: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    W = pdf.w

    # Navy header
    pdf.set_fill_color(17, 45, 78)
    pdf.rect(0, 0, W, 44, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_xy(18, 8)
    pdf.cell(0, 12, _s(cv_data.get("name", "Your Name")),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_xy(18, 23)
    pdf.cell(0, 7, _s(cv_data.get("current_title", "Software Engineer")),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Gold contact strip
    pdf.set_fill_color(194, 144, 28)
    pdf.rect(0, 44, W, 11, "F")
    contact = "  |  ".join(filter(None, [
        cv_data.get("email"), cv_data.get("phone"),
        cv_data.get("location"), cv_data.get("linkedin")
    ]))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(18, 46.5)
    pdf.cell(0, 6, _s(contact), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(30, 30, 30)
    pdf.set_y(63)

    def section(title):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(17, 45, 78)
        pdf.cell(0, 7, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(17, 45, 78)
        pdf.set_line_width(0.5)
        pdf.line(pdf.l_margin, pdf.get_y(), W - pdf.r_margin, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(30, 30, 30)

    if cv_data.get("summary"):
        section("Professional Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, _s(cv_data["summary"]))
        pdf.ln(4)

    if cv_data.get("skills"):
        section("Technical Skills")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, _s("  •  ".join(cv_data["skills"])))
        pdf.ln(4)

    if cv_data.get("experience"):
        section("Professional Experience")
        for exp in cv_data["experience"]:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.cell(0, 6, _s(exp.get("title", "")),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5,
                     _s(f'{exp.get("company","")}  |  {exp.get("period","")}'),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(30, 30, 30)
            pdf.set_font("Helvetica", "", 10)
            for b in exp.get("bullets", []):
                pdf.set_x(pdf.l_margin + 4)
                pdf.multi_cell(0, 5.5, _s(f"• {b}"))
            pdf.ln(3)

    if cv_data.get("education"):
        section("Education")
        for edu in cv_data["education"]:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.cell(0, 6, _s(edu.get("degree", "")),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5,
                     _s(f'{edu.get("institution","")}  |  {edu.get("year","")}'),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(30, 30, 30)
            pdf.ln(2)

    return bytes(pdf.output())


# ── TEMPLATE 2: TECH MODERN ───────────────────────────────────────────────────
def build_tech_modern(cv_data: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    W = pdf.w

    # Two-tone header
    pdf.set_fill_color(0, 168, 204)
    pdf.rect(0, 0, W, 42, "F")
    pdf.set_fill_color(20, 80, 160)
    pdf.rect(W * 0.55, 0, W * 0.45, 42, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_xy(18, 7)
    pdf.cell(0, 13, _s(cv_data.get("name", "Your Name")),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(18, 23)
    pdf.cell(0, 7, _s(cv_data.get("current_title", "Software Engineer")),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Contact strip
    pdf.set_fill_color(15, 50, 110)
    pdf.rect(0, 42, W, 12, "F")
    contact = "  *  ".join(filter(None, [
        cv_data.get("email"), cv_data.get("phone"),
        cv_data.get("location"), cv_data.get("linkedin")
    ]))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(160, 215, 255)
    pdf.set_xy(18, 45)
    pdf.cell(0, 6, _s(contact), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(30, 30, 30)
    pdf.set_y(62)

    def section(title):
        y = pdf.get_y()
        pdf.set_fill_color(0, 168, 204)
        pdf.rect(18, y, 4, 8, "F")
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 120, 170)
        pdf.set_xy(26, y)
        pdf.cell(0, 8, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(30, 30, 30)
        pdf.ln(2)

    # Skills 2-column grid
    if cv_data.get("skills"):
        section("Technical Skills")
        skills = cv_data["skills"]
        mid = (len(skills) + 1) // 2
        col1, col2 = skills[:mid], skills[mid:]
        pdf.set_font("Helvetica", "", 10)
        y_start = pdf.get_y()
        for s in col1:
            pdf.set_xy(26, pdf.get_y())
            pdf.cell(85, 5.5, _s(f">  {s}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        y_end = pdf.get_y()
        pdf.set_y(y_start)
        for s in col2:
            pdf.set_xy(112, pdf.get_y())
            pdf.cell(80, 5.5, _s(f">  {s}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(max(y_end, pdf.get_y()))
        pdf.ln(5)

    if cv_data.get("summary"):
        section("Professional Summary")
        pdf.set_x(26)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, _s(cv_data["summary"]))
        pdf.ln(5)

    if cv_data.get("experience"):
        section("Experience")
        for exp in cv_data["experience"]:
            pdf.set_x(26)
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(30, 30, 30)
            title_text = _s(exp.get("title", ""))
            period_text = _s(exp.get("period", ""))
            pdf.cell(120, 6, title_text)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 6, period_text,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
            pdf.set_x(26)
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.set_text_color(0, 140, 180)
            pdf.cell(0, 5, _s(exp.get("company", "")),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(50, 50, 50)
            pdf.set_font("Helvetica", "", 9.5)
            for b in exp.get("bullets", []):
                pdf.set_x(30)
                pdf.multi_cell(0, 5.5, _s(f"• {b}"))
            pdf.ln(4)

    if cv_data.get("education"):
        section("Education")
        for edu in cv_data["education"]:
            pdf.set_x(26)
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(0, 6, _s(edu.get("degree", "")),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(26)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5,
                     _s(f'{edu.get("institution","")}  |  {edu.get("year","")}'),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(30, 30, 30)
            pdf.ln(3)

    return bytes(pdf.output())


# ── TEMPLATE 3: MINIMAL SLATE ─────────────────────────────────────────────────
def build_minimal_slate(cv_data: dict) -> bytes:
    SB = 66  # sidebar width mm

    class SlatePDF(FPDF):
        def header(self):
            # Redraw sidebar background on every new page
            self.set_fill_color(45, 55, 72)
            self.rect(0, 0, SB, self.h, "F")

    pdf = SlatePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(0, 0, 0)
    W = pdf.w

    # ── Sidebar content (first page only) ────────────────────────────────────
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_xy(8, 16)
    parts = _s(cv_data.get("name", "Your Name")).split()
    if len(parts) >= 2:
        pdf.cell(SB - 12, 9, parts[0], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(8)
        pdf.cell(SB - 12, 9, " ".join(parts[1:]),
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.multi_cell(SB - 12, 9, " ".join(parts))

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(147, 197, 253)
    pdf.set_x(8)
    pdf.multi_cell(SB - 12, 5, _s(cv_data.get("current_title", "Software Engineer")))

    # Accent line
    pdf.set_draw_color(99, 179, 237)
    pdf.set_line_width(0.7)
    y_line = pdf.get_y() + 4
    pdf.line(8, y_line, SB - 8, y_line)

    def sb_heading(title):
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(99, 179, 237)
        pdf.set_x(8)
        pdf.cell(0, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(y_line + 6)
    sb_heading("CONTACT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(200, 220, 235)
    for field in ["email", "phone", "location", "linkedin"]:
        val = cv_data.get(field, "")
        if val:
            pdf.set_x(8)
            pdf.multi_cell(SB - 12, 4.8, _s(val))

    if cv_data.get("skills"):
        pdf.ln(4)
        sb_heading("SKILLS")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(200, 220, 235)
        for skill in cv_data["skills"]:
            pdf.set_x(8)
            pdf.multi_cell(SB - 12, 4.8, _s(f"• {skill}"))

    # ── Main content ──────────────────────────────────────────────────────────
    MX = SB + 10
    MW = W - SB - 14

    def main_section(title):
        pdf.set_x(MX)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(MW, 7, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(99, 179, 237)
        pdf.set_line_width(0.5)
        pdf.line(MX, pdf.get_y(), W - 5, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(30, 30, 30)

    pdf.set_y(16)

    if cv_data.get("summary"):
        main_section("Profile")
        pdf.set_x(MX)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.multi_cell(MW, 5.5, _s(cv_data["summary"]))
        pdf.ln(5)

    if cv_data.get("experience"):
        main_section("Experience")
        for exp in cv_data["experience"]:
            pdf.set_x(MX)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(MW, 6, _s(exp.get("title", "")),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(MX)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(MW, 5,
                     _s(f'{exp.get("company","")}  •  {exp.get("period","")}'),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "", 9.5)
            for b in exp.get("bullets", []):
                pdf.set_x(MX + 3)
                pdf.multi_cell(MW - 3, 5, _s(f"• {b}"))
            pdf.ln(3)

    if cv_data.get("education"):
        main_section("Education")
        for edu in cv_data["education"]:
            pdf.set_x(MX)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(MW, 6, _s(edu.get("degree", "")),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(MX)
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(MW, 5,
                     _s(f'{edu.get("institution","")}  •  {edu.get("year","")}'),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(30, 30, 30)
            pdf.ln(2)

    return bytes(pdf.output())


# ── COVER LETTER TEMPLATE ────────────────────────────────────────────────────
def build_cover_letter(letter_data: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    W = pdf.w

    pdf.set_fill_color(17, 24, 39)
    pdf.rect(0, 0, W, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(18, 8)
    pdf.cell(0, 8, _s(letter_data.get("full_name", "Your Name")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(18, 18)
    contact = "  |  ".join(filter(None, [
        letter_data.get("email", ""),
        letter_data.get("phone", ""),
        letter_data.get("location", ""),
    ]))
    pdf.cell(0, 6, _s(contact), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(8)
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)

    meta_lines = [
        datetime.now().strftime("%d %B %Y"),
        letter_data.get("target_company", ""),
        letter_data.get("target_role", ""),
    ]
    for line in meta_lines:
        if line:
            pdf.cell(0, 5.5, _s(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(0, 6, _s(letter_data.get("cover_letter", "")))

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.cell(0, 6, _s(letter_data.get("full_name", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
