import logging
import os
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

@tool
def create_file(file_path: str, content: str):
    """Create a file with the given content at the specified path."""
    logger.info(f",Tool_Invoked,'create_file','{file_path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    file_path = os.path.join(PROJECT_FOLDER, file_path)

    with open(file_path, "w") as f:
        f.write(content)
    return file_path

@tool
def read_file(file_path: str):
    """Read the content of a file at the specified path."""
    logger.info(f",Tool_Invoked,'read_file','{file_path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    file_path = os.path.join(PROJECT_FOLDER, file_path)

    with open(file_path, "r") as f:
        content = f.read()
    return content

@tool
def delete_file(file_path: str):
    """Delete the file at the specified path."""
    logger.info(f",Tool_Invoked,'delete_file','{file_path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    file_path = os.path.join(PROJECT_FOLDER, file_path)

    if os.path.exists(file_path):
        os.remove(file_path)
        return f"Deleted file: {file_path}"
    else:
        return f"Error: File not found: {file_path}"

@tool
def list_files(path: str):
    """List all files in the project folder."""
    logger.info(f",Tool_Invoked,'list_files','{path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    path = os.path.join(PROJECT_FOLDER, path)
    files = os.listdir(path)
    return files

@tool
def insert_into_file(file_path: str, content: str, position: Literal["start", "end"]):
    """Insert content into a file at the specified position."""
    logger.info(f",Tool_Invoked,'insert_into_file','{file_path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    file_path = os.path.join(PROJECT_FOLDER, file_path)

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
    logger.info(f",Tool_Invoked,'append_to_file','{file_path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    file_path = os.path.join(PROJECT_FOLDER, file_path)

    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    with open(file_path, "a") as f:
        f.write(content)
    return file_path

@tool
def update_file(file_path: str, content: str):
    """Update the content of a file at the specified path."""
    logger.info(f",Tool_Invoked,'update_file','{file_path}'")
    if PROJECT_FOLDER is None:
        return "Error: PROJECT_FOLDER is not set. Call update_project_folder first."

    file_path = os.path.join(PROJECT_FOLDER, file_path)

    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    with open(file_path, "w") as f:
        f.write(content)
    return file_path