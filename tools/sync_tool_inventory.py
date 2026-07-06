# tools/sync_tool_inventory.py
"""Verify TOOLS.md keys against code declaration sites, and mirror it into README.md.

Three surfaces (the avatar-authoring system); vrc-bridge is a separate runtime
system and is out of scope:
  vrc-unity-tools   -> class names carrying the [AgentTool] identity attribute
  vrc-blender-tools -> operator short-names (bl_idname) UNION cli/ script stems
  vrc-skills        -> skill frontmatter `name:`

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
        if py.stem != "__init__":
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


def extract_code_keys() -> dict:
    return {
        "vrc-unity-tools": extract_unity_keys(WORKSPACE / "vrc-unity-tools"),
        "vrc-blender-tools": extract_blender_keys(WORKSPACE / "vrc-blender-tools"),
        "vrc-skills": extract_skills_keys(WORKSPACE / "vrc-skills"),
    }


def parse_tools_md(path: Path) -> dict:
    text = _read(path)
    if BEGIN in text or END in text:
        raise InventoryError(f"{path}: must not contain the injection marker literals")
    result = {sfc: set() for sfc in SURFACES}
    sections_seen = set()
    current = None
    seen_delim = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            current = next((sfc for sfc in SURFACES if sfc in heading), None)
            if current:
                sections_seen.add(current)
            seen_delim = False
            continue
        if line.startswith("|"):
            first = line.strip("|").split("|")[0].strip()
            if re.fullmatch(r":?-{1,}:?", first.replace(" ", "")):
                seen_delim = True          # GFM delimiter row
                continue
            if not seen_delim:
                continue                   # header row (precedes delimiter)
            if current is None:
                raise InventoryError(f"{path}: table row outside an attributable section: {raw}")
            key = first.strip("`").strip()
            if key:
                result[current].add(key)
        else:
            seen_delim = False             # table ended
    missing_sections = [sfc for sfc in SURFACES if sfc not in sections_seen]
    if missing_sections:
        raise InventoryError(f"{path}: no section for surface(s): {missing_sections}")
    return result


def check(code_keys: dict, doc_keys: dict) -> list:
    problems = []
    for sfc in SURFACES:
        undocumented = sorted(code_keys[sfc] - doc_keys[sfc])
        phantom = sorted(doc_keys[sfc] - code_keys[sfc])
        if undocumented:
            problems.append(f"[{sfc}] in code but not TOOLS.md (undocumented): {undocumented}")
        if phantom:
            problems.append(f"[{sfc}] in TOOLS.md but not code (phantom/renamed): {phantom}")
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
               "_The callable surface of this system. Generated from `TOOLS.md`._\n\n"
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
    args = ap.parse_args(argv)
    try:
        code_keys = extract_code_keys()
        doc_keys = parse_tools_md(WORKSPACE / "TOOLS.md")
    except InventoryError as e:
        print(f"tool-inventory: ERROR: {e}", file=sys.stderr)
        return 2
    problems = check(code_keys, doc_keys)
    if problems:
        for p in problems:
            print(f"tool-inventory: DRIFT: {p}", file=sys.stderr)
        return 1
    if not args.check:
        try:
            wrote = inject(WORKSPACE / "README.md", WORKSPACE / "TOOLS.md")
        except InventoryError as e:
            print(f"tool-inventory: ERROR: {e}", file=sys.stderr)
            return 2
        if wrote:
            # stdout marker: the pre-commit hook stages README only on a real write,
            # so an unchanged block never sweeps unrelated README edits into a commit.
            print("README-UPDATED")
        print("tool-inventory: OK — README tools block in sync", file=sys.stderr)
    else:
        print("tool-inventory: OK — TOOLS.md matches code", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
