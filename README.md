# ActTrace

<!-- mcp-name: io.github.goww7/acttrace -->

A developer-facing **EU AI Act compliance API** for non-financial SaaS and
technology companies. ActTrace gives an engineering team three things,
self-serve, over an API or via MCP:

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

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn acttrace.app:app --reload --port 8080
```

```bash
# 1. Free diagnostic — no key needed
curl -s localhost:8080/api/acttrace/diagnostics/free -H 'content-type: application/json' -d '{
  "feature_name": "AI reply assistant",
  "description": "Drafts suggested customer support replies for agents.",
  "user_facing": true, "model_provider": "OpenAI", "use_case": "support_assist"
}'

# 2. Mint an API key
KEY=$(curl -s -XPOST localhost:8080/api/keys/generate | python3 -c 'import sys,json;print(json.load(sys.stdin)["api_key"])')

# 3. Classify (15 tokens)
curl -s localhost:8080/api/acttrace/classify -H "X-API-Key: $KEY" -H 'content-type: application/json' -d '{
  "feature_name": "AI reply assistant",
  "description": "Drafts customer support replies shown to agents.",
  "use_case": "support_assist", "user_facing": true, "model_provider": "OpenAI"
}'

# 4. Generate an Article 50 notice (10 tokens)
curl -s localhost:8080/api/acttrace/notices -H "X-API-Key: $KEY" -H 'content-type: application/json' -d '{
  "ai_system_name": "Support Copilot", "notice_type": "chatbot", "tone": "plain"
}'
```

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
tests/
```
