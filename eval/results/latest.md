# CV agent eval — 2026-11-24_172531

Model: `llama3.2:3b` · cases: 4 · checks passed: **64/65** · invented-content checks passed: **24/24**

| Case | Fit | Avg score | Checks | Latency (s) |
|---|---|---|---|---|
| backend_strong_match | strong | 60.0 | 16/16 | 68 |
| marketing_to_data_eng_weak_match | weak | 3.3 | 15/16 | 60 |
| student_to_frontend_partial | partial | 17.5 | 16/16 | 43 |
| pm_no_metrics | partial | 45.8 | 16/16 | 46 |

## Failed checks

- **marketing_to_data_eng_weak_match** — audit: all sections present: `["ALIGNMENT MATRIX"]`

## Mean latency per agent (s)

- audit_cv: 13.1
- cover_letter: 15.5
- rewrite_cv: 17.2
- score_skills: 8.3
- structure_cv: 0.0
