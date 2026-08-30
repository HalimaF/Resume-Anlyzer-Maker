"""Turn an existing profile or CV into structured CV Maker fields.

Handles two inputs with one parser:

* **LinkedIn's own PDF export** (profile -> More -> Save to PDF). This is the
  supported way to get a profile out of LinkedIn. Fetching a profile URL is
  not: the page serves an authwall to anyone not signed in, and LinkedIn's
  robots.txt prohibits automated access outright. So we parse the export the
  person already has a right to, rather than scraping.
* **Any existing resume** in PDF, DOCX or TXT.

Both arrive here as plain text. The parser keys off date ranges rather than
headings wherever it can, because dates survive PDF extraction far more
reliably than layout does.
"""

import re
from typing import Any, Dict, List, Optional

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

# "January 2021 - Present", "2018 - 2022", "Jun 2019 – Dec 2020"
DATE_RANGE = re.compile(
    rf"(?P<start>(?:{MONTHS})\.?\s+\d{{4}}|\d{{4}})"
    rf"\s*(?:-|–|—|to)\s*"
    rf"(?P<end>(?:{MONTHS})\.?\s+\d{{4}}|\d{{4}}|Present|Current|Now|Today)",
    re.IGNORECASE,
)

# LinkedIn appends "(3 years 8 months)" to each role.
DURATION = re.compile(r"\(\s*\d+\s*(?:year|yr|month|mo)s?[^)]*\)", re.IGNORECASE)

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
LINKEDIN_URL = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w\-%]+", re.IGNORECASE)
GENERIC_URL = re.compile(r"(?:https?://)?(?:www\.)?[\w-]+\.[a-z]{2,}(?:/[\w\-./%]*)?", re.IGNORECASE)
GITHUB_URL = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.IGNORECASE)

# Page furniture in a LinkedIn export, plus its footer contact repeats.
NOISE = (
    re.compile(r"^\s*page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*contact\s*$", re.IGNORECASE),
)

# Headings, in the spellings both LinkedIn and ordinary resumes use.
SECTION_ALIASES = {
    "summary": ("summary", "about", "about me", "profile", "professional summary",
                "career summary", "objective", "career objective", "overview"),
    "experience": ("experience", "work experience", "professional experience",
                   "employment", "employment history", "work history", "career history",
                   "positions held", "roles"),
    "education": ("education", "academic background", "educational background",
                  "academics", "schooling", "degrees"),
    "skills": ("top skills", "skills", "technical skills", "core skills", "key skills",
               "competencies", "core competencies", "technologies", "expertise",
               "areas of expertise", "tools", "toolkit", "proficiencies"),
    "certifications": ("certifications", "certification", "licenses & certifications",
                       "licenses", "licences", "credentials", "courses", "training",
                       "honors", "honours", "honors-awards", "awards", "publications"),
    "projects": ("projects", "key projects", "selected projects", "portfolio",
                 "personal projects", "academic projects"),
    "languages": ("languages",),
    "contact": ("contact", "contact information", "personal details"),
}

_HEADING_LOOKUP = {
    alias: canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}

_MAX_HEADING_WORDS = 4


def _is_noise(line: str) -> bool:
    return any(pattern.match(line) for pattern in NOISE)


def _heading(line: str) -> Optional[str]:
    """Canonical section name if this line is a heading, else None."""
    cleaned = line.strip().strip("=-_*#•~ ").rstrip(":").strip()
    if not cleaned or len(cleaned) > 48 or len(cleaned.split()) > _MAX_HEADING_WORDS:
        return None
    if any(ch in cleaned for ch in ".!?"):
        return None
    key = re.sub(r"[&/|,]+", " ", cleaned.lower())
    key = re.sub(r"\s+", " ", key).strip()
    return _HEADING_LOOKUP.get(key)


def _split_sections(lines: List[str]) -> Dict[str, List[str]]:
    """Bucket lines under the section heading that precedes them."""
    sections: Dict[str, List[str]] = {"_preamble": []}
    current = "_preamble"
    for line in lines:
        heading = _heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def looks_like_linkedin(text: str) -> bool:
    """Whether this is LinkedIn's own PDF export rather than a plain resume."""
    lowered = (text or "").lower()
    signals = sum(
        (
            bool(LINKEDIN_URL.search(lowered)),
            "top skills" in lowered,
            bool(DURATION.search(lowered)),
            "(linkedin)" in lowered,
        )
    )
    return signals >= 2


def _clean_lines(text: str) -> List[str]:
    lines = []
    for raw in (text or "").splitlines():
        line = raw.replace(" ", " ").rstrip()
        if not line.strip() or _is_noise(line):
            continue
        lines.append(line.strip())
    return lines


def _extract_contact(text: str, lines: List[str]) -> Dict[str, str]:
    email = EMAIL.search(text)
    linkedin = LINKEDIN_URL.search(text)
    github = GITHUB_URL.search(text)

    # A phone number must not be a date range or a duration.
    phone = ""
    for candidate in PHONE.finditer(text):
        value = candidate.group(0).strip()
        digits = re.sub(r"\D", "", value)
        if 7 <= len(digits) <= 15 and not DATE_RANGE.search(value):
            phone = value
            break

    website = ""
    for candidate in GENERIC_URL.finditer(text):
        url = candidate.group(0)
        if any(host in url.lower() for host in ("linkedin.com", "github.com")):
            continue
        if url.lower().endswith((".png", ".jpg", ".pdf")):
            continue
        if "@" in url or "." not in url.split("/")[0]:
            continue
        website = url
        break

    return {
        "email": email.group(0) if email else "",
        "phone": phone,
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
        "website": website,
    }


def _looks_like_person_name(line: str) -> bool:
    """A plausible human name: 2-4 capitalised words, no digits or symbols."""
    if EMAIL.search(line) or "http" in line.lower() or any(ch.isdigit() for ch in line):
        return False
    words = line.split()
    if not 2 <= len(words) <= 4:
        return False
    if _heading(line):
        return False
    capitalised = sum(1 for word in words if word[:1].isupper())
    return capitalised >= max(2, len(words) - 1)


def _name_index(lines: List[str], linkedin_url: str) -> int:
    """Index of the line holding the person's name, or -1.

    A LinkedIn export opens with a sidebar of skills and certifications, and
    those are capitalised two-word phrases too -- "Curriculum Development"
    looks exactly like a name. Three signals, strongest first.
    """
    # 1. The profile URL slug is the name, with the punctuation removed.
    slug = ""
    if linkedin_url:
        slug = re.sub(r"[^a-z]", "", linkedin_url.rsplit("/", 1)[-1].lower())
    if slug:
        for index, line in enumerate(lines):
            if re.sub(r"[^a-z]", "", line.lower()) == slug:
                return index

    # 2. LinkedIn's headline sits right under the name and reads "Role at Employer".
    for index, line in enumerate(lines[:60]):
        if not _looks_like_person_name(line):
            continue
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if re.search(r"\s+at\s+|\s+\|\s+", following) and not _heading(following):
            return index

    # 3. Fall back to the first plausible name outside a sidebar list.
    for index, line in enumerate(lines[:40]):
        if _looks_like_person_name(line):
            return index
    return -1


def _extract_identity(lines: List[str], linkedin_url: str) -> Dict[str, Any]:
    """Pull name, headline and location, and report which lines they used.

    The caller removes those lines before bucketing sections, otherwise the
    identity block gets absorbed by whichever sidebar heading preceded it.
    """
    index = _name_index(lines, linkedin_url)
    if index < 0:
        return {"fullName": "", "title": "", "location": "", "consumed": set()}

    consumed = {index}
    headline = ""
    location = ""

    for offset in (1, 2):
        position = index + offset
        if position >= len(lines):
            break
        candidate = lines[position]
        if _heading(candidate) or EMAIL.search(candidate) or DATE_RANGE.search(candidate):
            break
        # A comma-separated place name is the location; anything else is the headline.
        is_location = candidate.count(",") >= 1 and len(candidate) <= 80 and " at " not in candidate
        if is_location and not location:
            location = candidate
            consumed.add(position)
        elif not headline and len(candidate) <= 130:
            headline = candidate
            consumed.add(position)
        else:
            break

    return {
        "fullName": lines[index],
        "title": headline,
        "location": location,
        "consumed": consumed,
    }


ORGANISATION_SUFFIX = re.compile(
    r"\b(inc|ltd|limited|llc|llp|gmbh|plc|corp|corporation|co|company|group|"
    r"university|college|school|academy|hospital|trust|foundation|institute|"
    r"partners|associates|consulting|labs|technologies|solutions)\b\.?$",
    re.IGNORECASE,
)


def _is_organisation(line: str) -> bool:
    """Whether a line names an employer rather than a role."""
    return bool(ORGANISATION_SUFFIX.search(line.strip()))


def _is_header_like(line: str) -> bool:
    """Short, unpunctuated, not a bullet: the shape of a title or employer."""
    text = line.strip()
    if not text or len(text) > 80:
        return False
    if text.endswith((".", ";", ":")):
        return False
    if re.match(r"^[-*•·▪●○‣⁃]", text):
        return False
    # A sentence with many words is prose, not a header.
    return len(text.split()) <= 9


def _header_lines(pending: List[str]) -> List[str]:
    """The trailing lines above a date range that name the role and employer."""
    return [
        item
        for item in pending[-3:]
        if not DURATION.fullmatch(item.strip()) and _is_header_like(item)
    ]


def _parse_experience(block: List[str]) -> List[Dict[str, str]]:
    """Split an Experience block into entries, anchored on date ranges.

    Every real role carries a date range, and dates survive PDF extraction far
    better than indentation or font weight. So each date line closes one entry:
    the lines above it name the role and employer, the lines below describe it.
    """
    entries: List[Dict[str, str]] = []
    pending: List[str] = []
    index = 0

    while index < len(block):
        line = block[index]
        match = DATE_RANGE.search(line)

        if not match:
            pending.append(line)
            index += 1
            continue

        start = match.group("start").strip()
        end = match.group("end").strip()

        # Lines above the date name the role and the employer. LinkedIn writes
        # company first, then title; most resumes do the reverse, and many put
        # both on one line as "Title, Employer".
        header = _header_lines(pending)
        title, company = "", ""
        if len(header) >= 2:
            company, title = header[-2], header[-1]
            # A line ending in an organisation suffix is the employer, not the role.
            if _is_organisation(title) and not _is_organisation(company):
                company, title = title, company
        elif header:
            title = header[-1]

        # "Audit Manager, Ledger and Co" on one line.
        if title and not company and "," in title:
            role, _, employer = title.rpartition(",")
            if role.strip() and employer.strip():
                title, company = role.strip(), employer.strip()

        # Everything until the next date line describes the role.
        description: List[str] = []
        location = ""
        cursor = index + 1
        while cursor < len(block) and not DATE_RANGE.search(block[cursor]):
            candidate = block[cursor]
            if DURATION.fullmatch(candidate.strip()):
                cursor += 1
                continue
            # A short comma-separated line right after the dates is the location.
            if not description and not location and candidate.count(",") >= 1 and len(candidate) <= 60:
                location = candidate
            else:
                description.append(candidate)
            cursor += 1

        # The next entry's header sits at the tail of what we just consumed.
        # Take back only lines that read as a header, so a full sentence of
        # description is never mistaken for the next job title.
        pending = []
        if cursor < len(block):
            taken = 0
            while description and taken < 2 and _is_header_like(description[-1]):
                pending.insert(0, description.pop())
                taken += 1

        entries.append({
            "title": title.strip(),
            "company": company.strip(),
            "start": start,
            "end": end,
            "location": location,
            "description": "\n".join(
                re.sub(r"^[-*•·▪●○‣⁃]\s*", "", item).strip() for item in description
            ).strip(),
        })
        index = cursor

    return entries


def _parse_education(block: List[str]) -> List[Dict[str, str]]:
    """Education entries: institution, qualification, and a year or range."""
    entries: List[Dict[str, str]] = []
    pending: List[str] = []

    for line in block:
        year_match = DATE_RANGE.search(line) or re.search(r"\b(?:19|20)\d{2}\b", line)
        # LinkedIn writes "BSc, Computer Science · (2014 - 2018)" on one line.
        if year_match:
            text = DURATION.sub("", line)
            year = year_match.group(0).strip()
            qualification = text.replace(year, "").strip(" ·,()-–—")
            school = ""
            if pending:
                school = pending[-1]
            if not qualification and len(pending) >= 2:
                qualification, school = pending[-1], pending[-2]

            if qualification or school:
                degree, _, field = qualification.partition(",")
                entries.append({
                    "degree": degree.strip(" ·,"),
                    "field": field.strip(" ·,"),
                    "school": school.strip(),
                    "year": year,
                })
            pending = []
        else:
            pending.append(line)

    # A trailing entry with no year at all is still worth keeping.
    if len(pending) >= 2:
        entries.append({
            "degree": pending[-1].strip(),
            "field": "",
            "school": pending[-2].strip(),
            "year": "",
        })
    return entries


def _parse_skills(block: List[str]) -> List[str]:
    """Skills arrive one-per-line from LinkedIn, comma-separated from resumes."""
    skills: List[str] = []
    for line in block:
        parts = [part.strip(" ·•|") for part in re.split(r"[,;|·•]", line)]
        for part in parts:
            if 1 < len(part) <= 60 and not _heading(part):
                skills.append(part)

    seen = set()
    unique = []
    for skill in skills:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            unique.append(skill)
    return unique[:60]


def parse_profile(text: str) -> Dict[str, Any]:
    """Parse a LinkedIn export or a resume into CV Maker fields."""
    lines = _clean_lines(text)
    if not lines:
        return {
            "source": "unknown",
            "fields_found": 0,
            "warnings": ["No readable text was found in that file."],
            "profile": {},
        }

    contact = _extract_contact(text, lines)
    identity = _extract_identity(lines, contact["linkedin"])

    # Strip the identity block before bucketing, or the sidebar heading above
    # it (usually Certifications) absorbs the name, headline and location.
    body = [line for index, line in enumerate(lines) if index not in identity["consumed"]]
    sections = _split_sections(body)

    summary_lines = sections.get("summary", [])
    summary = " ".join(summary_lines).strip()

    experience = _parse_experience(sections.get("experience", []))
    education = _parse_education(sections.get("education", []))
    skills = _parse_skills(sections.get("skills", []))
    certifications = [line for line in sections.get("certifications", []) if len(line) > 2][:12]

    profile = {
        "fullName": identity["fullName"],
        "title": identity["title"],
        "location": identity["location"],
        "email": contact["email"],
        "phone": contact["phone"],
        "linkedin": contact["linkedin"],
        "github": contact["github"] or contact["website"],
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "certifications": certifications,
    }

    # Say plainly what could not be found, so nobody assumes an empty field
    # means the parser succeeded and their profile is thin.
    warnings: List[str] = []
    if not profile["fullName"]:
        warnings.append("Could not identify your name. Add it in the CV Maker.")
    if not experience:
        warnings.append("No dated roles were found. Add your experience manually.")
    if not education:
        warnings.append("No education entries were found.")
    if not skills:
        warnings.append("No skills list was found.")
    if not summary:
        warnings.append("No summary or About section was found.")

    filled = sum(
        1
        for value in (
            profile["fullName"], profile["email"], profile["summary"],
            profile["skills"], profile["experience"], profile["education"],
        )
        if value
    )

    return {
        "source": "linkedin" if looks_like_linkedin(text) else "resume",
        "fields_found": filled,
        "warnings": warnings,
        "profile": profile,
    }
