#!/bin/sh
# SessionStart hook. Two jobs:
#  1. Inject the live Unity Editor instance table (MCP-for-Unity heartbeats) so
#     every session pins routing before touching Unity.
#  2. Fail loud when the session's own environment is broken — a checkout missing
#     the gitignored vrc-mcp-proxy sibling or `uv` gets ZERO UnityMCP, and a host
#     missing pwsh or jq loses the other hooks or this table.
# No project names live here or in git — everything is read from ~/.unity-mcp at
# session start; instance hashes are path-derived cache keys, never stored.
# One jq run per file: a corrupt or mid-write heartbeat drops that entry only,
# never the whole table. Emits at most ONE SessionStart object; nothing when healthy
# and no Editor is live (so a healthy session pays no context cost).

# --- environment preflight -----------------------------------------------------
# Three checks share one message, because this hook is the only thing running at
# session start that does not depend on what it checks.
#
# 1. UnityMCP transport.
# Claude reaches UnityMCP through the gitignored vrc-mcp-proxy sibling via `uv run`.
# Diagnose a missing half here, proactively, rather than let the agent chase
# unity.md's "restart Claude". Root from $0 (always a concrete path) — NOT
# $CLAUDE_PROJECT_DIR, which may not reach this child shell; if root won't resolve
# we fall through and fire (fail closed). Skip only in a worktree (its .git is a
# FILE) — a worktree legitimately lacks the proxy (headless TestEditor, not live
# UnityMCP). A main checkout (.git dir) or a no-.git tree (a ZIP of the public repo,
# the likeliest broken clone) both fire.
preflight=""
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." 2>/dev/null && pwd)
if [ ! -f "$root/.git" ]; then
  miss=""
  [ -f "$root/vrc-mcp-proxy/pyproject.toml" ] || miss="vrc-mcp-proxy sibling"
  command -v uv >/dev/null 2>&1 || miss="${miss:+$miss and }uv"
  [ -z "$miss" ] || preflight="UnityMCP transport broken: $miss missing — this session gets ZERO UnityMCP. Clone the vrc-mcp-proxy sibling and/or install uv (see bootstrap.md steps 1-2)."
fi

# 2. pwsh. settings.json runs the prose hook on every Write|Edit and the serialized-read
# hook on every Read|Grep|Glob through `pwsh`. Windows ships powershell.exe 5.1, NOT pwsh,
# so on a host without it both hooks silently do nothing for a whole session and the Python
# suite's pwsh-gated cases skip instead of failing. Nothing else announces that; this shell
# is sh, so it can report an absence the pwsh hooks by definition cannot report themselves.
if ! command -v pwsh >/dev/null 2>&1; then
  preflight="${preflight:+$preflight }pwsh not installed — the prose and serialized-read hooks (settings.json) do nothing this session (prerequisite: docs/bootstrap.md §2)."
fi

# 3. jq. Both halves below are jq, so without it this hook emits NOTHING and exits 127:
# no instance table, and — worse — the fail-closed transport check above is computed and
# then thrown away. Report what was already learned instead of dying on it. Everything
# interpolated here is a literal assembled above (no quotes, no backslashes), so it is safe
# in a JSON string without the escaping jq would otherwise be doing. The fallback instruction
# echoes unity.md's rule that the ~/.unity-mcp heartbeat is truth; that doc owns it.
if ! command -v jq >/dev/null 2>&1; then
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "${preflight:+$preflight }jq not installed — no live Unity Editor table this session; read ~/.unity-mcp/ heartbeats yourself before any Unity call (prerequisite: docs/bootstrap.md §2)."
  exit 0
fi

# --- live instance table -------------------------------------------------------
rows=""
for f in "$HOME"/.unity-mcp/unity-mcp-status-*.json; do
  [ -e "$f" ] || break
  row=$(jq -r '
    select((.project_name? // "") != "" and (.last_heartbeat? // "") != "" and (.project_path? // "") != "")
    | select((.last_heartbeat | sub("[.][0-9]+"; "") | fromdateiso8601) > (now - 300))
    | "\(.project_name)@{HASH} (port \(.unity_port), \(.project_path | sub("/Assets$"; "")))"
  ' "$f" 2>/dev/null) || continue
  [ -n "$row" ] || continue
  hash=${f##*status-}; hash=${hash%.json}
  rows="$rows${rows:+; }$(printf '%s' "$row" | sed "s/{HASH}/$hash/")"
done

# --- emit one object (preflight, table, or both) -------------------------------
NL='
'
context="$preflight"
if [ -n "$rows" ]; then
  table="Unity Editors live now (~/.unity-mcp heartbeats): $rows. UnityMCP routing is silently arbitrary until pinned - call set_active_instance with the full Name@hash before any other Unity tool."
  if [ -n "$context" ]; then context="$context$NL$NL$table"; else context="$table"; fi
fi
[ -n "$context" ] || exit 0
jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
