"""Unit tests for grounding.py (no LLM needed).  Run: venv/bin/python -m unittest discover backend/tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grounding import grounding_report, is_clean, job_terms, missing_job_terms, ungrounded_numbers  # noqa: E402

CV = """Arben Hoxha
Backend Developer — Nordlicht Software (2021 – present)
- Built REST APIs in Python (FastAPI) used by 12 internal services.
- Grew coverage from 30% to 78% with pytest. PostgreSQL, Redis, Docker.
"""

JD = """Fintrail — Backend Engineer (Python)
Requirements:
- Production APIs in Python (FastAPI or Django)
- Strong SQL, ideally PostgreSQL
- Kafka for event streaming
- Experience with Kubernetes and Terraform
- Data modelling with dbt
"""


class NumbersTest(unittest.TestCase):
    def test_thousands_separator_is_normalised(self):
        self.assertEqual(ungrounded_numbers("from 4000 to 11,500", "from 4,000 to 11500"), [])

    def test_numbered_list_markers_are_ignored(self):
        self.assertEqual(ungrounded_numbers("1. Built APIs\n2) Wrote tests", CV), [])

    def test_new_number_is_flagged(self):
        self.assertEqual(ungrounded_numbers("cut latency by 40%", CV), ["40"])


class TermsTest(unittest.TestCase):
    def test_extracts_tools_including_line_start_and_lowercase(self):
        terms = {t.lower() for t in job_terms(JD)}
        for t in ("kafka", "kubernetes", "terraform", "dbt", "postgresql", "fastapi"):
            self.assertIn(t, terms)

    def test_skips_title_line_and_generic_words(self):
        terms = {t.lower() for t in job_terms(JD)}
        for t in ("fintrail", "backend", "strong", "experience", "data", "requirements"):
            self.assertNotIn(t, terms)

    def test_sql_counts_as_present_when_cv_says_postgresql(self):
        self.assertNotIn("SQL", missing_job_terms(CV, JD))

    def test_missing_terms(self):
        self.assertEqual(set(missing_job_terms(CV, JD)) & {"Kafka", "Kubernetes", "Terraform", "dbt", "Django"},
                         {"Kafka", "Kubernetes", "Terraform", "dbt", "Django"})


class ReportTest(unittest.TestCase):
    def test_clean_rewrite(self):
        rewrite = "Built REST APIs in Python and FastAPI for 12 services; raised coverage to 78%."
        self.assertTrue(is_clean(grounding_report(rewrite, CV, JD)))

    def test_invented_skill_and_metric(self):
        rewrite = "Deployed services on Kubernetes, cutting costs by 25%."
        report = grounding_report(rewrite, CV, JD)
        self.assertEqual(report["terms"], ["Kubernetes"])
        self.assertEqual(report["numbers"], ["25"])

    def test_whole_word_match_in_output(self):
        # 'Go' as a required skill must not match the word 'good'.
        report = grounding_report("A good team player.", CV, "Role\n- Experience with Go and gRPC")
        self.assertEqual(report["terms"], [])

    def test_allowed_text_counts_as_source(self):
        report = grounding_report("I led 3 launches.", CV, JD, allowed="Led 3 product launches")
        self.assertEqual(report["numbers"], [])


if __name__ == "__main__":
    unittest.main()
