"""Tests for PDF helpers and templates.  Run: venv/bin/python -m unittest discover backend/tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # noqa: E402

from pdf_templates import (  # noqa: E402
    _join, _s, build_corporate, build_cover_letter, build_minimal_slate, build_tech_modern, clean_cover_letter,
)

CV = {
    "name": "Jona Test", "email": "jona@example.com", "phone": "+355 69 000 0000", "location": "Tirana",
    "current_title": "Developer", "summary": "Builds things.", "skills": ["Python", "React"],
    "experience": [{"title": "Dev", "company": "Acme", "period": "", "bullets": ["• Built APIs", "- Shipped UI"]}],
    "education": [{"degree": "BSc", "institution": "Uni", "year": ""}],
}


def _text(pdf_bytes: bytes) -> str:
    return "".join(page.get_text() for page in fitz.open(stream=pdf_bytes, filetype="pdf"))


class CleanCoverLetterTest(unittest.TestCase):
    def test_strips_preamble_and_signature(self):
        raw = ("Here is a cover letter for Jona Kapaj:\n\nDear Hiring Manager,\n\nI build things.\n\n"
               "Best regards,\nJona Kapaj")
        self.assertEqual(clean_cover_letter(raw, "Jona Kapaj"), "Dear Hiring Manager,\n\nI build things.")

    def test_strips_sure_preamble_trailing_note_and_placeholders(self):
        raw = ("Sure! Here's a tailored letter:\n\nDear team,\n\nBody.\n\n[Your Name]\n\n"
               "Note: feel free to adjust the tone.")
        self.assertEqual(clean_cover_letter(raw, "Jona"), "Dear team,\n\nBody.")

    def test_leaves_clean_letter_alone(self):
        self.assertEqual(clean_cover_letter("Dear team,\n\nHere is why I fit.", "X"), "Dear team,\n\nHere is why I fit.")


class TextHelpersTest(unittest.TestCase):
    def test_join_skips_empty_parts(self):
        self.assertEqual(_join("Acme", "", None), "Acme")

    def test_non_latin1_keeps_base_letter(self):
        self.assertEqual(_s("Łódź – Kraków"), "Lódz - Kraków")  # ó is latin-1, kept; Ł and ź are mapped


class TemplatesTest(unittest.TestCase):
    def test_all_templates_render_without_dangling_separators(self):
        for build in (build_corporate, build_tech_modern, build_minimal_slate):
            text = _text(build(CV))
            self.assertIn("Jona Test", text)
            self.assertIn("Built APIs", text)
            self.assertNotIn("Acme  |", text)
            self.assertNotIn("• Built", text)  # bullet char from the data is not duplicated

    def test_cover_letter_has_single_signature(self):
        letter = "Here is a letter for Jona Test:\n\nDear team,\n\nBody.\n\nKind regards,\nJona Test"
        text = _text(build_cover_letter({"cover_letter": letter, "full_name": "Jona Test", "email": "j@x.com"}))
        self.assertNotIn("Here is", text)
        self.assertEqual(text.count("Jona Test"), 2)  # header + signature
        self.assertIn("j@x.com", text)


if __name__ == "__main__":
    unittest.main()
