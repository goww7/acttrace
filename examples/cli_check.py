"""Example: classify a single AI feature from the command line.

Useful in developer workflows — run once before opening a PR, or wire into a
pre-commit hook to catch prohibited/high-risk features early.

Setup (from the acttrace repo root):
    pip install -e .

Usage:
    python examples/cli_check.py \\
        --feature-name "Content moderator" \\
        --description "Flags potentially harmful user content for agent review." \\
        --user-facing false \\
        --internal-only true \\
        --model-provider "Anthropic"

    python examples/cli_check.py \\
        --feature-name "HR CV screener" \\
        --description "Screens job applicants and scores CVs for hiring decisions." \\
        --user-facing false \\
        --high-risk-domain true

    python examples/cli_check.py --help

Exit codes:
    0  minimal_risk or limited_risk_transparency (proceed; add required notices)
    1  prohibited, possible_high_risk, unknown, or out-of-scope (block / escalate)
"""
from __future__ import annotations

import argparse
import json
import sys

from acttrace.services.acttrace_classification_service import classify

_PASS_CATEGORIES = {"minimal_risk", "limited_risk_transparency"}


def _bool_arg(value: str) -> bool:
    if value.lower() in ("1", "true", "yes"):
        return True
    if value.lower() in ("0", "false", "no"):
        return False
    raise argparse.ArgumentTypeError(f"Expected true/false, got: {value!r}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ActTrace — EU AI Act CLI classifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--feature-name", required=True, help="Short name of the AI feature")
    p.add_argument("--description", required=True, help="What the feature does")
    p.add_argument(
        "--user-facing", metavar="BOOL", type=_bool_arg, default=None,
        help="Is the feature visible to end users? (true/false)",
    )
    p.add_argument(
        "--internal-only", metavar="BOOL", type=_bool_arg, default=None,
        help="Used only by internal staff? (true/false)",
    )
    p.add_argument("--model-provider", default=None, help="LLM/model vendor name")
    p.add_argument("--industry", default=None, help="Your company's industry")
    p.add_argument("--use-case", default=None, help="Use-case type (e.g. chatbot)")
    p.add_argument(
        "--high-risk-domain", metavar="BOOL", type=_bool_arg, default=None,
        help="Does the feature operate in an Annex III domain? (true/false)",
    )
    p.add_argument(
        "--automated-decision", metavar="BOOL", type=_bool_arg, default=None,
        help="Does it make automated decisions affecting people? (true/false)",
    )
    p.add_argument(
        "--json", dest="as_json", action="store_true",
        help="Print the full result as JSON",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    facts: dict = {
        "feature_name": args.feature_name,
        "description": args.description,
    }
    for key, value in [
        ("user_facing", args.user_facing),
        ("internal_only", args.internal_only),
        ("model_provider", args.model_provider),
        ("industry", args.industry),
        ("use_case", args.use_case),
        ("high_risk_domain", args.high_risk_domain),
        ("automated_decision", args.automated_decision),
    ]:
        if value is not None:
            facts[key] = value

    result = classify(facts)

    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        category = result["risk_category"]
        status = "[PASS]" if category in _PASS_CATEGORIES else "[FAIL]"
        print(f"{status}  Risk category : {category}")
        print(f"       Confidence   : {result['confidence']}")
        print(f"       Summary      : {result['summary']}")
        if result.get("obligations"):
            print("       Obligations  :")
            for ob in result["obligations"]:
                print(f"         - {ob}")
        if result.get("triggering_facts"):
            print(f"       Triggered by : {result['triggering_facts']}")

    passed = result["risk_category"] in _PASS_CATEGORIES
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
