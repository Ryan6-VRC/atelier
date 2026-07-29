#!/bin/sh
# PostToolUse hook on Write|Edit. One job: when the agent authors markdown in
# this workspace, inject one line routing to the write-for-agents skill and the
# constitution (tool-design.md owns where facts live; this only points at it).
# Scope is everything the agent writes — tracked or not, ignored or not. A file
# does not stop being worth writing well because git declines to store it, and
# this nudge is advice, not enforcement: the governed fence still decides what
# the commit-time form gate checks, and the two scopes are allowed to differ.
# Dedup is per file, per agent, and time-boxed. Repetition manufactures banner
# blindness, but a permanent marker is worse: compaction drops the injected line
# without ending the session, so the nudge has to be able to come back.
# Silent exits: not markdown, not in this workspace, and any payload this cannot
# read a file_path out of — malformed JSON, or jq missing. An unresolvable
# workspace root reports instead, since that one disables the hook wholesale
# while everything still looks healthy. It never blocks; every path out exits 0.
#
# Proportion, before hardening anything here: every failure mode this script has
# costs exactly one missing or one duplicated banner, and nothing downstream
# depends on it. The known gaps are therefore documented, not defended —
# markdown written through Bash never reaches a Write|Edit hook, a jq-less
# environment turns it off quietly, a junction-reached or differently-cased path
# misses the scope compare. Each is real and each is deliberately unfixed. Weigh
# anything new against a worst case of one absent line of advice.

input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path? // empty' 2>/dev/null)
[ -n "$path" ] || exit 0
case "$path" in *.[Mm][Dd]) ;; *) exit 0 ;; esac

# Marker identity, parsed only past the early exits: every Write/Edit in the
# session reaches this file, and a jq spawn per field is not free on Windows.
# agent_id is present only when the hook fires inside a subagent, and $sid is
# shared with the parent — so keying on $sid alone lets a parent's fire mask the
# workers that do most of the writing. Scope the marker dir to both.
sid=$(printf '%s' "$input" | jq -r '.session_id? // "nosession"' 2>/dev/null)
aid=$(printf '%s' "$input" | jq -r '.agent_id? // empty' 2>/dev/null)

# How long one nudge holds before the same file may be nudged again. A knob.
marker_ttl_min=45

# emit <dedup-key> <message> — one line of additionalContext, then exit 0.
# Every failure inside here falls through to emitting: a repeated banner is a
# nuisance, a dropped one is a hole in the routing.
emit() {
  tmp=$(cygpath -u "${TEMP:-/tmp}" 2>/dev/null) || tmp="${TMPDIR:-/tmp}"
  marker_dir="$tmp/claude-prose-hook/$sid${aid:+-$aid}"
  key=$(printf '%s' "$1" | cksum | cut -d' ' -f1)
  # An empty key would make the test below address the marker directory, which
  # exists — suppressing every nudge for the rest of the session.
  [ -n "$key" ] || key=nokey
  if mkdir -p "$marker_dir" 2>/dev/null; then
    # Ask the question whose true answer means suppress — a marker file
    # demonstrably younger than the window — so that find failing, or the
    # directory vanishing under a competing prune, nudges instead of silencing.
    if [ -n "$(find "$marker_dir" -name "$key" -type f -mmin "-$marker_ttl_min" 2>/dev/null)" ]; then
      exit 0
    fi
    # touch, not `: >`: `:` is a POSIX special built-in, so a redirection error
    # on it terminates the shell — exit non-zero, no output, both contracts
    # broken at once.
    touch "$marker_dir/$key" 2>/dev/null || :
    # Nobody else ever cleans this tree. Age-gate both arms: the directory arm
    # walks every session's dir, not just ours, and a live session's dir is
    # legitimately empty between its mkdir and its first marker.
    find "$tmp/claude-prose-hook" -mindepth 1 \
      \( -type f -mmin +1440 -o \( -type d -empty -mmin +1440 \) \) -delete 2>/dev/null
  fi
  jq -n --arg msg "$2" \
    '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $msg}}'
  exit 0
}

# Normalize to the shell's own path style; tool_input arrives as C:\... here.
path=$(cygpath -u "$path" 2>/dev/null) || path=$(printf '%s' "$path" | tr '\\' '/')

# Workspace root from $0 — the harness invokes this script by absolute path, so
# $0 carries the location, and the cd + `pwd -P` round trip is what normalizes
# it. `pwd -P` and not a logical `pwd`: the latter inherits the caller's path
# flavor and yields "C:\Users/..." against a "/c/Users/..." payload, which
# misses every compare in silence. The self-check below buys one thing only —
# catching a root that would not resolve at all. It does not validate flavor.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." 2>/dev/null && pwd -P)
[ -e "$root/tools/prose-hook.sh" ] || emit broken-root \
  "prose-hook: workspace root unresolved (got '$root') — the write-for-agents nudge is OFF for this session and every .md edit goes unrouted until tools/prose-hook.sh resolves its root."
case "$path" in "$root"/*) ;; *) exit 0 ;; esac

emit "$path" \
  "Markdown authored — apply the write-for-agents skill (declare the reader, then carve); where facts live is docs/tool-design.md (routing ladder, echoes, lifts)."
