# ActTrace skill

A Claude Code skill for **ActTrace** — a developer-facing EU AI Act
compliance API for non-financial SaaS and technology products.

The skill teaches Claude when and how to use ActTrace's two MCP tools:

- `acttrace_classify` — deterministic EU AI Act risk classification of an AI
  feature.
- `acttrace_generate_transparency_notice` — generates an Article 50
  transparency notice.

Output is informational and is **not legal advice or certified compliance**.

## Install

1. **Get an ActTrace API key.** Keys are self-serve and free:

   ```sh
   curl -X POST https://<your-acttrace-host>/api/keys/generate
   ```

   The response contains an `api_key` shaped `act_...` — it is shown only
   once, so save it.

2. **Connect the ActTrace MCP server.** Add it to your MCP client config,
   passing the API key in the `X-API-Key` header. SSE endpoint:

   ```
   http://<your-acttrace-host>:8002/sse
   ```

   Example MCP client entry:

   ```json
   {
     "mcpServers": {
       "acttrace": {
         "url": "http://<your-acttrace-host>:8002/sse",
         "headers": { "X-API-Key": "act_your_key_here" }
       }
     }
   }
   ```

   For local use, run the server over stdio instead:

   ```sh
   python -m backend.mcp_server          # stdio
   python -m backend.mcp_server --sse    # SSE on 0.0.0.0:8002
   ```

3. **Install the skill** by placing the `acttrace/` directory (this folder,
   containing `SKILL.md`) in your Claude Code skills directory.

Once installed, Claude will use the skill automatically when you ask whether
an AI feature is EU AI Act compliant, request a risk classification, or need
a transparency / Article 50 notice.
