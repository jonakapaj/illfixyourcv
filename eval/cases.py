"""
Evaluation cases: CV / job-description pairs with hand-written ground truth.

Each case records facts that are true about the CV, so the evaluator can check
model output against them without asking another LLM:

  employers      every employer that appears in the CV
  institutions   every school / university in the CV
  missing_skills skills the JD asks for that the CV does NOT show — if the
                 rewrite or cover letter claims them, that is an invented claim
  expected_fit   "strong" or "weak"; used to check score ordering across cases
"""

CASES = [
    {
        "id": "backend_strong_match",
        "expected_fit": "strong",
        "employers": ["Nordlicht Software", "Kaya Logistics"],
        "institutions": ["University of Tirana"],
        "missing_skills": ["Kubernetes", "Terraform", "gRPC"],
        "full_name": "Arben Hoxha",
        "target_company": "Fintrail",
        "target_role": "Backend Engineer (Python)",
        "key_achievement": "Cut API p95 latency from 800 ms to 240 ms by adding Redis caching",
        "cv": """Arben Hoxha
arben.hoxha@example.com | +355 69 123 4567 | Tirana, Albania | linkedin.com/in/arbenhoxha
Backend Developer

EXPERIENCE
Backend Developer — Nordlicht Software, Tirana (2021 – present)
- Built and maintain REST APIs in Python (FastAPI) used by 12 internal services.
- Cut API p95 latency from 800 ms to 240 ms by adding Redis caching.
- Wrote PostgreSQL migrations and query optimisations; reduced a nightly report job from 45 to 9 minutes.
- Set up GitHub Actions CI with pytest; test coverage went from 30% to 78%.

Junior Developer — Kaya Logistics, Durrës (2019 – 2021)
- Developed Django admin tools for warehouse staff.
- Integrated a third-party shipping API and handled webhook retries.
- Containerised two services with Docker.

EDUCATION
BSc Computer Science — University of Tirana, 2019

SKILLS
Python, FastAPI, Django, PostgreSQL, Redis, Docker, GitHub Actions, pytest, REST APIs, Git, Linux
""",
        "jd": """Fintrail — Backend Engineer (Python)
We are a payments startup looking for a backend engineer.
Requirements:
- 3+ years building production APIs in Python (FastAPI or Django)
- Strong SQL, ideally PostgreSQL
- Caching and performance work (Redis or similar)
- Automated testing and CI/CD
- Experience with Kubernetes and Terraform for deployments
- Nice to have: gRPC
""",
    },
    {
        "id": "marketing_to_data_eng_weak_match",
        "expected_fit": "weak",
        "employers": ["Bloom Cosmetics", "Agency Twelve"],
        "institutions": ["University of Vienna"],
        "missing_skills": ["Spark", "Airflow", "Scala", "Kafka", "dbt"],
        "full_name": "Lena Gruber",
        "target_company": "DataForge",
        "target_role": "Data Engineer",
        "key_achievement": "Grew the newsletter list from 4,000 to 11,500 subscribers in one year",
        "cv": """Lena Gruber
lena.gruber@example.com | +43 660 555 0101 | Vienna, Austria
Marketing Coordinator

EXPERIENCE
Marketing Coordinator — Bloom Cosmetics, Vienna (2022 – present)
- Planned and ran monthly email campaigns in Mailchimp.
- Grew the newsletter list from 4,000 to 11,500 subscribers in one year.
- Built weekly campaign reports in Google Sheets and Looker Studio.

Social Media Assistant — Agency Twelve, Vienna (2020 – 2022)
- Scheduled posts for 6 client accounts.
- Wrote short-form copy for Instagram and LinkedIn.

EDUCATION
BA Communication Studies — University of Vienna, 2020

SKILLS
Mailchimp, Google Sheets, Looker Studio, Canva, copywriting, basic SQL (one online course)
""",
        "jd": """DataForge — Data Engineer
Requirements:
- 3+ years building batch and streaming data pipelines
- Apache Spark and Scala or PySpark
- Orchestration with Airflow
- Kafka for event streaming
- Data modelling with dbt and a cloud warehouse (Snowflake or BigQuery)
- Strong Python and SQL
""",
    },
    {
        "id": "student_to_frontend_partial",
        "expected_fit": "partial",
        "employers": ["Pixelhaus"],
        "institutions": ["TU Munich"],
        "missing_skills": ["TypeScript", "GraphQL", "Next.js", "Storybook"],
        "full_name": "Mira Weber",
        "target_company": "Studio Kern",
        "target_role": "Junior Frontend Developer",
        "key_achievement": "Built a React dashboard for my thesis project used by 3 research groups",
        "cv": """Mira Weber
mira.weber@example.com | Munich, Germany | github.com/miraweber
Computer Science Student

EXPERIENCE
Working Student, Web Development — Pixelhaus, Munich (2023 – present)
- Fixed CSS layout bugs and built small UI components in React.
- Added form validation to the customer sign-up page.

PROJECTS
Thesis project: built a React dashboard used by 3 research groups to browse sensor data.
Personal site built with HTML, CSS and JavaScript.

EDUCATION
BSc Informatics — TU Munich, expected 2025

SKILLS
JavaScript, React, HTML, CSS, Tailwind CSS, Git, Figma
""",
        "jd": """Studio Kern — Junior Frontend Developer
Requirements:
- Solid JavaScript and React
- TypeScript in production code
- Next.js and server-side rendering
- Consuming GraphQL APIs
- Component documentation with Storybook
- Eye for design, comfortable with Figma
""",
    },
    {
        "id": "pm_no_metrics",
        "expected_fit": "partial",
        "employers": ["Adriatic Build", "City of Shkodër"],
        "institutions": ["University of Shkodër"],
        "missing_skills": ["PMP", "Scrum Master", "Jira", "Confluence"],
        "full_name": "Dritan Leka",
        "target_company": "Helix Digital",
        "target_role": "Project Manager",
        "key_achievement": "Coordinated the renovation of the municipal library from planning to handover",
        # Deliberately has almost no numbers: any metric in the rewrite is invented.
        "cv": """Dritan Leka
dritan.leka@example.com | Shkodër, Albania
Project Coordinator

EXPERIENCE
Project Coordinator — Adriatic Build, Shkodër (2020 – present)
- Coordinated subcontractors on residential construction projects.
- Kept project schedules and budgets up to date and reported to the site director.
- Organised weekly progress meetings with clients.

Administrative Officer — City of Shkodër (2017 – 2020)
- Coordinated the renovation of the municipal library from planning to handover.
- Prepared tender documents and tracked supplier contracts.

EDUCATION
BSc Civil Engineering — University of Shkodër, 2017

SKILLS
Scheduling, budgeting, stakeholder communication, MS Project, Excel, tendering
""",
        "jd": """Helix Digital — Project Manager
Requirements:
- Experience managing projects end to end
- Agile delivery; Scrum Master certification preferred
- PMP certification is a plus
- Daily use of Jira and Confluence
- Strong stakeholder communication and budget tracking
""",
    },
]
