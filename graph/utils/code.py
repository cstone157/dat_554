import os
import logging

from .config import PROMPTS
from .llm import invoke_llm, invoke_llm_with_tools
from .files import read_file, create_file, append_to_file, insert_into_file, delete_file, list_files, get_project_folder, save_file
from .python_tools import check_python_version, create_virtualenv, check_virtualenv, check_libraries, install_libraries, freeze_libraries
from .state import AgentState
from .user import prompt_user

logger = logging.getLogger(__name__)

def generate_code(state: AgentState) -> AgentState:
    """Generate code based on the current task."""
    logger.info(f",Agent_Invoked,'generate_code','{state.get('next_task', '')}'")

    next_task = state.get("next_task", "")
    prompt = PROMPTS["code_generation"].format(prompt=next_task, description=state.get("user_prompt", ""))
    messages = [{"role": "user", "content": prompt}]

    tools = [
        read_file, create_file, append_to_file, insert_into_file, delete_file, list_files,
        check_python_version, create_virtualenv, check_virtualenv, check_libraries, install_libraries, freeze_libraries
    ]

    response = invoke_llm_with_tools(state, messages, tools)

    if isinstance(response, str):
        save_file("docs/GeneratedCode.md", response)
    else:
        logger.error(f"Failed to generate code {response}.")
        raise ValueError("Failed to generate code.")

    return state