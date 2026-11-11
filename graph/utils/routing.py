import json
import logging

from .config import PROMPTS
from .llm import invoke_llm, invoke_llm_with_tools
from .files import read_file, create_file, append_to_file, insert_into_file, delete_file, list_files, get_project_folder, save_file
from .python_tools import check_python_version, create_virtualenv, check_virtualenv, check_libraries, install_libraries, freeze_libraries
from .state import AgentState

logger = logging.getLogger(__name__)


def task_route(state: AgentState) -> AgentState:
    """Check for the next pending task and route accordingly.

    If ``next_task`` is already set, returns it unchanged (the caller
    should not overwrite a task that was previously assigned).  Otherwise
    pops the first item from ``pending_tasks`` and stores it in
    ``next_task``.

    Returns the string ``"coder"`` when there is work to do or
    ``"evaluator"`` when all tasks are complete.
    """
    # If a task is already assigned, keep it — don't overwrite.
    if state.get("next_task"):
        logger.info(f",Agent_Invoked,'task_route','{state['next_task'].splitlines()[0]}'")
        return "coder"

    pending = state.get("pending_tasks", [])
    if not pending:
        logger.info(",Agent_Invoked,'task_route','no more tasks'")
        return "evaluator"

    task = pending.pop(0)
    state["next_task"] = task
    return "coder"