import logging
import os
from typing import Annotated, Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
def linter_tool(file_path: str, code: str) -> str:
    """Validate Python code syntax."""
    logger.info(f"Tool_Invoked,'linter_tool','{file_path}'")
    try:
        compile(code, file_path, "exec")
        return "SYNTAX_OK"
    except SyntaxError as error:
        return f"SYNTAX_ERROR: {error}"
