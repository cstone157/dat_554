import logging
import os
import subprocess
from typing import Annotated, Literal

from langchain_core.tools import tool

from .files import get_project_folder, validate_path_within_project_folder

logger = logging.getLogger(__name__)

ENVIRONMENT_VARIABLES = None
VIRTUAL_ENVIRONMENT = False
def get_python_environment():
    """
    Setup the Python environment for the project.

    Returns:
        A dictionary containing the environment variables and project folder path.
    """
    global ENVIRONMENT_VARIABLES
    if ENVIRONMENT_VARIABLES is None:
        project_folder = get_project_folder()
        ENVIRONMENT_VARIABLES = os.environ.copy()
        ENVIRONMENT_VARIABLES["PYTHONPATH"] = os.path.join(project_folder, "src")
        ENVIRONMENT_VARIABLES["PROJECT_FOLDER"] = project_folder
    return ENVIRONMENT_VARIABLES


@tool
def check_python_version(path: str) -> str:
    """Check the Python version in the specified virtual environment."""
    global VIRTUAL_ENVIRONMENT
    logger.info(f"Tool_Invoked,'check_python_version','{path}'")

    local_env = get_python_environment()
    if VIRTUAL_ENVIRONMENT:
        try:
            result = subprocess.run(["uv", "python", "--version"], capture_output=True, text=True, env=local_env)
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"
    return "Python virtual environment is not set up."

@tool
def setup_uv_virtual_environment(path: str) -> str:
    """Setup the Python environment for the specified virtual environment."""
    global VIRTUAL_ENVIRONMENT
    logger.info(f"Tool_Invoked,'setup_virtual_environment','{path}'")

    local_env = get_python_environment()
    try:
        result = subprocess.run(["uv", "venv"], capture_output=True, text=True, env=local_env)
        if result.return_code == 0:
            VIRTUAL_ENVIRONMENT = True
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

@tool
def add_package_uv_virtual_environment(package_name: str) -> str:
    """Add a package to the specified uv virtual environment."""
    global VIRTUAL_ENVIRONMENT
    logger.info(f"Tool_Invoked,'add_package_uv_virtual_environment','{package_name}'")

    local_env = get_python_environment()
    
    if VIRTUAL_ENVIRONMENT:
        try:
            result = subprocess.run(["uv", "add", package_name], capture_output=True, text=True, env=local_env)
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"
    return "Python virtual environment is not set up."

@tool
def run_python_script(script_path: str) -> str:
    """Run a Python script in the specified uv virtual environment."""
    global VIRTUAL_ENVIRONMENT
    logger.info(f"Tool_Invoked,'run_python_script','{script_path}'")

    local_env = get_python_environment()
    if VIRTUAL_ENVIRONMENT:
        # Validate the script path stays within PROJECT_FOLDER
        resolved = validate_path_within_project_folder(script_path)
        if isinstance(resolved, str) and resolved.startswith("Error:"):
            return resolved

        try:
            result = subprocess.run(
                ["uv", "run", resolved],
                capture_output=True, text=True, env=local_env
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"
    return "Python virtual environment is not set up."