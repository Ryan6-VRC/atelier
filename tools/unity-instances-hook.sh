#!/bin/sh
# SessionStart hook: inject the live Unity Editor instance table (MCP-for-Unity
# heartbeats) so every session pins routing before touching Unity.
# No project names live here or in git — everything is read from ~/.unity-mcp at
# session start; instance hashes are path-derived cache keys, never stored.
# One jq run per file: a corrupt or mid-write heartbeat drops that entry only,
# never the whole table.
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
[ -n "$rows" ] || exit 0
jq -n --arg rows "$rows" '{hookSpecificOutput: {hookEventName: "SessionStart",
  additionalContext: ("Unity Editors live now (~/.unity-mcp heartbeats): " + $rows
    + ". UnityMCP routing is silently arbitrary until pinned - call set_active_instance with the full Name@hash before any other Unity tool.")}}'
