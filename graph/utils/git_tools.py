import logging
import os
import subprocess
from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def git_status():
    """Get the current status of the Git repository."""
    try:
        result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting Git status: {e}")
        return ""

@tool
def git_init():
    """Initialize a new Git repository."""
    try:
        result = subprocess.run(
            ["git", "init"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error initializing Git repository: {e}")
        return ""

@tool
def git_add(file_path: str):
    """Add a file to the Git staging area."""
    try:
        result = subprocess.run(
            ["git", "add", file_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error adding file to Git staging area: {e}")
        return ""

@tool
def git_commit(message: str):
    """Commit changes to the Git repository with a message."""
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error committing changes to Git repository: {e}")
        return ""
