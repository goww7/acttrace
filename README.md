# ActTrace

<!-- mcp-name: io.github.goww7/acttrace -->

A developer-facing **EU AI Act compliance API** for non-financial SaaS and
technology companies. Give ActTrace a description of an AI feature and it
returns a deterministic risk classification, the specific Article obligations
that apply, and a ready-to-ship Article 50 transparency notice — all in one
API call, no LLM involved.

ActTrace gives an engineering team three things, self-serve, over an API or
via MCP:

1. A deterministic **risk classification** of an AI feature under the EU AI Act.
2. A ready-to-ship **Article 50 transparency notice**.
3. A **free diagnostic** as the public entry point.

> **Not legal advice.** ActTrace provides operational compliance workflow
> support and documentation drafts. It does not provide legal advice, does not
> certify compliance, and does not replace review by qualified counsel. Every
> response carries this disclaimer.

ActTrace is scoped for **non-financial** companies. Financial-services use
cases (banking, trading, portfolio/investment advice, credit scoring, …) are
deliberately classified `out_of_scope_financial_services`.

## How it works

The engine applies a **7-step deterministic decision tree** to the facts you
supply — no LLM, no network call, fully offline-capable:

```
1. Financial-services conflict guard  → out_of_scope_financial_services
2. Prohibited practices (Article 5)   → prohibited
3. Annex III high-risk keywords/flag  → possible_high_risk
4. Missing required facts             → unknown
5. User-facing + transparency words   → limited_risk_transparency
6. Internal-only, no automation       → minimal_risk
7. Fallback                           → unknown
```

First rule that matches wins. Every result carries the triggered keywords,
the obligations that apply, source references, and a `rule_version` string
for audit trails.

## Quickstart — Python (no server)

The classification engine is pure Python. Install the package and call it
directly — no API key, no database, no running server.

```bash
pip install -e .           # from the repo root
python examples/quickstart.py
```

```python
from acttrace.services.acttrace_classification_service import classify

result = classify({
    "feature_name": "Support Copilot",
    "description": "An AI chatbot that drafts customer support replies "
                   "shown to the end-user in a live chat widget.",
    "use_case": "support_assist",
    "user_facing": True,
    "model_provider": "OpenAI",
})

print(result["risk_category"])   # limited_risk_transparency
print(result["obligations"])     # Article 50 disclosure requirements
print(result["rule_version"])    # acttrace-rules-1.0.0
```

See `examples/quickstart.py` for three annotated examples covering
`limited_risk_transparency`, `minimal_risk`, and `possible_high_risk`.

## Quickstart — HTTP API

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn acttrace.app:app --reload --port 8080
```

```bash
# 1. Free diagnostic — no key needed
curl -s localhost:8080/api/acttrace/diagnostics/free \
  -H 'content-type: application/json' -d '{
  "feature_name": "AI reply assistant",
  "description": "Drafts suggested customer support replies for agents.",
  "user_facing": true, "model_provider": "OpenAI", "use_case": "support_assist"
}'

# 2. Mint an API key
KEY=$(curl -s -XPOST localhost:8080/api/keys/generate \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["api_key"])')

# 3. Classify (15 tokens)
curl -s localhost:8080/api/acttrace/classify \
  -H "X-API-Key: $KEY" -H 'content-type: application/json' -d '{
  "feature_name": "AI reply assistant",
  "description": "Drafts customer support replies shown to agents.",
  "use_case": "support_assist", "user_facing": true, "model_provider": "OpenAI"
}'

# 4. Generate an Article 50 notice (10 tokens)
curl -s localhost:8080/api/acttrace/notices \
  -H "X-API-Key: $KEY" -H 'content-type: application/json' -d '{
  "ai_system_name": "Support Copilot", "notice_type": "chatbot", "tone": "plain"
}'
```

## Install — Claude Code plugin / MCP server

ActTrace ships as a Claude Code plugin: an `acttrace` skill plus a local MCP
server. The MCP server runs via `uvx` — a deterministic rules engine, offline,
no API key.

```
/plugin marketplace add goww7/acttrace
/plugin install acttrace@acttrace
```

Then ask Claude *"Is my chatbot EU AI Act compliant?"* or *"Write an Article 50
notice for our support assistant."* The MCP server also runs standalone with
any MCP client: `uvx acttrace-mcp`.

## Endpoints

| Method & path | Auth | Tokens | Purpose |
|---|---|--:|---|
| `POST /api/acttrace/diagnostics/free` | none | 0 | Public risk diagnostic |
| `POST /api/acttrace/classify` | key | 15 | Documented risk classification |
| `POST /api/acttrace/notices` | key | 10 | Article 50 transparency notice |
| `POST /api/keys/generate` | none | 0 | Issue a free-plan key |
| `GET  /api/health` | none | 0 | Liveness |

Auth is `X-API-Key`. Responses carry `X-Request-ID`, `X-Plan`,
`X-Tokens-Charged`, `X-Tokens-Remaining`, `X-RateLimit-*`. Errors are
structured `{"code","message","detail"}` (401/403/429).

### `classify` input fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `feature_name` | string | recommended | Human-readable name |
| `description` | string | **yes** | What the feature does — used for keyword matching |
| `use_case` | string | recommended | e.g. `support_assist`, `summarization`, `chatbot` |
| `user_facing` | bool | recommended | `true` if end-users interact with the AI output |
| `model_provider` | string | if `user_facing` | e.g. `OpenAI`, `Anthropic` |
| `internal_only` | bool | optional | `true` → minimal-risk path |
| `automated_decision` | bool | optional | `true` if the AI makes decisions without human review |
| `high_risk_domain` | bool | optional | Override: force high-risk path |
| `sensitive_data` | bool | optional | Processes personal or sensitive data |
| `financial_override` | bool | optional | Bypass the financial-services conflict guard |

## MCP

`python -m acttrace.mcp_server --sse --port 8002` exposes two tools —
`acttrace_classify` and `acttrace_generate_transparency_notice` — authenticated
with the same `X-API-Key`. A Claude Code skill is in `skill/acttrace/`.

## Tests

```bash
.venv/bin/python -m pytest -q
```

54 tests: classification engine (7 acceptance fixtures), conflict guard,
notice generator, and HTTP API contract.

## Deploy

`docker-compose.yml` builds a standalone two-container stack (API + MCP) on
ports 8080 / 8002 with its own volume — isolated from FinanceData2. To go live,
append `caddy-acttrace.snippet` to the shared Caddyfile (replace the
placeholder domain). See `BLUEPRINT.md` for the full build contract.

## Layout

```
acttrace/
  app.py config.py dependencies.py
  middleware/   api_key_auth.py
  routers/      acttrace.py  keys.py
  services/     acttrace_service.py  acttrace_classification_service.py
                acttrace_notice_service.py  acttrace_constants.py
                api_key_service.py
  repositories/ acttrace_repository.py  api_key_repository.py
  schemas/      acttrace.py
  mcp_server/   server.py  __main__.py  context.py  tools/acttrace.py
skill/acttrace/ SKILL.md  README.md
examples/       quickstart.py
tests/
```
