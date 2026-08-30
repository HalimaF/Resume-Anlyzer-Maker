# Career Desk

A local resume toolkit: a Flask API and a static multi-page frontend. Everything
runs on your machine — no account, no hosting, no uploads to anyone.

- **Import** — drop a LinkedIn PDF export or an old CV and every CV field is
  filled in for you
- **Resume Analyzer** — score, ATS checks, skill detection, and a list of fixes
  ranked by how many points each one adds
- **Job Match** — the same analysis scoped to a target role or a pasted posting
- **CV Maker** — live-preview builder with four templates, autosave, PDF export
- **Cover Letter** — tone-controlled letter built from your own highlights
- **Bulk Review** — score and rank up to 25 resumes against one posting

## Run it

One command starts the API, serves the frontend, and opens a browser:

```powershell
pip install -r backend/requirements.txt
python run.py
```

That serves the app at `http://localhost:5500` and the API at
`http://localhost:5000`. `python run.py --no-browser` skips opening a browser;
`--api-port` and `--web-port` move either server.

<details>
<summary>Running the two servers separately</summary>

```powershell
# terminal 1 - API
cd backend
python run.py

# terminal 2 - frontend
cd frontend
python -m http.server 5500
```

The frontend defaults to `http://localhost:5000` for the API. Change it under
**Settings** on any page that talks to it; the choice is remembered.

</details>

## Accuracy

The analyzer's value is being right, so accuracy is measured, not asserted. Two
hand-labeled corpora live in `backend/eval/`: one used while building the rules,
and one written afterwards and never tuned against.

```powershell
cd backend
python -m eval.measure     # prints per-case errors and P/R/F1
```

Current results across 18 resumes and 165 labeled judgements:

| Task | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Skill detection | 100% | 100% | **100%** |
| Section detection | 100% | 100% | **100%** |

`pytest` fails the build if either drops below 95%, so accuracy cannot regress
silently.

**How that number was reached.** The held-out corpus scored 90.7% on first
contact and exposed nine real defects — a `telemetry` alias colliding with
vital-signs monitoring, `gcp` matching Good Clinical Practice instead of Google
Cloud, a single-letter skill matching the initial in an email address, and so
on. Those were fixed, which means the held-out set is no longer strictly
held-out; treat 90.7% as the honest first-contact figure and 100% as the current
regression floor. Adding new labeled cases is the way to keep it honest.

### What makes it accurate

| Rule | Why it exists |
| --- | --- |
| Longest phrase wins | `C++` consumes its span, so `C` can never fire inside it |
| Negation detection | "no experience with Kubernetes" is a claim of *absence*; counting it tells people they have a skill they disclaimed |
| Aspiration detection | "currently learning Rust" is not Rust experience |
| Heading-anchored sections | "I wrote the executive summary" is not a Summary section |
| Ambiguous-token corroboration | "I excel at" is not Microsoft Excel; "Go the extra mile" is not Golang |
| Line-bounded context | A `Skills` heading two lines away cannot vouch for "BA Communication Design" |

Skills the resume disclaims are reported separately, so the tool can explain why
it disagreed with you rather than silently dropping the mention.

### Coverage

336 skills across 17 professional fields — software, data, design, product,
marketing, sales, finance, healthcare, education, HR, legal, operations, and
media. `frontend/jobs.json` carries **28 roles across 11 fields**, from
Registered Nurse and Teacher to Solicitor, HR Manager and Site Supervisor, and
`tests/test_jobs_catalog.py` fails the build if any role lists a requirement the
catalog cannot detect.

This mattered: when the catalog was software-only, three of the seven roles
could detect **none** of their own requirements, so a designer or a marketer
scored near zero no matter what they uploaded.

## Importing a profile

`import.html` builds a CV from what you already have:

- **LinkedIn's own PDF export** — profile → **More** → **Save to PDF**
- **Any existing CV** in PDF, DOCX or TXT
- **Pasted text** from your profile page

**A LinkedIn profile URL cannot be read, by this or anything else.** The page
serves a sign-in wall to anything that is not a logged-in browser, and
LinkedIn's robots.txt prohibits automated access outright. Pasting a bare
profile link therefore returns the three-step export instructions rather than
failing silently or returning an empty profile.

The parser keys off date ranges rather than layout, because dates survive PDF
extraction and indentation does not. It handles LinkedIn's sidebar (where
"Curriculum Development" looks exactly like a name — the profile URL slug
disambiguates it), both `Company / Title / Dates` and `Title, Employer` orders,
and reports in plain words which sections it could not find.

## Scoring model

One model backs every endpoint, so a resume scores the same alone as it does in
a bulk batch. Each component is scored 0-100, clamped, then weighted:

| Component | Weight | What it measures |
| --- | --- | --- |
| Keyword matching | 30% | Skill breadth, plus coverage of the target job's skills |
| Content quality | 20% | Summary, achievement verbs, depth, and the share of bullets carrying a number |
| Structure & format | 20% | Section completeness, by real headings |
| ATS compliance | 20% | Contact details, headings, action verbs, length |
| Experience relevance | 10% | Tenure, from an explicit claim or the span of dated roles |

**Job match is driven by skills, not wording.** A posting is mostly boilerplate
about benefits and culture; scoring raw word overlap measures writing style, not
fit. The match score is 75% skill coverage and 25% wording overlap, and both are
reported separately so the number is auditable.

**Missing skills are scoped to the job description.** Without one there is no
meaningful notion of a missing skill, so the list stays empty rather than
listing the entire catalog.

## Optional AI enrichment

Off by default. The analyzer produces its score and its ranked fixes entirely
without a model; enrichment only adds what rules are bad at — skills outside the
catalog, and rewriting weak bullets.

Any OpenAI-compatible endpoint works. Copy `backend/.env.example` to
`backend/.env` and uncomment a block:

```bash
# Ollama: free, open source, runs locally, nothing leaves your machine
ollama pull llama3.1:8b && ollama serve
```

```ini
LLM_ENABLED=true
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b
```

Groq and OpenRouter free tiers are also documented in `.env.example`.

Every failure path — unreachable, slow, HTTP error, unparseable reply —
degrades to no enrichment and the analysis completes normally. At most 6,000
characters of resume text are sent, and `/api/health` reports whether the layer
is on and where it points, which the Settings panel shows you before you upload
anything.

## Configuration

All optional, read from the environment or `backend/.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MAX_FILE_SIZE` | `10485760` (10 MB) | Per-file upload cap |
| `MAX_BULK_FILES` | `25` | Resumes per bulk batch |
| `MAX_CONTENT_LENGTH` | derived | Total request cap, sized to hold a full batch |
| `OCR_ENGINE` | `rapidocr` | `rapidocr` or `easyocr` |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `LLM_ENABLED` | `false` | Turn on AI enrichment |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `llama3.1:8b` | Model name |
| `LLM_API_KEY` | *(empty)* | Only needed by hosted providers |
| `LLM_TIMEOUT` | `45` | Seconds |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Status, catalog size, limits, AI state |
| GET | `/api/skills` | Skills catalog (`q`, `limit`), grouped by category |
| POST | `/api/analyze` | Analyze an upload (multipart: `resume`, optional `job_description`) |
| POST | `/api/analyze/text` | Analyze raw text (JSON: `resume_text`, optional `job_description`, `use_ai`) |
| POST | `/api/ats-check` | ATS checklist only (JSON: `resume_text`) |
| POST | `/api/report/download` | Render an analysis payload to PDF |
| POST | `/api/bulk-analyze` | Rank many resumes (multipart: `resumes`, optional `job_description`) |
| POST | `/api/candidate-report` | Narrative report for one scored candidate |
| POST | `/api/rewrite-cv` | Gap analysis, plus model rewrites when enrichment is on |
| POST | `/api/import/profile` | LinkedIn export or CV to structured CV fields (multipart `profile`, or JSON `text`) |

Supported uploads: **PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP**. Text-layer PDFs
never touch OCR; it runs only for image-only pages.

## Project structure

```text
ResumeAnalyzer/
├─ run.py                       # one-command launcher
├─ backend/
│  ├─ app/
│  │  ├─ data/skills.json       # 336 skills, 17 fields, with aliases
│  │  ├─ services/
│  │  │  ├─ catalog.py          # matching: longest-phrase, negation, ambiguity
│  │  │  ├─ text_utils.py       # normalization, stopwords, heading detection
│  │  │  ├─ analyzer.py         # sections, ATS checks, JD comparison
│  │  │  ├─ scoring.py          # the single weighted scoring model
│  │  │  ├─ feedback.py         # ranks fixes by point impact
│  │  │  ├─ profile_import.py   # LinkedIn export / CV -> structured fields
│  │  │  ├─ llm.py              # optional OpenAI-compatible enrichment
│  │  │  ├─ extractor.py        # PDF / DOCX / TXT / image text extraction
│  │  │  └─ report_generator.py
│  │  ├─ config.py
│  │  └─ routes.py
│  ├─ eval/                     # labeled corpora + accuracy harness
│  ├─ tests/
│  └─ run.py                    # API only
└─ frontend/
   ├─ css/{styles,import,cv-maker,cover-letter}.css
   ├─ js/{shared,import,analyzer,cv-maker,cover-letter,bulk-analyzer}.js
   ├─ index.html                # home
   ├─ import.html · analyzer.html · job-finder.html · cv-maker.html
   ├─ cover-letter-generator.html · bulk-analyzer.html
   └─ jobs.json                 # 28 roles across 11 fields
```

`analyzer.html` and `job-finder.html` share `js/analyzer.js`; the script adapts
to whichever elements the host page provides and to whether that page treats the
target role as required.

## Tests

```powershell
cd backend
pip install -r requirements-dev.txt
pytest
```

Covers the API surface, every detection rule that used to be wrong, the scoring
helpers, the LLM layer's failure modes, and the accuracy gate.

## Privacy

Uploads are written to a temporary file, read once, and deleted immediately.
Nothing is stored and no account exists. CV Maker and Cover Letter keep your
drafts in `localStorage` on your own machine. The only case where text leaves
your computer is a hosted AI endpoint you configured yourself — and pointing
`LLM_BASE_URL` at a local Ollama keeps even that on-device.
