#!/usr/bin/env python3
"""LangGraph application that generates, runs, and evaluates Python code based on user description."""

import argparse
import json
import logging
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from utils.config import PROMPTS
from utils.files import update_work_dir, write_plan
from utils.llm import get_llm, update_llm_config
from utils.log_filter import setup_global_logging, set_global_agent_id, add_file_handler
from utils.state import AgentState
from utils.tool import ask_user, update_project_folder
from utils.user_nodes import prompt_user, prompt_user_feedback

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


def _invoke_llm_with_tools(llm, messages: list, tools: list, max_tool_calls: int = 10) -> str:
    """Invoke LLM with tool support, executing tool calls in a loop.

    Args:
        llm: The LLM instance (bound with tools if needed).
        messages: List of message dicts for the conversation.
        tools: List of LangChain tools to bind.
        max_tool_calls: Maximum number of tool call rounds to prevent infinite loops.

    Returns:
        The final text content from the LLM response.
    """
    logger.info("Invoking LLM with tools. Max tool calls: %d", max_tool_calls)
    tool_map = {t.name: t for t in tools}
    tool_call_count = 0

    while tool_call_count < max_tool_calls:
        response = llm.invoke(messages)

        # Check if the response contains tool calls
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            return response.content.strip()

        # Execute each tool call and add results to messages
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")

            logger.info("Executing tool: %s with args: %s", tool_name, tool_args)

            if tool_name in tool_map:
                tool_result = tool_map[tool_name].invoke(tool_args)
                logger.info("Tool '%s' returned: %s", tool_name, tool_result[:200] if len(str(tool_result)) > 200 else tool_result)
            else:
                tool_result = f"Error: Unknown tool '{tool_name}'"

            # Add assistant response with tool calls to messages
            messages.append(response)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "content": str(tool_result),
                "tool_call_id": tool_call_id,
            })

        tool_call_count += 1

    logger.warning("Reached max tool calls (%d); returning last response content", max_tool_calls)
    print(messages)
    return response.content.strip()


def generate_plan(state: AgentState) -> AgentState:
    """Generate a detailed implementation plan using LLM based on user description."""
    logger.info("Generating plan")
    llm = get_llm()

    # Bind the ask_user tool to the LLM
    llm_with_tools = llm.bind_tools([ask_user])

    prompt = PROMPTS.get("plan", "").format(description=state["user_description"])
    messages = [{"role": "user", "content": prompt}]

    plan = _invoke_llm_with_tools(llm_with_tools, messages, [ask_user])
    logger.info("Generated plan")
    print(plan)

    # Extract plan from markdown fences if present
    match = re.search(r'```markdown\s*\n(.*?)\n```', plan, re.DOTALL)
    if match:
        plan = match.group(1).strip()
    elif plan.startswith("```"):
        lines = plan.strip().split("\n")
        lines.pop(0)  # Remove ``` line
        if lines[-1].strip() == "```":
            lines.pop()  # Remove closing ``` line
        plan = "\n".join(lines).strip()
    logger.info("extracted plan from markdown fences if present")

    # Save plan to project folder
    write_plan(plan)
    return {"plan": plan}


def _extract_file_paths(text: str) -> list[str]:
    """Extract file paths from plan text.

    Looks for patterns like:
    - `path/to/file.py` or `path\\to\\file.py`
    - Lines like 'Create src/module.py' or 'File: src/module.py'
    """
    logger.info("Extracting file paths from plan.")
    files: set[str] = set()
    # Match backtick-enclosed paths (common in markdown plans)
    for m in re.finditer(r'`([^/\s`]{2,}\.\w{1,6})`', text):
        path = m.group(1).replace("\\", "/")
        if not any(c in path for c in "=()[]{}|"):
            files.add(path)
    # Match common directives: 'Create X', 'Add X', 'File: X'
    for m in re.finditer(r'(?:creat|add|file\s*[:–-])\s+[`’"]?([^/\s`’"()]{2,}\.\w{1,6})[`’"]?', text, re.IGNORECASE):
        path = m.group(1).replace("\\", "/")
        if not any(c in path for c in "=()[]{}|"):
            files.add(path)
    return sorted(files)


def plan_to_files(state: AgentState) -> AgentState:
    """Parse the generated plan, extract file paths, create directories and placeholder files."""
    logger.info("Processing plan to create files.")
    project_folder = state.get("project_folder", ".")
    plan = state.get("plan", "")
    if not plan:
        logger.warning("No plan available; skipping plan_to_files.")
        return {}

    file_paths = _extract_file_paths(plan)
    created: list[str] = []
    for rel in file_paths:
        full_path = Path(project_folder) / rel
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            # Write a TODO placeholder so the file exists
            full_path.write_text(
                f"# TODO: implement {rel}\n",
                encoding="utf-8",
            )
            created.append(str(rel))

    logger.info("Created %d files from plan: %s", len(created), created)
    return {
        "plan_file_structure": "\n".join(f"  - {f}" for f in created) if created else "No files to create.",
    }


def parse_tasks(text: str) -> dict[str, list[dict]]:
    """Parse LLM task output into pending and completed arrays.

    Expected format from the LLM (per Agents_task.md prompt):
        T1: Task title
        Description of what needs to be done...
        Priority: critical / high / medium / low
        Effort: small / medium / large
    """
    logger.info("Parsing tasks from LLM output.")
    pending: list[dict] = []
    completed: list[dict] = []

    for block in re.finditer(r'(T\d+\s*[:.]\s*.+?)(?=T\d+\s*[:.]|$)', text, re.DOTALL):
        block_text = block.group(1).strip()

        header_match = re.match(r'(T\d+)\s*[:.]\s*(.*)', block_text.split('\n')[0])
        if not header_match:
            continue

        task_id = header_match.group(1)
        title = header_match.group(2).strip()

        body_lines = block_text.split('\n')[1:]
        body = '\n'.join(body_lines).strip()

        prio_match = re.search(r'Priority\s*[:.]\s*(\w+)', body, re.IGNORECASE)
        priority = prio_match.group(1).lower() if prio_match else "medium"

        effort_match = re.search(r'Effort\s*[:.]\s*(\w+)', body, re.IGNORECASE)
        effort = effort_match.group(1).lower() if effort_match else "medium"

        desc = re.sub(
            r'\n?\s*(?:Priority|Effort)\s*[:.]\s*\w+',
            '',
            body,
            flags=re.IGNORECASE
        ).strip()
        desc = ' '.join(desc.split()) if desc else ""

        pending.append({
            "id": task_id,
            "title": title,
            "description": desc,
            "priority": priority,
            "effort": effort,
        })

    return {"pending_tasks": pending, "completed_tasks": completed}


def generate_tasks(state: AgentState) -> AgentState:
    """Break the implementation plan into a list of actionable tasks using LLM."""
    logger.info("Generating tasks")
    llm = get_llm()

    prompt = PROMPTS.get("task", "").format(plan=state.get("plan", "No plan provided."))
    response = llm.invoke(prompt)
    tasks_text = response.content.strip()
    logger.info("Generated tasks")

    # Extract tasks from markdown fences if present
    match = re.search(r'```markdown\s*\n(.*?)\n```', tasks_text, re.DOTALL)
    if match:
        tasks_text = match.group(1).strip()
    elif tasks_text.startswith("```"):
        lines = tasks_text.strip().split("\n")
        lines.pop(0)  # Remove opening fence
        if lines[-1].strip() == "```":
            lines.pop()  # Remove closing fence
        tasks_text = "\n".join(lines).strip()
    logger.info("extracted tasks from markdown fences if present")

    # Parse tasks into structured pending/completed arrays
    parsed_tasks = parse_tasks(tasks_text)

    # Save structured tasks to project folder as JSON
    project_folder = state.get("project_folder", ".")
    docs_dir = Path(project_folder) / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = docs_dir / "Tasks.json"
    tasks_file.write_text(json.dumps(parsed_tasks, indent=2), encoding="utf-8")
    logger.info("Structured tasks saved to %s", tasks_file)

    return parsed_tasks


def generate_code(state: AgentState) -> AgentState:
    """Generate Python code for a single task using LLM.

    Reads current_task_index from state to determine which pending task
    to work on. Writes the generated code directly to the appropriate
    file in project_folder.
    """
    current_idx = state.get("current_task_index", 0)
    logger.info("Generating code for task")
    logger.info("Generating code task %s", current_idx)
    llm = get_llm()

    project_folder = state.get("project_folder", ".")
    description = state["user_description"]
    plan = state.get("plan", "No plan provided.")
    pending_tasks: list[dict] = list(state.get("pending_tasks", []))
    completed_tasks: list[dict] = list(state.get("completed_tasks", []))

    # Guard against index out of range (shouldn't happen if graph is correct, but safety first)
    if current_idx >= len(pending_tasks):
        logger.warning("current_task_index %d >= len(pending_tasks) %d; no task to generate", current_idx, len(pending_tasks))
        return {"generated_code": "", "review_result": "pass"}  # signal: nothing to do

    task = pending_tasks[current_idx]
    task_id = task.get("id", "?")
    title = task.get("title", "Untitled")
    desc = task.get("description", "")

    # Increment attempt counter for this task
    task_attempts = state.get("task_attempts", 0) + 1
    max_retries = state.get("max_retries", 5)
    logger.info("Generating code for task %d: %s (%s) - attempt %d/%d", current_idx, title, desc, task_attempts, max_retries)

    # --- Determine output file path from task description or plan ---
    filepath: str | None = None
    if match := re.search(r'`([^/\s`]{2,}\.\w{1,6})`', desc):
        filepath = match.group(1).replace("\\", "/")
    if not filepath:
        for m in re.finditer(r'`([^/\s`]{2,}\.\w{1,6})`', plan):
            candidate = m.group(1).replace("\\", "/")
            if not any(c in candidate for c in "=()[]{}|"):
                filepath = candidate
                break
    if not filepath:
        filepath = "generated_code.py"
    out_path = Path(project_folder) / filepath
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Build per-task prompt ---
    task_prompt = PROMPTS.get("code", "").format(
        description=description,
        plan=f"{plan}\n\nCurrent task to implement: {task_id}: {title}\n  {desc}"
    )
    response = llm.invoke(task_prompt)
    code = response.content.strip()

    # --- Extract code from markdown fences if present ---
    match = re.search(r'```python\s*\n(.*?)\n```', code, re.DOTALL)
    if match:
        code = match.group(1).strip()
    elif code.startswith("```"):
        lines = code.strip().split("\n")
        lines.pop(0)  # Remove ``` line
        if lines[-1].strip() == "```":
            lines.pop()  # Remove closing ``` line
        code = "\n".join(lines).strip()
    logger.info("extracted code from markdown fences for %s", task_id)

    # --- Write generated code to the appropriate file ---
    out_path.write_text(code, encoding="utf-8")
    logger.info("Wrote %s (%s) to %s", task_id, title, out_path)

    return {
        "generated_code": code,
        "pending_tasks": pending_tasks,  # unchanged; current task stays until reviewed
        "completed_tasks": completed_tasks,
        "task_attempts": task_attempts,
    }


def check_and_advance_tasks(state: AgentState) -> AgentState:
    """Advance to the next pending task (increment index, reset per-task state)."""
    logger.info("Checking and advancing tasks.")
    pending_tasks: list[dict] = list(state.get("pending_tasks", []))
    completed_tasks: list[dict] = list(state.get("completed_tasks", []))
    current_idx = state.get("current_task_index", 0)

    # Move the task from pending to completed
    if current_idx < len(pending_tasks):
        completed_tasks.append(pending_tasks[current_idx])
        logger.info("Moved task %d (%s) to completed", current_idx, pending_tasks[current_idx].get("title"))

    next_idx = current_idx + 1
    logger.info("Advancing to next task index: %d (pending=%d, completed=%d)",
                next_idx, len(pending_tasks), len(completed_tasks))

    return {
        "current_task_index": next_idx,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
        "review_result": None,  # reset
        "task_attempts": 0,  # reset attempt counter for the new task
    }


def review_and_route(state: AgentState) -> AgentState:
    """Review execution and evaluation results; decide route path.

    Returns a review_result string that the conditional edges use:
      - "fail"              : code failed to run → route back to generate_code
      - "poor"              : evaluation score too low → route back to generate_code
      - "max_retries_exceeded": retry limit reached for this task → advance to next task
      - "pass"              : all good → advance to next task or END
    """
    logger.info("Reviewing and routing task.")
    task_attempts = state.get("task_attempts", 0)
    max_retries = state.get("max_retries", 5)

    # Check if we've exceeded the maximum number of retries
    if task_attempts >= max_retries:
        pending_tasks = state.get("pending_tasks", [])
        current_idx = state.get("current_task_index", 0)
        if current_idx < len(pending_tasks):
            task_info = pending_tasks[current_idx]
            logger.error(
                "Max retries (%d) exceeded for task %d (%s); skipping to next task",
                max_retries, current_idx, task_info.get("title", "Untitled")
            )
            return {"review_result": "max_retries_exceeded"}
        return {"review_result": "pass"}

    exec_result = state.get("execution_result", {})
    returncode = exec_result.get("returncode", -1)
    stderr = exec_result.get("stderr", "")
    evaluation = state.get("evaluation", "")

    # Check 1: Did the code run successfully?
    if returncode != 0:
        logger.warning("Code failed to run (returncode=%d, stderr=%s); routing back to generate_code", returncode, stderr[:200])
        return {"review_result": "fail"}

    # Check 2: Evaluate score from the evaluation text
    # Extract numeric score if present (e.g., "Score: 7/10" or just a number)
    score_match = re.search(r'(\d+\.?\d*)', evaluation)
    if not score_match:
        # No explicit score — do a basic keyword check on the LLM output
        score = evaluate_score(evaluation)
    else:
        score = float(score_match.group(1))
        # Heuristic: if score is very small it might be part of prose, not a 0-10 rating
        if score < 0.1 or (score > 50 and "/" not in evaluation):
            score = evaluate_score(evaluation)

    logger.info("Evaluation score: %.1f", score)
    threshold = float(os.environ.get("EVAL_THRESHOLD", "7.0"))

    if score < threshold:
        logger.warning("Evaluation score %.1f below threshold %.1f; routing back to generate_code",
                       score, threshold)
        return {"review_result": "poor"}

    logger.info("Review passed (score=%.1f >= %.1f); advancing task", score, threshold)
    return {"review_result": "pass"}


def evaluate_score(evaluation: str) -> float:
    """Heuristically extract a 0-10 score from an LLM evaluation text.

    Returns 9.0 (pass) if no clear signal of failure is found.
    """
    logger.info("Evaluating generated code score.")
    eval_lower = evaluation.lower()
    # Explicit bad keywords
    for kw in ["critical error", "fatal error", "syntax error", "does not work",
               "broken", "non-functional", "unacceptable", "failing"]:
        if kw in eval_lower:
            return 3.0
    # Explicit good keywords
    for kw in ["works correctly", "fully functional", "passes all", "excellent", "perfect"]:
        if kw in eval_lower:
            return 9.0
    # Fallback: look for any number that could be a score (heuristic)
    numbers = re.findall(r'\b(\d{1,2})\.?\d*\b', evaluation)
    if numbers:
        num = float(numbers[0])
        if 0 <= num <= 10:
            return num
    # Default to pass
    return 9.0


def has_more_pending(state: AgentState) -> bool:
    """Check if there are more pending tasks to process."""
    logger.info("Checking if there are more pending tasks.")
    pending_tasks: list[dict] = state.get("pending_tasks", [])
    current_idx = state.get("current_task_index", 0)
    has_more = current_idx < len(pending_tasks)
    logger.info("has_more_pending: %s (idx=%d, total=%d)", has_more, current_idx, len(pending_tasks))
    return has_more


def run_code(state: AgentState) -> AgentState:
    """Write generated code to a temp file and execute it."""
    logger.info("Running generated code.")
    project_folder = state.get("project_folder", ".")
    code = state["generated_code"]

    # Determine the Python interpreter (venv if available, else python3)
    venv_dir = Path(project_folder).resolve() / ".venv"
    if venv_dir.exists():
        if os.name == "nt":
            python_exe = str(venv_dir / "Scripts" / "python.exe")
        else:
            python_exe = str(venv_dir / "bin" / "python")
    else:
        python_exe = "python3"

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
        f.write(code)
        temp_path = f.name

    try:
        # Execute the code in the project folder so files land there
        result = subprocess.run(
            [python_exe, temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_folder,
        )
        execution_result = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        logger.info("Execution completed with return code: %s", result.returncode)
    except subprocess.TimeoutExpired:
        execution_result = {
            "stdout": "",
            "stderr": "Execution timed out after 30 seconds",
            "returncode": -1
        }
        logger.warning("Execution timed out after 30 seconds")
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)

    return {"execution_result": execution_result}


def evaluate(state: AgentState) -> AgentState:
    """Evaluate the generated code using LLM."""
    logger.info("Evaluating generated code.")
    llm = get_llm()

    execution = state["execution_result"]
    prompt = PROMPTS.get("eval", "").format(
        description=state["user_description"],
        code=state["generated_code"],
        stdout=execution.get("stdout", ""),
        stderr=execution.get("stderr", ""),
        returncode=execution.get("returncode", -1)
    )

    response = llm.invoke(prompt)
    logger.info("Evaluation completed.")
    return {"evaluation": response.content.strip()}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="LangGraph Code Generator & Evaluator")
    parser.add_argument("--model", type=str, default=None,
                        help="LLM model name (overrides LLM_MODEL_NAME env var)")
    parser.add_argument("-p", "--project_folder", required=True, type=str,
                        help="Project folder path")
    parser.add_argument("-u", "--user_prompt", type=str, default=None,
                        help="Initial user prompt for code generation (skips interactive input)")
    parser.add_argument("-i", "--id", type=str, default=None, dest="agent_id",
                        help="Unique identifier for this agent run (auto-generated if not provided)")
    parser.add_argument("-s", "--skip_feedback", action="store_true", default=False,
                        help="Skip asking the user for feedback during execution")
    parser.add_argument("--eval_threshold", type=float, default=None,
                        help="Minimum evaluation score (0-10) to pass review. Can also be set via EVAL_THRESHOLD env var.")
    parser.add_argument("--max_retries", type=int, default=5,
                        help="Maximum number of code regeneration attempts per task (default: 5)")
    
    return parser.parse_args()



def create_venv(project_folder: str) -> str:
    """Create a Python virtual environment in the project folder if it doesn't exist.

    Returns the path to the venv's Python interpreter.
    """
    venv_dir = Path(project_folder) / ".venv"
    requirements_file = Path(__file__).parent / "requirements.txt"

    if not venv_dir.exists():
        logger.info("Creating virtual environment in %s", venv_dir)
        subprocess.run(
            ["python3", "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

    # Determine the Python executable for this platform
    if os.name == "nt":  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
        pip_exe = venv_dir / "bin" / "pip"

    # Install requirements if the file exists and the venv is fresh
    if requirements_file.exists():
        logger.info("Installing requirements from %s", requirements_file)
        subprocess.run(
            [str(pip_exe), "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
        )

    return str(python_exe)


def main():
    """Main entry point: build and run the LangGraph workflow."""
    args = parse_args()

    # Set EVAL_THRESHOLD env var if user passed --eval_threshold
    if args.eval_threshold is not None:
        os.environ["EVAL_THRESHOLD"] = str(args.eval_threshold)

    # Generate or use provided unique ID
    agent_id = args.agent_id or str(uuid.uuid4())[:8]

    # Update project folder for tools and file operations
    update_project_folder(args.project_folder)

    # Create and configure virtual environment for generated code execution
    venv_python = create_venv(args.project_folder)
    logger.info("Virtual environment Python: %s", venv_python)

    # Set up global logging with agent_id on the root logger
    # so all modules (user_nodes, graph, state, etc.) inherit it.
    setup_global_logging()
    set_global_agent_id(agent_id)

    # Add file handler with the same AgentFormatter
    add_file_handler(args.project_folder + "/workflow.log")
    logger.info("Logging to file: %s", args.project_folder + "/workflow.log")

    # Update LLM configuration with CLI arguments if provided
    if args.model is not None:
        update_llm_config(model_name=args.model)

    # Update the global working directory for file operations
    update_work_dir(args.project_folder)


    # Initialize state with CLI args; prompt_user will fill user_description
    initial_state: AgentState = {}
    initial_state["project_folder"] = args.project_folder
    initial_state["user_prompt"] = args.user_prompt
    initial_state["_skip_feedback"] = args.skip_feedback
    initial_state["current_task_index"] = 0
    initial_state["agent_id"] = agent_id

    initial_state["max_retries"] = args.max_retries
    initial_state["task_attempts"] = 0

    # Build the graph
    graph_builder = StateGraph(AgentState)

    # Add nodes
    graph_builder.add_node("prompt_user", prompt_user)
    graph_builder.add_node("generate_plan", generate_plan)
    graph_builder.add_node("plan_to_files", plan_to_files)
    graph_builder.add_node("generate_tasks", generate_tasks)
    graph_builder.add_node("generate_code", generate_code)
    graph_builder.add_node("run_code", run_code)
    graph_builder.add_node("evaluate", evaluate)
    graph_builder.add_node("review_and_route", review_and_route)
    graph_builder.add_node("check_and_advance_tasks", check_and_advance_tasks)

    # Set entry point
    graph_builder.set_entry_point("prompt_user")
    
    # Linear flow: prompt → plan → files → tasks → generate_code → run → evaluate → review → advance/end
    graph_builder.add_edge("prompt_user", "generate_plan")
    graph_builder.add_edge("generate_plan", "plan_to_files")
    graph_builder.add_edge("plan_to_files", "generate_tasks")
    graph_builder.add_edge("generate_tasks", "generate_code")
    graph_builder.add_edge("generate_code", "run_code")
    graph_builder.add_edge("run_code", "evaluate")
    graph_builder.add_edge("evaluate", "review_and_route")

    # Conditional edges from review_and_route:
    #   "fail" or "poor"              → generate_code (retry current task)
    #   "max_retries_exceeded" or "pass" → check_and_advance_tasks (move to next task or END)
    graph_builder.add_conditional_edges(
        "review_and_route",
        lambda state: state.get("review_result", "pass"),
        {
            "fail": "generate_code",
            "poor": "generate_code",
            "max_retries_exceeded": "check_and_advance_tasks",
            "pass": "check_and_advance_tasks",
        },
    )

    # After advancing, decide: more tasks? loop back to generate_code. Done? END.
    graph_builder.add_conditional_edges(
        "check_and_advance_tasks",
        lambda state: has_more_pending(state),
        {True: "generate_code", False: END},
    )

    # Compile the graph
    app = graph_builder.compile()

    # Run the workflow
    print("=" * 60)
    print("  Python Code Generator & Evaluator")
    print("=" * 60)
    print()

    result = app.invoke(initial_state)
    logger.info("Workflow completed.")

    # Build and display results
    lines = []
    lines.append("\n" + "=" * 60)
    lines.append("  RESULTS")
    lines.append("=" * 60)
    lines.append("\n📝 User Description:")
    lines.append(f"   {result['user_description']}")
    lines.append("\n�️  Implementation Plan:")
    lines.append("-" * 40)
    lines.append(result.get("plan", "No plan generated."))
    lines.append("-" * 40)    
    pending = result.get("pending_tasks", [])
    completed = result.get("completed_tasks", [])
    if pending or completed:
        lines.append("\n✅ Tasks:")
        if pending:
            lines.append("   Pending:")
            for task in pending:
                lines.append(f"      [{task.get('id', '?')}] {task.get('title', 'Untitled')}")
        if completed:
            lines.append("   Completed:")
            for task in completed:
                lines.append(f"      [{task.get('id', '?')}] {task.get('title', 'Untitled')}")
        lines.append("-" * 40)    
    lines.append("\n�💻 Generated Code:")
    lines.append("-" * 40)
    lines.append(result["generated_code"])
    lines.append("-" * 40)

    exec_result = result["execution_result"]
    lines.append("\n⚡ Execution Results:")
    if exec_result["stdout"]:
        lines.append(f"\n   Standard Output:\n   {exec_result['stdout']}")
    if exec_result["stderr"]:
        lines.append(f"\n   Standard Error:\n   {exec_result['stderr']}")
    lines.append(f"   Return Code: {exec_result['returncode']}")

    lines.append("\n📊 Evaluation:")
    lines.append("-" * 40)
    lines.append(result["evaluation"])
    lines.append("-" * 40)
    output_text = "\n".join(lines) + "\n"

    # Print to console
    print(output_text)

    # # Write to log file via logger
    # for line in output_text.splitlines():
    #     logger.info(line)

    # Save results to files
    project_folder = result.get("project_folder", "tmp")
    Path(project_folder + "/results.txt").write_text(output_text, encoding="utf-8")
    # Path(project_folder + "/generated_code.py").write_text(result["generated_code"], encoding="utf-8")
    print(f"Results written to {project_folder}")



if __name__ == "__main__":
    main()
