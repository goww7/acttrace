# ActTrace MVP — Build Blueprint (the contract / jig)

ActTrace is a developer-facing **EU AI Act compliance API**: self-serve risk
classification + Article 50 transparency-notice generation, for **non-financial**
SaaS and technology companies. Buyer = the engineer shipping an AI feature.

This file is the contract. Build agents implement against it **exactly** — do not
invent interfaces, table names, enum values, keyword lists, or string constants.

## Scope (trimmed MVP — do not exceed)

IN: 3 HTTP endpoints, deterministic classification engine, Article 50 notice
generator, 2 MCP tools, a Claude skill, tests, deploy artifacts.

OUT (deliberately deferred): organizations CRUD, intake questionnaire, evidence
vault, compliance-packet export, audit-events endpoint, admin UI, change/diff
jobs, RQ workers, Stripe. Do **not** build these.

## Hard product rules

- Non-financial only. Financial-services use cases → `out_of_scope_financial_services`.
- Never claims legal advice or certified compliance. `DISCLAIMER` on every output.
- API-first. No customer UI beyond a later static diagnostic page.

## Single database

One file `acttrace.sqlite3` (env `ACTTRACE_DB_PATH`, default repo root). Both
`ActTraceRepository` and `ApiKeyRepository` open this same file (different tables).
SQLite WAL, inline `CREATE TABLE IF NOT EXISTS` migrations in each repo `__init__`.
Pattern copied from FinanceData2: no base class, per-call `closing(_connect())`,
`threading.Lock` around writes.

## File ownership — STRICT

CONTRACT files (orchestrator-written, agents must NOT modify):
`backend/config.py`, `backend/dependencies.py`, `backend/schemas/acttrace.py`,
`backend/repositories/acttrace_repository.py`,
`backend/services/acttrace_constants.py`, `backend/services/acttrace_service.py`,
`backend/routers/acttrace.py`.

FOUNDATION agent writes ONLY: `backend/middleware/api_key_auth.py`,
`backend/services/api_key_service.py`, `backend/repositories/api_key_repository.py`,
`backend/routers/keys.py`, `backend/app.py`, `requirements.txt`, `pyproject.toml`.

CLASSIFICATION agent writes ONLY:
`backend/services/acttrace_classification_service.py`,
`tests/test_classification.py`, `tests/test_conflict_guard.py`.

NOTICE agent writes ONLY: `backend/services/acttrace_notice_service.py`,
`tests/test_notice_service.py`.

MCP agent writes ONLY: `backend/mcp_server/server.py`,
`backend/mcp_server/__main__.py`, `backend/mcp_server/context.py`,
`backend/mcp_server/tools/acttrace.py`, `skill/acttrace/SKILL.md`,
`skill/acttrace/README.md`.

No agent creates/edits `__init__.py` (they exist) or files outside its list.
`tests/conftest.py` and `tests/test_api.py` are written by the orchestrator.

## Classification engine contract

Module `backend/services/acttrace_classification_service.py` exposes:

```python
def classify(facts: dict) -> dict
```

`facts` keys (all optional; strings unless noted): `company_name`, `industry`,
`feature_name`, `name`, `description`, `use_case`, `model_provider`, `model_name`,
`human_review_level`, `user_facing` (bool), `eu_available` (bool),
`internal_only` (bool), `automated_decision` (bool), `high_risk_domain` (bool),
`sensitive_data` (bool), `financial_override` (bool).

Returns a dict with keys: `risk_category` (str), `confidence` (str),
`summary` (str), `rationale` (str), `triggering_facts` (list[str]),
`missing_information` (list[str]), `obligations` (list[str]),
`source_refs` (list[dict]), `rule_version` (str).

Import keyword lists, obligations, source refs and string constants from
`backend.services.acttrace_constants` — **do not redefine them**.

### Decision precedence — first match wins

Normalize a haystack = lowercase concatenation of `industry`, `feature_name`,
`name`, `description`, `use_case`, `company_name`.

1. **Conflict guard** — if `financial_override` is not True and any
   `CONFLICT_GUARD_KEYWORDS` substring is in the haystack →
   `out_of_scope_financial_services`, confidence `high`.
2. **Prohibited** — any `PROHIBITED_KEYWORDS` in haystack → `prohibited`,
   confidence `high`.
3. **High-risk** — any `HIGH_RISK_KEYWORDS` in haystack, OR `high_risk_domain`
   is True → `possible_high_risk`, confidence `medium`.
4. **Missing info** — if `description` empty → add to `missing_information`;
   if `user_facing` is True and `model_provider` empty → add to
   `missing_information`. If `missing_information` non-empty → `unknown`,
   confidence `low`.
5. **Transparency** — if `user_facing` is True and any `TRANSPARENCY_KEYWORDS`
   in haystack → `limited_risk_transparency`, confidence `medium`.
6. **Minimal** — if `internal_only` True AND `user_facing` not True AND
   `automated_decision` not True AND `high_risk_domain` not True AND
   `sensitive_data` not True → `minimal_risk`, confidence `medium`.
7. Else → `unknown`, confidence `low`.

`obligations` = `OBLIGATIONS[risk_category]`. `source_refs` = `SOURCE_REFS`.
`rule_version` = `RULE_VERSION`. `triggering_facts` = the matched keywords /
flags that produced the verdict. `summary` and `rationale` = short human strings.

### Acceptance fixtures — `classify()` MUST satisfy all 7

| # | facts (abbreviated) | expected risk_category |
|---|---|---|
| 1 | use_case=support_assist, user_facing=true, model_provider=OpenAI, description set, human_review_level=required_before_action | `limited_risk_transparency` |
| 2 | feature_name="internal document summarizer", internal_only=true, user_facing=false, automated_decision=false, description set | `minimal_risk` |
| 3 | feature_name="HR CV screener", description mentions hiring/recruitment | `possible_high_risk` |
| 4 | feature_name="exam scorer", description mentions student assessment | `possible_high_risk` |
| 5 | feature_name="portfolio recommender", description mentions investment advice | `out_of_scope_financial_services` |
| 6 | feature_name="credit scoring assistant", description mentions creditworthiness | `out_of_scope_financial_services` |
| 7 | feature_name="chatbot", user_facing=true, model_provider missing, description set | `unknown` |

`test_classification.py` covers fixtures 1-4,7 + confidence checks.
`test_conflict_guard.py` covers fixtures 5-6 + `financial_override=True` bypass +
several financial keywords.

## Notice generator contract

Module `backend/services/acttrace_notice_service.py` exposes:

```python
def generate_notice(params: dict) -> dict
```

`params`: `ai_system_name`, `feature_name`, `notice_type`, `tone`, `language`,
`output_categories` (list), `human_review_level`, `risk_category` (optional).

Returns dict: `body` (str), `suggested_placement` (str), `caveats` (list[str]),
`human_review_recommended` (bool), `notice_type`, `tone`, `language`.

Template-based. `notice_type` ∈ {chatbot, ai_generated_content, support_assist,
summarization, synthetic_media, internal_ai, other}. `tone` ∈ {plain, formal,
developer_docs, policy, ui_microcopy}. English only for the MVP.

Every `body` must disclose AI use and advise human review of important output.
Reference example (chatbot / plain): "This feature uses artificial intelligence
to help generate responses. AI-generated content may be incomplete or
inaccurate. You should review important information before relying on it."
`caveats` always includes a line pointing to `DISCLAIMER` (not legal advice).
`human_review_recommended` is True unless `human_review_level` is
`required_before_action`.

`test_notice_service.py`: one notice per `notice_type`; body non-empty; body
discloses AI; caveats non-empty; tone variation changes the body.

## Foundation contract (interfaces the orchestrator files depend on)

`backend/repositories/api_key_repository.py` — `ApiKeyRepository(db_path)`,
tables `acttrace_api_keys`, `acttrace_api_usage_log`. Keys hashed with `bcrypt`.
Methods: `create_key(plan="free") -> {"api_key": <plaintext>, "key_prefix",
"plan", "id"}`; `get_by_key(api_key) -> dict | None` (dict has `id`,
`key_prefix`, `plan`, `is_active` bool, `tokens_used`, `tokens_limit`);
`increment_token_usage(api_key, tokens)`; `log_usage(**kw)`.

`backend/services/api_key_service.py` — `ApiKeyService(repo)`. Holds
`TOKEN_COSTS` and `get_token_cost(endpoint, method) -> int`. Token costs:
`/api/acttrace/diagnostics/free`→0, `/api/acttrace/classify`→15,
`/api/acttrace/notices`→10, `/api/keys`→0, `/api/health`→0, default→1.
`check_and_increment(api_key, endpoint, method) -> dict` — raises `ValueError`
with code string for invalid/deactivated, returns usage dict otherwise; free
plan hard-blocked over quota (`QUOTA_EXCEEDED`), paid plans allow overage.

`backend/middleware/api_key_auth.py` — `ApiKeyAuthMiddleware(BaseHTTPMiddleware)`.
Exempt paths: `/api/acttrace/diagnostics/free`, `/api/health`, `/api/keys`,
`/docs`, `/openapi.json`, `/redoc`, `/`. Reads `X-API-Key`; on failure returns
JSON `{"code","message","detail"}` with 401/403/429. On success sets
`request.state.api_key` (the key dict) and `request.state.request_id` (uuid4).
Response headers: `X-Request-ID`, `X-Plan`, `X-Tokens-Charged`,
`X-Tokens-Remaining`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`.

`backend/routers/keys.py` — `POST /api/keys/generate` (exempt) issuing a free
key via `ApiKeyRepository.create_key`. `GET /api/health` lives here too.

`backend/app.py` — `create_app()` FastAPI factory: registers
`ApiKeyAuthMiddleware`, includes `backend.routers.acttrace.router`,
`backend.routers.keys.router`. Title "ActTrace API".

`requirements.txt`: fastapi, uvicorn, pydantic>=2, bcrypt, httpx, pytest, mcp.

## Endpoints

- `POST /api/acttrace/diagnostics/free` — no auth, 0 tokens. Public funnel entry.
- `POST /api/acttrace/classify` — auth, 15 tokens.
- `POST /api/acttrace/notices` — auth, 10 tokens.
- `POST /api/keys/generate` — no auth. `GET /api/health` — no auth.

## MCP contract

`backend/mcp_server/` — FastMCP + SSE, mirroring FinanceData2's pattern. Tools:
`acttrace.classify` and `acttrace.generate_transparency_notice`. Each
authenticates via `X-API-Key` (reuse `ApiKeyRepository`), calls
`ActTraceService`, returns structured JSON, creates audit events (the service
already does this). Skill at `skill/acttrace/SKILL.md` documents the two tools.
