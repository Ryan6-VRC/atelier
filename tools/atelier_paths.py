# tools/atelier_paths.py
"""The canonical "find the main checkout" resolver (Python). Run as a script it prints the
resolved path — the door for non-Python consumers (.githooks/pre-commit), so sh never carries
its own copy of the git incantation. The PowerShell twin is Get-AtelierMainCheckout in
tools/test-venue-common.ps1: same invariant (canon here), deliberately different failure
contract — it returns $null so provisioning callers can refuse loud and name the parameter to
pass, where this module's consumers (tests, commit gates) want best-effort with the fallback
made visible."""
import subprocess
import sys
from pathlib import Path

OWN_TREE = Path(__file__).resolve().parent.parent


def resolve() -> tuple:
    """(main checkout, fell_back). The main checkout is where the gitignored `vrc-*` siblings
    and `docs/local/` actually live; a linked worktree carries only tracked files, so a check
    that looks beside its own tree silently degrades there.

    Mechanism: `--git-common-dir` points at the main tree's `.git` from any linked worktree,
    and resolves to the tree's own `.git` in the main tree — so its parent is the main
    checkout in both. `--path-format=absolute` is load-bearing, not decoration: plain
    `--git-common-dir` answers a bare relative ".git" from the main tree (measured, git 2.54),
    which a parent-join would resolve against the caller's cwd rather than the repo. The query
    is anchored on this file's tree (cwd=OWN_TREE), not wherever the caller stands.

    The parent must itself hold a `.git` (file or dir): under `--separate-git-dir`, or in a
    worktree of a bare repo, the common dir's parent is a real directory that is NOT a
    checkout, and answering it would point every sibling read at a stranger's directory.
    Those layouts — like any git failure — fall back to this tree, i.e. to the pre-resolver
    behavior. fell_back=True marks every fallback so consumers can say so instead of
    presenting a degraded run as the resolved one (check_prose prints it)."""
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             cwd=OWN_TREE, capture_output=True, text=True, check=True)
        parent = Path(out.stdout.strip()).parent
    except (OSError, subprocess.CalledProcessError, ValueError):
        return OWN_TREE, True
    if not (parent / ".git").exists():
        return OWN_TREE, True
    return parent, False


def main_checkout() -> Path:
    """resolve() for the callers that only want the path."""
    return resolve()[0]


if __name__ == "__main__":
    # as_posix: sh callers compare this against `git rev-parse --show-toplevel`,
    # which prints forward slashes on Windows.
    print(main_checkout().as_posix())
    sys.exit(0)
