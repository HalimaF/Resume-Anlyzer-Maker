"""Hand-labeled resume corpus for measuring analyzer accuracy.

Each case carries resume text plus ground truth a human reviewer agreed on:
which catalog skills the text genuinely evidences, and which sections it
genuinely has. Cases deliberately include the traps that break naive matching -
ambiguous tokens, negated mentions, non-tech domains, and section words used as
ordinary prose.
"""

CASES = [
    {
        "id": "backend-py-clean",
        "text": """
Aisha Rahman
aisha.rahman@example.com | +92 300 1234567 | Lahore, Pakistan

PROFESSIONAL SUMMARY
Backend engineer with 4 years building high-throughput REST services.

WORK EXPERIENCE
Backend Engineer, Systems Ltd (2021 - Present)
- Built and shipped 12 microservices in Python and Django, cutting p95 latency by 38%.
- Containerised the platform with Docker and deployed on Kubernetes across AWS.
- Automated releases through GitHub Actions, reducing deploy time from 45 to 6 minutes.

EDUCATION
BS Computer Science, Punjab University, 2020

TECHNICAL SKILLS
Python, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, REST API
""",
        "skills": {
            "Python", "Django", "PostgreSQL", "Redis", "Docker", "Kubernetes",
            "AWS", "Git", "REST API", "GitHub Actions", "Microservices",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "ambiguous-words",
        "text": """
Daniel Osei
daniel.osei@example.com | +44 7700 900123

PROFILE
Operations analyst. I excel at turning messy spreadsheets into clear decisions,
and I go the extra mile for stakeholders. My work has driven revenue growth.

EXPERIENCE
Operations Analyst, Retail Group (2019 - 2024)
- Managed a team of 6 and improved reporting turnaround by 30%.
- Rebuilt the weekly forecast, saving 200 hours per year.

EDUCATION
BA Economics, University of Leeds, 2018

SKILLS
Microsoft Excel, Power BI, SQL, stakeholder communication
""",
        # "excel at" and "go the extra mile" must NOT register as skills.
        "skills": {
            "Excel", "Power BI", "SQL", "Communication", "Leadership",
            "Stakeholder Management", "Revenue Growth",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "nurse-non-tech",
        "text": """
Maria Costa, RN
maria.costa@example.com | +351 912 345 678

SUMMARY
Registered nurse with 7 years in acute cardiac care.

PROFESSIONAL EXPERIENCE
Senior Staff Nurse, Hospital Santa Maria (2018 - Present)
- Led a 12-bed cardiac unit, improving patient throughput by 22%.
- Trained 30 junior nurses in triage and emergency protocols.
- Collaborated with physicians on care plans for 400+ patients annually.

EDUCATION
BSc Nursing, University of Lisbon, 2016

SKILLS
Patient Care, Triage, Cardiac Monitoring, Team Leadership, Communication
""",
        "skills": {
            "Leadership", "Communication", "Collaboration", "Patient Care",
            "Triage", "Clinical Documentation", "Vital Signs Monitoring",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "negated-and-prose-traps",
        "text": """
Tom Fletcher
tom.fletcher@example.com | 555-0142

ABOUT ME
Frontend developer. I have no experience with Kubernetes or Terraform yet, but I
am learning. I wrote the executive summary for our education technology client,
whose product certification programme I helped launch.

ROLES
Frontend Developer, Studio Nine (2020 - Present)
- Developed 20+ React interfaces with TypeScript and Tailwind CSS.
- Improved Lighthouse performance scores from 61 to 96.

WHAT I KNOW
React, TypeScript, Tailwind CSS, HTML, CSS, Git
""",
        # Kubernetes/Terraform are explicitly negated. "summary", "education"
        # and "certification" appear only as prose, never as section headings.
        "skills": {"React", "TypeScript", "Tailwind CSS", "HTML", "CSS", "Git"},
        "sections": {"summary", "experience", "skills"},
    },
    {
        "id": "aliases-and-symbols",
        "text": """
Wei Zhang
wei.zhang@example.com | +86 138 0013 8000

SUMMARY
Systems programmer, 6 years.

EXPERIENCE
Systems Engineer, Nebula Compute (2019 - Present)
- Wrote services in Golang and C++ handling 40k requests/second.
- Ported the auth layer to C# for the Windows client.
- Ran everything on k8s with a Postgres backing store.
- Built ML pipelines with sklearn and served them behind a Node JS gateway.

EDUCATION
MS Computer Engineering, Tsinghua University, 2018

SKILLS
Golang, C++, C#, k8s, Postgres, sklearn, Node JS
""",
        "skills": {
            "Go", "C++", "C#", "Kubernetes", "PostgreSQL", "Scikit-learn",
            "Node.js", "Machine Learning",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "designer-non-tech",
        "text": """
Lena Fischer
lena.fischer@example.com | +49 151 23456789

PROFILE
Product designer with 5 years shipping consumer mobile apps.

EXPERIENCE
Senior Product Designer, Klar (2020 - Present)
- Designed and shipped 14 features in Figma, lifting activation 19%.
- Built and maintained a design system used by 3 product teams.
- Ran usability testing sessions with 60+ participants.

EDUCATION
BA Communication Design, HfG Karlsruhe, 2018

SKILLS
Figma, Sketch, Prototyping, Wireframing, Design Systems, Usability Testing, User Research
""",
        "skills": {
            "Figma", "Sketch", "Prototyping", "Wireframing", "Design Systems",
            "Usability Testing", "User Research", "Mobile Development",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "data-scientist",
        "text": """
Priya Nair
priya.nair@example.com | +91 98765 43210

PROFESSIONAL SUMMARY
Data scientist with 5 years in demand forecasting.

EXPERIENCE
Data Scientist, Freightly (2020 - Present)
- Shipped an XGBoost forecasting model that reduced stockouts by 27%.
- Built feature pipelines in Pandas and NumPy over a BigQuery warehouse.
- Deployed models with MLflow and monitored drift in production.

PROJECTS
Churn model using PyTorch and deep learning on 2M rows.

EDUCATION
MSc Statistics, IIT Bombay, 2019

SKILLS
Python, SQL, Pandas, NumPy, Scikit-learn, XGBoost, PyTorch, BigQuery, Tableau
""",
        "skills": {
            "Python", "SQL", "Pandas", "NumPy", "Scikit-learn", "XGBoost",
            "PyTorch", "BigQuery", "Tableau", "Deep Learning",
            "Feature Engineering", "Forecasting", "MLOps", "Statistics",
        },
        "sections": {"summary", "experience", "education", "skills", "projects"},
    },
    {
        "id": "sparse-fresher",
        "text": """
Omar Haddad
omar.haddad@example.com

EDUCATION
BS Software Engineering, NUST, 2025

PROJECTS
Weather app built with Flask and SQLite.
Portfolio site in HTML and CSS.
""",
        "skills": {"Flask", "SQLite", "HTML", "CSS"},
        "sections": {"education", "projects"},
    },
    {
        "id": "accountant-non-tech",
        "text": """
Grace Mensah
grace.mensah@example.com | +233 24 123 4567

SUMMARY
Chartered accountant, 9 years in audit and financial reporting.

EXPERIENCE
Audit Manager, Ledger and Co (2017 - Present)
- Led statutory audits for 18 clients with combined revenue over $400M.
- Reduced close cycle from 12 days to 7 through process redesign.

EDUCATION
BSc Accounting, University of Ghana, 2014

CERTIFICATIONS
ACCA, Chartered Accountant licence

SKILLS
Financial Reporting, Audit, IFRS, Advanced Excel, Time Management, Leadership
""",
        "skills": {
            "Excel", "Leadership", "Time Management", "Accounting", "Auditing",
            "Financial Reporting", "IFRS", "Process Improvement",
        },
        "sections": {"summary", "experience", "education", "certifications", "skills"},
    },
    {
        "id": "devops-heavy",
        "text": """
Ivan Petrov
ivan.petrov@example.com | +7 916 123 4567

PROFILE
Platform engineer, 8 years.

EXPERIENCE
Staff Platform Engineer, Volna (2018 - Present)
- Managed 300+ node Kubernetes clusters on Azure and GCP.
- Wrote Terraform modules and Ansible playbooks for the whole estate.
- Built CI/CD with Jenkins, cutting mean deploy time by 4x.
- Instrumented services and ran incident response for a 99.95% SLA.

EDUCATION
MS Computer Science, MSU, 2016

CERTIFICATIONS
Certified Kubernetes Administrator

SKILLS
Kubernetes, Docker, Terraform, Ansible, Jenkins, Azure, GCP, Linux, Bash, CI/CD
""",
        "skills": {
            "Kubernetes", "Docker", "Terraform", "Ansible", "Jenkins",
            "Azure", "GCP", "Linux", "Bash", "CI/CD",
            "Monitoring", "Incident Response", "Site Reliability",
        },
        "sections": {"summary", "experience", "education", "certifications", "skills"},
    },
]
