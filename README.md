# Smart Resume Analyzer

A complete web-based **Smart Resume Analyzer** project with:
- Flask backend API
- Modern responsive frontend UI with drag-and-drop upload
- Resume skill detection, missing skill analysis, professional feedback
- Optional job description matching
- ATS structure analysis with section coverage insights
- Resume score (0-100)
- PDF report export
- Ready-to-deploy setup for Render/Railway (backend) and Netlify/Vercel (frontend)

## Project Structure

```text
ResumeAnalyzer/
├─ backend/
│  ├─ app/
│  │  ├─ data/skills.json
│  │  ├─ services/
│  │  │  ├─ analyzer.py
│  │  │  ├─ extractor.py
│  │  │  ├─ feedback.py
│  │  │  └─ report_generator.py
│  │  ├─ config.py
│  │  ├─ routes.py
│  │  └─ __init__.py
│  ├─ requirements.txt
│  ├─ run.py
│  ├─ wsgi.py
│  ├─ Procfile
│  └─ runtime.txt
├─ frontend/
│  ├─ css/styles.css
│  ├─ js/app.js
│  ├─ index.html
│  ├─ netlify.toml
│  └─ vercel.json
└─ README.md
```

## Features

### Backend (Flask)
- Upload resume files in **PDF and image** formats
- PDF text extraction with **PyMuPDF**
- Image text extraction with **EasyOCR**
- Skill detection against a predefined skills dataset
- Missing skills identification
- Professional natural-language feedback generation
- Optional job description keyword matching and improvement tips
- ATS-style structure analysis (present/missing sections + actionable tips)
- ATS checker with checklist, score, and recommendations
- Resume score calculation (0-100)
- JSON API responses
- PDF analysis report export endpoint
- Skills catalog endpoint with query filtering
- Raw text analysis endpoint (for integrations and testing)

### Frontend (HTML/CSS/JS)
- Modern and responsive visual design
- Drag-and-drop upload area
- Dark mode toggle with persistent preference
- Result cards for:
  - Detected skills
  - Missing skills
  - Top resume keywords
  - Feedback and suggestions
  - Job description match data
  - ATS structure insights
  - ATS checker (passed/failed checklist)
  - Skills explorer (searchable catalog)
- Animated transitions, hover states, iconography, and color highlights

## Local Setup

## 1. Backend Setup

1. Open terminal in the `backend` folder.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Run Flask app.

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Server runs at: `http://localhost:5000`

Health check:

```text
GET http://localhost:5000/api/health
```

## 2. Frontend Setup

Open another terminal in the `frontend` folder and run a static server:

```powershell
cd frontend
python -m http.server 5500
```

Open in browser: `http://localhost:5500`

Set API Base URL in the UI to: `http://localhost:5000`

## API Endpoints

### Analyze Resume
- **POST** `/api/analyze`
- Content-Type: `multipart/form-data`
- Form fields:
  - `resume` (required file)
  - `job_description` (optional text)

Response (example):

```json
{
  "resume_score": 76,
  "detected_skills": ["Flask", "Python", "SQL"],
  "missing_skills": ["Docker", "Kubernetes"],
  "top_keywords": [{ "keyword": "python", "count": 5 }],
  "feedback": {
    "professional_summary": ["..."],
    "suggestions": ["..."]
  },
  "job_description_analysis": {
    "job_description_match_score": 68,
    "matched_keywords": ["api", "python"],
    "missing_jd_keywords": ["docker", "redis"],
    "improvement_tips": ["..."]
  },
  "meta": {
    "detected_skill_count": 3,
    "missing_skill_count": 2
  }
}
```

### Analyze Raw Resume Text
- **POST** `/api/analyze/text`
- Content-Type: `application/json`
- JSON body:
  - `resume_text` (required string)
  - `job_description` (optional string)

### Skills Catalog
- **GET** `/api/skills`
- Query params:
  - `q` (optional, substring search)
  - `limit` (optional, default 200, max 500)

Example:

```text
GET /api/skills?q=cloud&limit=50
```

### ATS Checker
- **POST** `/api/ats-check`
- Content-Type: `application/json`
- JSON body:
  - `resume_text` (required string)

Response fields:
- `ats_score`
- `checks`
- `passed_checks`
- `total_checks`
- `recommendations`

### Download PDF Report
- **POST** `/api/report/download`
- Content-Type: `application/json`
- Body: analysis JSON (same shape as response above)
- Returns: downloadable PDF report

## Deployment

## Backend on Render or Railway
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn wsgi:app`
- Runtime already provided in `runtime.txt`
- Optional Render blueprint file included: `backend/render.yaml`

## Frontend on Netlify
- Publish directory: `frontend`
- `netlify.toml` included for SPA-style routing

## Frontend on Vercel
- Deploy `frontend` directory as static site
- `vercel.json` included for rewrite routing

## Notes
- EasyOCR may download model files on first run.
- For production OCR speed, consider running on CPU-optimized or GPU-enabled infrastructure.
- You can expand `backend/app/data/skills.json` with domain-specific skills.

## Running Tests

Run backend tests with:

```powershell
cd backend
pytest
```

Current test coverage includes:
- Health endpoint
- Skills endpoint and query filtering
- Raw text analysis endpoint
- Upload analysis endpoint (with extractor monkeypatched for fast test execution)
- Input validation behavior
