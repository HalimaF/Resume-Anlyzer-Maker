"""Held-out resume cases, written after the engine was tuned.

The main corpus was used to find and fix bugs, so scoring 100% on it proves
little on its own. These cases were never used to adjust rules, aliases, or
thresholds; the number they produce is the honest one.
"""

CASES = [
    {
        "id": "hd-solicitor",
        "text": """
Rachel Adeyemi
r.adeyemi@example.com | +44 20 7946 0812 | London

Profile
Commercial solicitor, 6 years post-qualification.

Employment History
Associate, Harrow & Finch LLP (2019 - Present)
- Drafted and negotiated 90+ commercial contracts worth GBP 25M combined.
- Led due diligence on three M&A transactions.
- Advised clients on GDPR and data protection obligations.

Education
LLB Law, King's College London, 2016

Qualifications
Solicitor of England and Wales, admitted 2018

Key Skills
Contract drafting, litigation, legal research, corporate governance, negotiation
""",
        "skills": {
            "Contract Law", "Litigation", "Legal Research", "Corporate Law",
            "Negotiation", "Due Diligence", "Compliance", "Data Privacy Law",
        },
        "sections": {"summary", "experience", "education", "certifications", "skills"},
    },
    {
        "id": "hd-teacher",
        "text": """
Samuel Boateng
s.boateng@example.com | +233 20 998 1122

Career Objective
Secondary mathematics teacher with 8 years in the classroom.

Professional Experience
Head of Mathematics, Accra Grammar School (2018 - Present)
- Redesigned the curriculum for years 10-12, lifting pass rates from 61% to 84%.
- Mentored 7 junior teachers and ran weekly lesson planning workshops.
- Introduced Moodle for coursework submission across 400 students.

Education
BEd Mathematics, University of Cape Coast, 2015

Skills
Curriculum design, lesson planning, student assessment, classroom management
""",
        "skills": {
            "Curriculum Development", "Classroom Management", "Assessment Design",
            "Learning Management Systems", "Leadership",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "hd-sales-negations",
        "text": """
Carlos Duarte
carlos.duarte@example.com | +34 611 223 344

Summary
Enterprise account executive, 5 years in SaaS.

Experience
Account Executive, Nimbus Software (2020 - Present)
- Exceeded quota four years running, closing EUR 3.2M in new business.
- Managed a pipeline of 60+ opportunities in Salesforce.
- Ran contract negotiation through to signature for 40 enterprise deals.
I have no experience with Marketo and I am currently learning Tableau.

Education
BA Business Administration, IE University, 2019

Skills
Solution selling, pipeline management, CRM, negotiation, account management
""",
        # Marketo (Marketing Automation) is disclaimed; Tableau is aspirational.
        "skills": {
            "B2B Sales", "Pipeline Management", "CRM", "Negotiation",
            "Account Management", "Revenue Growth",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "hd-hospitality",
        "text": """
Nadia Karim
nadia.karim@example.com | +971 50 123 4567

About
Hotel operations manager, 10 years across luxury properties.

Work History
Operations Manager, Marina Bay Hotel (2017 - Present)
- Oversaw front of house and housekeeping teams totalling 85 staff.
- Cut guest complaint volume by 43% through a new service protocol.
- Owned a AED 4M annual operating budget.

Education
Diploma in Hospitality Management, Emirates Academy, 2013

Core Competencies
Guest services, team leadership, budget management, health and safety, scheduling
""",
        "skills": {
            "Hospitality Operations", "Leadership", "Budget Management",
            "Health and Safety", "Operations Management", "Customer Focus",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "hd-collision-traps",
        "text": """
Peter Novak
p.novak@example.com | +420 601 234 567

Profile
Embedded systems engineer, 12 years.

Experience
Firmware Engineer, Sensorik (2014 - Present)
- Wrote firmware in C for ARM microcontrollers shipping in 2M devices.
- Built host tooling in Rust and a small Go service for telemetry ingest.
- Ran the release train and maintained SAP integration for parts ordering.

Education
MSc Electrical Engineering, CTU Prague, 2012

Skills
C, Rust, Go, embedded systems, SAP, Git
""",
        # "C" alone is the trap: it must be found here (list + "embedded"/
        # "programming" support) without dragging in C++ or C#.
        "skills": {"C", "Rust", "Go", "SAP", "Git"},
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "hd-marketing",
        "text": """
Yuki Tanaka
yuki.tanaka@example.com | +81 90 1234 5678

Career Summary
Growth marketer, 7 years in consumer subscription products.

Professional Experience
Senior Growth Manager, Habitat (2019 - Present)
- Grew organic search traffic 240% through a rebuilt SEO content programme.
- Ran paid search and social media campaigns on a JPY 90M annual budget.
- Set up marketing automation in HubSpot, lifting trial-to-paid 18%.
- Led A/B testing across onboarding, landing pages and pricing.

Education
BA Marketing, Waseda University, 2016

Skills
SEO, SEM, content marketing, marketing automation, Google Analytics, CRO
""",
        "skills": {
            "SEO", "SEM", "Content Marketing", "Social Media", "Marketing Automation",
            "Google Analytics", "Conversion Optimization", "A/B Testing",
            "Campaign Management", "Budget Management",
        },
        "sections": {"summary", "experience", "education", "skills"},
    },
    {
        "id": "hd-messy-headings",
        "text": """
ELENA PETROVA
elena.petrova@example.com

>> WHAT I DO
Full-stack developer, 3 years.

>> WHERE I HAVE WORKED
Developer, Kite Labs (2022 - Present)
- Shipped a Vue.js dashboard backed by a FastAPI service and Postgres.
- Set up GitHub Actions so every merge deploys automatically.

>> SCHOOLING
BS Information Systems, Moscow State University, 2021

>> TOOLS
Vue.js, FastAPI, PostgreSQL, Docker, GitHub Actions, Git
""",
        # Decorated headings; "SCHOOLING" and "TOOLS" are real aliases, while
        # "WHAT I DO" / "WHERE I HAVE WORKED" are not - the dated role entry
        # is what has to carry Experience.
        "skills": {
            "Vue.js", "FastAPI", "PostgreSQL", "Docker", "GitHub Actions", "Git",
        },
        "sections": {"experience", "education", "skills"},
    },
    {
        "id": "hd-sparse-negation-only",
        "text": """
Jonah Weiss
jonah.weiss@example.com

Objective
Career changer moving into data work.

Education
BA History, Reed College, 2019

Skills
I want to learn Python and I am learning SQL. No experience with Tableau yet.
Strong written communication and attention to detail.
""",
        # Every technical mention is aspirational or disclaimed. Only the two
        # genuine soft skills should survive.
        "skills": {"Communication", "Attention to Detail"},
        "sections": {"summary", "education", "skills"},
    },
]
