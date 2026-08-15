# tools/sync_tool_inventory.py
"""Verify the documented tool/skill rosters against code declaration sites, and
mirror TOOLS.md into README.md.

Three surfaces (the avatar-authoring system); vrc-bridge is a separate runtime
system and is out of scope:
  vrc-unity-tools   -> class names carrying the [AgentTool] identity attribute
  vrc-blender-tools -> operator short-names (bl_idname) UNION cli/ script stems
  vrc-skills        -> skill frontmatter `name:`

Tool rows live in TOOLS.md; the skills roster lives in README.md's `## Skills`
section (human-facing — agents get skill descriptions injected per-session).

--check       : verify keys == code; exit non-zero on drift; write nothing.
(default) sync: run the check; only if it passes, inject TOOLS.md into README.md
                between marker comments (bootstrapping the markers on first run).
"""
import argparse
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SURFACES = ("vrc-unity-tools", "vrc-blender-tools", "vrc-skills")
TOOLS_MD_SURFACES = ("vrc-unity-tools", "vrc-blender-tools")
SKILLS_HEADING = "Skills"
DOC_SOURCE = {"vrc-unity-tools": "TOOLS.md", "vrc-blender-tools": "TOOLS.md",
              "vrc-skills": f"README.md (## {SKILLS_HEADING})"}
# Each skills row links its key to the skill's SKILL.md in the plugin repo. The URL is
# a pure function of the key, so requiring it here catches a *renamed* skill: the old
# key fails the drift check against skills/*/SKILL.md, taking its stale link with it.
# It does NOT catch a *new* skill — keys come from the local working tree, while the
# URL points at pushed `main`, so a roster row committed ahead of the vrc-skills merge
# ships a live 404 until that merge lands. Push the skill first (vrc-skills/README.md
# states the ordering); verifying it here would put a network read in a warn-only hook.
SKILL_URL = "https://github.com/Ryan6-VRC/vrc-skills/blob/main/skills/{key}/SKILL.md"
BEGIN = "<!-- BEGIN tools -->"
END = "<!-- END tools -->"


class InventoryError(Exception):
    """Fail-loud error; message names the offender."""


def _read(path: Path) -> str:
    """Read a source file, turning any failure into a fail-loud InventoryError
    (named offender) rather than a bare OSError/UnicodeDecodeError traceback."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise InventoryError(f"{path}: cannot read ({type(e).__name__})")


def _require_dir(path: Path) -> Path:
    """A missing declaration-site directory is a structural error (repo not checked
    out / renamed), not tool drift — surface it loudly."""
    if not path.is_dir():
        raise InventoryError(f"missing expected directory: {path}")
    return path


def extract_unity_keys(repo: Path) -> set:
    """Class names carrying [AgentTool], scanning packages/**/*.cs."""
    keys = set()
    for cs in sorted(_require_dir(repo / "packages").rglob("*.cs")):
        text = _read(cs)
        for m in re.finditer(r"^[ \t]*\[AgentTool\]", text, re.MULTILINE):
            # Bind to the ADJACENT declaration only (the first `class` before any
            # '{' or ';'), so a misplaced attribute — on a struct/enum, or inside a
            # block comment above an unrelated class — fails loud instead of silently
            # binding a distant identifier.
            cm = re.search(r"^[^{;]*?\bclass\s+([A-Za-z_]\w*)", text[m.end():])
            if not cm:
                raise InventoryError(f"{cs}: [AgentTool] is not on a class declaration")
            name = cm.group(1)
            if name in keys:
                raise InventoryError(f"duplicate [AgentTool] type name '{name}' (e.g. {cs})")
            keys.add(name)
    return keys


def extract_blender_keys(repo: Path) -> set:
    """Operator short-names (bl_idname avatarprep.<name>) UNION cli/*.py stems.

    Globs the whole avatarprep package rather than pinning operators.py, so an
    operator declared in any module is still inventoried and a renamed operators.py
    fails loud (missing dir) instead of vanishing silently. The `avatarprep.` prefix
    excludes the AVATARPREP_PT_* panel idname in ui.py."""
    keys = set()
    for src in sorted(_require_dir(repo / "avatarprep").rglob("*.py")):
        for m in re.finditer(r"""bl_idname\s*=\s*['"]avatarprep\.([A-Za-z_]\w*)['"]""", _read(src)):
            keys.add(m.group(1))
    for py in sorted(_require_dir(repo / "cli").glob("*.py")):  # non-recursive: skips __pycache__
        if not py.stem.startswith("_"):  # _-prefixed = private plumbing (_common, __init__), not a tool door
            keys.add(py.stem)
    return keys


def _frontmatter_name(path: Path) -> str:
    lines = _read(path).splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"\s*name:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return ""


def extract_skills_keys(repo: Path) -> set:
    keys = set()
    for skill_md in sorted(_require_dir(repo / "skills").glob("*/SKILL.md")):
        name = _frontmatter_name(skill_md)
        if not name:
            raise InventoryError(f"{skill_md}: no `name:` in frontmatter")
        if name in keys:
            raise InventoryError(f"duplicate skill name '{name}' (e.g. {skill_md})")
        keys.add(name)
    return keys


def extract_code_keys(code_root: Path = None) -> dict:
    code_root = code_root or WORKSPACE
    return {
        "vrc-unity-tools": extract_unity_keys(code_root / "vrc-unity-tools"),
        "vrc-blender-tools": extract_blender_keys(code_root / "vrc-blender-tools"),
        "vrc-skills": extract_skills_keys(code_root / "vrc-skills"),
    }


# ── Door coverage: every callable entry point named where an agent will read it ─────────────
#
# The defect: a doc names a tool and describes it without ever showing the callable, so the
# agent guesses `OwnMaterial(...)` for `OwnMaterial.Run(...)` and spends a compile round-trip.
#
# A door is `public static string` on an [AgentTool] class, at depth 1 — the kit's own
# convention, since a door returns its one-line verdict ending `| log=<path>`. The door set
# therefore tracks the code with nobody maintaining a list, and the two tables below are the
# entire judgment; they stay small because the convention does the work.
NOT_DOORS = {
    # string-returning but internal: content stamps, and diagnostic fragments already inlined
    # into the verdicts that need them.
    ("CompileClips", "HashClipContent"), ("CompileClips", "ReadContentStamp"),
    ("ReportConsole", "BenignLabel"), ("ReportConsole", "ConsoleFilterNote"),
    # Returns the reason a handle was refused — already inlined into every verdict that wants
    # it (ReportController, CheckAnimator, DecompileController), so nothing reaches for it
    # first and a doc row for it would document a string helper.
    ("ReportController", "RefuseWhy"),
}
DOORS_EXTRA = {
    # Doors whose return type is not `string`. ScanAnchorSeams hands back its offender lines;
    # vrc-patterns' gate drives it directly.
    ("CheckAvatar", "ScanAnchorSeams"),
}

_AGENT_TOOL_ANCHOR = re.compile(r"^[ \t]*\[AgentTool\]", re.MULTILINE)
_STATIC_SIG = re.compile(
    r"^[ \t]*public\s+static\s+"
    r"(?!readonly\b|class\b|struct\b|partial\b|enum\b|interface\b)"
    r"(?:async\s+)?"
    r"(?P<ret>\([^)]*\)|[\w.<>,\[\]\?]+(?:\s*<[^>()]*>)?)\s+"
    r"(?P<name>\w+)\s*\(", re.MULTILINE)


def blank_out(src: str) -> str:
    r"""Replace the CONTENTS of comments, strings and char literals with spaces, preserving
    length and line structure, so every structural regex below sees code only.

    One character-state pass, not a comment pass then a string pass: `@"https?://\S+"` holds
    `//`, and a `//` comment in this tree holds an odd number of quotes, so either ordering of
    two independent passes desynchronises the rest of the file. Char literals are tracked for
    the same reason — `c0 == '"'` is live here and reads as a string opener to any scanner
    that ignores `'…'`."""
    out = list(src)
    i, n = 0, len(src)

    def wipe(a, b):
        for k in range(a, min(b, n)):
            if src[k] != "\n":
                out[k] = " "

    while i < n:
        two = src[i:i + 2]
        if two == "//":
            j = src.find("\n", i)
            j = n if j < 0 else j
            wipe(i, j)
            i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            wipe(i, j)
            i = j
        elif src[i] in '@$' and src[i:i + 3].lstrip('@$')[:1] == '"':
            k = i                                  # skip the prefix run: @" $" @$" $@"
            while src[k] in '@$':
                k += 1
            j = k + 1
            if '@' in src[i:k]:                    # verbatim: no escapes, "" is one quote,
                while j < n:                       # and it may legitimately span lines
                    if src[j] == '"':
                        if src[j:j + 2] == '""':
                            j += 2
                            continue
                        j += 1
                        break
                    j += 1
            else:                                  # interpolated only: ordinary escapes
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == '"' or src[j] == "\n":
                        j += 1
                        break
                    j += 1
            wipe(i, j)
            i = j
        elif src[i] in '"\'':
            quote, j = src[i], i + 1
            while j < n:
                if src[j] == "\\":             # \" \\ \' inside either literal
                    j += 2
                    continue
                if src[j] == quote:
                    j += 1
                    break
                if src[j] == "\n":             # unterminated: never run past the line
                    break
                j += 1
            wipe(i, j)
            i = j
        else:
            i += 1
    return "".join(out)


def _depth1_body(blanked: str, decl_start: int) -> str:
    """A class body with everything nested deeper than one level blanked, so a nested type's
    members are not credited to the tool (`UploadAvatar.UploadOutcome.Uploaded` is not a door
    of `UploadAvatar`). Runs on blanked source, where every brace left is structural."""
    i = blanked.find("{", decl_start)
    if i < 0:
        return ""
    depth, j, kept = 0, i, []
    while j < len(blanked):
        ch = blanked[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        kept.append(ch if (depth <= 1 or ch == "\n") else " ")
        j += 1
    return "".join(kept)


def extract_unity_doors(repo: Path) -> tuple:
    """(doors, statics, namespaces): {class: {door name}}, {class: {every public static name}},
    {class: declared namespace}.

    Reads with Python, never a shelled grep: `ReportConsole.cs` carries raw NUL bytes, and
    `rg`/`grep`/`git grep` all classify it as binary and skip it without a word — silently
    dropping a five-door tool class from the census."""
    doors, statics, namespaces = {}, {}, {}
    for cs in sorted(_require_dir(repo / "packages").rglob("*.cs")):
        blanked = blank_out(_read(cs))
        nsm = re.search(r"^\s*namespace\s+([\w.]+)", blanked, re.MULTILINE)
        for m in _AGENT_TOOL_ANCHOR.finditer(blanked):
            cm = re.search(r"^[^{;]*?\bclass\s+([A-Za-z_]\w*)", blanked[m.end():])
            if not cm:
                raise InventoryError(f"{cs}: [AgentTool] is not on a class declaration")
            cls = cm.group(1)
            body = _depth1_body(blanked, m.end() + cm.start())
            names, door_names = set(), set()
            for sig in _STATIC_SIG.finditer(body):
                name = sig.group("name")
                names.add(name)
                if sig.group("ret").strip() == "string" and (cls, name) not in NOT_DOORS:
                    door_names.add(name)
            for c, n in DOORS_EXTRA:
                if c != cls:
                    continue
                # A renamed method would drop out of DOORS_EXTRA silently, quietly deleting a
                # door from the census. NOT_DOORS rots the other way — its stale entry stops
                # excluding and the door turns up as a new coverage finding — so only this
                # table needs the guard.
                if n not in names:
                    raise InventoryError(
                        f"DOORS_EXTRA names {c}.{n}, which is not a public static on {c} "
                        f"({cs.name}) — the method was renamed or removed; update the table")
                door_names.add(n)
            statics.setdefault(cls, set()).update(names)
            doors.setdefault(cls, set()).update(door_names)
            if nsm:
                namespaces[cls] = nsm.group(1)
    return doors, statics, namespaces


def _governed_docs(docs_root: Path) -> list:
    """Every tracked doc an agent reads for a call shape. `docs/local/` is gitignored scratch."""
    return sorted(p for p in _require_dir(docs_root / "docs").rglob("*.md")
                  if "local" not in p.relative_to(docs_root).parts)


def _skill_bodies(code_root: Path) -> list:
    """Every `vrc-skills` skill body, for the RESOLUTION scan only.

    Tolerant of absence by design, unlike `_governed_docs`' `_require_dir`: this reads a
    sibling repo, and `--code-root` legitimately points somewhere without one (a worktree,
    a partial checkout, a manual run). Requiring it would turn a missing sibling into the
    exit-2 arm, which the pre-commit hook prints as "README was not checked" — suppressing
    the mirror over a check that was never the point of the invocation."""
    skills = code_root / "vrc-skills" / "skills"
    if not skills.is_dir():
        return []
    return sorted(skills.glob("*/SKILL.md"))


# The call tail, shared by both patterns below. The arg list is optional and a CAPTURE group
# rather than a match requirement: `Tool.Method` with no arg list is how much of the corpus names a door, and
# it rots on a rename exactly like `Tool.Method(` does, so resolution must see it. What the group
# then reports is "this site was a paste-able call", which only coverage cares about.
#
# `[ \t]`, never `\s`: `\s` spans newlines, so `Tool.Run\n\n(See also …)` would capture `'\n\n('`
# and credit a paragraph break as an argument list. Harmless while the group gated the match;
# a false coverage credit once it is a flag.
#
# The trailing `(?!\.\w)` is what keeps an optional arg list from turning every dotted member
# path into a call: `UploadAvatar.UploadOutcome.Uploaded` — a shape `_depth1_body` exists to
# handle — would otherwise resolve as a call to `UploadAvatar.UploadOutcome` and be reported as
# naming no public static, under a remedy ("fix the call or the doc") that fits nothing the
# author did. A dot followed by a word character continues a path; a dot followed by anything
# else is sentence punctuation, so `see T.Run.` stays checked.
#
# `(?!\w)` anchors the method name so the lookahead cannot be dodged by giving back characters:
# without it `UploadOutcome` shortens to `UploadOutcom`, whose next char is `e` rather than `.`,
# and the false positive returns wearing a truncated name. It is inert on its own — earlier
# drafts credited it with guarding `RenderThumbnail` against `RenderThumbnailPlay`, which the
# literal dot has always done — and load-bearing only in front of a lookahead that can fail.
_CALL_TAIL = r"(?!\w)([ \t]*\()?(?!\.\w)"


def _call_re(cls: str) -> re.Pattern:
    """`Tool.Method`, with or without a following arg list, and with an optional namespace prefix
    so the fully-qualified form the docs prescribe (`Ryan6Vrc.AgentTools.Editor.Tool.Method`)
    counts. The literal dot after the class name stops `RenderThumbnail` matching
    `RenderThumbnailPlay.Run` — load-bearing now that both classes' primary door is `Run` and
    only the prefix separates them.

    The method must start uppercase: every door is PascalCase, while `CheckSeam.cs (line 40)`
    — a file reference the docs already make — otherwise reads as a call to a method `cs`. That
    guard carries more weight since the arg list became optional, because what remains matchable
    without one is any capitalised word following a tool-class dot. `_CALL_TAIL` excludes the
    dotted member paths. What is left is a doc naming a nested type with no member after it
    (`UploadAvatar.UploadOutcome`), which still reads as a call and would be reported as naming
    no public static — the known residual false red, and the reason to reach for the extractor's
    nested-type names if one ever lands in the corpus.

    Group 2 is the paren — see `_CALL_TAIL`, and `_resolution_scan` for who reads it."""
    return re.compile(r"(?<![\w])(?:\w+\.)*" + re.escape(cls) + r"\.([A-Z]\w*)" + _CALL_TAIL)


# The qualified form the docs prescribe. Its prefix is what makes a wrong one checkable: a
# call carrying `Ryan6Vrc.<Kit>.Editor.` is asserting a namespace, and asserting the wrong one
# is the recurring stumble `unity.md` §Invocation names (AgentTools vs AvatarTools).
#
# Parenless too, and it has to be: `_call_re`'s `(?:\w+\.)*` prefix swallows a parenless
# qualified ref and resolves it clean, so a paren-only arm here would leave a shape that reads
# as namespace-checked and is not.
_QUALIFIED_CALL = re.compile(
    r"Ryan6Vrc\.(?:Agent|Avatar)Tools\.Editor\.(\w+)\.([A-Z]\w*)" + _CALL_TAIL)


def _resolution_scan(texts: list, statics: dict, namespaces: dict,
                     found: set, seen: dict = None, fix_in: str = None) -> None:
    """Both resolution arms over one corpus: every `Tool.Method(` names a real public static,
    and every fully-qualified call names the kit that class actually lives in.

    `seen` is the coverage accumulator and is **optional on purpose**. Coverage asks "is every
    door named somewhere an agent reads it", and `docs/` is that somewhere — a door named only
    in a skill body is still undocumented. Passing `seen` from a corpus that does not answer
    the coverage question would let a door named only in a `SKILL.md` count as covered and its
    finding vanish, which is the check silently *loosening* while the diff appears to tighten
    it. So the skills and `TOOLS.md` passes supply `found` and withhold `seen`; nothing else
    separates them.

    Within a `seen` corpus there is a second, finer version of the same asymmetry: only a match
    that carried an arg list credits coverage. Resolution reads every match, because a parenless
    `Tool.Method` rots on a rename just as surely; coverage reads only the paste-able ones,
    because the missing-door message prescribes exactly that form ("write `Cls.Name(…)` at its
    row so an agent can paste it") and a remedy the check would not accept is not a remedy.

    `fix_in` names the repo a finding must be fixed in, when that is not the tree being
    committed. Every finding this check emitted before was clearable in the same commit; a
    `vrc-skills` one is not, and an unqualified message sends the committer hunting in the
    wrong tree."""
    where = f" (fix in `{fix_in}`)" if fix_in else ""
    for cls in sorted(statics):
        pat = _call_re(cls)
        for rel, text in texts:
            for m in pat.finditer(text):
                if seen is not None and m.group(2):
                    seen.setdefault(cls, set()).add(m.group(1))
                if m.group(1) not in statics[cls]:
                    found.add((rel, f"`{cls}.{m.group(1)}` names no public static on {cls} — "
                                    f"the declaration site is canon; fix the call or the "
                                    f"doc{where}"))
    for rel, text in texts:
        for m in _QUALIFIED_CALL.finditer(text):
            cls, method = m.group(1), m.group(2)
            if cls not in statics:
                found.add((rel, f"`{m.group(0)}…` names no [AgentTool] class `{cls}`{where}"))
            elif namespaces.get(cls) and not m.group(0).startswith(namespaces[cls] + "."):
                found.add((rel, f"`{cls}.{method}` is qualified with the wrong kit — {cls} "
                                f"lives in `{namespaces[cls]}`{where}"))


_BACKTICKED = re.compile(r"`([A-Z]\w*)(?:\([^`]*\))?`")


def _bare_door_rows(tools_md: str, statics: dict, found: set) -> None:
    """`TOOLS.md` rows that name a member of their OWN key class without the class prefix.

    The file is a table keyed by class, so its rows once wrote door names bare — the key
    supplied the class to the reader, and to nothing else: a bare `` `Run` `` is invisible to
    every scan here, which is how six rows in the system tool index went on teaching deleted
    door names through a rename the gate reported green.

    The direction matters. "An unresolvable bare token is a stale door" is the natural reading
    and is unusable — these rows are thick with `Transform`, `PENDING`, `ReleaseStatus` and
    sibling class names, and it runs about 13 false to 3 true, inferring what a token means.
    Inverted, it asserts a state: a token that IS a declared static of the class its own row is
    keyed by resolves against a declaration site, whatever else it might have been. Nothing
    else is touched, and the message stays inside what the trigger proved (see the emit site).

    This is what keeps the prefix a house style rather than a one-time cleanup — a new row
    written bare is caught when it is written, so every surviving token is prefixed and the
    next rename is caught by the resolution scan above.

    Adds to `found` rather than returning, so these share the resolution scans' dedupe-by-issue
    and their sort: a row naming `Run` twice is one finding, not two."""
    seen_delim, in_tools = False, False
    for raw in tools_md.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            # Door names only mean anything under the Unity kit; the Blender surface keys are
            # operator names with no C# statics behind them.
            in_tools = "vrc-unity-tools" in line.lstrip("#").strip()
            seen_delim = False
            continue
        if not line.startswith("|"):
            seen_delim = False
            continue
        key, seen_delim = _row_key(line, seen_delim)
        if key is None or not in_tools or key not in statics:
            continue
        for m in _BACKTICKED.finditer("|".join(line.split("|")[2:])):
            if m.group(1) in statics[key]:
                # "public static", not "door": the membership test is `statics`, which keeps the
                # NOT_DOORS members this file elsewhere insists are not doors. And the prescribed
                # class is offered, not asserted — the trigger only proves the name resolves on
                # THIS row's class, and every [AgentTool] class declares `Run`, so a row
                # mentioning a sibling tool's door bare would otherwise be handed a fix naming
                # the wrong owner.
                found.add(("TOOLS.md", f"`{m.group(1)}` is written bare in the {key} row, and it "
                                       f"names a public static — prefix it with the class that "
                                       f"declares it (`{key}.{m.group(1)}` if this row's tool is "
                                       f"the one meant, otherwise that tool's class), so a rename "
                                       f"cannot rot the row unseen; a row key is not a prefix any "
                                       f"check can read"))


def check_doors(code_root: Path, docs_root: Path) -> tuple:
    """(problems, census). Coverage: every door is named somewhere an agent reads it.
    Resolution: every documented call on a tool class names a real public static, and a
    fully-qualified one names the kit that class actually lives in.

    Pins entry-point NAMES and namespaces only — arguments, defaults and overloads are not
    compared, so a doc's argument list is illustrative and the declaration site stays canon.

    Three corpora, deliberately asymmetric. `docs/` gets both scans. `vrc-skills`' skill bodies
    and `TOOLS.md` get **resolution only**: they paste the same call literals and rot the same
    way, but they are trigger-gated task bodies and routing rows rather than the door roster,
    so demanding a literal call there would be a false red. `_resolution_scan`'s docstring owns
    why the split has to be structural rather than a promise.

    `TOOLS.md` is read strictly, unlike the skills' tolerated absence: it sits in the same tree
    as `docs/`, so a missing one is a broken `--docs-root` rather than a legitimately partial
    checkout, and `main()` already fails on that path a line earlier. `README.md` is not read at
    all — `inject()` generates its tool block from this file, so scanning both double-reports one
    source. The rows only became reachable at all once they carried the class prefix that
    `_bare_door_rows` now pins.

    Scope this does NOT claim: a door rename lands in `vrc-unity-tools`, whose own commits
    never run this hook at all. So this is a lagging detector that catches drift on the next
    Atelier commit — from any tree, since the hook resolves the main checkout for
    `--code-root` — not a gate that prevents it."""
    doors, statics, namespaces = extract_unity_doors(code_root / "vrc-unity-tools")
    texts = [(p.relative_to(docs_root).as_posix(), _read(p)) for p in _governed_docs(docs_root)]
    # Relative to CODE_root, not docs_root: the two diverge in a worktree by design (see
    # main()'s two-root comment), and `relative_to` on a path outside its argument raises
    # ValueError — an uncaught traceback, not even the InventoryError exit-2 arm.
    skill_texts = [(p.relative_to(code_root).as_posix(), _read(p))
                   for p in _skill_bodies(code_root)]
    tools_md = _read(docs_root / "TOOLS.md")

    seen, found = {}, set()          # found: dedupe by issue, not by occurrence
    _resolution_scan(texts, statics, namespaces, found, seen=seen)
    _resolution_scan(skill_texts, statics, namespaces, found, fix_in="vrc-skills")
    _resolution_scan([("TOOLS.md", tools_md)], statics, namespaces, found)
    _bare_door_rows(tools_md, statics, found)
    problems = [f"{rel}: {msg}" for rel, msg in sorted(found)]
    missing = [(c, n) for c in sorted(doors) for n in sorted(doors[c] - seen.get(c, set()))]
    for cls, name in missing:
        problems.append(f"{cls}.{name} is a door with no literal call under docs/ — write "
                        f"`{cls}.{name}(…)` at its row so an agent can paste it")
    # Naming: every class names its primary door `Run` (tool-design.md §Tools). The rule's whole
    # power is that it has no exceptions -- the kit once ran two conventions at once (`Run` on 18
    # classes, the class's own verb on 20), and agents generalized whichever they met first onto
    # the other half, at about one session in eighteen. Asserted against `doors` rather than
    # `statics` so a future NOT_DOORS entry can still suppress a member.
    #
    # Scope, stated because the message would otherwise overclaim: this asserts a `Run` door
    # EXISTS. There is no machine notion of "primary" here -- a class that keeps `Report()` and
    # adds a thin `Run()` beside it passes, which is the alias the canon clause ("rename to
    # converge rather than alias") forbids. Existence is the necessary half and the checkable
    # one; whether the `Run` is the real entry point stays a review question.
    for cls in sorted(doors):
        if "Run" not in doors[cls]:
            problems.append(f"{cls} declares no `Run` door — the primary door is always `Run`; "
                            f"rename {cls}'s primary, and keep the verdict label as it is (the "
                            f"label names the action, not the door)")
    total = sum(len(v) for v in doors.values())
    return problems, (f"doors {total - len(missing)}/{total} named across "
                      f"{len(doors)} [AgentTool] classes")


LINK_RE = re.compile(r"^\[(?P<text>.+?)\]\((?P<url>\S+)\)$")


def _first_cell(line: str) -> str:
    return line.strip("|").split("|")[0].strip()


def _row_key(line: str, seen_delim: bool):
    """Interpret one `|`-prefixed table line: (key_or_None, new_seen_delim).
    The header row precedes the GFM delimiter row and yields no key. A key cell may
    be wrapped in a markdown link — the link text carries the key."""
    first = _first_cell(line)
    if re.fullmatch(r":?-{1,}:?", first.replace(" ", "")):
        return None, True                  # GFM delimiter row
    if not seen_delim:
        return None, False                 # header row
    m = LINK_RE.match(first)
    if m:
        first = m.group("text").strip()
    return first.strip("`").strip() or None, True


def parse_tools_md(path: Path) -> dict:
    text = _read(path)
    if BEGIN in text or END in text:
        raise InventoryError(f"{path}: must not contain the injection marker literals")
    result = {sfc: set() for sfc in TOOLS_MD_SURFACES}
    sections_seen = set()
    current = None
    seen_delim = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            current = next((sfc for sfc in TOOLS_MD_SURFACES if sfc in heading), None)
            if current:
                sections_seen.add(current)
            seen_delim = False
            continue
        if line.startswith("|"):
            key, seen_delim = _row_key(line, seen_delim)
            if key is None:
                continue
            if current is None:
                raise InventoryError(f"{path}: table row outside an attributable section: {raw}")
            result[current].add(key)
        else:
            seen_delim = False             # table ended
    missing_sections = [sfc for sfc in TOOLS_MD_SURFACES if sfc not in sections_seen]
    if missing_sections:
        raise InventoryError(f"{path}: no section for surface(s): {missing_sections}")
    return result


def parse_readme_skills(path: Path) -> set:
    """Keys from README.md's hand-maintained `## {SKILLS_HEADING}` table; the
    section ends at the next heading of any level. Each row must link its key to the
    skill's SKILL.md (SKILL_URL)."""
    keys = set()
    in_section = False
    found = False
    seen_delim = False
    for raw in _read(path).splitlines():
        line = raw.strip()
        if line.startswith("#"):
            if in_section:
                break
            in_section = line.lstrip("#").strip() == SKILLS_HEADING
            found = found or in_section
            continue
        if not in_section:
            continue
        if line.startswith("|"):
            cell = _first_cell(line)
            key, seen_delim = _row_key(line, seen_delim)
            if key:
                # Diagnose a malformed cell as such: on no match `key` is the whole raw
                # cell, so folding both cases into one message would name a nonsense
                # offender and interpolate the broken cell into the URL it demands.
                m = LINK_RE.match(cell)
                if not m:
                    raise InventoryError(
                        f"{path}: skills row key cell is not a plain markdown link: {cell}")
                want = SKILL_URL.format(key=key)
                if m.group("url") != want:
                    raise InventoryError(
                        f"{path}: skills row `{key}` must link its key to {want}")
                keys.add(key)
        else:
            seen_delim = False
    if not found:
        raise InventoryError(f"{path}: no `## {SKILLS_HEADING}` section (the skills roster)")
    if not keys:
        raise InventoryError(f"{path}: `## {SKILLS_HEADING}` section has no table rows")
    return keys


def check(code_keys: dict, doc_keys: dict) -> list:
    problems = []
    for sfc in SURFACES:
        undocumented = sorted(code_keys[sfc] - doc_keys[sfc])
        phantom = sorted(doc_keys[sfc] - code_keys[sfc])
        if undocumented:
            problems.append(f"[{sfc}] in code but not {DOC_SOURCE[sfc]} (undocumented): {undocumented}")
        if phantom:
            problems.append(f"[{sfc}] in {DOC_SOURCE[sfc]} but not code (phantom/renamed): {phantom}")
    return problems


def render_block(tools_md: str) -> str:
    return (f"{BEGIN}\n"
            "<!-- generated from TOOLS.md — edit TOOLS.md, not here -->\n\n"
            f"{tools_md.rstrip()}\n\n{END}")


def inject(readme_path: Path, tools_md_path: Path) -> bool:
    """Mirror TOOLS.md into the README tools block. Returns True iff the file was
    actually rewritten (so the hook can stage README only on a real change)."""
    tools_md = _read(tools_md_path)
    readme = _read(readme_path)
    nb, ne = readme.count(BEGIN), readme.count(END)
    if nb != ne or nb > 1:
        raise InventoryError(f"{readme_path}: unbalanced/duplicate tool markers (BEGIN={nb}, END={ne})")
    block = render_block(tools_md)
    if nb == 0:
        new = (readme.rstrip() + "\n\n## Tools\n\n"
               "_The tool surface the skills above drive. Generated from `TOOLS.md`._\n\n"
               + block + "\n")
    else:
        start, end_i = readme.index(BEGIN), readme.index(END)
        if end_i < start:
            raise InventoryError(f"{readme_path}: END marker precedes BEGIN marker")
        new = readme[:start] + block + readme[end_i + len(END):]
    if new != readme:
        readme_path.write_text(new, encoding="utf-8", newline="\n")
        return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify TOOLS.md against code; mirror it into README.md")
    ap.add_argument("--check", action="store_true", help="verify only; no writes; non-zero on drift")
    # Two roots, because they diverge in a worktree: the `vrc-*` siblings are gitignored and
    # absent there, so the docs under test and the code they describe live in different trees.
    # One root would either abort on the missing siblings or validate the main tree's docs
    # while the edited ones go unchecked.
    ap.add_argument("--docs-root", type=Path, default=WORKSPACE,
                    help="tree holding TOOLS.md / README.md / docs (default: this script's repo)")
    ap.add_argument("--code-root", type=Path, default=None,
                    help="tree holding the vrc-* sibling repos (default: --docs-root)")
    args = ap.parse_args(argv)
    docs_root = args.docs_root
    code_root = args.code_root or docs_root
    if code_root != docs_root:
        # The DRIFT/DOORS lines below carry no per-line tree marker, so say once whose code
        # this run judged: from a branch, roster drift can be another session's uncommitted
        # sibling state, not this commit's to clear (dispatched-work.md §Terminal state).
        print(f"tool-inventory: code read from {code_root} (live sibling state; docs from "
              f"{docs_root})", file=sys.stderr)
    try:
        code_keys = extract_code_keys(code_root)
        doc_keys = parse_tools_md(docs_root / "TOOLS.md")
        doc_keys["vrc-skills"] = parse_readme_skills(docs_root / "README.md")
        door_problems, census = check_doors(code_root, docs_root)
    except InventoryError as e:
        print(f"tool-inventory: ERROR: {e}", file=sys.stderr)
        return 2
    # Door findings print even when key drift fires. The commonest cause of drift is landing a
    # new tool — exactly the commit whose door rows matter most — and returning here first
    # would suppress the census and every door line while the hook still said "findings above".
    print(f"tool-inventory: {census}", file=sys.stderr)
    for p in door_problems:
        print(f"tool-inventory: DOORS: {p}", file=sys.stderr)
    problems = check(code_keys, doc_keys)
    if problems:
        for p in problems:
            print(f"tool-inventory: DRIFT: {p}", file=sys.stderr)
        return 1
    if not args.check:
        try:
            wrote = inject(docs_root / "README.md", docs_root / "TOOLS.md")
        except InventoryError as e:
            print(f"tool-inventory: ERROR: {e}", file=sys.stderr)
            return 2
        if wrote:
            # stdout marker: the pre-commit hook stages README only on a real write,
            # so an unchanged block never sweeps unrelated README edits into a commit.
            print("README-UPDATED")
        print("tool-inventory: OK — README tools block in sync", file=sys.stderr)
    else:
        print("tool-inventory: OK — TOOLS.md + README skills roster match code", file=sys.stderr)
    # Door findings never gate the mirror above: an undocumented door is a finding about docs/,
    # while the mirror is TOOLS.md → README.md. Gating it would stop the public README tracking
    # TOOLS.md for as long as a door row sat unwritten — and the hook only warns, so nobody
    # would see why.
    return 1 if door_problems else 0


if __name__ == "__main__":
    sys.exit(main())
