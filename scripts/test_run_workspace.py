import json
import contextlib
import io
import os
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import manage_run_workspace as workspace
from manage_run_workspace import WorkspaceError, cleanup_run_directory, create_run_directory


class RunWorkspaceTests(unittest.TestCase):
    def test_create_cli_emits_ascii_safe_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(workspace.main(["create"]), 0)
        raw = output.getvalue()
        self.assertTrue(raw.isascii())
        run_dir = Path(json.loads(raw)["run_dir"])
        self.assertTrue(cleanup_run_directory(run_dir))

    def test_create_and_cleanup_round_trip(self):
        run_dir = create_run_directory()
        (run_dir / "candidate.png").write_bytes(b"temporary")

        self.assertTrue(cleanup_run_directory(run_dir))
        self.assertFalse(run_dir.exists())
        self.assertFalse(cleanup_run_directory(run_dir))

    def test_concurrent_cleanup_claims_directory_once(self):
        run_dir = create_run_directory()
        barrier = threading.Barrier(2)
        original_validate = workspace._validated_run_directory

        def synchronized_validate(path):
            result = original_validate(path)
            barrier.wait(timeout=5)
            return result

        with patch.object(workspace, "_validated_run_directory", side_effect=synchronized_validate):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(cleanup_run_directory, (run_dir, run_dir)))

        self.assertEqual(sorted(results), [False, True])
        self.assertFalse(run_dir.exists())

    def test_revalidates_after_atomic_claim(self):
        run_dir = create_run_directory()
        outside = Path(tempfile.mkdtemp(prefix="bridge-two-images-outside-"))
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        original_rename = os.rename
        original_copy = None
        calls = 0

        def replace_with_link(source, destination):
            nonlocal calls, original_copy
            calls += 1
            if calls > 1:
                return original_rename(source, destination)
            original_copy = Path(str(destination) + "-original")
            original_rename(source, original_copy)
            try:
                try:
                    os.symlink(outside, source, target_is_directory=True)
                except OSError:
                    completed = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(source), str(outside)],
                        capture_output=True,
                        text=True,
                        errors="replace",
                    )
                    if completed.returncode != 0:
                        raise OSError(completed.stderr or completed.stdout)
                original_rename(source, destination)
            except OSError as exc:
                self.skipTest(f"Directory symlinks are unavailable: {exc}")

        try:
            with patch.object(workspace.os, "rename", side_effect=replace_with_link):
                with self.assertRaises(WorkspaceError):
                    cleanup_run_directory(run_dir)
            self.assertEqual((outside / "keep.txt").read_text(encoding="utf-8"), "keep")
        finally:
            if os.path.lexists(run_dir):
                if run_dir.is_symlink():
                    run_dir.unlink()
                elif run_dir.resolve() == outside.resolve():
                    os.rmdir(run_dir)
                else:
                    workspace.shutil.rmtree(run_dir)
            if original_copy and original_copy.exists():
                workspace.shutil.rmtree(original_copy)
            workspace.shutil.rmtree(outside)

    def test_refuses_tampered_marker(self):
        run_dir = create_run_directory()
        marker = run_dir / workspace.MARKER_NAME
        marker.write_text(json.dumps({"kind": "forged"}), encoding="utf-8")
        try:
            with self.assertRaises(WorkspaceError):
                cleanup_run_directory(run_dir)
        finally:
            workspace.shutil.rmtree(run_dir)


if __name__ == "__main__":
    unittest.main()
