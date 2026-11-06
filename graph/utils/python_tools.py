import logging
import os
import subprocess
from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

def check_virtualenv(path: str) -> bool:
    """Check if a virtual environment exists at the specified path."""
    if not os.path.isdir(path):
        return False
    cfg_file = os.path.join(path, "pyvenv.cfg")
    return os.path.isfile(cfg_file)
def is_blacklisted_library(library: str) -> bool:
    """Check if a library is blacklisted."""
    blacklisted_libraries = ["dangerous_library_1", "dangerous_library_2"]  # Example blacklist
    return library in blacklisted_libraries


@tool
def check_python_version(path: str) -> str:
    """Check the Python version in the specified virtual environment."""
    logger.info(f",Tool_Invoked,'check_python_version','{path}'")
    python_executable = os.path.join(path, "bin", "python3")
    result = subprocess.run([python_executable, "--version"], capture_output=True, text=True)
    return result.stdout.strip()

@tool
def create_virtualenv(path: str) -> None:
    """Create a virtual environment at the specified path."""
    logger.info(f",Tool_Invoked,'create_virtualenv','{path}'")
    subprocess.run(["python3", "-m", "venv", path])

@tool
def check_virtualenv(path: str) -> bool:
    """Check if a virtual environment exists at the specified path."""
    logger.info(f",Tool_Invoked,'check_virtualenv_tool','{path}'")
    return check_virtualenv(path)

@tool
def check_libraries(path: str) -> bool:
    """Check if the specified virtual environment has installed libraries."""
    logger.info(f",Tool_Invoked,'check_libraries','{path}'")
    site_packages = os.path.join(path, "lib", "python3", "site-packages")
    return os.path.isdir(site_packages) and bool(os.listdir(site_packages))

@tool
def install_libraries(path: str, libraries: list[str]) -> list[str]:
    """Install specified libraries into the virtual environment at the given path."""
    logger.info(f",Tool_Invoked,'install_libraries','{path}','{libraries}'")
    pip_executable = os.path.join(path, "bin", "pip")
    for library in libraries:
        if is_blacklisted_library(library):
            logger.warning(f"Library '{library}' is blacklisted and will not be installed.")
            continue
    installed_libraries = [lib for lib in libraries if not is_blacklisted_library(lib)]
    subprocess.run([pip_executable, "install"] + installed_libraries)
    return installed_libraries

@tool
def freeze_libraries(path: str) -> list[str]:
    """Freeze the installed libraries in the specified virtual environment."""
    logger.info(f",Tool_Invoked,'freeze_libraries','{path}'")
    pip_executable = os.path.join(path, "bin", "pip")
    result = subprocess.run([pip_executable, "freeze", "-r", "requirements.txt"], capture_output=True, text=True)
    return [line.strip() for line in result.stdout.split("\n") if line.strip()]