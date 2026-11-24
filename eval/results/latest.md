# CV agent eval — 2026-11-24_151301

Model: `llama3:latest` · cases: 4 · checks passed: **54/65** · invented-content checks passed: **15/24**

| Case | Fit | Avg score | Checks | Latency (s) |
|---|---|---|---|---|
| backend_strong_match | strong | 79.2 | 14/16 | 196 |
| marketing_to_data_eng_weak_match | weak | 6.7 | 13/16 | 165 |
| student_to_frontend_partial | partial | 0.0 | 11/16 | 155 |
| pm_no_metrics | partial | 65.8 | 15/16 | 146 |

## Failed checks

- **backend_strong_match** — rewrite: no invented numbers: `["3", "70", "80"]`
- **backend_strong_match** — rewrite: no invented skills: `[{"skill": "Kubernetes", "context": "…SQL and experience with PostgreSQL. Proficient in Kubernetes and Terraform for deployments. **CORE SKILLS**…"}, {"skill": "Terraform", "context": "…nce with PostgreSQL. Proficient in Kubernetes and Terraform for deployments. **CORE SKILLS** * Python (Fast…"}]`
- **marketing_to_data_eng_weak_match** — rewrite: no invented numbers: `["185", "3"]`
- **marketing_to_data_eng_weak_match** — rewrite: no invented skills: `[{"skill": "Spark", "context": "…development and orchestration. Skilled in Apache Spark, Scala, and Python, with a strong foundation in d…"}, {"skill": "Scala", "context": "…pment and orchestration. Skilled in Apache Spark, Scala, and Python, with a strong foundation in data mod…"}, {"skill": "dbt", "context": "…evelopment and orchestration * Data modeling with dbt and cloud warehousing (Snowflake or BigQuery) * S…"}]`
- **marketing_to_data_eng_weak_match** — cover letter: no invented skills: `[{"skill": "Spark", "context": "…insights. Your company's emphasis on using Apache Spark, Scala, and Airflow resonates with my passion for…"}, {"skill": "Airflow", "context": "…pany's emphasis on using Apache Spark, Scala, and Airflow resonates with my passion for scalable and effici…"}, {"skill": "Scala", "context": "…s. Your company's emphasis on using Apache Spark, Scala, and Airflow resonates with my passion for scalab…"}, {"skill": "dbt", "context": "…ally, I've honed my skills in data modeling using dbt and cloud warehouses like Snowflake. My experienc…"}]`
- **student_to_frontend_partial** — rewrite: no invented numbers: `["25", "30"]`
- **student_to_frontend_partial** — rewrite: no invented skills: `[{"skill": "TypeScript", "context": "…ith a strong foundation in JavaScript, React, and TypeScript. Proficient in building scalable and maintainable…"}, {"skill": "GraphQL", "context": "…d server-side rendering. Experienced in consuming GraphQL APIs and creating component documentation with St…"}, {"skill": "Next.js", "context": "…ding scalable and maintainable applications using Next.js and server-side rendering. Experienced in consumi…"}, {"skill": "Storybook", "context": "…QL APIs and creating component documentation with Storybook. Possesses a keen eye for design and is comfortab…"}]`
- **student_to_frontend_partial** — cover letter: 230-370 words: `202`
- **student_to_frontend_partial** — cover letter: signed with name: `"I'm excited about the prospect of joining the Studio Kern team and contributing my skills and experience to the company. With my strong foundation in JavaScript, React, and HTML/CSS, I'm confident that I would be a valuable asset to the team. I'm available to start immediately and look forward to discussing my application further."`
- **student_to_frontend_partial** — cover letter: no invented skills: `[{"skill": "TypeScript", "context": "…side rendering, and GraphQL APIs. The emphasis on TypeScript in production code also resonated with me, as I'v…"}, {"skill": "GraphQL", "context": "…to work with Next.js, server-side rendering, and GraphQL APIs. The emphasis on TypeScript in production co…"}, {"skill": "Next.js", "context": "…articularly drawn to the opportunity to work with Next.js, server-side rendering, and GraphQL APIs. The emp…"}]`
- **pm_no_metrics** — rewrite: no invented skills: `[{"skill": "Scrum Master", "context": "…racts, ensuring successful project procurement. * Scrum Master Certification: (Preferred but not required) **PR…"}, {"skill": "Jira", "context": "…r expectations. Skilled in MS Project, Excel, and Jira, with a strong understanding of project managemen…"}, {"skill": "Confluence", "context": "…within budget, and with high quality. * Jira and Confluence: Proficient in using Jira and Confluence for proj…"}]`

## Mean latency per agent (s)

- audit_cv: 55.5
- cover_letter: 25.5
- rewrite_cv: 39.2
- score_skills: 8.2
- structure_cv: 37.4
