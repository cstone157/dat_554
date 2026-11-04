import logging
import os
import subprocess
from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

def check_virtualenv(path: str) -> bool:
    """Check if a virtual environment exists at the specified path."""
    # 1. Ensure the directory itself exists
    if not os.path.isdir(path):
        return False
        
    # 2. Check for the definitive pyvenv.cfg file at the root
    cfg_file = os.path.join(path, "pyvenv.cfg")
    
    return os.path.isfile(cfg_file)


@tool
def create_virtualenv(path: str) -> None:
    """Create a virtual environment at the specified path."""
    logger.info(f",Tool_Invoked,'create_virtualenv','{path}'")
    subprocess.run(["python3", "-m", "venv", path])