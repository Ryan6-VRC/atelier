# tools/check_prose.py
"""Workspace prose-governance check, run from the meta-repo root.

Four passes over the assembled workspace; a pass whose sibling repo is absent
skips with a printed NOTE (absence is a valid workspace state, never a failure):

  1. vrc-skills' own gate, tools/validate_skills.py (subprocess) — skill
     anatomy; its errors/warnings count here.
  2. Doc pointers: every docs-file reference in a SKILL.md resolves against the
     meta-repo (docs/ listing, root .md files, files in vrc-skills). WARN.
  3. Tool names, structured slot only: each leading bold-backticked name in a
     skill's "## Tools" bullets appears in TOOLS.md. WARN. Prose outside that
     slot is never scanned.
  4. Form: tools/reflow_md.py's --check over the governed fence — files
     enumerated from the governed_fence constants in docs/tool-design.md
     (roots, glob, exclude, check-ignore). ERROR on drift: the form gate is
     already the declared convention.

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

def _strip_comment(line):
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in '"\'':
            quote = ch
            out.append(ch)
        elif ch == '#':
            break
        else:
            out.append(ch)
    return ''.join(out).rstrip()


def _scalar(s):
    s = s.strip()
    if s[:1] in ('"', "'") and s.endswith(s[0]) and len(s) > 1:
        return s[1:-1]
    if s.lower() in ('true', 'false'):
        return s.lower() == 'true'
    try:
        return int(s)
    except ValueError:
        return s


def _value(v):
    if v.startswith('['):
        return [_scalar(x) for x in v.strip('[]').split(',') if x.strip()]
    if v.startswith('{'):
        d = {}
        for pair in v.strip('{}').split(','):
            if ':' in pair:
                k, pv = pair.split(':', 1)
                d[k.strip()] = _scalar(pv)
        return d
    return _scalar(v)


def _lenient_yaml(block):
    """Stdlib fallback: flat keys, one nesting level, inline [] / {} — enough
    for the constants blocks this reads."""
    root, child = {}, None
    for raw in block.splitlines():
        line = _strip_comment(raw)
        if not line.strip() or ':' not in line:
            continue
        indented = line[:1] in (' ', '\t')
        key, val = line.strip().split(':', 1)
        val = val.strip()
        target = child if (indented and child is not None) else root
        if val == '':
            target[key] = {}
            if not indented:
                child = target[key]
        else:
            target[key] = _value(val)
            if not indented:
                child = None
    return root


def read_constants(path, marker):
    if not path.is_file():
        raise GateError(f'{path}: not found — cannot read its constants block')
    text = path.read_text(encoding='utf-8')
    for block in re.findall(r'^\s{0,3}```ya?ml[^\n]*\n(.*?)^\s{0,3}```\s*$', text, re.M | re.S):
        if marker in block:
            return yaml.safe_load(block) if yaml else _lenient_yaml(block)
    raise GateError(f'{path}: no fenced yaml block containing "{marker}"')


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


def skill_dirs():
    skills = ROOT / 'vrc-skills' / 'skills'
    if not skills.is_dir():
        return []
    return sorted(p for p in skills.iterdir() if p.is_dir() and (p / 'SKILL.md').is_file())


# ---- pass 1: the repo-local skill gate ----

# The contract validate_skills.py pins (its main/__main__ comments own it): exit 0
# clean/warnings, 1 findings + this summary line on stdout, 2 internal failure
# (traceback on stderr, never a partial summary). We trust the child's own tally
# and treat a missing summary, an inconsistent count, or exit 2 as an internal
# failure — never scoring a crashed gate as clean.
VALIDATE_SUMMARY_RE = re.compile(
    r'^validate_skills: \d+ skill\(s\), (\d+) error\(s\), (\d+) warning\(s\)\s*$')


def pass_validate(out):
    out.start('validate_skills')
    script = ROOT / 'vrc-skills' / 'tools' / 'validate_skills.py'
    if not script.is_file():
        print('NOTE  pass 1 (validate_skills): vrc-skills (or its tools/validate_skills.py) '
              'absent — skipped')
        return
    p = subprocess.run([sys.executable, str(script)], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    rel = _display(script)
    out_lines = (p.stdout or '').splitlines()
    for line in out_lines + (p.stderr or '').splitlines():
        print(line)

    if p.returncode not in (0, 1):
        out.error(rel, f'exited {p.returncode} (internal failure — see stderr above)')
        return
    summary = next((m for l in out_lines if (m := VALIDATE_SUMMARY_RE.match(l))), None)
    if summary is None:
        out.error(rel, f'exited {p.returncode} without its summary line — the gate crashed '
                       'mid-run (internal failure)')
        return
    errs, warns = int(summary.group(1)), int(summary.group(2))
    seen_err = sum(1 for l in out_lines if l.startswith('ERROR'))
    seen_warn = sum(1 for l in out_lines if l.startswith('WARN'))
    if (errs > 0) != (p.returncode == 1) or errs != seen_err or warns != seen_warn:
        out.error(rel, f'summary ({errs}e/{warns}w at exit {p.returncode}) disagrees with its '
                       f'own emitted lines ({seen_err}e/{seen_warn}w) — internal failure')
        return
    out.add(errs, warns)


# ---- pass 2: doc pointers resolve in the meta-repo ----

def pass_doc_pointers(out, exempt):
    out.start('doc-pointers')
    dirs = skill_dirs()
    if not dirs:
        print('NOTE  pass 2 (doc-pointers): vrc-skills absent — skipped')
        return
    vrc_skills = ROOT / 'vrc-skills'
    known_names = ({p.name for p in (ROOT / 'docs').glob('*.md')} |
                   {p.name for p in ROOT.glob('*.md')} |
                   {p.name for p in vrc_skills.rglob('*.md') if '.git' not in p.parts})

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
                if '/' in ref:
                    first = ref.split('/')[0]
                    if first.startswith('vrc-') and not (ROOT / first).is_dir():
                        continue  # sibling absent: not resolvable, not a finding
                    if not any((base / ref).exists() for base in (ROOT, vrc_skills, d)):
                        out.warn(f'{rel}:{i}', f"doc pointer '{ref}' does not resolve in the workspace")
                elif ref not in known_names:
                    out.warn(f'{rel}:{i}', f"doc pointer '{ref}' matches no meta-repo doc, "
                                           f"root file, or vrc-skills file")


# ---- pass 3: Tools-section names appear in TOOLS.md ----

def pass_tool_names(out, exempt, terminal_section):
    out.start('tool-names')
    dirs = skill_dirs()
    tools_md = ROOT / 'TOOLS.md'
    if not dirs or not tools_md.is_file():
        print('NOTE  pass 3 (tool-names): vrc-skills or TOOLS.md absent — skipped')
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
    excludes = tuple(str(e).rstrip('/') + '/' for e in fence.get('exclude', []))
    glob_pat = str(fence.get('glob', '**/*.md'))
    # Pre-prune ignored top-level dirs so the walk never enters the big
    # untracked venues (Unity projects, reference clones).
    top = [p.name for p in repo.iterdir() if p.is_dir() and p.name != '.git']
    top_ignored = git_ignored(repo, top) if fence.get('not_ignored') else set()

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
    if fence.get('not_ignored'):
        dropped = git_ignored(repo, rels)
        rels = [r for r in rels if r not in dropped]
    return [repo / r for r in rels]


def fnmatch_md(rel, pat):
    import fnmatch
    # "**/" also matches zero directories (glob semantics fnmatch lacks).
    return fnmatch.fnmatch(rel, pat) or (pat.startswith('**/') and fnmatch.fnmatch(rel, pat[3:]))


def pass_form(out):
    out.start('form')
    fence = read_constants(ROOT / 'docs' / 'tool-design.md', 'governed_fence')['governed_fence']
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
    print(f'form: {len(set(files))} governed file(s) checked')


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # findings quote UTF-8 prose

    out = Findings()
    pass_validate(out)

    exempt, terminal = [], 'Tools'
    conv = ROOT / 'vrc-skills' / 'CONVENTIONS.md'
    if conv.is_file():
        consts = read_constants(conv, 'description_prefix')
        exempt = consts.get('exempt_skills', [])
        terminal = consts.get('terminal_section', terminal)
    pass_doc_pointers(out, exempt)
    pass_tool_names(out, exempt, terminal)
    pass_form(out)

    per = ', '.join(f'{name} {e}/{w}' for name, (e, w) in out.per_pass.items())
    print(f'check_prose: {out.errors} error(s), {out.warnings} warning(s) [{per} (errors/warnings)]')
    return 1 if out.errors else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except GateError as e:
        sys.stderr.write(f'error: {e}\n')
        sys.exit(2)
