"""Measure analyzer accuracy against the hand-labeled corpus.

Reports precision / recall / F1 for skill detection and for section detection,
plus a per-case breakdown of exactly which calls were wrong. Run from
``backend/``:

    python -m eval.measure
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.analyzer import (  # noqa: E402
    analyze_resume_structure,
    detect_skills,
    load_skills,
)
from eval.corpus import CASES  # noqa: E402
from eval.holdout import CASES as HOLDOUT_CASES  # noqa: E402

SKILLS_FILE = Path(__file__).resolve().parent.parent / "app" / "data" / "skills.json"


def prf(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def evaluate(cases, title: str):
    catalog = load_skills(SKILLS_FILE)

    s_tp = s_fp = s_fn = 0
    sec_tp = sec_fp = sec_fn = 0
    rows = []

    for case in cases:
        predicted = set(detect_skills(case["text"], SKILLS_FILE)["detected_skills"])
        expected = set(case["skills"])
        # Only judge skills the catalog could possibly name; an unlisted skill
        # is a catalog-coverage problem, reported separately below.
        expected_in_catalog = expected & set(catalog)

        tp = predicted & expected_in_catalog
        fp = predicted - expected_in_catalog
        fn = expected_in_catalog - predicted
        s_tp, s_fp, s_fn = s_tp + len(tp), s_fp + len(fp), s_fn + len(fn)

        structure = analyze_resume_structure(case["text"])
        pred_sec = set(structure["present_sections"])
        exp_sec = set(case["sections"])
        stp, sfp, sfn = pred_sec & exp_sec, pred_sec - exp_sec, exp_sec - pred_sec
        sec_tp, sec_fp, sec_fn = sec_tp + len(stp), sec_fp + len(sfp), sec_fn + len(sfn)

        rows.append((case["id"], sorted(fp), sorted(fn), sorted(sfp), sorted(sfn)))

    print("=" * 78)
    print(f"{title} - PER-CASE ERRORS")
    print("=" * 78)
    for case_id, fp, fn, sfp, sfn in rows:
        if not (fp or fn or sfp or sfn):
            print(f"  {case_id:26s} clean")
            continue
        print(f"  {case_id}")
        if fp:
            print(f"      skill false positives : {fp}")
        if fn:
            print(f"      skill missed          : {fn}")
        if sfp:
            print(f"      section hallucinated  : {sfp}")
        if sfn:
            print(f"      section missed        : {sfn}")

    print()
    print("=" * 78)
    print(f"{title} - TOTALS")
    print("=" * 78)
    p, r, f = prf(s_tp, s_fp, s_fn)
    print(f"  Skill detection    P={p:6.1%}  R={r:6.1%}  F1={f:6.1%}   "
          f"(tp={s_tp} fp={s_fp} fn={s_fn})")
    p, r, f = prf(sec_tp, sec_fp, sec_fn)
    print(f"  Section detection  P={p:6.1%}  R={r:6.1%}  F1={f:6.1%}   "
          f"(tp={sec_tp} fp={sec_fp} fn={sec_fn})")

    # Catalog coverage: real skills the catalog cannot express at all.
    uncoverable = sorted({name for c in cases for name in c["skills"]} - set(catalog))
    if uncoverable:
        print(f"\n  Ground-truth skills absent from catalog: {uncoverable}")

    return prf(s_tp, s_fp, s_fn), prf(sec_tp, sec_fp, sec_fn)


def main() -> int:
    evaluate(CASES, "TUNED CORPUS")
    print()
    skill, section = evaluate(HOLDOUT_CASES, "HELD-OUT CORPUS (never tuned against)")

    print()
    print("=" * 78)
    print("VERDICT - held-out is the honest number")
    print("=" * 78)
    for label, scores in (("Skill", skill), ("Section", section)):
        f1 = scores[2]
        print(f"  {label + ' F1':14s} {f1:6.1%}   target 95%   "
              f"{'PASS' if f1 >= 0.95 else 'FAIL'}")

    return 0 if (skill[2] >= 0.95 and section[2] >= 0.95) else 1


if __name__ == "__main__":
    raise SystemExit(main())
