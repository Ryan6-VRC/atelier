#!/bin/sh
# SessionStart hook. Two jobs:
#  1. Inject the live Unity Editor instance table (MCP-for-Unity heartbeats) so
#     every session pins routing before touching Unity.
#  2. Fail loud when the UnityMCP transport itself can't start — a checkout
#     missing the gitignored vrc-mcp-proxy sibling or `uv` gets ZERO UnityMCP.
# No project names live here or in git — everything is read from ~/.unity-mcp at
# session start; instance hashes are path-derived cache keys, never stored.
# One jq run per file: a corrupt or mid-write heartbeat drops that entry only,
# never the whole table. Emits at most ONE SessionStart object; nothing when healthy
# and no Editor is live (so a healthy session pays no context cost).

# --- transport preflight -------------------------------------------------------
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
