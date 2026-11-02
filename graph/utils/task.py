import logging

from .config import PROMPTS
from .llm import invoke_llm, invoke_llm_with_tools
from .files import read_file, create_file, append_to_file, insert_into_file, delete_file, list_files
from .state import AgentState
from .user import prompt_user

logger = logging.getLogger(__name__)

def generate_task(state: AgentState) -> AgentState:
    """Generate a detailed task list using LLM based on user description."""
    logger.info(f",Agent_Invoked,'generate_task','{state.get('user_prompt', '')}'")

    plan = state.get("plan", "")
    messages = []

    prompt = PROMPTS["task"].format(description=plan)
    tools = [prompt_user, read_file, create_file, append_to_file, insert_into_file, delete_file, list_files]
    messages.append({"role": "user", "content": prompt})


    response = invoke_llm_with_tools(messages, tools)
    state["task_list"] = response

    # Store the generated task list in the TaskList.md in the docs folder
    create_file("docs/Task.md", response)

    return state