# Releasing ActTrace

ActTrace is distributed three ways from this one repository: the GitHub source,
a PyPI package (`acttrace-mcp`), and a Claude Code plugin (skill + MCP server).

## 1. PyPI — the MCP server package

```bash
python -m build
python -m twine upload dist/*
```

`twine` prompts for credentials — use a PyPI API token (username `__token__`,
password the token). The distribution name is `acttrace-mcp`; the import
package is `acttrace`; the console script is `acttrace-mcp`.

## 2. MCP Registry

```bash
mcp-publisher login github     # GitHub device-flow login; verifies the io.github.goww7/* namespace
mcp-publisher publish          # reads server.json
```

Publish to PyPI **first** — the `server.json` registry entry references the
`acttrace-mcp` PyPI package. The `io.github.goww7/acttrace` namespace needs no
domain or DNS record; it is verified by the GitHub login.

## 3. Claude Code plugin

The plugin is this repository (`.claude-plugin/`, `skills/`, `.mcp.json`).
Once it is on GitHub it installs with:

```
/plugin marketplace add goww7/acttrace
/plugin install acttrace@acttrace
```

The plugin's MCP server runs `uvx acttrace-mcp`, so step 1 (PyPI) must be done
for the plugin's MCP tools to work.

## Version bumps

Bump `version` in `pyproject.toml`, `server.json`, and
`.claude-plugin/plugin.json` together.
