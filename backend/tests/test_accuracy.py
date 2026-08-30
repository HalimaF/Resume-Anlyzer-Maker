"""Accuracy regression gate.

The analyzer's whole value is being right, so precision and recall are treated
as a test that fails the build, not a number in a report someone reads once.
"""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.analyzer import analyze_resume_structure, detect_skills, load_skills  # noqa: E402
from eval.corpus import CASES  # noqa: E402
from eval.holdout import CASES as HOLDOUT_CASES  # noqa: E402

SKILLS_FILE = BACKEND / "app" / "data" / "skills.json"
TARGET_F1 = 0.95


def _f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0


def _score(cases):
    catalog = set(load_skills(SKILLS_FILE))
    s_tp = s_fp = s_fn = 0
    sec_tp = sec_fp = sec_fn = 0
    errors = []

    for case in cases:
        predicted = set(detect_skills(case["text"], SKILLS_FILE)["detected_skills"])
        expected = set(case["skills"]) & catalog
        s_tp += len(predicted & expected)
        s_fp += len(predicted - expected)
        s_fn += len(expected - predicted)
        if predicted != expected:
            errors.append(f"{case['id']}: +{sorted(predicted - expected)} -{sorted(expected - predicted)}")

        pred_sec = set(analyze_resume_structure(case["text"])["present_sections"])
        exp_sec = set(case["sections"])
        sec_tp += len(pred_sec & exp_sec)
        sec_fp += len(pred_sec - exp_sec)
        sec_fn += len(exp_sec - pred_sec)
        if pred_sec != exp_sec:
            errors.append(f"{case['id']} sections: +{sorted(pred_sec - exp_sec)} -{sorted(exp_sec - pred_sec)}")

    return _f1(s_tp, s_fp, s_fn), _f1(sec_tp, sec_fp, sec_fn), errors


@pytest.mark.parametrize(
    "cases,label",
    [(CASES, "tuned corpus"), (HOLDOUT_CASES, "held-out corpus")],
)
def test_skill_detection_meets_accuracy_target(cases, label):
    skill_f1, _, errors = _score(cases)
    assert skill_f1 >= TARGET_F1, (
        f"Skill F1 on the {label} is {skill_f1:.1%}, below the {TARGET_F1:.0%} target.\n"
        + "\n".join(errors)
    )


@pytest.mark.parametrize(
    "cases,label",
    [(CASES, "tuned corpus"), (HOLDOUT_CASES, "held-out corpus")],
)
def test_section_detection_meets_accuracy_target(cases, label):
    _, section_f1, errors = _score(cases)
    assert section_f1 >= TARGET_F1, (
        f"Section F1 on the {label} is {section_f1:.1%}, below the {TARGET_F1:.0%} target.\n"
        + "\n".join(errors)
    )
