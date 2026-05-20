"""Example: CI/CD compliance gate — fail the build if any AI feature is prohibited
or possible high-risk.

Reads a JSON file listing AI features (see examples/features.json), runs each
through the ActTrace classification engine, and exits non-zero if any cross the
risk threshold. Drop this into a CI pipeline to catch risky features before they
reach production.

Setup (from the acttrace repo root):
    pip install -e .

Usage:
    python examples/ci_gate.py examples/features.json
    python examples/ci_gate.py examples/features.json --strict  # warn = fail too

GitHub Actions step:
    - name: EU AI Act compliance gate
      run: |
        pip install -e .
        python examples/ci_gate.py examples/features.json

Exit codes:
    0  all features passed (minimal_risk or limited_risk_transparency)
    1  one or more features are prohibited or possible_high_risk
    2  bad arguments or unreadable manifest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from acttrace.services.acttrace_classification_service import classify

_FAIL_CATEGORIES = {"prohibited", "possible_high_risk"}
_WARN_CATEGORIES = {"unknown", "needs_legal_review", "out_of_scope_financial_services"}


def _load_manifest(path: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ci_gate] Cannot read manifest {path!r}: {exc}", file=sys.stderr)
        sys.exit(2)
    return raw if isinstance(raw, list) else raw.get("features", [])


def run_gate(manifest_path: str, *, strict: bool = False) -> int:
    features = _load_manifest(manifest_path)
    if not features:
        print("[ci_gate] No features found in manifest — nothing to check.")
        return 0

    passed, warned, failed = [], [], []

    for feature in features:
        name = feature.get("name") or feature.get("feature_name") or "unnamed"
        result = classify(feature)
        cat = result["risk_category"]
        entry = {
            "name": name,
            "risk_category": cat,
            "confidence": result["confidence"],
            "summary": result["summary"],
        }
        if cat in _FAIL_CATEGORIES:
            failed.append(entry)
        elif cat in _WARN_CATEGORIES:
            warned.append(entry)
        else:
            passed.append(entry)

    total = len(features)
    print(f"\nActTrace compliance gate — {total} feature(s) checked\n")

    for f in passed:
        print(f"  [OK]   {f['name']}: {f['risk_category']}")
    for w in warned:
        print(f"  [WARN] {w['name']}: {w['risk_category']} — {w['summary']}")
    for f in failed:
        print(f"  [FAIL] {f['name']}: {f['risk_category']} — {f['summary']}")

    gate_failed = bool(failed) or (strict and bool(warned))

    if gate_failed:
        blocking = failed + (warned if strict else [])
        print(
            f"\nGate FAILED: {len(blocking)} feature(s) need resolution before "
            "deployment. See ActTrace docs for obligations and next steps."
        )
        return 1

    if warned:
        print(f"\n{len(warned)} feature(s) flagged for review — check summaries above.")

    print(
        f"\nGate PASSED: all {len(passed)} clear feature(s) within acceptable "
        "risk range."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ActTrace CI gate — validate an AI feature manifest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("manifest", help="Path to features.json manifest file")
    parser.add_argument(
        "--strict", action="store_true",
        help="Also fail on 'unknown' or 'needs_legal_review' categories",
    )
    args = parser.parse_args()
    sys.exit(run_gate(args.manifest, strict=args.strict))


if __name__ == "__main__":
    main()
