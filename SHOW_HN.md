# Launch draft — Show HN

Distribution ships with the MVP, not after it. This is a draft, not a
published post. Tighten the numbers and the link before posting.

---

**Title:** Show HN: ActTrace – EU AI Act compliance API for developers

**Body:**

The EU AI Act's transparency obligations (Article 50 — chatbots, AI-generated
content) apply from August 2026. If you ship an AI feature into the EU you
need a documented risk classification and user-facing disclosure copy.

Existing AI-governance tools are enterprise GRC suites sold top-down to
compliance teams. There was nothing an engineer could just call from an API.

ActTrace is that: a deterministic classifier + an Article 50 transparency-notice
generator, behind an HTTP API and an MCP tool you can call straight from Claude
Code / Cursor.

- `POST /diagnostics/free` — risk classification, no signup
- `POST /classify` — documented assessment with rationale + obligations
- `POST /notices` — ready-to-ship Article 50 disclosure copy
- MCP tools so an agent can classify a feature while you build it

Deterministic rules engine, not an LLM guessing — same input, same verdict,
with an audit trail. Scoped to non-financial SaaS. It is not legal advice and
does not certify compliance — it is drafting + documentation support for
engineering teams.

Free diagnostic, no card: <link>

Happy to answer questions on the classification logic and the AI Act timeline.

---

## Companion posts (same week)

- **dev.to / personal blog:** "What the EU AI Act actually requires from a SaaS
  shipping an AI feature" — link the free diagnostic in the conclusion.
- **MCP registry + Claude plugin marketplace:** publish the `skill/acttrace`
  skill and the MCP server listing.
- **r/SaaS, Indie Hackers:** short version of the Show HN post.
