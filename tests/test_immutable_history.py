import json
import shutil
from pathlib import Path

from scripts.verify_immutable_history import DEFAULT_MANIFEST, verify


def copy_legacy_tree(destination: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    for directory in ("dashboard/history", "data/snapshots"):
        shutil.copytree(root / directory, destination / directory)


def test_repository_legacy_files_match_manifest():
    assert verify() == []


def test_modified_legacy_file_is_rejected(tmp_path):
    copy_legacy_tree(tmp_path)
    target = tmp_path / "dashboard/history/2026-07-19.html"
    target.write_bytes(target.read_bytes() + b"tampered")
    errors = verify(DEFAULT_MANIFEST, tmp_path)
    assert any("Hash mismatch" in error for error in errors)


def test_unregistered_legacy_file_is_rejected(tmp_path):
    copy_legacy_tree(tmp_path)
    (tmp_path / "data/snapshots/unregistered.xlsx").write_bytes(b"new")
    errors = verify(DEFAULT_MANIFEST, tmp_path)
    assert any("Unregistered file" in error for error in errors)
