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
    run_python_script, create_directory, setup_git_repository

logger = logging.getLogger(__name__)

def coder_node(state: AgentState):
    from ..tools.files import get_project_folder
    import os

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

    # Initialize workspace from existing files on disk (only if it's empty)
    project_folder = get_project_folder()
    workspace = dict(state.get("workspace", {}))
    if not workspace and project_folder:
        for root, dirs, files in os.walk(project_folder):
            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, project_folder)
                try:
                    with open(full_path, "r") as f:
                        workspace[rel_path] = f.read()
                except Exception:
                    pass

    # Initialize the conversation with the system message and the user prompt
    conversation = [SystemMessage(content="You are a Principal Software Engineer."), HumanMessage(content=prompt)]
    llm = get_llm().bind_tools([
        create_file, read_file, list_files, insert_into_file, append_to_file, update_file,
        check_python_version, setup_uv_virtual_environment, add_package_uv_virtual_environment, 
        run_python_script, create_directory, setup_git_repository
    ])

    # Invoke the LLM with the conversation
    while True:
        logger.info(f"Agent_Working,'coder_node','Calling LLM {conversation[-1].content.split('\n')[0]}'")
        response = llm.invoke(conversation)

        if not response.tool_calls:
            break
        conversation.append(response)

        # Track file paths touched by this batch so we can sync them to workspace afterward
        touched_files: set[str] = set()

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
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
                "setup_git_repository": setup_git_repository
            }[tool_name]
            try:
                result = tool.invoke(tool_call["args"])

                # Track assigned files and touched files on disk
                fp = tool_call["args"].get("file_path")
                if fp:
                    if fp not in current_task.assigned_files:
                        current_task.assigned_files.append(fp)
                    if tool_name in (
                        "create_file", "read_file", "list_files",
                        "insert_into_file", "append_to_file", "update_file"
                    ):
                        touched_files.add(fp)

                # For create/update, the content is directly available from args
                if tool_name == "create_file":
                    workspace[fp] = tool_call["args"].get("content", "")
                elif tool_name == "update_file":
                    workspace[fp] = tool_call["args"].get("content", "")

                conversation.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
            except Exception as e:
                trace_str = traceback.format_exc()
                logger.error(f"Tool call failed: {e}\n{trace_str.split('\n')[0]}")
                conversation.append(ToolMessage(content=f"Tool call failed: {e}\n{trace_str}", tool_call_id=tool_call["id"]))

        # After all tools in the batch have executed on disk, sync touched files from disk into workspace.
        # This covers reads, inserts, appends, and any files whose state changed but wasn't captured above.
        if project_folder:
            for rel_path in touched_files:
                full_path = os.path.join(project_folder, rel_path)
                try:
                    with open(full_path, "r") as f:
                        workspace[rel_path] = f.read()
                except Exception:
                    pass

    logger.info(f"Agent_Resolved,'coder_node',''")
    current_task.status = "coded"
    return {
        "workspace": workspace,
        "evaluation_passed": False  # Reset gate for Evaluator
    }