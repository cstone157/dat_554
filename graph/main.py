#!/usr/bin/env python3
"""LangGraph application that generates, runs, and evaluates Python code based on user description."""

import argparse
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class AgentState(TypedDict, total=False):
    """State schema for the code generation agent."""
    user_prompt: str
    user_description: str
    plan: str
    tasks: str
    plan_file_structure: str
    user_feedback: str
    generated_code: str
    execution_result: dict  # {stdout: str, stderr: str, returncode: int}
    evaluation: str
    model: str
    project_folder: str


# Prompt templates
PROMPT_PLANNER = ""
PROMPT_TASKER = ""
PROMPT_GENERATE_CODE = ""
PROMPT_EVALUATE = ""
with open(Path("agents/Agents_plan.md").resolve(), "r") as f:
    PROMPT_PLANNER = f.read()
with open(Path("agents/Agents_task.md").resolve(), "r") as f:
    PROMPT_TASKER = f.read()
with open(Path("agents/Agents_code.md").resolve(), "r") as f:
    PROMPT_GENERATE_CODE = f.read()
with open(Path("agents/Agents_eval.md").resolve(), "r") as f:
    PROMPT_EVALUATE = f.read()


def prompt_user(state: AgentState) -> AgentState:
    """Get user description via CLI input."""
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
    """Get user feedback via CLI input for iterative refinement."""
    if state.get("_skip_feedback"):
        logger.info("--skip_feedback set, skipping feedback step.")
        return {"user_feedback": state.get("user_feedback", ""), "_has_feedback": False}
    logger.info("Prompting user for feedback.")
    feedback = input("\nEnter feedback or improvements (leave empty to skip):\n> ").strip()
    has_feedback = bool(feedback)
    return {"user_feedback": feedback if feedback else state.get("user_feedback", ""), "_has_feedback": has_feedback}


def generate_plan(state: AgentState) -> AgentState:
    """Generate a detailed implementation plan using LLM based on user description."""
    llm_base_url = os.environ.get("LLM_BASE_URL", "")
    llm_name = state.get("model") or os.environ.get("LLM_MODEL_NAME", "qwen3.6")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    logger.info("Generating plan using LLM model: %s", llm_name)
    llm = ChatOpenAI(model=llm_name, temperature=0, api_key=llm_api_key, base_url=llm_base_url if llm_base_url else None)

    prompt = PROMPT_PLANNER.format(description=state["user_description"])
    response = llm.invoke(prompt)
    plan = response.content.strip()
    logger.info("Generated plan")
    
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
    project_folder = state.get("project_folder", ".")
    docs_dir = Path(project_folder) / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    plan_file = docs_dir / "Plan.md"
    plan_file.write_text(plan, encoding="utf-8")
    logger.info("Plan saved to %s", plan_file)

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


def generate_tasks(state: AgentState) -> AgentState:
    """Break the implementation plan into a list of actionable tasks using LLM."""
    llm_base_url = os.environ.get("LLM_BASE_URL", "")
    llm_name = state.get("model") or os.environ.get("LLM_MODEL_NAME", "qwen3.6")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    logger.info("Generating tasks using LLM model: %s", llm_name)
    llm = ChatOpenAI(model=llm_name, temperature=0, api_key=llm_api_key, base_url=llm_base_url if llm_base_url else None)

    prompt = PROMPT_TASKER.format(plan=state.get("plan", "No plan provided."))
    response = llm.invoke(prompt)
    tasks = response.content.strip()
    logger.info("Generated tasks")

    # Extract tasks from markdown fences if present
    match = re.search(r'```markdown\s*\n(.*?)\n```', tasks, re.DOTALL)
    if match:
        tasks = match.group(1).strip()
    elif tasks.startswith("```"):
        lines = tasks.strip().split("\n")
        lines.pop(0)  # Remove opening fence
        if lines[-1].strip() == "```":
            lines.pop()  # Remove closing fence
        tasks = "\n".join(lines).strip()
    logger.info("extracted tasks from markdown fences if present")

    # Save tasks to project folder
    project_folder = state.get("project_folder", ".")
    docs_dir = Path(project_folder) / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = docs_dir / "Task.md"
    tasks_file.write_text(tasks, encoding="utf-8")
    logger.info("Tasks saved to %s", tasks_file)

    return {"tasks": tasks}


def generate_code(state: AgentState) -> AgentState:
    """Generate Python code using LLM based on user description and plan."""
    llm_base_url = os.environ.get("LLM_BASE_URL", "")
    llm_name = state.get("model") or os.environ.get("LLM_MODEL_NAME", "qwen3.6")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    logger.info("Generating code using LLM model : %s", llm_name)
    llm = ChatOpenAI(model=llm_name, temperature=0, api_key=llm_api_key, base_url=llm_base_url if llm_base_url else None)

    prompt = PROMPT_GENERATE_CODE.format(
        description=state["user_description"],
        plan=state.get("plan", "No plan provided.")
    )
    response = llm.invoke(prompt)
    code = response.content.strip()
    logger.info("Generated code")
    
    # Extract code from markdown fences if present
    match = re.search(r'```python\s*\n(.*?)\n```', code, re.DOTALL)
    if match:
        code = match.group(1).strip()
    elif code.startswith("```"):
        # Remove opening and closing fences even without language specifier
        lines = code.strip().split("\n")
        lines.pop(0)  # Remove ``` line
        if lines[-1].strip() == "```":
            lines.pop()  # Remove closing ``` line
        code = "\n".join(lines).strip()
    logger.info("extracted code from markdown fences if present")

    return {"generated_code": code}


def run_code(state: AgentState) -> AgentState:
    """Write generated code to a temp file and execute it."""
    logger.info("Running generated code.")
    code = state["generated_code"]

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
        f.write(code)
        temp_path = f.name

    try:
        # Execute the code
        result = subprocess.run(
            ["python3", temp_path],
            capture_output=True,
            text=True,
            timeout=30
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
    llm_name = state.get("model") or __import__("os").environ.get("LLM_MODEL_NAME", "gpt-4o-mini")
    llm_api_key = __import__("os").environ.get("LLM_API_KEY", "")
    llm_base_url = __import__("os").environ.get("LLM_BASE_URL", "")
    llm = ChatOpenAI(model=llm_name, temperature=0, api_key=llm_api_key, base_url=llm_base_url if llm_base_url else None)

    execution = state["execution_result"]
    prompt = PROMPT_EVALUATE.format(
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
    parser.add_argument("-s", "--skip_feedback", action="store_true", default=False,
                        help="Skip asking the user for feedback during execution")
    
    return parser.parse_args()


def main():
    """Main entry point: build and run the LangGraph workflow."""
    args = parse_args()

    # Set up log file if specified
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s : %(message)s",
        handlers=[
            logging.FileHandler(args.project_folder + "/workflow.log"),
            logging.StreamHandler()
        ]
    )
    logger.info("Logging to file: %s", args.project_folder + "/workflow.log")

    # Initialize state with CLI args; prompt_user will fill user_description
    initial_state: AgentState = {}
    initial_state["project_folder"] = args.project_folder
    initial_state["user_prompt"] = args.user_prompt
    initial_state["_skip_feedback"] = args.skip_feedback

    if args.model:
        initial_state["model"] = args.model

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

    # Conditionally add feedback node if not skipped
    if not args.skip_feedback:
        graph_builder.add_node("prompt_user_feedback", prompt_user_feedback)

    # Set entry point and edges (plan -> create files -> tasks -> generate code -> run -> evaluate, with optional feedback loop)
    graph_builder.set_entry_point("prompt_user")
    graph_builder.add_edge("prompt_user", "generate_plan")
    graph_builder.add_edge("generate_plan", "plan_to_files")
    graph_builder.add_edge("plan_to_files", "generate_tasks")
    graph_builder.add_edge("generate_tasks", "generate_code")
    graph_builder.add_edge("generate_code", "run_code")
    
    if not args.skip_feedback:
        graph_builder.add_edge("run_code", "prompt_user_feedback")
        graph_builder.add_conditional_edges(
            "prompt_user_feedback",
            lambda state: "generate_code" if state.get("_has_feedback") else "evaluate",
            {"generate_code": "generate_code", "evaluate": "evaluate"},
        )
    else:
        graph_builder.add_edge("run_code", "evaluate")
    
    graph_builder.add_edge("evaluate", END)

    # Compile the graph
    app = graph_builder.compile()

    # Run the workflow
    print("=" * 60)
    print("  Python Code Generator & Evaluator")
    print("=" * 60)
    print()

    result = app.invoke(initial_state)

    # Initialize state with CLI args; prompt_user will fill user_description
    initial_state: AgentState = {}
    if args.model:
        initial_state["model"] = args.model

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
    lines.append("\n✅ Tasks:")
    lines.append("-" * 40)
    lines.append(result.get("tasks", "No tasks generated."))
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

    # Write to log file via logger
    for line in output_text.splitlines():
        logger.info(line)

    # Save results to files
    project_folder = result.get("project_folder", "tmp")
    Path(project_folder + "/results.txt").write_text(output_text, encoding="utf-8")
    Path(project_folder + "/generated_code.py").write_text(result["generated_code"], encoding="utf-8")
    print(f"Results written to {project_folder}")



if __name__ == "__main__":
    main()
