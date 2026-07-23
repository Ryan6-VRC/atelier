# tools/reflow_md.py
"""Reflow markdown prose to one line per paragraph, and gate that it stays that way.

The workspace convention (CLAUDE.md, "Writing for agents"): prose wraps at
paragraph boundaries, not at a column. Each paragraph and each list item is a
single physical line; editors soft-wrap for display. A mid-paragraph edit then
touches one line instead of reflowing a block, so diffs stay minimal under
"update, don't add".

This tool both establishes and enforces that form:

  reflow_md.py FILE...           reflow the given files in place
  reflow_md.py --check FILE...   exit non-zero if any file is not already
                                 canonical; write nothing (the CI/pre-commit gate)

Because the reflow is idempotent, "already canonical" == reflow(f) == f, so the
same function defines the form and checks it. Every write is guarded twice: the
whitespace-collapsed token stream must be unchanged (no word added/removed/
reordered/altered), AND the result must be a fixed point of reflow (reflow(res)
== res) — either failing aborts loud, naming the file, rather than writing a
corrupted or non-canonical result.

These guards make word loss impossible and non-canonical output impossible; they
do NOT prove no *structural* mis-join. Joining lines is token-invariant, so an
unusual construct the classifier below doesn't recognize could in principle be
joined wrongly while both guards pass — a change that alters rendering, never
content, and so shows up in the reflow's diff. `--check` is therefore a strong
gate, not a proof: review the one-time repo-wide reflow diff; trust the gate for
steady-state edits.

Byte-preserved: fenced code (any delimiter run length; an inner shorter run does
not close an outer longer one) and indented (4-space) code; raw-text HTML
elements (<pre>/<script>/<style>/<textarea>) and any line opening an HTML block;
table rows (any line with '|'); blockquotes; ATX and setext headings; thematic
breaks; link/footnote reference definitions ([label]: / [^id]:); YAML
front-matter (only when properly terminated); and hard-break lines (trailing two
spaces / backslash). The file's existing newline style (LF/CRLF) is preserved.

Pass an explicit tracked-file list, never a directory — scope is then exact and
never descends into gitignored/vendor/reference trees (the -z/-0 pair is
space-safe for paths containing spaces):

  git ls-files -z '*.md' | xargs -0 python tools/reflow_md.py --check
"""
import argparse
import re
import sys
from pathlib import Path

LIST_RE = re.compile(r'^(\s*)([-*+]|\d+[.)])\s+\S')
FENCE_OPEN_RE = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
HEADING_RE = re.compile(r'^\s{0,3}#{1,6}(\s|$)')
HR_RE = re.compile(r'^\s{0,3}([-*_])(\s*\1){2,}\s*$')
SETEXT_RE = re.compile(r'^\s{0,3}(=+|-+)\s*$')          # a setext underline / dash rule, alone on its line
INDENT_CODE_RE = re.compile(r'^(\t| {4,})')
DEF_RE = re.compile(r'^\s{0,3}\[\^?[^\]]+\]:\s')        # [label]: url  |  [^id]: footnote text
HTML_RAW_OPEN_RE = re.compile(r'^\s{0,3}<(pre|script|style|textarea)[\s/>]', re.IGNORECASE)


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
    if SETEXT_RE.match(line):        # ===  /  --- underline or dash rule
        return True
    if '|' in line:                  # table row (conservative: never join across a pipe)
        return True
    if s.startswith('>'):            # blockquote
        return True
    if s.startswith('<'):            # HTML block / tag / comment / autolink at line start
        return True
    if DEF_RE.match(line):           # link / footnote reference definition
        return True
    if INDENT_CODE_RE.match(line):
        return True
    return False


def _is_hardbreak(line):
    return line.endswith('  ') or line.rstrip('\n').endswith('\\')


def _fence_close(line, ch, length):
    """A closing fence: >= `length` of the SAME char `ch`, <=3 indent, nothing
    but whitespace after (a closing fence carries no info string)."""
    m = re.match(r'^\s{0,3}(' + re.escape(ch) + r'+)[ \t]*$', line)
    return bool(m) and len(m.group(1)) >= length


def reflow(text):
    """Collapse continuation lines within prose paragraphs and list items to one
    physical line each; leave every non-prose block byte-identical. Operates on
    LF-normalized text (caller restores the original newline)."""
    lines = text.split('\n')
    out = []
    i = 0
    n = len(lines)

    # YAML front-matter passthrough — only when a real terminator exists at col 0.
    if n and lines[0] == '---':
        close = next((k for k in range(1, n) if lines[k] in ('---', '...')), None)
        if close is not None:
            out.extend(lines[:close + 1])
            i = close + 1

    while i < n:
        line = lines[i]

        # Fenced code: verbatim until a matching-or-longer close of the same char.
        fo = FENCE_OPEN_RE.match(line)
        if fo:
            seq = fo.group(1)
            ch, length = seq[0], len(seq)
            out.append(line)
            i += 1
            while i < n:
                out.append(lines[i])
                closed = _fence_close(lines[i], ch, length)
                i += 1
                if closed:
                    break
            continue

        # Raw-text HTML element: verbatim until its close tag.
        ho = HTML_RAW_OPEN_RE.match(line)
        if ho:
            tag = ho.group(1).lower()
            close_re = re.compile(r'</' + tag + r'>', re.IGNORECASE)
            out.append(line)
            done = bool(close_re.search(line))
            i += 1
            while not done and i < n:
                out.append(lines[i])
                done = bool(close_re.search(lines[i]))
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
            if _is_special_standalone(nxt):       # heading/hr/setext/table/quote/html/def/indent-code
                break
            if FENCE_OPEN_RE.match(nxt):
                break
            if LIST_RE.match(nxt):                # a new list item ends the current one
                break
            if _is_hardbreak(nxt):                # a hard break must keep its own line
                break
            acc = acc.rstrip() + ' ' + nxt.strip()
            i += 1
        out.append(acc)
    return '\n'.join(out)


def _reflow_file_content(path):
    """Return (original_text_LF, reflowed_text_LF, newline). Reads bytes so the
    file's newline style is known and preserved. Guards the result twice: token
    preservation, then idempotency — either failing raises a named ReflowError
    rather than emitting a corrupted or non-canonical file."""
    data = path.read_bytes()
    newline = '\r\n' if b'\r\n' in data else '\n'
    src = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    res = reflow(src)
    if src.split() != res.split():
        a, b = src.split(), res.split()
        where = next((f'token {k}: {a[k]!r} vs {b[k]!r}'
                      for k in range(min(len(a), len(b))) if a[k] != b[k]),
                     f'length {len(a)} vs {len(b)}')
        raise ReflowError(f'{path}: reflow would alter content ({where}) — refusing')
    if reflow(res) != res:
        raise ReflowError(f'{path}: reflow is not idempotent here (unhandled construct) — refusing')
    return src, res, newline


def main(argv=None):
    ap = argparse.ArgumentParser(description='Reflow markdown to one line per paragraph.')
    ap.add_argument('paths', nargs='+', help='markdown files (pass an explicit list, e.g. via git ls-files)')
    ap.add_argument('--check', action='store_true',
                    help='verify canonical form; write nothing; exit non-zero on drift')
    args = ap.parse_args(argv)

    drifted = []
    wrote = 0
    for name in args.paths:
        f = Path(name)
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
