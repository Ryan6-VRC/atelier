#!/bin/sh
# PostToolUse hook on Write|Edit. One job: when governed prose is touched, inject
# one line routing to the write-for-agents skill and the constitution
# (tool-design.md owns the fence policy; this script only implements it).
# Governed = an .md inside this workspace whose owning repo does not ignore it —
# check-ignore rather than ls-files so a file still being authored counts.
# Session-scoped dedup: one fire per file per session; repetition manufactures
# banner blindness. Every non-governed case exits 0 silently — a normal edit
# pays no context cost. Fail quiet, not loud: a broken hook must never block edits.

input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path? // empty' 2>/dev/null)
sid=$(printf '%s' "$input" | jq -r '.session_id? // "nosession"' 2>/dev/null)
[ -n "$path" ] || exit 0
case "$path" in *.md|*.MD) ;; *) exit 0 ;; esac

# Normalize to the shell's own path style so prefix-compare against pwd works
# (tool_input arrives as C:\... on Windows; pwd here is /c/...).
path=$(cygpath -u "$path" 2>/dev/null) || path=$(printf '%s' "$path" | tr '\\' '/')

# Workspace root from $0, not $CLAUDE_PROJECT_DIR — same reasoning as
# unity-instances-hook.sh: $0 is always a concrete path in this child shell.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." 2>/dev/null && pwd) || exit 0
case "$path" in "$root"/*) ;; *) exit 0 ;; esac
rel=${path#"$root"/}

# Skip non-governed paths. The first three mirror governed_fence.exclude in
# docs/tool-design.md (canon); this shell echo can't parse the YAML, so
# check_prose.py's hook-echo pass fails loud if they drift. references/ is the
# load-bearing one — its clones carry their own .git and slip the check-ignore
# below; the gitignored entries are belt-and-suspenders. AvatarProject/Sandbox
# are the untracked Unity venues (not fence entries — venues, not docs).
case "$rel" in
  test-output/*|references/*|docs/local/*|AvatarProject/*|Sandbox/*) exit 0 ;;
esac

command -v git >/dev/null 2>&1 || exit 0

# Owning repo = nearest ancestor with .git (dir or worktree file), stopping at root.
d=$(dirname -- "$path")
repo=""
while :; do
  [ -e "$d/.git" ] && { repo="$d"; break; }
  [ "$d" = "$root" ] && break
  parent=$(dirname -- "$d")
  [ "$parent" = "$d" ] && break
  d="$parent"
done
[ -n "$repo" ] || exit 0
git -C "$repo" check-ignore -q -- "$path" 2>/dev/null && exit 0

# One fire per file per session.
tmp=$(cygpath -u "${TEMP:-/tmp}" 2>/dev/null) || tmp="${TMPDIR:-/tmp}"
marker_dir="$tmp/claude-prose-hook/$sid"
key=$(printf '%s' "$path" | cksum | cut -d' ' -f1)
mkdir -p "$marker_dir" 2>/dev/null || exit 0
[ -e "$marker_dir/$key" ] && exit 0
: > "$marker_dir/$key"

jq -n '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: "Governed prose touched — apply the write-for-agents skill (declare the reader, then carve); where facts live is docs/tool-design.md (routing ladder, echoes, lifts)."}}'
