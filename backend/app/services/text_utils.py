"""Shared text normalization, stopwords, and heading recognition."""

import re
from typing import List

WORD_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.#-]{1,}\b")

# Characters that legitimately hug a skill token in a resume list.
LIST_DELIMITERS = set(",;:/|•·()[]{}\n\t")

# Generic English + resume/JD boilerplate. A JD is mostly boilerplate, so a
# match score computed over raw tokens measures writing style, not fit. This
# list is what makes the score mean something.
STOPWORDS = frozenset(
    """
    a about above across after again against all almost along already also although always am among an and
    another any anyone anything are around as at back be became because become becomes been before being below
    best better between beyond both but by can cannot could did do does doing done down during each either else
    enough etc even ever every everyone everything except few first for from further get gets give given go goes
    going good got had has have having he her here hers him his how however i if in inside instead into is it its
    itself just keep kept know known last least less let like likely made make makes making many may maybe me might
    more most much must my myself near need needs neither never new next no none nor not nothing now of off often on
    once one only onto or other others otherwise our ours out over own per perhaps please put rather really same say
    see seen several shall she should since so some someone something still such take taken than that the their them
    themselves then there these they thing things this those though through throughout thus to together too toward
    towards under until up upon us use used uses using usually very via was way we well were what when where whether
    which while who whom whose why will with within without would yet you your yours yourself

    ability able about across additional advantage applicant applicants application applications apply applying
    background benefits candidate candidates career company competitive culture description desirable duties
    employee employer employment environment equal essential excellent experience experienced familiarity flexible
    full growth hire hiring holiday hour hours ideal including insurance job jobs join joining knowledge level
    location looking must offer offers opportunity opportunities organisation organization package paid pension
    person plus position positions preferred proven qualification qualifications qualified relevant remote
    requirement requirements responsibilities responsibility role roles salary seeking senior skill skills someone
    strong successful suitable team teams temporary time title understanding vacancy valued work working world year
    years
    """.split()
)

# Words that read as section headings in real resumes, mapped to a canonical
# section name. Matching is heading-anchored, so "education technology" in a
# sentence never counts as an Education section.
SECTION_HEADINGS = {
    "summary": [
        "summary", "professional summary", "career summary", "executive summary",
        "profile", "professional profile", "personal profile", "about me", "about",
        "objective", "career objective", "overview", "introduction",
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment",
        "employment history", "work history", "career history", "roles",
        "professional background", "relevant experience", "internship",
        "internships", "positions held", "career",
    ],
    "education": [
        "education", "academic background", "academic qualifications",
        "academics", "educational background", "degrees", "schooling",
    ],
    "projects": [
        "projects", "key projects", "selected projects", "personal projects",
        "academic projects", "portfolio", "case studies", "side projects",
    ],
    "certifications": [
        "certifications", "certification", "certificates", "licences", "licenses",
        "credentials", "qualifications", "professional qualifications", "courses",
        "training", "professional development",
        "awards", "achievements", "honors", "honours",
    ],
    "skills": [
        "skills", "technical skills", "core skills", "key skills", "soft skills",
        "competencies", "core competencies", "technologies", "tech stack",
        "toolkit", "tools", "expertise", "areas of expertise", "proficiencies",
        "what i know", "strengths", "capabilities", "specialties", "specialities",
    ],
}

# Reverse index, longest phrase first so "professional experience" wins over
# "experience" when a heading contains both.
_HEADING_LOOKUP = sorted(
    ((phrase, section) for section, phrases in SECTION_HEADINGS.items() for phrase in phrases),
    key=lambda pair: -len(pair[0]),
)

# A heading is short, unpunctuated, and sits on its own line.
_MAX_HEADING_WORDS = 5
_MAX_HEADING_CHARS = 60

# "(2021 - Present)", "Jan 2020 – Mar 2023", "2018-2022": strong evidence of a
# dated role or degree entry even when the heading is unconventional.
DATE_RANGE_PATTERN = re.compile(
    r"(?:19|20)\d{2}\s*(?:-|–|—|to)\s*(?:(?:19|20)\d{2}|present|current|now|date)",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    """Collapse all whitespace to single spaces, for phrase lookups."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def normalize_lines(text: str) -> str:
    """Lowercase and tidy spacing while preserving line structure.

    Skill and heading detection both rely on line breaks, so they need this
    variant rather than ``normalize_text``.
    """
    collapsed = re.sub(r"[^\S\n]+", " ", text.lower())
    return re.sub(r"\n{2,}", "\n", collapsed).strip()


def heading_of(line: str) -> str:
    """Return the canonical section a line is a heading for, else ""․

    Requires the line to actually look like a heading: short, few words, and
    no sentence punctuation. This is the whole reason "I wrote the executive
    summary for our client" no longer counts as a Summary section.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > _MAX_HEADING_CHARS:
        return ""

    # Drop decoration a heading may carry: trailing colon, leading bullets,
    # and the rule characters people use to underline headings.
    cleaned = stripped.strip("=-_*#•~ ").rstrip(":").strip()
    if not cleaned:
        return ""

    # Sentence punctuation disqualifies it; headings are not sentences.
    if any(ch in cleaned for ch in ".!?"):
        return ""

    words = cleaned.split()
    if not words or len(words) > _MAX_HEADING_WORDS:
        return ""

    lowered = " ".join(words).lower()
    # Strip a leading ampersand-joined pair down to comparable text, e.g.
    # "Skills & Tools" -> "skills tools".
    comparable = re.sub(r"[&/|,]+", " ", lowered)
    comparable = re.sub(r"\s+", " ", comparable).strip()

    for phrase, section in _HEADING_LOOKUP:
        if comparable == phrase or re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", comparable):
            return section
    return ""


def count_words(text: str) -> int:
    """Word count as a person would read it off a word processor.

    One definition, used by every caller. The ATS length check and the figure
    shown beside the score used to count differently -- the checker's pattern
    required a leading letter and two characters, so it dropped every number
    and short token. The same resume was reported as both 102 and 79 words on
    one screen.
    """
    return len((text or "").split())


def content_words(text: str) -> List[str]:
    """Meaningful tokens only: stopwords and one/two-letter noise removed."""
    return [
        token
        for token in WORD_PATTERN.findall(normalize_text(text))
        if token not in STOPWORDS and len(token) > 2
    ]
