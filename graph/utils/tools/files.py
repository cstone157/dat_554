import logging
import os
import sys

from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

PROJECT_FOLDER = None  # Set this to the root folder of your project if needed
def update_project_folder(path: str):
    """Update the project folder path."""
    global PROJECT_FOLDER
    PROJECT_FOLDER = path
def get_project_folder():
    """Get the current project folder path."""
    return PROJECT_FOLDER
def save_file(file_path: str, content: str):
    """Save content to a file at the specified path."""
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."
    file_path = os.path.join(PROJECT_FOLDER, file_path)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        f.write(content)
    return file_path

def validate_path_within_project_folder(file_path: str) -> str:
    """Validate and resolve a file path to ensure it stays within PROJECT_FOLDER.
    
    Rejects absolute paths, paths with '..' traversal that escape the project root.
    Returns the resolved absolute path if valid, or an error string if invalid.
    """
    proj = get_project_folder()
    if not proj:
        return "Error: PROJECT_FOLDER is not set."

    if os.path.isabs(file_path):
        raise ValueError(f"Absolute paths are rejected: {file_path}")

    resolved = os.path.normpath(os.path.join(proj, file_path))
    real_proj = os.path.realpath(proj)

    # Compare consistently: always compare realpath against realpath of the candidate
    if os.path.isdir(resolved):
        real_resolved = os.path.realpath(resolved)
    else:
        # For files that don't exist yet, resolve the parent dir's realpath
        parent = os.path.dirname(resolved) or '.'
        real_resolved = os.path.realpath(parent) + os.sep + os.path.basename(resolved)

    if real_resolved != real_proj and not real_resolved.startswith(real_proj + os.sep):
        raise ValueError(f"Path escapes PROJECT_FOLDER: {file_path}")

    return resolved

@tool
def create_directory(path: str):
    """Create a directory at the specified path."""
    logger.info(f"Tool_Invoked,'create_directory','{path}'")
    path = validate_path_within_project_folder(path)

    os.makedirs(path, exist_ok=True)
    return path

@tool
def create_file(file_path: str, content: str):
    """Create a file with the given content at the specified path."""
    logger.info(f"Tool_Invoked,'create_file','{file_path}'")
    file_path = validate_path_within_project_folder(file_path)

    with open(file_path, "w") as f:
        f.write(content)
    return file_path

@tool
def read_file(file_path: str):
    """Read the content of a file at the specified path."""
    logger.info(f"Tool_Invoked,'read_file','{file_path}'")
    file_path = validate_path_within_project_folder(file_path)

    with open(file_path, "r") as f:
        content = f.read()
    return content

@tool
def delete_file(file_path: str):
    """Delete the file at the specified path."""
    logger.info(f"Tool_Invoked,'delete_file','{file_path}'")
    file_path = validate_path_within_project_folder(file_path)

    if os.path.exists(file_path):
        os.remove(file_path)
        return f"Deleted file: {file_path}"
    else:
        return f"Error: File not found: {file_path}"

@tool
def list_files(path: str):
    """List all files in the project folder."""
    logger.info(f"Tool_Invoked,'list_files','{path}'")
    path = validate_path_within_project_folder(path)

    files = os.listdir(path)
    return files

@tool
def insert_into_file(file_path: str, content: str, position: Literal["start", "end"]):
    """Insert content into a file at the specified position."""
    logger.info(f"Tool_Invoked,'insert_into_file','{file_path}'")
    file_path = validate_path_within_project_folder(file_path)

    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    with open(file_path, "r") as f:
        existing_content = f.read()

    if position == "start":
        new_content = content + existing_content
    elif position == "end":
        new_content = existing_content + content
    else:
        return "Error: Invalid position. Use 'start' or 'end'."

    with open(file_path, "w") as f:
        f.write(new_content)
    return file_path


@tool
def append_to_file(file_path: str, content: str):
    """Append content to the end of a file at the specified path."""
    logger.info(f"Tool_Invoked,'append_to_file','{file_path}'")
    file_path = validate_path_within_project_folder(file_path)

    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    with open(file_path, "a") as f:
        f.write(content)
    return file_path

@tool
def update_file(file_path: str, content: str):
    """Update the content of a file at the specified path."""
    logger.info(f"Tool_Invoked,'update_file','{file_path}'")
    file_path = validate_path_within_project_folder(file_path)

    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    with open(file_path, "w") as f:
        f.write(content)
    return file_path