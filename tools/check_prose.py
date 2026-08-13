# tools/check_prose.py
"""Workspace prose-governance check, run from the meta-repo root.

Four passes over the assembled workspace. A pass with nothing to work on — an
absent sibling repo, no governed skill directory — skips with a printed NOTE:
absence is a valid workspace state, never a failure. A family whose repo IS
present but whose directory is gone is the other thing, and fails loud
(FAMILY_REQUIRED_BY).

  1. vrc-skills' own gate, tools/validate_skills.py (subprocess) — skill
     anatomy; its errors/warnings count here. Passes 1-3 cover both governed
     enumerations (SKILL_FAMILIES): the plugin repo's skills/ and this repo's
     .claude/skills/, held to one anatomy. Numbered first, RUN last: it is the
     only pass whose failures abort the run, so the others report first.
  2. Doc pointers: every docs-file reference in a SKILL.md resolves against the
     meta-repo (docs/ listing, root .md files, files in vrc-skills). WARN.
  3. Tool names, structured slot only: each leading bold-backticked name in a
     skill's "## Tools" bullets appears in TOOLS.md. WARN. Prose outside that
     slot is never scanned.
  4. Form: tools/reflow_md.py's --check over the governed fence — files
     enumerated from the governed_fence constants in docs/tool-design.md
     (roots, glob, exclude, check-ignore). ERROR on drift: the form gate is
     already the declared convention. Individual roots still NOTE-skip, but
     resolving to zero files overall is the one absence that is not a valid
     state — this repo's own .md is always inside the fence — so it fails
     loud rather than reporting a clean run over nothing.

The fence bounds this gate only. tools/prose-hook.ps1's write-time nudge fires
on any markdown the agent authors in the workspace and reads no fence constant,
so there is no echo of these constants left to keep in sync.

Skills in CONVENTIONS.md's exempt list are held to frontmatter checks only, so
passes 2-3 skip them (their doc references include run-time artifacts by design).
Exit 0 when only warnings, 1 on any error, 2 on an internal failure.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
BACKTICK_RE = re.compile(r'`([^`\n]+)`')
MD_NAME_RE = re.compile(r'^[\w-]+\.md$')
MD_PATH_RE = re.compile(r'^[\w./-]+/[\w.-]+\.md$')
DOCS_REF_RE = re.compile(r'\bdocs/[\w-]+\.md\b')
H2_RE = re.compile(r'^\s{0,3}##(?!#)\s*(.*?)\s*$')
FENCE_RE = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
# A checkable tool token: one bare identifier, optionally a trailing wildcard
# ("Check*"); dotted package ids, paths, and glossed phrases are not the slot.
TOOL_TOKEN_RE = re.compile(r'^[A-Za-z0-9_]+\*?$')
TOOLS_BULLET_RE = re.compile(r'^\s*[-*]\s+\*\*(`.*?)\*\*')


class GateError(Exception):
    """Fail-loud error; message names what is missing."""


# ---- constants blocks (docs/tool-design.md, vrc-skills/CONVENTIONS.md) ----

def read_constants(path, marker):
    if not path.is_file():
        raise GateError(f'{path}: not found — cannot read its constants block')
    text = path.read_text(encoding='utf-8')
    for block in re.findall(r'^\s{0,3}```ya?ml[^\n]*\n(.*?)^\s{0,3}```\s*$', text, re.M | re.S):
        if marker in block:
            try:
                consts = yaml.safe_load(block)
            except yaml.YAMLError as e:
                # Not a lint finding about someone's prose: the gate cannot read
                # its own configuration, which is an internal failure (exit 2).
                raise GateError(f'{path}: constants block is not valid YAML: {e}') from e
            if not isinstance(consts, dict):
                raise GateError(f'{path}: constants block is not a mapping (got '
                                f'{type(consts).__name__})')
            return consts
    raise GateError(f'{path}: no fenced yaml block containing "{marker}"')


def validate_fence(fence):
    """Fail loud (GateError → exit 2) on a fence whose shape would silently
    meter the wrong file set. An empty roots or a mistyped exclude does not
    raise on its own — it selects zero files and reports success, the one
    failure a governance gate must never have. Element types are checked too:
    a non-str in roots reaches Path.glob and raises TypeError, and one in
    exclude is str()-coerced into an exclusion that silently never matches."""
    if not isinstance(fence, dict):
        raise GateError('docs/tool-design.md: constants block has no governed_fence mapping')
    for key, typ in (('roots', list), ('exclude', list), ('glob', str), ('not_ignored', bool)):
        if key not in fence:
            raise GateError(f'docs/tool-design.md: governed_fence missing key: {key}')
        if not isinstance(fence[key], typ):
            raise GateError(f'docs/tool-design.md: governed_fence key {key!r} must be '
                            f'{typ.__name__}, got {type(fence[key]).__name__}')
    for key in ('roots', 'exclude'):
        for item in fence[key]:
            if not isinstance(item, str) or not item:
                raise GateError(f'docs/tool-design.md: governed_fence {key} entries must be '
                                f'non-empty strings, got {item!r}')
    if not fence['roots']:
        raise GateError('docs/tool-design.md: governed_fence roots is empty — '
                        'the form pass would check zero files and report success')


# ---- shared helpers ----

def strip_fences(lines):
    out, fence = [], None
    for ln in lines:
        m = FENCE_RE.match(ln)
        if fence:
            out.append('')
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
        elif m:
            fence = m.group(1)
            out.append('')
        else:
            out.append(ln)
    return out


def _display(p):
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


class Findings:
    def __init__(self):
        self.per_pass = {}

    def start(self, name):
        self.per_pass[name] = [0, 0]
        self._cur = self.per_pass[name]

    def error(self, loc, msg):
        self._cur[0] += 1
        print(f'ERROR {loc}: {msg}')

    def warn(self, loc, msg):
        self._cur[1] += 1
        print(f'WARN  {loc}: {msg}')

    def add(self, errors, warnings):
        self._cur[0] += errors
        self._cur[1] += warnings

    @property
    def errors(self):
        return sum(e for e, _ in self.per_pass.values())

    @property
    def warnings(self):
        return sum(w for _, w in self.per_pass.values())


# Both governed skill enumerations. A project skill under the meta-repo's
# .claude/skills/ is not a lighter class than a plugin skill — vrc-skills'
# CONVENTIONS.md "The gate" holds both to one anatomy; only the owning repo
# differs, which matters solely to the link check the child gate runs.
SKILL_FAMILIES = ('vrc-skills/skills', '.claude/skills')

# A family whose owning repo is present but whose directory is gone is corruption,
# not absence. Naming directories explicitly took that check away from the child
# gate (invoked bare, it raises "skills/ not found" and exits 2), so it has to be
# made here or a vanished vrc-skills/skills drops 14 skills and the run still
# scores clean. The meta-repo owns no such invariant: having no project skills at
# all is an ordinary state, so .claude/skills has no required marker.
FAMILY_REQUIRED_BY = {'vrc-skills/skills': 'vrc-skills'}


def all_skill_dirs():
    """Every candidate directory, unfiltered — so pass 1's child gate still gets
    to report a skill directory that has no SKILL.md at all."""
    families = []
    for fam in SKILL_FAMILIES:
        d = ROOT / fam
        if d.is_dir():
            families.append(d)
        elif (marker := FAMILY_REQUIRED_BY.get(fam)) and (ROOT / marker).is_dir():
            raise GateError(f'{marker} is present but {fam}/ is missing — the skill family '
                            'vanished; refusing to score the remaining families as a clean run')
    return sorted(p for f in families for p in f.iterdir() if p.is_dir())


def skill_dirs():
    """The subset that has a SKILL.md, for the passes that read one."""
    return [p for p in all_skill_dirs() if (p / 'SKILL.md').is_file()]


# ---- pass 1: the repo-local skill gate ----

# The contract validate_skills.py pins (its main/__main__ comments own it): exit 0
# clean/warnings, 1 findings + this summary line on stdout, 2 internal failure
# (traceback on stderr, never a partial summary). We trust the child's own tally
# and treat a missing summary, an inconsistent count, or exit 2 as an internal
# failure — never scoring a crashed gate as clean. Internal failure means GateError
# (exit 2), not out.error (exit 1): a crashed child gate is not a prose finding, and
# borrowing the findings code told every caller the docs were bad when the gate
# never ran. The cross-check below is sound only because the child guarantees one
# finding per line (its Findings._emit collapses whitespace) — without that, a
# newline in an authored skill name splits one finding into two ERROR lines and
# forges a tally mismatch out of an ordinary lint finding.
VALIDATE_SUMMARY_RE = re.compile(
    r'^validate_skills: \d+ skill\(s\), (\d+) error\(s\), (\d+) warning\(s\)\s*$')


def pass_validate(out):
    out.start('validate_skills')
    script = ROOT / 'vrc-skills' / 'tools' / 'validate_skills.py'
    if not script.is_file():
        # The gate lives in the sibling, so its absence also silences anatomy
        # checking for THIS repo's project skills — name that casualty, or the
        # run reads as a clean bill over skills nothing linted.
        local = [p for p in (ROOT / '.claude' / 'skills').glob('*') if p.is_dir()]
        casualty = (f'; {len(local)} .claude/skills/ skill(s) went unchecked' if local else '')
        print('NOTE  pass 1 (validate_skills): vrc-skills (or its tools/validate_skills.py) '
              f'absent — skipped{casualty}')
        return
    dirs = all_skill_dirs()
    if not dirs:
        print('NOTE  pass 1 (validate_skills): no governed skill directories — skipped')
        return
    # Name both enumerations rather than letting the child default to its own
    # skills/ — one invocation, so the single-summary contract below still holds.
    p = subprocess.run([sys.executable, str(script)] + [str(d) for d in dirs],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    rel = _display(script)
    out_lines = (p.stdout or '').splitlines()
    for line in out_lines + (p.stderr or '').splitlines():
        print(line)

    if p.returncode not in (0, 1):
        raise GateError(f'{rel}: exited {p.returncode} (internal failure — see stderr above)')
    summary = next((m for l in out_lines if (m := VALIDATE_SUMMARY_RE.match(l))), None)
    if summary is None:
        raise GateError(f'{rel}: exited {p.returncode} without its summary line — the gate '
                        'crashed mid-run (internal failure)')
    errs, warns = int(summary.group(1)), int(summary.group(2))
    seen_err = sum(1 for l in out_lines if l.startswith('ERROR'))
    seen_warn = sum(1 for l in out_lines if l.startswith('WARN'))
    if (errs > 0) != (p.returncode == 1) or errs != seen_err or warns != seen_warn:
        raise GateError(f'{rel}: summary ({errs}e/{warns}w at exit {p.returncode}) disagrees '
                        f'with its own emitted lines ({seen_err}e/{seen_warn}w) — internal '
                        'failure')
    out.add(errs, warns)


# ---- pass 2: doc pointers resolve in the meta-repo ----

def pass_doc_pointers(out, exempt, fence):
    out.start('doc-pointers')
    dirs = skill_dirs()
    if not dirs:
        print('NOTE  pass 2 (doc-pointers): no governed skill directories — skipped')
        return
    vrc_skills = ROOT / 'vrc-skills'
    known_names = ({p.name for p in (ROOT / 'docs').glob('*.md')} |
                   {p.name for p in ROOT.glob('*.md')} |
                   {p.name for p in vrc_skills.rglob('*.md') if '.git' not in p.parts})

    # Collect first, so the "is this per-tree scratch?" question is one batched
    # check-ignore rather than one per pointer.
    cited = []   # (rel, line, ref) in encounter order
    for d in dirs:
        if d.name in exempt:
            continue
        lines = strip_fences((d / 'SKILL.md').read_text(encoding='utf-8').splitlines())
        rel = _display(d / 'SKILL.md')
        seen = set()
        for i, ln in enumerate(lines, 1):
            refs = [t for t in BACKTICK_RE.findall(ln)
                    if MD_NAME_RE.match(t) or MD_PATH_RE.match(t)]
            refs += DOCS_REF_RE.findall(ln)
            for ref in refs:
                if ref in seen:
                    continue
                seen.add(ref)
                cited.append((rel, i, d, ref))

    # A pointer into a per-tree scratch path (docs/local/, test-output/) is
    # unresolvable by construction, not broken: those trees are untracked, so they
    # exist only in the tree that made them. Ask git that question directly rather
    # than reusing the form fence's exclude list — the fence answers "is this ours
    # to reflow", which is not the same question. references/ is excluded from the
    # fence yet references/README.md is tracked and cited by skills, so keying on
    # the fence would have silently stopped checking a live pointer.
    per_tree = git_ignored(ROOT, sorted({ref for _, _, _, ref in cited if '/' in ref}))

    for rel, i, d, ref in cited:
        if ref in per_tree:
            continue
        if '/' in ref:
            first = ref.split('/')[0]
            if first.startswith('vrc-') and not (ROOT / first).is_dir():
                continue  # sibling absent: not resolvable, not a finding
            if not any((base / ref).exists() for base in (ROOT, vrc_skills, d)):
                out.warn(f'{rel}:{i}', f"doc pointer '{ref}' does not resolve in the workspace")
        elif ref not in known_names:
            # Bare names resolve partly out of vrc-skills, so with the sibling
            # absent a miss says nothing about the pointer — same carve-out the
            # slash branch above makes, which this branch was missing.
            if not vrc_skills.is_dir():
                continue
            out.warn(f'{rel}:{i}', f"doc pointer '{ref}' matches no meta-repo doc, "
                                   f"root file, or vrc-skills file")


# ---- pass 3: Tools-section names appear in TOOLS.md ----

def pass_tool_names(out, exempt, terminal_section):
    out.start('tool-names')
    dirs = skill_dirs()
    tools_md = ROOT / 'TOOLS.md'
    if not dirs or not tools_md.is_file():
        print('NOTE  pass 3 (tool-names): no governed skill directories, or TOOLS.md '
              'absent — skipped')
        return
    roster_text = tools_md.read_text(encoding='utf-8')

    def resolves(tok):
        pat = re.escape(tok[:-1]) + r'[A-Za-z0-9_]*' if tok.endswith('*') else re.escape(tok)
        return re.search(r'\b' + pat + r'\b', roster_text)

    for d in dirs:
        if d.name in exempt:
            continue
        lines = strip_fences((d / 'SKILL.md').read_text(encoding='utf-8').splitlines())
        rel = _display(d / 'SKILL.md')
        heads = [(i, m.group(1)) for i, ln in enumerate(lines) if (m := H2_RE.match(ln))]
        start = next((i for i, t in reversed(heads)
                      if t == terminal_section or t.startswith(terminal_section + ' ')), None)
        if start is None:
            continue  # anatomy warning is pass 1's; nothing structured to check
        end = next((i for i, _ in heads if i > start), len(lines))
        for i in range(start + 1, end):
            m = TOOLS_BULLET_RE.match(lines[i])
            if not m:
                continue
            for tok in BACKTICK_RE.findall(m.group(1)):
                if TOOL_TOKEN_RE.match(tok) and not resolves(tok):
                    out.warn(f'{rel}:{i + 1}', f"Tools-section name '{tok}' not found in TOOLS.md")


# ---- pass 4: one-line-per-paragraph form over the governed fence ----

def git_ignored(repo, relpaths):
    """The subset of relpaths git would ignore in repo (check-ignore batch)."""
    if not relpaths:
        return set()
    p = subprocess.run(['git', '-C', str(repo), 'check-ignore', '--stdin', '-z'],
                       input='\0'.join(relpaths), capture_output=True, text=True,
                       encoding='utf-8')
    if p.returncode > 1:
        raise GateError(f'git check-ignore failed in {repo}: {p.stderr.strip()}')
    return {x for x in p.stdout.split('\0') if x}


def governed_md(repo, fence):
    # Every key is guaranteed present and typed by validate_fence, so these
    # subscript rather than defaulting — one spelling of the contract.
    excludes = tuple(e.rstrip('/') + '/' for e in fence['exclude'])
    glob_pat = fence['glob']
    # Pre-prune ignored top-level dirs so the walk never enters the big
    # untracked venues (Unity projects, reference clones).
    top = [p.name for p in repo.iterdir() if p.is_dir() and p.name != '.git']
    top_ignored = git_ignored(repo, top) if fence['not_ignored'] else set()

    rels = []
    for dirpath, dirnames, filenames in os.walk(repo):
        base = Path(dirpath).relative_to(repo).as_posix()
        base = '' if base == '.' else base + '/'
        dirnames[:] = [dn for dn in dirnames
                       if dn != '.git' and not (base + dn + '/').startswith(excludes)
                       and not (base == '' and dn in top_ignored)]
        for fn in filenames:
            rel = base + fn
            if fnmatch_md(rel, glob_pat) and not rel.startswith(excludes):
                rels.append(rel)
    if fence['not_ignored']:
        dropped = git_ignored(repo, rels)
        rels = [r for r in rels if r not in dropped]
    return [repo / r for r in rels]


def fnmatch_md(rel, pat):
    import fnmatch
    # "**/" also matches zero directories (glob semantics fnmatch lacks).
    return fnmatch.fnmatch(rel, pat) or (pat.startswith('**/') and fnmatch.fnmatch(rel, pat[3:]))


def pass_form(out, fence):
    out.start('form')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import reflow_md

    files = []
    for pat in fence['roots']:
        repos = [ROOT] if pat == '.' else sorted(p for p in ROOT.glob(pat) if p.is_dir())
        if not repos:
            print(f'NOTE  pass 4 (form): no sibling matches root "{pat}" — skipped')
        for repo in repos:
            if not (repo / '.git').exists():
                print(f'NOTE  pass 4 (form): {_display(repo)} is not a git repo — skipped')
                continue
            files += governed_md(repo, fence)

    for f in sorted(set(files)):
        try:
            src, res, _ = reflow_md._reflow_file_content(f)
        except reflow_md.ReflowError as e:
            out.error(_display(f), f'reflow refused: {e}')
            continue
        except UnicodeDecodeError as e:
            out.error(_display(f), f'not valid UTF-8: {e}')
            continue
        if src != res:
            out.error(_display(f), 'not one-line-per-paragraph (run tools/reflow_md.py on it)')
    if not files:
        # Zero files is never a real workspace: this repo's own .md is always in
        # the fence. Reporting "0 checked, no findings" would pass the gate by
        # measuring nothing.
        raise GateError('the governed fence resolved zero files — check the '
                        'governed_fence constants in docs/tool-design.md')
    print(f'form: {len(set(files))} governed file(s) checked')


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # findings quote UTF-8 prose

    # Checked before any pass: read_constants needs yaml, and so does the child
    # gate pass 1 subprocesses, whose exit-2 would otherwise surface ahead of the
    # real cause.
    if yaml is None:
        raise GateError('pyyaml not installed — pip install pyyaml '
                        '(prerequisite: docs/bootstrap.md §2)')

    out = Findings()
    exempt, terminal = [], 'Tools'
    conv = ROOT / 'vrc-skills' / 'CONVENTIONS.md'
    if conv.is_file():
        consts = read_constants(conv, 'description_prefix')
        exempt = consts.get('exempt_skills', [])
        terminal = consts.get('terminal_section', terminal)
    consts_fence = read_constants(ROOT / 'docs' / 'tool-design.md', 'governed_fence')
    # Bare subscripting would raise KeyError and exit 1, which this module
    # reserves for lint findings; a malformed constants block is an internal
    # failure (exit 2), same as a missing one.
    fence = consts_fence.get('governed_fence')
    validate_fence(fence)
    pass_doc_pointers(out, exempt, fence)
    pass_tool_names(out, exempt, terminal)
    pass_form(out, fence)
    # Pass 1 runs last precisely because it is the one that can abort the run:
    # its internal failures raise (exit 2), and a maintainer with a half-refactored
    # vrc-skills checkout still needs passes 2-4 to adjudicate the doc edits they
    # actually made. Nothing else orders these — the yaml check above is the only
    # real precondition. Cost: pass 1's output prints after the others'.
    pass_validate(out)

    per = ', '.join(f'{name} {e}/{w}' for name, (e, w) in out.per_pass.items())
    print(f'check_prose: {out.errors} error(s), {out.warnings} warning(s) [{per} (errors/warnings)]')
    return 1 if out.errors else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except GateError as e:
        sys.stderr.write(f'error: {e}\n')
        sys.exit(2)
    except Exception:
        # Exit 1 means "lint findings"; an unhandled crash must not borrow that
        # code and read as a prose problem. Mirrors validate_skills.py.
        import traceback
        traceback.print_exc()
        sys.exit(2)
