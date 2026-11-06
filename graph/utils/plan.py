import os
import logging

from .config import PROMPTS
from .llm import invoke_llm, invoke_llm_with_tools
from .files import read_file, create_file, append_to_file, insert_into_file, delete_file, list_files, get_project_folder, save_file
from .state import AgentState
from .user import prompt_user

logger = logging.getLogger(__name__)

def generate_plan(state: AgentState) -> AgentState:
    """Generate a detailed implementation plan using LLM based on user description."""
    logger.info(f",Agent_Invoked,'generate_plan','{state.get('user_prompt', '')}'")

    user_prompt = state.get("user_prompt", "")
    messages = []

    if state.get('skip_user_prompt', False):
        prompt = PROMPTS["plan"].format(description=user_prompt)
        tools = [prompt_user, read_file, create_file, append_to_file, insert_into_file, delete_file, list_files]
        messages.append({"role": "user", "content": prompt})
    else:
        prompt = PROMPTS["plan_no_feedback"].format(description=user_prompt)
        tools = [read_file, create_file, append_to_file, insert_into_file, delete_file, list_files]
        messages.append({"role": "user", "content": prompt})

    response = invoke_llm_with_tools(state, messages, tools)
    state["plan"] = response

    # Store the generated plan in the Plan.md in the docs folder
    save_file("docs/Plan.md", response)

    return state