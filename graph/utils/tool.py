import logging
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

@tool
def ask_user(question: str) -> str:
    """Ask the user a question and return their response.
    Use this when you need additional information, clarification, or
    confirmation from the user before proceeding with a task.

    Args:
        question: The question to ask the user. Be specific and clear.

    Returns:
        The user's text response from the command-line prompt.
    """
    logger.info("Prompting user for input.")
    logger.info("Asking user: %s", question)
    try:
        response = input(f"\n{question}\n> ").strip()
        logger.info("User responded: %s", response)
        return response if response else "(no response)"
    except EOFError:
        return "(user input not available — EOF)"
    except KeyboardInterrupt:
        return "(user input cancelled by user)"


@tool
def manage_file(
    operation: Literal["create", "update", "delete"],
    path: str,
    content: str = "",
) -> str:
    """Create, update, or delete a file within the project folder.

    Use this tool to write new files, modify existing ones, or remove files.
    All operations are restricted to paths inside PROJECT_FOLDER.

    Args:
        operation: One of "create", "update", or "delete".
            - "create": Write content to a new file (fails if file exists).
            - "update": Overwrite an existing file with new content.
            - "delete": Remove the specified file.
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

    if operation == "delete":
        if not file_path.exists():
            return f"File not found: {file_path}"
        file_path.unlink()
        return f"Deleted: {file_path}"

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
