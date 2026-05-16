---
name: acttrace
description: Use when the user asks whether an AI feature is EU AI Act compliant, needs an AI-system risk classification, or needs an Article 50 transparency notice / disclosure copy for a user-facing AI feature. For non-financial SaaS and technology products. Not for financial-services AI (banking, trading, investment, credit) — those are out of scope.
---

# acttrace

EU AI Act compliance for non-financial SaaS. Two jobs: classify an AI feature's
risk category, and draft an Article 50 transparency notice. Backed by the local
ActTrace MCP server — a deterministic rules engine, offline, no API key.

## When fired

"Is my chatbot EU AI Act compliant?" / "Classify this AI feature" / "What risk
category is our CV-screening tool?" / "Write an Article 50 disclosure for our
support assistant" / "Do we need an AI transparency notice?"

## Tools

- `acttrace_classify` — deterministic risk classification. Returns one of
  `prohibited`, `possible_high_risk`, `limited_risk_transparency`,
  `minimal_risk`, `unknown`, `out_of_scope_financial_services`, plus
  confidence, rationale, the obligations list, and source references.
- `acttrace_generate_transparency_notice` — an Article 50 notice: body text,
  suggested placement, caveats, by `notice_type` and `tone`.

## Process

1. Gather what the user actually knows about the AI feature: what it does,
   whether it is user-facing, the model provider, whether a human reviews the
   output before it acts, and the domain (HR, education, support, etc.).
2. Call `acttrace_classify` with those facts. Do **not** invent missing facts —
   omit them; the engine reports what is missing and returns `unknown` if it
   cannot classify.
3. Present the risk category, the rationale, and the obligations list verbatim.
4. If the category is `possible_high_risk`, `prohibited`, `needs_legal_review`
   or `out_of_scope_financial_services`, surface the `escalation_warning`
   prominently.
5. If the feature is user-facing and `limited_risk_transparency`, offer to
   generate a notice with `acttrace_generate_transparency_notice`.

## Hard rules

- This is **not legal advice** and does not certify compliance. Always show the
  disclaimer the tools return.
- ActTrace covers **non-financial SaaS only**. If the use case is financial
  (banking, trading, portfolio/investment, credit scoring), the classifier
  returns `out_of_scope_financial_services` — relay that; do not improvise a
  financial-services compliance opinion.
- Do not override the classifier's verdict. If it returns `unknown`, ask the
  user for the missing facts rather than guessing.
- The EU AI Act's Article 50 transparency obligations apply from August 2026.
