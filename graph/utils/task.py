import os
import logging

from .config import PROMPTS
from .llm import invoke_llm, invoke_llm_with_tools
from .files import read_file, create_file, append_to_file, insert_into_file, delete_file, list_files, get_project_folder, save_file
from .python_tools import check_python_version, create_virtualenv, check_virtualenv, check_libraries, install_libraries, freeze_libraries
from .state import AgentState
from .user import prompt_user

logger = logging.getLogger(__name__)

def generate_task(state: AgentState) -> AgentState:
    """Generate a detailed task list using LLM based on user description."""
    logger.info(f",Agent_Invoked,'generate_task','{state.get('user_prompt', '')}'")

    plan = state.get("plan", "")
    messages = []

    prompt = PROMPTS["task"].format(plan=plan)
    if state.get('skip_user_prompt', False):
        tools = [prompt_user, read_file, create_file, append_to_file, insert_into_file, delete_file, list_files]
    else:
        tools = [read_file, create_file, append_to_file, insert_into_file, delete_file, list_files]
    # tools = [prompt_user, read_file, create_file, append_to_file, insert_into_file, delete_file, list_files]
    messages.append({"role": "user", "content": prompt})

    response = invoke_llm_with_tools(state, messages, tools)

    # Store the generated task list in the TaskList.md in the docs folder
    save_file("docs/Task.md", response)

    # Convert the task list into an array of task objects
    if isinstance(response, str):
        # Split the response based upon blank lines into seperate tasks
        state["pending_tasks"] = response.split("\n\n")
        state["completed_tasks"] = []
    else:
        logger.error(f"Failed to generate task list {response}.")
        raise ValueError("Failed to generate task list.")

    return state


# def task_route(state: AgentState) -> AgentState:
#     """Route the task based on its status."""
#     logger.info(f",Agent_Invoked,'task_route','{state.get('next_task', '')}'")

#     tools = [
#         read_file, create_file, append_to_file, insert_into_file, delete_file, list_files,
#         check_python_version, create_virtualenv, check_virtualenv, check_libraries, install_libraries, freeze_libraries
#     ]

#     # Set the next task if none is currently set
#     if len(state["pending_tasks"]) > 0 and state.get("next_task") is None:
#         state["next_task"] = state["pending_tasks"][0]
#         state["pending_tasks"] = state["pending_tasks"][1:]
#     elif len(state["pending_tasks"]) > 0:
#         state["completed_tasks"].append(state["next_task"])
#         state["next_task"] = state["pending_tasks"][0]
#         state["pending_tasks"] = state["pending_tasks"][1:]
#     else:
#         state["next_task"] = None
#         return {"next_task": None}

#     return {"next_task": state["next_task"]}