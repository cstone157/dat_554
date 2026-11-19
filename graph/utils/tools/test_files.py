"""Tests for graph/utils/tools/files.py — all file-writing tools."""

import os
import textwrap
from pathlib import Path

import pytest

# Import the module under test so we can control PROJECT_FOLDER
from graph.utils.tools.files import (
    save_file,
    validate_path_within_project_folder,
    create_directory,
)


@pytest.fixture(autouse=True, scope="session")
def _set_project_folder(tmp_path_factory):
    """Create a temporary project root for all tests in this session."""
    base = tmp_path_factory.mktemp("project_root", numbered=False)
    # We need a module-level variable to control PROJECT_FOLDER.
    # Since the import binds the name at import time, we use monkeypatch.
    return base


class TestSaveFile:

    def test_returns_file_path_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = save_file("hello.txt", "world")
        assert result == str(tmp_path / "hello.txt")

    def test_writes_content_to_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        save_file("data.txt", "foo\nbar")
        assert (tmp_path / "data.txt").read_text() == "foo\nbar"

    def test_overwrites_existing_file(self, tmp_path, monkeypatch):
        existing = tmp_path / "dup.txt"
        existing.write_text("old")

        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        save_file("dup.txt", "new")
        assert existing.read_text() == "new"

    def test_creates_intermediate_directories(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        save_file("a/b/c/nested.txt", "deep content")
        assert (tmp_path / "a" / "b" / "c" / "nested.txt").read_text() == "deep content"

    def test_returns_error_when_project_folder_not_set(self, monkeypatch):
        monkeypatch.setattr("graph.utils.tools.files.PROJECT_FOLDER", None)
        result = save_file("anywhere.txt", "content")
        assert "Error: PROJECT_FOLDER is not set" in result

    def test_handles_absolute_path_input_normally(self, tmp_path, monkeypatch):
        """save_file does *not* validate paths; it simply joins with PROJECT_FOLDER.
        This tests that behaviour — the path is joined verbatim."""
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = save_file("nested/file.txt", "ok")
        assert (tmp_path / "nested" / "file.txt").read_text() == "ok"


class TestValidatePathWithinProjectFolder:

    def test_returns_error_when_project_folder_not_set(self, monkeypatch):
        monkeypatch.setattr("graph.utils.tools.files.PROJECT_FOLDER", None)
        result = validate_path_within_project_folder("anything")
        assert result == "Error: PROJECT_FOLDER is not set."

    def test_rejects_absolute_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        with pytest.raises(ValueError, match="Absolute paths are rejected"):
            validate_path_within_project_folder("/etc/passwd")

    def test_rejects_parent_traversal_escaping_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        with pytest.raises(ValueError, match="Path escapes PROJECT_FOLDER"):
            validate_path_within_project_folder("../../../etc/passwd")

    def test_rejects_nested_parent_traversal_escaping(self, tmp_path, monkeypatch):
        """Nested dir traversal that escapes the project root should be rejected."""
        sub = tmp_path / "sub"
        sub.mkdir()
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(sub)
        )
        with pytest.raises(ValueError, match="Path escapes PROJECT_FOLDER"):
            validate_path_within_project_folder("../other/secret")

    def test_accepts_relative_path_staying_within_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = validate_path_within_project_folder("hello.txt")
        assert result == str(tmp_path / "hello.txt")

    def test_accepts_nested_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = validate_path_within_project_folder("a/b/c/file.txt")
        assert result == str(tmp_path / "a" / "b" / "c" / "file.txt")

    def test_normpath_resolves_dots(self, tmp_path, monkeypatch):
        """Paths like './foo' should be normalised."""
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = validate_path_within_project_folder("./foo")
        assert result == str(tmp_path / "foo")

    def test_normpath_resolves_parent_refs(self, tmp_path, monkeypatch):
        """'a/../b/bar' normalises to 'b/bar'. Still within project → accepted."""
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        (tmp_path / "a").mkdir()
        result = validate_path_within_project_folder("a/../b/bar")
        assert result == str(tmp_path / "b" / "bar")

    def test_accepts_existing_directory_inside_project(self, tmp_path, monkeypatch):
        sub = tmp_path / "existing_dir"
        sub.mkdir()
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = validate_path_within_project_folder("existing_dir")
        assert result == str(sub)


class TestCreateDirectory:

    def test_creates_new_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = create_directory.func("new_dir")
        assert result == str(tmp_path / "new_dir")
        assert (tmp_path / "new_dir").is_dir()

    def test_creates_nested_directories(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = create_directory.func("a/b/c")
        assert result == str(tmp_path / "a" / "b" / "c")
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_is_idempotent_for_existing_directory(self, tmp_path, monkeypatch):
        existing = tmp_path / "existing"
        existing.mkdir()
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = create_directory.func("existing")
        assert result == str(existing)

    def test_rejects_absolute_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        with pytest.raises(ValueError, match="Absolute paths are rejected"):
            create_directory.func("/tmp/some_dir")

    def test_rejects_parent_traversal_escaping_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        with pytest.raises(ValueError, match="Path escapes PROJECT_FOLDER"):
            create_directory.func("../../../tmp")

    def test_rejects_nested_parent_traversal_escaping(self, tmp_path, monkeypatch):
        sub = tmp_path / "sub"
        sub.mkdir()
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(sub)
        )
        with pytest.raises(ValueError, match="Path escapes PROJECT_FOLDER"):
            create_directory.func("../other")

    def test_accepts_dot_slash_prefix(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "graph.utils.tools.files.PROJECT_FOLDER", str(tmp_path)
        )
        result = create_directory.func("./dot_dir")
        assert (tmp_path / "dot_dir").is_dir()
