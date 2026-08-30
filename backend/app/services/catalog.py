"""Skill catalog loading and evidence-aware skill matching.

Three rules make this materially more accurate than plain substring search:

1. **Longest phrase wins.** All terms compete in one alternation ordered by
   length, so "C++" consumes its span and "C" can never fire inside it.
2. **Negated and aspirational mentions do not count.** "No experience with
   Kubernetes" and "currently learning Rust" are claims about *absence*.
   Counting them tells a candidate they have a skill they explicitly disclaimed.
3. **Ambiguous tokens need corroboration.** "Excel", "Go", "C" and "R" are
   ordinary English. They only count in list context or beside a supporting term.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .text_utils import LIST_DELIMITERS, normalize_lines

# Skill names that collide with ordinary English. A bare match is not evidence;
# each needs list context or one of these supporting terms nearby.
AMBIGUOUS_CONTEXT: Dict[str, Set[str]] = {
    "c": {"programming", "language", "languages", "embedded", "systems", "c++", "cpp", "coding", "developer"},
    "go": {"golang", "programming", "language", "languages", "backend", "microservices", "developer", "concurrency"},
    "r": {"python", "statistics", "statistical", "sas", "spss", "stata", "cran", "tidyverse", "ggplot", "data"},
    "excel": {"microsoft", "ms", "advanced", "proficient", "pivot", "macros", "vba", "spreadsheet",
              "spreadsheets", "sheets", "word", "powerpoint", "formulas", "vlookup"},
    "sap": {"erp", "finance", "modules", "hana", "fico", "mm", "sd", "abap"},
    "pr": {"media", "press", "relations", "communications", "publicity"},
    # Bare "communication" is usually part of a course or department name
    # ("BA Communication Design"). As a claimed skill it sits in a list or
    # next to a qualifier.
    "communication": {"skills", "written", "verbal", "strong", "excellent", "clear",
                      "stakeholder", "interpersonal", "client", "effective", "team"},
}

# How far around an ambiguous match to look for a supporting term.
_CONTEXT_WINDOW = 48

# Phrases that turn a nearby skill mention into a claim of *not* having it.
# Each is multi-word on purpose: a bare "learning" would swallow the
# "learning" in "machine learning".
NEGATION_CUES = (
    "no experience", "not experienced", "no exposure", "no knowledge", "no hands-on",
    "no hands on", "not familiar", "unfamiliar with", "never used", "never worked with",
    "no background in", "little experience", "limited experience", "no formal training",
    "without experience", "lack experience", "lacking experience", "no prior experience",
)

ASPIRATION_CUES = (
    "want to learn", "wish to learn", "hope to learn", "plan to learn", "planning to learn",
    "looking to learn", "keen to learn", "eager to learn", "interested in learning",
    "currently learning", "am learning", "i am learning", "starting to learn",
    "beginning to learn", "would like to learn", "aiming to learn", "learning about",
)

ALL_NEGATION_CUES = NEGATION_CUES + ASPIRATION_CUES

# A negation cue only reaches forward to the end of its clause. Sentence
# terminators and hard breaks end its reach; "and"/"or" do not, so
# "no experience with Kubernetes or Terraform" suppresses both.
_CLAUSE_BREAK = re.compile(r"[.;!?\n]")


@dataclass(frozen=True)
class Skill:
    name: str
    category: str


@lru_cache(maxsize=4)
def _load_raw(skills_file_str: str) -> str:
    return Path(skills_file_str).read_text(encoding="utf-8")


@lru_cache(maxsize=4)
def _parse_catalog(skills_file_str: str) -> Tuple[Tuple[Skill, ...], Tuple[Tuple[str, Tuple[str, ...]], ...]]:
    """Return (skills, term_index) for a catalog file.

    ``term_index`` maps each searchable term to the skill names it evidences;
    one term can serve several skills (e.g. "ui/ux" implies User Experience).
    Supports the v2 category format and the legacy flat ``{"skills": [...]}``.
    """
    data = json.loads(_load_raw(skills_file_str))

    skills: List[Skill] = []
    term_to_skills: Dict[str, List[str]] = {}

    def add(name: str, category: str, terms: List[str]) -> None:
        skills.append(Skill(name=name, category=category))
        for term in terms:
            key = re.sub(r"\s+", " ", term.strip().lower())
            if not key:
                continue
            bucket = term_to_skills.setdefault(key, [])
            if name not in bucket:
                bucket.append(name)

    categories = data.get("categories")
    if isinstance(categories, dict):
        for category, entries in categories.items():
            for entry in entries:
                if isinstance(entry, str):
                    add(entry, category, [entry])
                elif isinstance(entry, dict) and entry.get("name"):
                    name = entry["name"]
                    terms = [name, *entry.get("aliases", []), *entry.get("evidence", [])]
                    add(name, category, terms)
    else:
        for name in data.get("skills", []):
            add(name, "General", [name])

    index = tuple((term, tuple(names)) for term, names in term_to_skills.items())
    return tuple(skills), index


@lru_cache(maxsize=4)
def _build_matcher(skills_file_str: str) -> Tuple["re.Pattern", Dict[str, Tuple[str, ...]]]:
    """Compile every term into one alternation, longest phrase first.

    Ordering is what guarantees "C++" beats "C" and "machine learning" beats
    a stray "learning": Python's alternation takes the first branch that
    matches at a position.
    """
    _, index = _parse_catalog(skills_file_str)
    lookup = {term: names for term, names in index}

    # Longest first; tie-break alphabetically for a stable, reproducible regex.
    terms = sorted(lookup, key=lambda t: (-len(t), t))

    def source(term: str) -> str:
        # Allow any whitespace run where the term has a space, so a term can
        # still match across an awkward line wrap inside a phrase.
        return r"\s+".join(re.escape(part) for part in term.split(" "))

    # One shared boundary for the whole alternation. The trailing guard is what
    # stops "c" from matching inside "c++" even before ordering is considered;
    # the `\.\w` half of it stops single letters from matching the initial in
    # an email address or a name ("r.adeyemi@example.com" is not the R language).
    pattern = re.compile(
        r"(?<![\w+#.@])(?:" + "|".join(source(t) for t in terms) + r")(?![\w#+]|\.\w|@)",
        re.IGNORECASE,
    )
    return pattern, lookup


def load_catalog(skills_file: Path) -> List[Skill]:
    skills, _ = _parse_catalog(str(Path(skills_file).resolve()))
    return list(skills)


def load_skills(skills_file: Path) -> List[str]:
    """Flat list of skill names, for the /api/skills catalog endpoint."""
    return [skill.name for skill in load_catalog(skills_file)]


def load_categories(skills_file: Path) -> Dict[str, str]:
    """Map every skill name to its category."""
    return {skill.name: skill.category for skill in load_catalog(skills_file)}


def _is_negated(text: str, start: int) -> bool:
    """True when a negation or aspiration cue governs the clause at ``start``.

    Looks back only to the start of the current clause, so a cue in the
    previous sentence cannot suppress an unrelated later mention.
    """
    breaks = [m.end() for m in _CLAUSE_BREAK.finditer(text, 0, start)]
    clause_start = breaks[-1] if breaks else 0
    clause = text[clause_start:start]
    return any(cue in clause for cue in ALL_NEGATION_CUES)


def _has_corroboration(text: str, start: int, end: int, term: str) -> bool:
    """Whether an ambiguous term's occurrence is really a skill mention."""
    before = text[start - 1] if start > 0 else "\n"
    after = text[end] if end < len(text) else "\n"
    if before in LIST_DELIMITERS or after in LIST_DELIMITERS:
        return True

    # Corroboration has to come from the same line. Without that clamp a
    # "Skills" heading two lines below would vouch for "Communication" in
    # "BA Communication Design", which is a degree name, not a skill.
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end

    window = text[max(line_start, start - _CONTEXT_WINDOW): min(line_end, end + _CONTEXT_WINDOW)]
    neighbours = set(re.findall(r"[a-z0-9+#]+", window))
    return bool(neighbours & AMBIGUOUS_CONTEXT.get(term, set()))


def find_skills(text: str, skills_file: Path) -> Dict[str, object]:
    """Detect skills evidenced by ``text``.

    Returns detected names plus the mentions that were deliberately rejected,
    so the UI can explain itself instead of silently disagreeing with the user.
    """
    pattern, lookup = _build_matcher(str(Path(skills_file).resolve()))
    normalized = normalize_lines(text)

    detected: Set[str] = set()
    disclaimed: Set[str] = set()

    for match in pattern.finditer(normalized):
        term = re.sub(r"\s+", " ", match.group(0).lower())
        names = lookup.get(term)
        if not names:
            continue

        if term in AMBIGUOUS_CONTEXT and not _has_corroboration(
            normalized, match.start(), match.end(), term
        ):
            continue

        if _is_negated(normalized, match.start()):
            disclaimed.update(names)
            continue

        detected.update(names)

    # A skill stated positively somewhere outranks a single disclaimer.
    disclaimed -= detected

    return {
        "detected": sorted(detected, key=str.lower),
        "disclaimed": sorted(disclaimed, key=str.lower),
    }
