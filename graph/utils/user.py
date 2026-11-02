import logging
from langchain_core.tools import tool

from .state import AgentState

logger = logging.getLogger(__name__)

@tool
def prompt_user(question: str) -> str:
    """Ask the user a question and return their response.
    Use this when you need additional information, clarification, or
    confirmation from the user before proceeding with a task.

    Args:
        question: The question to ask the user. Be specific and clear.

    Returns:
        The user's text response from the command-line prompt.
    """
    logger.info(f",Tool_Invoked,'prompt_user','{question}'")
    try:
        response = input(f"\n{question}\n> ").strip()
        logger.info("User responded: %s", response)
        return response if response else "(no response)"
    except EOFError:
        return "(user input not available — EOF)"
    except KeyboardInterrupt:
        return "(user input cancelled by user)"