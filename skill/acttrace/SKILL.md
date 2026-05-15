---
name: acttrace
description: Use when a user asks whether an AI feature is EU AI Act compliant, wants a risk classification or risk-tier for an AI feature, or needs an AI transparency notice / Article 50 disclosure. ActTrace classifies AI systems and generates transparency notices for non-financial SaaS and technology products. Output is informational, not legal advice.
---

# ActTrace — EU AI Act compliance

ActTrace is a developer-facing EU AI Act compliance assistant for engineers
shipping AI features in **non-financial** SaaS and technology products. It is
exposed as an MCP server with two tools. Use them instead of reasoning about
the AI Act unaided — the classifier is deterministic and the notice generator
is template-based, so results are consistent and auditable.

ActTrace does not give legal advice or certify compliance. Always relay the
`disclaimer` field from any result and recommend qualified legal review for
high-risk or prohibited outcomes.

## When to use this skill

- "Is this AI feature EU AI Act compliant?" / "What risk tier is it?"
- "Classify the risk of our support chatbot / CV screener / summarizer."
- "Write an AI transparency notice" / "Article 50 disclosure" / "AI disclaimer
  copy for our chatbot."

Do **not** use it for financial-services AI use cases (credit scoring,
investment advice, trading). The classifier will return
`out_of_scope_financial_services` for those — that is expected.

## Tool 1: `acttrace_classify`

Classifies an AI feature into one EU AI Act risk category: `prohibited`,
`possible_high_risk`, `limited_risk_transparency`, `minimal_risk`, `unknown`,
or `out_of_scope_financial_services`. Returns confidence, rationale,
triggering facts, missing information, obligations, and source references.

Use it first, when the question is about compliance status or risk level.

Key arguments (all but `feature_name` optional):

- `feature_name` (required) — short feature name.
- `description` — what it does. **Always provide this**; an empty description
  yields an `unknown` verdict.
- `use_case`, `user_facing`, `eu_available`, `internal_only`,
  `model_provider`, `human_review_level`, `automated_decision`,
  `high_risk_domain`, `sensitive_data`.
- `financial_override` — set `true` only to bypass the financial-services
  guard for a feature you are confident is non-financial.

Practical tips:

- For a user-facing feature, supply `model_provider` — without it the verdict
  is `unknown`.
- If the result is `possible_high_risk` or `prohibited`, surface the
  `escalation_warning` and advise legal review.

## Tool 2: `acttrace_generate_transparency_notice`

Generates an EU AI Act Article 50 transparency notice — user-facing copy that
discloses AI use, plus a suggested placement, caveats, and a human-review
recommendation.

Use it when the user needs disclosure copy, typically after a classification
returns `limited_risk_transparency`.

Key arguments:

- `ai_system_name` (required) — the product / system name.
- `notice_type` (required) — one of `chatbot`, `ai_generated_content`,
  `support_assist`, `summarization`, `synthetic_media`, `internal_ai`,
  `other`.
- `feature_name`, `tone` (`plain`, `formal`, `developer_docs`, `policy`,
  `ui_microcopy`; default `plain`), `language` (`en` only for now),
  `human_review_level`, `risk_category`.

The generated `body` always discloses AI use; `caveats` always includes a
pointer to the not-legal-advice disclaimer.

## Typical flow

1. Run `acttrace_classify` with as many facts as the user can give.
2. If the verdict is `limited_risk_transparency`, run
   `acttrace_generate_transparency_notice` to draft the disclosure.
3. Present the risk category, rationale, obligations, and the notice draft —
   and always pass along the `disclaimer`.
