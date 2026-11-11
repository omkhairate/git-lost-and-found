import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOL = Path(__file__).resolve().parents[1] / "git-lost-found"


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.org",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.org",
        }
        self.git("init", "-q")
        self.file("src/notes.txt", b"keep this context\nremove this phrase\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")

    def run_command(self, *args, cwd=None, check=True):
        return subprocess.run(
            args, cwd=cwd or self.repo, env=self.env, check=check, capture_output=True
        )

    def git(self, *args):
        return self.run_command("git", *args).stdout

    def tool(self, *args, **kwargs):
        return self.run_command(sys.executable, str(TOOL), *args, **kwargs)

    def file(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_search_and_export_dropped_stash(self):
        self.file("src/notes.txt", b"keep this context\nrecovered phrase\n")
        self.git("add", "src/notes.txt")
        self.file("src/notes.txt", b"keep this context\nrecovered phrase\nunstaged edit\n")
        self.file("new file.txt", b"untracked phrase\n")
        self.file("binary.dat", b"\x00\xff")
        self.git("stash", "push", "-u", "-m", "test stash")
        oid = self.git("rev-parse", "stash").decode().strip()
        self.assertEqual(self.tool("search", "recovered phrase", check=False).returncode, 1)
        self.git("stash", "drop")

        for query in ("recovered phrase", "remove this phrase", "untracked phrase"):
            result = self.tool("search", query, cwd=self.repo / "src")
            self.assertIn(oid.encode(), result.stdout)
        for query in ("keep this context", "src/notes.txt"):
            self.assertEqual(self.tool("search", query, check=False).returncode, 1)

        before = self.git("status", "--porcelain")
        preview = self.tool("show", oid[:12]).stdout
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.tool("show", oid, "-o", "restored.patch")
        patch_file = self.repo / "restored.patch"
        self.assertEqual(patch_file.read_bytes(), preview)
        self.assertEqual(self.tool("show", oid, "-o", "restored.patch", check=False).returncode, 2)
        self.assertEqual(patch_file.read_bytes(), preview)
        self.git("apply", "--check", "restored.patch")
        self.git("apply", "restored.patch")
        self.assertIn(b"unstaged edit", (self.repo / "src/notes.txt").read_bytes())
        self.assertEqual((self.repo / "new file.txt").read_bytes(), b"untracked phrase\n")
        self.assertEqual((self.repo / "binary.dat").read_bytes(), b"\x00\xff")

    def test_show_rejects_regular_commits(self):
        oid = self.git("rev-parse", "HEAD").decode().strip()
        result = self.tool("show", oid, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"not a recognized Git stash", result.stderr)


if __name__ == "__main__":
    unittest.main()
