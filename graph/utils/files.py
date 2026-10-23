import logging
import subprocess
import os
from pathlib import Path

from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

PROJECT_FOLDER = None  # Set this to the root folder of your project if needed
def update_project_folder(path: str):
    """Update the project folder path."""
    global PROJECT_FOLDER
    PROJECT_FOLDER = path


def write_file(content, path='.', file_name='file.txt', encoding='utf-8'):
    """
    Write content to a file at the specified path.

    Args:
        content (str): The content to write to the file.
        path (str): The directory path where the file will be saved. Defaults to '.'.
        file_name (str): The name of the file. Defaults to 'file.txt'.
        encoding (str): The encoding to use for writing the file. Defaults to 'utf-8'.
    """
    global PROJECT_FOLDER
    if PROJECT_FOLDER is None:
        full_path = Path(path) / file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)
    else:
        full_path = Path(PROJECT_FOLDER) / path / file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)


def write_plan(content, path='.', file_name='Plan.md', encoding='utf-8'):
    """
    Write the plan content to a file named 'Plan.md' at the specified path.

    Args:
        content (str): The plan content to write to the file.
        path (str): The directory path where the file will be saved. Defaults to '.'.
        file_name (str): The name of the file. Defaults to 'Plan.md'.
        encoding (str): The encoding to use for writing the file. Defaults to 'utf-8'.
    """
    logger.info("Writing plan to %s", Path(PROJECT_FOLDER) / path / file_name if PROJECT_FOLDER else Path(path) / file_name)
    write_file(content, path=f"{path}/docs", file_name=file_name, encoding=encoding)



@tool
def manage_file(
    operation: Literal["create", "update"],
    path: str,
    content: str = "",
) -> str:
    """Create or update a file within the project folder.

    Use this tool to write new files, modify existing ones, or remove files.
    All operations are restricted to paths inside PROJECT_FOLDER.

    Args:
        operation: One of "create", "update", or "delete".
            - "create": Write content to a new file (fails if file exists).
            - "update": Overwrite an existing file with new content.
        path: The file path relative to PROJECT_FOLDER.
            Cannot contain ".." or start with "/" to prevent directory traversal.
        content: The text content to write (required for "create" and "update",
                 ignored for "delete").

    Returns:
        A status message describing the result of the operation.
    """
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    base = Path(PROJECT_FOLDER).resolve()

    # Validate path to prevent directory traversal
    if ".." in path.split(os.sep) or path.startswith("/"):
        return f"Error: Invalid path '{path}'. Paths must be relative and cannot contain '..' or start with '/'."

    file_path = (base / path).resolve()

    # Ensure the resolved path is still inside PROJECT_FOLDER
    try:
        file_path.relative_to(base)
    except ValueError:
        return f"Error: Path '{path}' resolves outside PROJECT_FOLDER ({PROJECT_FOLDER})."

    # if operation == "delete":
    #     if not file_path.exists():
    #         return f"File not found: {file_path}"
    #     file_path.unlink()
    #     return f"Deleted: {file_path}"

    # For create/update, content is required
    if not content and operation in ("create", "update"):
        return "Error: 'content' is required for create and update operations."

    if operation == "create":
        if file_path.exists():
            return f"File already exists: {file_path}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Created: {file_path}"

    if operation == "update":
        if not file_path.exists():
            return f"File not found: {file_path}"
        file_path.write_text(content, encoding="utf-8")
        return f"Updated: {file_path}"

    return f"Error: Unknown operation '{operation}'. Use 'create', 'update', or 'delete'."


@tool
def read_file(
    path: str,
) -> str:
    """Read the contents of a file within the project folder.

    Use this tool to retrieve text content from files in the project.
    All access is restricted to paths inside PROJECT_FOLDER.

    Args:
        path: The file path relative to PROJECT_FOLDER.
            Cannot contain ".." or start with "/" to prevent directory traversal.

    Returns:
        The text contents of the file, or an error message if the operation fails.
    """
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    base = Path(PROJECT_FOLDER).resolve()

    # Validate path to prevent directory traversal
    if ".." in path.split(os.sep) or path.startswith("/"):
        return f"Error: Invalid path '{path}'. Paths must be relative and cannot contain '..' or start with '/'."

    file_path = (base / path).resolve()

    # Ensure the resolved path is still inside PROJECT_FOLDER
    try:
        file_path.relative_to(base)
    except ValueError:
        return f"Error: Path '{path}' resolves outside PROJECT_FOLDER ({PROJECT_FOLDER})."

    if not file_path.exists():
        return f"File not found: {file_path}"

    if not file_path.is_file():
        return f"Not a file: {file_path}"

    try:
        content = file_path.read_text(encoding="utf-8")
        return content
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not a UTF-8 encoded text file."
    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'."
    except Exception as e:
        return f"Error reading '{file_path}': {e}"


def create_venv(project_folder: str) -> str:
    """Create a Python virtual environment in the project folder if it doesn't exist.

    Returns the path to the venv's Python interpreter.
    """
    venv_dir = Path(project_folder) / ".venv"
    requirements_file = Path(__file__).parent / "requirements.txt"

    if not venv_dir.exists():
        logger.info("Creating virtual environment in %s", venv_dir)
        subprocess.run(
            ["python3", "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

    # Determine the Python executable for this platform
    if os.name == "nt":  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
        pip_exe = venv_dir / "bin" / "pip"

    # Install requirements if the file exists and the venv is fresh
    if requirements_file.exists():
        logger.info("Installing requirements from %s", requirements_file)
        subprocess.run(
            [str(pip_exe), "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
        )

    return str(python_exe)