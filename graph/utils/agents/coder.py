import logging
from typing import List

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from ..state import AgentState, Task
from ..llm import get_llm
from ..tools import create_file, read_file, list_files, insert_into_file, append_to_file, \
    update_file, check_python_version, setup_uv_virtual_environment, add_package_uv_virtual_environment, \
    run_python_script

logger = logging.getLogger(__name__)

def coder_node(state: AgentState):
    # Get the current task and its description
    current_task_id = state["current_task_id"]
    current_task = None
    for t in state["tasks"]:
        if t.id == current_task_id:
            current_task = t
            break
    task_desc = current_task.description if current_task else "General implementation"

    # Get the issues for the current task
    issues = []
    for i in state.get("issues", []):
        if i.task_id == current_task_id:
            issues.append(i)
    issues_context = "\n".join([i.description for i in issues])
    prompt = f"Implement task: {task_desc}.\nExisting Issues to fix:\n{issues_context}"

    logger.info(f"Agent_Invoked,'coder_node','{prompt.split('\n')[0]}'")

    # Initialize the conversation with the system message and the user prompt
    conversation = [SystemMessage(content="You are a Principal Software Engineer."), HumanMessage(content=prompt)]
    llm = get_llm().bind_tools([
        create_file, read_file, list_files, insert_into_file, append_to_file, update_file,
        check_python_version, setup_uv_virtual_environment, add_package_uv_virtual_environment, run_python_script
    ])

    # DELETE ME
    # # Process tools and update mock-workspace
    # new_workspace = dict(state.get("workspace", {}))

    # Invoke the LLM with the conversation
    while True:
        response = llm.invoke(conversation)
        
        print(f"Coder response : {response}")

        if not response.tool_calls:
            break
        conversation.append(response)
        for tool_call in response.tool_calls:
            tool = {
                "create_file": create_file,
                "read_file": read_file,
                "list_files": list_files,
                "insert_into_file": insert_into_file,
                "append_to_file": append_to_file,
                "update_file": update_file,
                "check_python_version": check_python_version,
                "setup_uv_virtual_environment": setup_uv_virtual_environment,
                "add_package_uv_virtual_environment": add_package_uv_virtual_environment,
                "run_python_script": run_python_script,
            }[tool_call["name"]]
            result = tool.invoke(tool_call["args"])
            conversation.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

            # DELETE ME
            # # Append the results to our workspace
            # if tool_call["name"] in {"create_file"}:
            #     new_workspace[tool_call["args"]["file_path"]] = result
    
    return {
        # "workspace": new_workspace,
        "evaluation_passed": False # Reset gate for Evaluator
    }