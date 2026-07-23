# tools/reflow_md.py
"""Reflow markdown prose to one line per paragraph, and gate that it stays that way.

The workspace convention (CLAUDE.md, "Writing for agents"): prose wraps at
paragraph boundaries, not at a column. Each paragraph and each list item is a
single physical line; editors soft-wrap for display. A mid-paragraph edit then
touches one line instead of reflowing a block, so diffs stay minimal under
"update, don't add".

This tool both establishes and enforces that form:

  reflow_md.py PATH...            reflow in place (PATH = file, or dir -> recurse *.md)
  reflow_md.py --check PATH...    exit non-zero if any file is not already
                                  canonical; write nothing (the CI/pre-commit gate)

Because the reflow is idempotent, "already canonical" == reflow(f) == f, so the
same function defines the form and checks it. Byte-preserved: fenced/indented
code, table rows (any line with '|'), blockquotes, headings, HR, setext
underlines, YAML front-matter, and hard-break lines (trailing two spaces / '\\').
The file's existing newline style (LF/CRLF) is preserved.

Safety invariant, always asserted before any write: the whitespace-collapsed
token stream is unchanged -> only inter-token whitespace moved, no word was
added, removed, reordered, or altered. A violation aborts loud, naming the file,
rather than writing a corrupted result.

For a repo-wide gate, pass an explicit tracked-file list rather than a dir so
scope is exact and never surprises:  reflow_md.py --check $(git ls-files '*.md')
"""
import argparse
import re
import sys
from pathlib import Path

LIST_RE = re.compile(r'^(\s*)([-*+]|\d+[.)])\s+\S')
FENCE_RE = re.compile(r'^\s*(```|~~~)')
HEADING_RE = re.compile(r'^\s{0,3}#{1,6}(\s|$)')
HR_RE = re.compile(r'^\s{0,3}([-*_])(\s*\1){2,}\s*$')
SETEXT_RE = re.compile(r'^\s{0,3}(=+|-+)\s*$')
INDENT_CODE_RE = re.compile(r'^(\t| {4,})')

SKIP_DIRS = {'.git', 'node_modules'}


class ReflowError(Exception):
    """Fail-loud error; message names the offending file."""


def _is_special_standalone(line):
    """Lines that are their own logical line and never join with a neighbour."""
    s = line.strip()
    if s == '':
        return True
    if HEADING_RE.match(line):
        return True
    if HR_RE.match(line):
        return True
    if '|' in line:            # table row (conservative: never join across a pipe)
        return True
    if s.startswith('>'):      # blockquote
        return True
    if INDENT_CODE_RE.match(line):
        return True
    return False


def _is_hardbreak(line):
    return line.endswith('  ') or line.rstrip('\n').endswith('\\')


def reflow(text):
    """Collapse continuation lines within prose paragraphs and list items to one
    physical line each; leave every non-prose block byte-identical. Operates on
    LF-normalized text (caller restores the original newline)."""
    lines = text.split('\n')
    out = []
    i = 0
    n = len(lines)

    # YAML front-matter passthrough
    if n and lines[0].strip() == '---':
        out.append(lines[0])
        i = 1
        while i < n and lines[i].strip() != '---':
            out.append(lines[i])
            i += 1
        if i < n:
            out.append(lines[i])
            i += 1

    in_fence = False
    fence_tok = None
    while i < n:
        line = lines[i]
        m = FENCE_RE.match(line)
        if in_fence:
            out.append(line)
            if m and (fence_tok in line):
                in_fence = False
                fence_tok = None
            i += 1
            continue
        if m:
            in_fence = True
            fence_tok = m.group(1)
            out.append(line)
            i += 1
            continue

        if _is_special_standalone(line) or _is_hardbreak(line):
            out.append(line)
            i += 1
            continue

        # Start of a joinable logical line (paragraph OR list item).
        acc = line.rstrip()
        i += 1
        while i < n:
            nxt = lines[i]
            if nxt.strip() == '':                 # blank ends the block
                break
            if _is_special_standalone(nxt):       # heading/hr/table/quote/indent-code
                break
            if FENCE_RE.match(nxt):
                break
            if LIST_RE.match(nxt):                # a new list item ends the current one
                break
            if SETEXT_RE.match(nxt) and acc.strip():
                break
            if _is_hardbreak(acc):                # prior line forced a break
                break
            acc = acc.rstrip() + ' ' + nxt.strip()
            if _is_hardbreak(nxt):
                i += 1
                break
            i += 1
        out.append(acc)
    return '\n'.join(out)


def _reflow_file_content(path):
    """Return (original_text_LF, reflowed_text_LF, newline). Reads bytes so the
    file's newline style is known and preserved; asserts token preservation."""
    data = path.read_bytes()
    newline = '\r\n' if b'\r\n' in data else '\n'
    src = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    res = reflow(src)
    if src.split() != res.split():
        # Name the first divergence for a legible failure.
        a, b = src.split(), res.split()
        where = next((f'token {k}: {a[k]!r} vs {b[k]!r}'
                      for k in range(min(len(a), len(b))) if a[k] != b[k]),
                     f'length {len(a)} vs {len(b)}')
        raise ReflowError(f'{path}: reflow would alter content ({where}) — refusing')
    return src, res, newline


def _iter_md(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for f in sorted(p.rglob('*.md')):
                if any(part in SKIP_DIRS for part in f.parts):
                    continue
                yield f
        else:
            yield p


def main(argv=None):
    ap = argparse.ArgumentParser(description='Reflow markdown to one line per paragraph.')
    ap.add_argument('paths', nargs='+', help='markdown files, or dirs to recurse for *.md')
    ap.add_argument('--check', action='store_true',
                    help='verify canonical form; write nothing; exit non-zero on drift')
    args = ap.parse_args(argv)

    drifted = []
    wrote = 0
    for f in _iter_md(args.paths):
        src, res, newline = _reflow_file_content(f)
        if src == res:
            continue
        if args.check:
            drifted.append(f)
        else:
            f.write_bytes(res.replace('\n', newline).encode('utf-8'))
            wrote += 1

    if args.check:
        if drifted:
            sys.stderr.write('Not one-line-per-paragraph (run `reflow_md.py`):\n')
            for f in drifted:
                sys.stderr.write(f'  {f}\n')
            return 1
        return 0
    print(f'reflowed {wrote} file(s)')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ReflowError as e:
        sys.stderr.write(f'error: {e}\n')
        sys.exit(2)
