"""Tests for cv_parser.py.  Run: venv/bin/python -m unittest discover backend/tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cv_parser import clean_rewrite, parse_rewrite  # noqa: E402

MARKDOWN = """Here is the rewritten CV optimized for the role:

**PROFESSIONAL SUMMARY**
Backend developer building Python APIs.
Focused on performance.

**CORE SKILLS**

* Python (FastAPI and Django)
* Redis (caching)
* React: experienced in building reusable UI components

**PROFESSIONAL EXPERIENCE**

**Backend Developer, Nordlicht Software (2021 – present)**

* Built REST APIs used by 12 services.
* Cut p95 latency from 800 ms to 240 ms
  by adding Redis caching.

**Junior Developer | Kaya Logistics | 2019 – 2021**
- Built Django admin tools.

**EDUCATION**

* BSc Computer Science, University of Tirana, 2019
* Relevant coursework: Databases, Networks

Note: I kept all content from the original CV.
"""

PLAIN = """PROFESSIONAL SUMMARY
Project coordinator with construction experience.

SKILLS
Languages: Albanian, English, Italian
Scheduling, budgeting, MS Project

PROFESSIONAL EXPERIENCE
Project Coordinator
Adriatic Build | Jan 2020 – Present
- Coordinated subcontractors.

EDUCATION
BSc Civil Engineering
University of Shkodër
2017
"""


class CleanTest(unittest.TestCase):
    def test_removes_preamble_and_note(self):
        out = clean_rewrite(MARKDOWN)
        self.assertTrue(out.startswith("**PROFESSIONAL SUMMARY**"))
        self.assertNotIn("Note:", out)


class ParseMarkdownTest(unittest.TestCase):
    def setUp(self):
        self.d = parse_rewrite(MARKDOWN)

    def test_summary_joined(self):
        self.assertEqual(self.d["summary"], "Backend developer building Python APIs. Focused on performance.")

    def test_skills_drop_notes_and_descriptions(self):
        self.assertEqual(self.d["skills"], ["Python", "Redis", "React"])

    def test_roles(self):
        first, second = self.d["experience"]
        self.assertEqual((first["title"], first["company"], first["period"]),
                         ("Backend Developer", "Nordlicht Software", "2021 – present"))
        self.assertEqual(first["bullets"][1], "Cut p95 latency from 800 ms to 240 ms by adding Redis caching.")
        self.assertEqual((second["title"], second["company"], second["period"]),
                         ("Junior Developer", "Kaya Logistics", "2019 – 2021"))

    def test_education(self):
        self.assertEqual(self.d["education"],
                         [{"degree": "BSc Computer Science", "institution": "University of Tirana", "year": "2019"}])


class ParsePlainTest(unittest.TestCase):
    def setUp(self):
        self.d = parse_rewrite(PLAIN)

    def test_company_line_under_title(self):
        role = self.d["experience"][0]
        self.assertEqual((role["title"], role["company"], role["period"]),
                         ("Project Coordinator", "Adriatic Build", "Jan 2020 – Present"))

    def test_list_style_skills(self):
        self.assertEqual(self.d["skills"][:4], ["Albanian", "English", "Italian", "Scheduling"])

    def test_multiline_education(self):
        edu = self.d["education"][0]
        self.assertEqual(edu["degree"], "BSc Civil Engineering")
        self.assertEqual(edu["institution"], "University of Shkodër")


class FallbackTest(unittest.TestCase):
    def test_unstructured_text_returns_none(self):
        self.assertIsNone(parse_rewrite("Just a paragraph with no sections at all."))


if __name__ == "__main__":
    unittest.main()
