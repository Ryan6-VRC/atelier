# tools/atelier_paths.py
"""The canonical "find the main checkout" resolver (Python). Run as a script it prints the
resolved path — the door for non-Python consumers (.githooks/pre-commit), so sh never carries
its own copy of the git incantation. The PowerShell twin is Get-AtelierMainCheckout in
tools/test-venue-common.ps1: same invariant (canon here), deliberately different failure
contract — it returns $null so provisioning callers can refuse loud and name the parameter to
pass, where this module's consumers (tests, commit gates) want best-effort with the fallback
made visible."""
import os
import subprocess
import sys
from pathlib import Path

OWN_TREE = Path(__file__).resolve().parent.parent

# Repo-identity env, scrubbed before every git call: git prefers these over discovery, and a
# pre-commit hook (or `git bisect run`) exports them — under an inherited GIT_DIR the query
# would answer for the exporting repo no matter what cwd says. Same hazard, same list as
# check_prose.git_ignored.
_SCRUB = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
          'GIT_OBJECT_DIRECTORY', 'GIT_CEILING_DIRECTORIES')


def _common_dir(cwd, env) -> Path:
    out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         cwd=cwd, capture_output=True, text=True, check=True, env=env)
    return Path(out.stdout.strip())


def resolve() -> tuple:
    """(main checkout, fell_back). The main checkout is where everything a linked worktree
    doesn't carry actually lives: the gitignored `vrc-*` siblings, the untracked working
    venues (AvatarProject and any personal ones), and `docs/local/`. A check that looks
    beside its own tree silently degrades there.

    Mechanism: `--git-common-dir` points at the main tree's `.git` from any linked worktree,
    and resolves to the tree's own `.git` in the main tree — so its parent is the main
    checkout in both. `--path-format=absolute` is load-bearing, not decoration: plain
    `--git-common-dir` answers a bare relative ".git" from the main tree (measured, git 2.54),
    which a parent-join would resolve against the caller's cwd rather than the repo. The query
    is anchored on this file's tree (cwd=OWN_TREE), not wherever the caller stands.

    The answer is authenticated, not assumed: the parent directory's own repo must name the
    same common dir back. A bare `.git`-exists check is not identity — under
    `--separate-git-dir` the common dir's parent can be an unrelated checkout, and answering
    it would point every sibling read (and pass 1's subprocess) at a stranger's tree. Layouts
    that fail the round-trip — like any git failure — fall back to this tree, i.e. to the
    pre-resolver behavior. fell_back=True marks every fallback so consumers can say so
    instead of presenting a degraded run as the resolved one (check_prose prints it; the CLI
    door exits 3)."""
    env = {k: v for k, v in os.environ.items() if k not in _SCRUB}
    try:
        common = _common_dir(OWN_TREE, env)
        parent = common.parent
        if _common_dir(parent, env) != common:
            return OWN_TREE, True
    except (OSError, subprocess.CalledProcessError, ValueError):
        return OWN_TREE, True
    return parent, False


def main_checkout() -> Path:
    """resolve() for the callers that only want the path."""
    return resolve()[0]


if __name__ == "__main__":
    # as_posix: sh callers compare this against `git rev-parse --show-toplevel`,
    # which prints forward slashes on Windows. Exit 3 on fallback — the printed
    # path is then this tree, and an sh caller treating it as the main checkout
    # would both misreport the cause and, worse, take the main-tree write path
    # inside a worktree.
    path, fell_back = resolve()
    print(path.as_posix())
    sys.exit(3 if fell_back else 0)
