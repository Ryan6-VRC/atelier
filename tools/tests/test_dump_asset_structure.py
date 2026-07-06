# tools/tests/test_dump_asset_structure.py
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dump_asset_structure as d  # noqa: E402


class TestCounts(unittest.TestCase):
    def test_ext_counts_excludes_meta_and_labels_extensionless(self):
        c = d.ext_counts(["a.png", "a.png.meta", "b.PNG", "README", "x.mat"])
        self.assertEqual(c[".png"], 2)        # case-folded
        self.assertEqual(c[".mat"], 1)
        self.assertEqual(c["(no ext)"], 1)
        self.assertNotIn(".meta", c)

    def test_format_counts_sorted_and_empty(self):
        from collections import Counter
        self.assertEqual(d.format_counts(Counter()), "")
        self.assertEqual(
            d.format_counts(Counter({".png": 2, ".mat": 1})),
            "1 .mat, 2 .png",
        )


class TestRender(unittest.TestCase):
    def _tree(self):
        # rel-posix dir -> {"files":[...], "subdirs":[...]}
        return {
            "Assets": {"files": ["csc.rsp"], "subdirs": ["Assets/Avatars", "Assets/Vendor"]},
            "Assets/Avatars": {"files": [], "subdirs": ["Assets/Avatars/Chocolat"]},
            "Assets/Avatars/Chocolat": {"files": ["Chocolat.prefab"], "subdirs": ["Assets/Avatars/Chocolat/Models"]},
            "Assets/Avatars/Chocolat/Models": {"files": ["Chocolat.fbx", "Chocolat.fbx.meta"], "subdirs": []},
            "Assets/Vendor": {"files": [], "subdirs": ["Assets/Vendor/Avatars"]},
            "Assets/Vendor/Avatars": {"files": [], "subdirs": ["Assets/Vendor/Avatars/Chocolat"]},
            "Assets/Vendor/Avatars/Chocolat": {"files": ["c.fbx"], "subdirs": ["Assets/Vendor/Avatars/Chocolat/Textures"]},
            "Assets/Vendor/Avatars/Chocolat/Textures": {"files": ["t1.png", "t1.png.meta", "t2.png"], "subdirs": []},
        }

    def test_tracked_tree_full_depth_local_counts(self):
        lines = d.render(self._tree(), "Assets", ignored_roots=set())
        text = "\n".join(lines)
        self.assertIn("Assets/", text)
        self.assertIn("Models/   1 .fbx", text)            # local, .meta excluded
        self.assertIn("Chocolat/   1 .prefab", text)       # nested file shows via its dir's counts
        self.assertNotIn("(gitignored)", text)
        self.assertNotIn("(recursive)", text)

    def test_ignored_truncated_at_depth_2_with_recursive_rollup(self):
        lines = d.render(self._tree(), "Assets", ignored_roots={"Assets/Vendor"})
        text = "\n".join(lines)
        self.assertIn("Vendor/  (gitignored)", text)
        # Chocolat is depth 2 under Vendor -> recursive rollup, no deeper recursion
        self.assertIn("Chocolat/   1 .fbx, 2 .png   (recursive)", text)
        self.assertNotIn("Textures/", text)                # truncated below depth 2

    def test_marker_only_on_topmost(self):
        lines = d.render(self._tree(), "Assets", ignored_roots={"Assets/Vendor"})
        # exactly one (gitignored) marker even though many dirs are under Vendor
        self.assertEqual("\n".join(lines).count("(gitignored)"), 1)

    def test_render_is_deterministic(self):
        a = d.render(self._tree(), "Assets", ignored_roots={"Assets/Vendor"})
        b = d.render(self._tree(), "Assets", ignored_roots={"Assets/Vendor"})
        self.assertEqual(a, b)


class TestCollectAndGenerate(unittest.TestCase):
    def test_collect_reads_fixture(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            (proj / "Assets" / "Avatars" / "X").mkdir(parents=True)
            (proj / "Assets" / "csc.rsp").write_text("x")
            (proj / "Assets" / "Avatars" / "X" / "x.fbx").write_text("x")
            # created in non-sorted order to prove collect sorts subdirs
            for name in ("b", "A", "c"):
                (proj / "Assets" / "Avatars" / "X" / name).mkdir()
            tree = d.collect(proj / "Assets", proj)
            self.assertIn("Assets", tree)
            self.assertIn("Assets/Avatars/X", tree)
            self.assertIn("x.fbx", tree["Assets/Avatars/X"]["files"])
            self.assertEqual(
                tree["Assets/Avatars/X"]["subdirs"],
                ["Assets/Avatars/X/A", "Assets/Avatars/X/b", "Assets/Avatars/X/c"],
            )

    def test_recursive_counts_sums_subtree(self):
        tree = {
            "Assets/V": {"files": ["a.png", "a.png.meta"], "subdirs": ["Assets/V/W"]},
            "Assets/V/W": {"files": ["b.png", "c.mat"], "subdirs": []},
        }
        c = d.recursive_counts(tree, "Assets/V")
        self.assertEqual(c[".png"], 2)
        self.assertEqual(c[".mat"], 1)

    def test_generate_missing_assets_exits(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                d.generate(Path(tmp))   # no Assets/ subdir


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True)


class TestGitAdapter(unittest.TestCase):
    def _repo_with_vendor(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proj = Path(tmp)
        _git(["init"], tmp)
        (proj / ".gitignore").write_text("/Assets/Vendor/\n", encoding="utf-8")
        for sub in ["Assets/Avatars/X", "Assets/Vendor/Avatars/Y/Tex"]:
            (proj / sub).mkdir(parents=True)
        return proj

    def test_topmost_only(self):
        proj = self._repo_with_vendor()
        dirs = ["Assets/Avatars/X", "Assets/Vendor",
                "Assets/Vendor/Avatars", "Assets/Vendor/Avatars/Y"]
        roots = d.get_ignored_roots(proj, dirs)
        self.assertEqual(roots, {"Assets/Vendor"})  # no descendants

    def test_nothing_ignored_is_not_an_error(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        _git(["init"], tmp)
        (Path(tmp) / "Assets" / "Avatars").mkdir(parents=True)
        roots = d.get_ignored_roots(Path(tmp), ["Assets/Avatars"])
        self.assertEqual(roots, set())  # check-ignore exits 1, handled

    def test_not_a_repo_fails_loudly(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        # no git init -> git check-ignore exits 128
        with self.assertRaises(SystemExit):
            d.get_ignored_roots(Path(tmp), ["Assets/Whatever"])


class TestCliWriteAndCheck(unittest.TestCase):
    def _project(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proj = Path(tmp)
        _git(["init"], tmp)
        (proj / ".gitignore").write_text("/Assets/Vendor/\n", encoding="utf-8")
        (proj / "Assets" / "Avatars" / "X").mkdir(parents=True)
        (proj / "Assets" / "Avatars" / "X" / "x.fbx").write_text("x")
        return proj

    def test_write_is_utf8_lf_and_idempotent(self):
        proj = self._project()
        d.main([str(proj)])
        raw = (proj / "STRUCTURE.md").read_bytes()
        self.assertNotIn(b"\r\n", raw)                 # LF only
        self.assertEqual(raw.decode("utf-8"), d.generate(proj))  # idempotent
        d.main([str(proj)])                            # second run...
        self.assertEqual((proj / "STRUCTURE.md").read_bytes(), raw)  # ...no change

    def test_check_detects_stale(self):
        proj = self._project()
        d.main([str(proj)])
        (proj / "STRUCTURE.md").write_text("stale\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            d.main([str(proj), "--check"])


REAL_AVATARPROJECT = Path(__file__).resolve().parents[2] / "AvatarProject"


class TestRealData(unittest.TestCase):
    @unittest.skipUnless(REAL_AVATARPROJECT.exists(), "AvatarProject not present")
    def test_real_avatarproject_truncates_vendor(self):
        # generate() must be pure: capture STRUCTURE.md before/after and assert it is
        # untouched, whether or not the project already has a committed snapshot.
        snap = REAL_AVATARPROJECT / "STRUCTURE.md"
        before = snap.read_bytes() if snap.exists() else None
        body = d.generate(REAL_AVATARPROJECT)
        after = snap.read_bytes() if snap.exists() else None
        self.assertIn("Vendor/  (gitignored)", body)
        self.assertIn("(recursive)", body)
        self.assertEqual(before, after,
                         "generate() must not create or modify STRUCTURE.md")


if __name__ == "__main__":
    unittest.main()
