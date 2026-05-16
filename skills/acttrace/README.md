# ActTrace skill

A Claude Code skill + MCP server for **EU AI Act compliance**: classify an AI
feature's risk category and generate Article 50 transparency notices. For
non-financial SaaS and technology products.

## Install

```
/plugin marketplace add goww7/acttrace
/plugin install acttrace@acttrace
```

The plugin bundles the `acttrace` skill and wires the ActTrace MCP server. The
server runs locally via `uvx` (PyPI package `acttrace-mcp`) — no hosted
service, no API key, fully offline. Classification is a deterministic rules
engine.

Then ask Claude things like *"is my chatbot EU AI Act compliant?"* or
*"write an Article 50 notice for our support assistant."*

## Tools the skill uses

- `acttrace_classify` — deterministic EU AI Act risk classification.
- `acttrace_generate_transparency_notice` — Article 50 transparency notice.

## Not legal advice

ActTrace provides documentation drafts and operational workflow support. It
does not provide legal advice and does not certify compliance.
