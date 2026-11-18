import logging
from typing import List
import traceback

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from ..state import AgentState, Task
from ..llm import get_llm
from ..tools import create_file, read_file, list_files, insert_into_file, append_to_file, \
    update_file, check_python_version, setup_uv_virtual_environment, add_package_uv_virtual_environment, \
    run_python_script, create_directory

logger = logging.getLogger(__name__)

def coder_node(state: AgentState):
    # Get the current task and its description
    current_task_id = state["current_task_id"]
    current_task = None
    for t in state["tasks"]:
        if t.id == current_task_id:
            current_task = t
            break
    current_task.status = "in_progress"
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
        check_python_version, setup_uv_virtual_environment, add_package_uv_virtual_environment, 
        run_python_script, create_directory
    ])

    # DELETE ME
    # # Process tools and update mock-workspace
    # new_workspace = dict(state.get("workspace", {}))

    # Invoke the LLM with the conversation
    while True:
        logger.info(f"Agent_Working,'coder_node','Calling LLM {conversation[-1].content.split('\n')[0]}'")
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
                "create_directory": create_directory,
            }[tool_call["name"]]
            try:
                print(f"Invoking tool: {tool_call['name']} with args: {tool_call['args']}")
                result = tool.invoke(tool_call["args"])
                print(f"Tool {tool_call['name']} returned: {result}")

                # Check if any of the tool calls that involve file operations were called
                if tool_call["name"] in {"create_file", "read_file", "list_files", "insert_into_file", "append_to_file", "update_file"}:
                    print(f"File operation called: {tool_call['name']} with args: {tool_call['args']}")
                    if ("file_path" in tool_call["args"]) and (tool_call["args"]["file_path"] not in current_task.assigned_files):
                        current_task.assigned_files.append(tool_call["args"]["file_path"])

                conversation.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            except Exception as e:
                trace_str = traceback.format_exc()
                print(trace_str)
                logger.error(f"Tool call failed: {e}\n{trace_str.split('\n')[0]}")
                conversation.append(ToolMessage(content=f"Tool call failed: {e}\n{trace_str}", tool_call_id=tool_call["id"]))

            # DELETE ME
            # # Append the results to our workspace
            # if tool_call["name"] in {"create_file"}:
            #     new_workspace[tool_call["args"]["file_path"]] = result

    logger.info(f"Agent_Resolved,'coder_node',''")
    current_task.status = "coded"
    return {
        # "workspace": new_workspace,
        "evaluation_passed": False # Reset gate for Evaluator
    }