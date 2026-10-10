import logging
from .state import AgentState

logger = logging.getLogger(__name__)

def prompt_user(state: AgentState) -> AgentState:
    """
    Get user description via CLI input.
    """

    logger.info("Prompting user for Python function description.")
    if state.get("user_description"):
        return state

    # Use --user_prompt argument if provided, otherwise ask interactively
    if state.get("user_prompt"):
        description = state["user_prompt"]
        logger.info("Using --user_prompt argument: %s", description)
    else:
        description = input("Enter a Python function description:\n> ").strip()
        while not description:
            description = input("Description cannot be empty. Enter a Python function description:\n> ").strip()
        logger.info("User provided description : %s", description)
    return {"user_description": description}


def prompt_user_feedback(state: AgentState) -> AgentState:
    """
    Get user feedback via CLI input for iterative refinement.
    """

    if state.get("_skip_feedback"):
        logger.info("--skip_feedback set, skipping feedback step.")
        return {"user_feedback": state.get("user_feedback", ""), "_has_feedback": False}
    logger.info("Prompting user for feedback.")
    feedback = input("\nEnter feedback or improvements (leave empty to skip):\n> ").strip()
    has_feedback = bool(feedback)
    return {"user_feedback": feedback if feedback else state.get("user_feedback", ""), "_has_feedback": has_feedback}
