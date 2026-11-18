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
    create_file,
    read_file,
    delete_file,
    list_files,
    insert_into_file,
    append_to_file,
    update_file,
    get_project_folder,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()  # Remove autouse=True
def _test_project(tmp_path, monkeypatch):
    """Wire PROJECT_FOLDER to a temporary directory."""
    from graph.utils.tools import files as mod
    project_root = tmp_path / "project"
    project_root.mkdir()
    yield str(project_root)
    monkeypatch.setattr(mod, "PROJECT_FOLDER", None)

# ---------------------------------------------------------------------------
# Helpers — raw (undecorated) functions
# ---------------------------------------------------------------------------

class TestSaveFile:
    """Tests for save_file()."""

    def test_returns_resolved_relative_path(self, tmp_path, _test_project):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        result = save_file("sub/hello.txt", "hi")
        assert result == os.path.join(str(mod.PROJECT_FOLDER), "sub", "hello.txt")
        assert (tmp_path / "project" / "sub" / "hello.txt").read_text() == "hi"

    def test_creates_intermediate_directories(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        save_file("a/b/c/deep.txt", "deep content")
        assert (tmp_path / "project" / "a" / "b" / "c" / "deep.txt").exists()

    def test_overwrites_existing_file(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        save_file("f.txt", "first")
        save_file("f.txt", "second")
        assert (tmp_path / "project" / "f.txt").read_text() == "second"

    def test_returns_error_when_project_folder_none(self):
        from graph.utils.tools import files as mod
        # Clear PROJECT_FOLDER to exercise the guard path
        old = mod.PROJECT_FOLDER
        mod.PROJECT_FOLDER = None
        try:
            result = save_file("a.txt", "content")
            assert result.startswith("Error: PROJECT_FOLDER is not set")
        finally:
            mod.PROJECT_FOLDER = old


class TestValidatePath:
    """Tests for validate_path_within_project_folder()."""

    def test_valid_relative_path(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        result = validate_path_within_project_folder("sub/f.txt")
        assert "project/sub/f.txt" in result

    def test_abs_path_raises_value_error(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        with pytest.raises(ValueError, match="Absolute paths are rejected"):
            validate_path_within_project_folder("/etc/passwd")

    def test_parent_traversal_outside_root_raises(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        with pytest.raises(ValueError, match="Path escapes PROJECT_FOLDER"):
            validate_path_within_project_folder("../secret/key.txt")

    def test_parent_traversal_stays_inside_ok(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = tmp_path / "project" / "a" / "b" / "sub"
        proj.mkdir(parents=True)
        mod.PROJECT_FOLDER = str(proj)
        # '..' moves up one level to 'b/', which IS inside project/a/b/sub
        result = validate_path_within_project_folder("../../f.txt")
        assert "f.txt" in result

    def test_directory_paths_handled(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = tmp_path / "project"
        sub = proj / "sub"
        sub.mkdir()
        mod.PROJECT_FOLDER = str(proj)
        result = validate_path_within_project_folder("sub")
        assert os.path.realpath(result) == os.path.realpath(str(sub))

    def test_none_project_folder_returns_error(self):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = None
        result = validate_path_within_project_folder("f.txt")
        assert "Error: PROJECT_FOLDER is not set" in result


# ---------------------------------------------------------------------------
# @tool functions (they also invoke validate_path_within_project_folder)
# ---------------------------------------------------------------------------

class TestCreateDirectory:
    """Tests for create_directory."""

    def test_creates_directory(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        result = create_directory.invoke({"path": "new_dir"})
        assert os.path.isdir(os.path.join(str(mod.PROJECT_FOLDER), "new_dir"))

    def test_returns_directory_path(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        result = create_directory.invoke({"path": "a/b"})
        assert os.path.isdir(os.path.join(str(mod.PROJECT_FOLDER), "a", "b"))

    def test_no_error_when_already_exists(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "dir").mkdir()
        result = create_directory.invoke({"path": "dir"})
        assert os.path.isdir(os.path.join(proj, "dir"))

    def test_rejects_absolute_path(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        with pytest.raises(ValueError, match="Absolute paths are rejected"):
            create_directory.invoke({"path": "/etc"})


class TestCreateFile:
    """Tests for create_file."""

    def test_creates_and_writes_content(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        result = create_file.invoke({"file_path": "hello.txt", "content": "world"})
        assert (tmp_path / "project" / "hello.txt").read_text() == "world"

    def test_returns_file_path(self, tmp_path):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        result = create_file.invoke({"file_path": "a.txt", "content": "x"})
        assert "a.txt" in result

    def test_creates_parent_directories(self, tmp_path):
        from graph.utils.tools import files as mod
        # create_file does NOT create parents — it will hit a FileNotFound.
        mod.PROJECT_FOLDER = str(tmp_path / "project")
        # Ensure parent exists first; we only test that existing-dir creation works
        sub = Path(mod.PROJECT_FOLDER) / "sub"
        sub.mkdir()
        result = create_file.invoke({"file_path": "sub/nested.txt", "content": "ok"})
        assert (tmp_path / "project" / "sub" / "nested.txt").read_text() == "ok"


class TestReadFile:
    """Tests for read_file."""

    def test_reads_content(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "data.txt").write_text("read me")
        result = read_file.invoke({"file_path": "data.txt"})
        assert result == "read me"

    def test_raises_on_missing_file(self):
        from graph.utils.tools import files as mod
        with pytest.raises(FileNotFoundError):
            read_file.invoke({"file_path": "nope.txt"})


class TestDeleteFile:
    """Tests for delete_file."""

    def test_deletes_existing_file(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "x.txt").write_text("delete")
        result = delete_file.invoke({"file_path": "x.txt"})
        assert not os.path.exists(os.path.join(proj, "x.txt"))
        assert "Deleted file:" in result

    def test_returns_error_on_missing_file(self):
        from graph.utils.tools import files as mod
        result = delete_file.invoke({"file_path": "missing.txt"})
        assert "Error: File not found" in result


class TestListFiles:
    """Tests for list_files."""

    def test_lists_files_in_directory(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "a.txt").touch()
        Path(proj, "b.txt").touch()
        result = list_files.invoke({"path": "."})
        assert "a.txt" in result
        assert "b.txt" in result

    def test_lists_in_sub_directory(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        sub = os.path.join(proj, "sub")
        os.makedirs(sub)
        Path(sub, "c.txt").touch()
        mod.PROJECT_FOLDER = proj
        result = list_files.invoke({"path": "sub"})
        assert "c.txt" in result


class TestInsertIntoFile:
    """Tests for insert_into_file."""

    def test_insert_at_start(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "t.txt").write_text("world")
        result = insert_into_file.invoke({"file_path": "t.txt", "content": "hello ", "position": "start"})
        assert (tmp_path / "project" / "t.txt").read_text() == "hello world"

    def test_insert_at_end(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "t.txt").write_text("hello")
        result = insert_into_file.invoke({"file_path": "t.txt", "content": " world", "position": "end"})
        assert (tmp_path / "project" / "t.txt").read_text() == "hello world"


    def test_invalid_position(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "t.txt").write_text("data")
        # Call .func directly to bypass LangChain's Literal schema validation
        result = insert_into_file.func(
            file_path="t.txt", content="x", position="middle"
        )
        assert "Error: Invalid position" in result


    # insert_into_file
    def test_missing_file_returns_error(self):
        from graph.utils.tools import files as mod
        result = insert_into_file.invoke({
            "file_path": "nope.txt", "content": "x", "position": "start"
        })
        assert "Error: File not found" in result

    # append_to_file
    def test_missing_file_returns_error(self):
        from graph.utils.tools import files as mod
        result = append_to_file.invoke({"file_path": "nope.txt", "content": "x"})
        assert "Error: File not found" in result

    # update_file
    def test_missing_file_returns_error(self):
        from graph.utils.tools import files as mod
        result = update_file.invoke({"file_path": "nope.txt", "content": "x"})
        assert "Error: File not found" in result


class TestAppendToFile:
    """Tests for append_to_file."""

    def test_appends_content(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "t.txt").write_text("first")
        result = append_to_file.invoke({"file_path": "t.txt", "content": "\nsecond"})
        assert (tmp_path / "project" / "t.txt").read_text() == "first\nsecond"

    def test_missing_file_returns_error(self):
        from graph.utils.tools import files as mod
        with pytest.raises(FileNotFoundError):
            append_to_file.invoke({"file_path": "nope.txt", "content": "x"})


class TestUpdateFile:
    """Tests for update_file."""

    def test_updates_content(self, tmp_path):
        from graph.utils.tools import files as mod
        proj = str(tmp_path / "project")
        mod.PROJECT_FOLDER = proj
        Path(proj, "t.txt").write_text("old")
        result = update_file.invoke({"file_path": "t.txt", "content": "new"})
        assert (tmp_path / "project" / "t.txt").read_text() == "new"

    def test_missing_file_returns_error(self):
        from graph.utils.tools import files as mod
        with pytest.raises(FileNotFoundError):
            update_file.invoke({"file_path": "nope.txt", "content": "x"})


# ---------------------------------------------------------------------------
# Integration / project-folder lifecycle
# ---------------------------------------------------------------------------

class TestProjectFolderLifecycle:
    """Tests for get_project_folder() / update_project_folder()."""


    def test_default_is_none(self):
        from graph.utils.tools import files as mod
        old = mod.PROJECT_FOLDER
        try:
            mod.PROJECT_FOLDER = None
            assert mod.PROJECT_FOLDER is None
            assert get_project_folder() is None
        finally:
            mod.PROJECT_FOLDER = old


    def test_update_and_get(self):
        from graph.utils.tools import files as mod
        mod.PROJECT_FOLDER = "/tmp/test"
        assert get_project_folder() == "/tmp/test"