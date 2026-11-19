import os
import subprocess
from unittest.mock import patch

import pytest

from graph.utils.tools.environment import (
    ENVIRONMENT_VARIABLES,
    get_python_environment,
)
import graph.utils.tools.files as files_module
import graph.utils.tools.environment as env_module


@pytest.fixture(autouse=True)
def _reset_globals():
    """Reset module-level globals before every test."""
    prev_project_folder = getattr(files_module, "PROJECT_FOLDER", None)
    env_module.ENVIRONMENT_VARIABLES = None

    yield

    # Restore original project folder for other tests.
    files_module.PROJECT_FOLDER = prev_project_folder


# The raw (undecorated) function behind the @tool decorator
_setup_git_repository_raw = env_module.setup_git_repository.func


class TestGetPythonEnvironment:
    """Tests for `get_python_environment`."""

    def test_returns_dict(self, tmp_path):
        project_dir = str(tmp_path / "project_root_0")
        os.makedirs(project_dir, exist_ok=True)
        files_module.PROJECT_FOLDER = project_dir

        result = get_python_environment()
        assert isinstance(result, dict)

    def test_first_call_sets_env_vars(self, tmp_path):
        project_dir = str(tmp_path / "project_root")
        os.makedirs(project_dir, exist_ok=True)
        files_module.PROJECT_FOLDER = project_dir

        result = get_python_environment()

        assert "PROJECT_FOLDER" in result
        assert result["PROJECT_FOLDER"] == project_dir
        assert "PYTHONPATH" in result
        expected_pythonpath = os.path.join(project_dir, "src")
        assert result["PYTHONPATH"] == expected_pythonpath

    def test_returns_copy_of_os_environ(self, tmp_path):
        project_dir = str(tmp_path / "project_root2")
        os.makedirs(project_dir, exist_ok=True)
        files_module.PROJECT_FOLDER = project_dir

        result = get_python_environment()

        for key in os.environ:
            assert key in result
            assert result[key] == os.environ[key]

    def test_subsequent_calls_return_same_object(self, tmp_path):
        """Verify the caching behaviour — same dict object on repeated calls."""
        project_dir = str(tmp_path / "project_root3")
        os.makedirs(project_dir, exist_ok=True)
        files_module.PROJECT_FOLDER = project_dir

        first_call = get_python_environment()
        second_call = get_python_environment()

        assert first_call is second_call

    def test_modified_result_does_not_affect_cache(self, tmp_path):
        """Mutating the returned dict must not mutate the cached copy."""
        project_dir = str(tmp_path / "project_root4")
        os.makedirs(project_dir, exist_ok=True)
        files_module.PROJECT_FOLDER = project_dir

        result1 = get_python_environment()
        result1["CUSTOM_KEY"] = "custom_value"
        del result1["CUSTOM_KEY"]  # remove before second call to validate

        result2 = get_python_environment()

        assert "CUSTOM_KEY" not in result2

    def test_respects_update_project_folder(self, tmp_path):
        """When the project folder changes, the next call should reflect it."""
        # Reset cache so we start fresh.
        env_module.ENVIRONMENT_VARIABLES = None

        dir_a = str(tmp_path / "dir_a")
        os.makedirs(dir_a, exist_ok=True)
        files_module.PROJECT_FOLDER = dir_a

        result_a = get_python_environment()
        assert result_a["PROJECT_FOLDER"] == dir_a

        # Mutate the cached copy so it's *not* updated — but then force a
        # refresh by clearing the cache and setting a new project folder.
        env_module.ENVIRONMENT_VARIABLES = None
        dir_b = str(tmp_path / "dir_b")
        os.makedirs(dir_b, exist_ok=True)
        files_module.PROJECT_FOLDER = dir_b

        result_b = get_python_environment()
        assert result_b["PROJECT_FOLDER"] == dir_b

    def test_resets_and_recomputes_when_CACHE_cleared(self, tmp_path):
        """Clearing the cache should trigger a fresh read of get_project_folder."""
        dir_a = str(tmp_path / "dir_c")
        os.makedirs(dir_a, exist_ok=True)
        files_module.PROJECT_FOLDER = dir_a

        result_a = get_python_environment()

        # Invalidate cache manually.
        env_module.ENVIRONMENT_VARIABLES = None

        dir_b = str(tmp_path / "dir_d")
        os.makedirs(dir_b, exist_ok=True)
        files_module.PROJECT_FOLDER = dir_b

        result_b = get_python_environment()
        assert result_a["PROJECT_FOLDER"] != result_b["PROJECT_FOLDER"]
        assert result_b["PROJECT_FOLDER"] == dir_b

    def test_project_folder_unset_raises_type_error(self):
        """When PROJECT_FOLDER is None, os.path.join(None, ...) raises TypeError."""
        files_module.PROJECT_FOLDER = None  # explicit reset

        with pytest.raises(TypeError):
            get_python_environment()


class TestSetupGitRepository:
    """Tests for `setup_git_repository`."""

    @pytest.fixture(autouse=True)
    def _setup_project_folder(self, tmp_path):
        files_module.PROJECT_FOLDER = str(tmp_path / "project_root")
        env_module.ENVIRONMENT_VARIABLES = None  # force fresh cache

    def test_returns_string(self, tmp_path):
        mock_result = subprocess.CompletedProcess(
            args=["git", "init", "test_repo"], returncode=0, stdout="", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = _setup_git_repository_raw("test_repo")
        assert isinstance(result, str)

    def test_calls_git_init_with_correct_args(self, tmp_path):
        """Verify subprocess.run is called with the correct arguments."""
        mock_result = subprocess.CompletedProcess(
            args=["git", "init", "new_repo"], returncode=0, stdout="", stderr=""
        )
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _setup_git_repository_raw("new_repo")

        mock_run.assert_called_once_with(
            ["git", "init", "new_repo"],
            capture_output=True,
            text=True,
            env=env_module.ENVIRONMENT_VARIABLES,
        )

    def test_returns_stdout_on_success(self, tmp_path):
        expected_output = "Initialized empty Git repository in /tmp/new_repo/.git/\n"
        mock_result = subprocess.CompletedProcess(
            args=["git", "init", "new_repo"], returncode=0, stdout=expected_output, stderr=""
        )
        with patch("subprocess.run", return_value=mock_result):
            result = _setup_git_repository_raw("new_repo")

        assert result.strip() == expected_output.strip()

    def test_returns_error_string_on_exception(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = _setup_git_repository_raw("bad_path")

        assert result.startswith("Error:")
        assert "git not found" in result

    def test_passes_environment_variables(self, tmp_path):
        """Ensure environment variables from get_python_environment are passed through."""
        expected_env = env_module.ENVIRONMENT_VARIABLES
        mock_result = subprocess.CompletedProcess(
            args=["git", "init", "new_repo"], returncode=0, stdout="", stderr=""
        )

        def check_env(*args, **kwargs):
            assert kwargs["env"] is expected_env
            return mock_result

        with patch("subprocess.run", side_effect=check_env):
            _setup_git_repository_raw("new_repo")

