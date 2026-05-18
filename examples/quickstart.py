"""ActTrace quickstart — classify an AI system, no server required.

Run:
    pip install -e ..          # install acttrace from the repo root
    python quickstart.py

The classification engine is pure Python: no database, no API key, no network.
It applies a deterministic 7-step decision tree (BLUEPRINT.md) against the
facts you supply and returns a risk category, confidence level, obligations,
and rationale — all in one dict.
"""

import json
from acttrace.services.acttrace_classification_service import classify

EXAMPLES = [
    {
        "label": "Customer-facing support chatbot",
        "facts": {
            "feature_name": "Support Copilot",
            "description": "An AI chatbot that drafts customer support replies "
                           "shown to the end-user in a live chat widget.",
            "use_case": "support_assist",
            "user_facing": True,
            "model_provider": "OpenAI",
        },
    },
    {
        "label": "Internal document summariser (no user exposure)",
        "facts": {
            "feature_name": "Engineering Summariser",
            "description": "Summarises internal engineering design docs for staff. "
                           "Output is reviewed by the author before any action.",
            "internal_only": True,
            "user_facing": False,
            "automated_decision": False,
            "sensitive_data": False,
            "high_risk_domain": False,
        },
    },
    {
        "label": "CV-screening / hiring ranker",
        "facts": {
            "feature_name": "TalentSort",
            "description": "Ranks and filters job applicants during hiring and "
                           "recruitment based on CV text.",
        },
    },
]


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print("="*60)


def _print_result(label: str, result: dict) -> None:
    _section(label)
    print(f"  Risk category : {result['risk_category']}")
    print(f"  Confidence    : {result['confidence']}")
    print(f"  Summary       : {result['summary']}")
    if result["triggering_facts"]:
        print(f"  Triggered by  : {', '.join(result['triggering_facts'])}")
    if result["missing_information"]:
        print(f"  Missing info  : {', '.join(result['missing_information'])}")
    print("\n  Obligations:")
    for obligation in result["obligations"]:
        print(f"    • {obligation}")
    print(f"\n  Rule version  : {result['rule_version']}")


def main() -> None:
    print("\nActTrace — EU AI Act risk classifier (offline / no API key)")
    print("Not legal advice. See disclaimer in each response.")

    for example in EXAMPLES:
        result = classify(example["facts"])
        _print_result(example["label"], result)

    print("\n" + "="*60)
    print("  Full JSON output for the first example")
    print("="*60)
    first_result = classify(EXAMPLES[0]["facts"])
    print(json.dumps(first_result, indent=2))


if __name__ == "__main__":
    main()
