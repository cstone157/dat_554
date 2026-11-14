import logging
import os
from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def test_runner_tool(test_command: str) -> str:
    """Run a test command."""
    logger.info(f"Tool_Invoked,'test_runner_tool','{test_command}'")
    return os.popen(test_command).read()