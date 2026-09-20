#!/usr/bin/env python3
"""LangGraph application that generates, runs, and evaluates Python code based on user description."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s, %(message)s")

# Load environment variables from .env file
load_dotenv()


class AgentState(TypedDict):
    """State schema for the code generation agent."""
    user_description: str
    generated_code: str
    execution_result: dict  # {stdout: str, stderr: str, returncode: int}
    evaluation: str


# Prompt templates
PROMPT_GENERATE_CODE = ""
PROMPT_EVALUATE = ""
with open(Path("agents/Agents_code.md").resolve(), "r") as f:
    PROMPT_GENERATE_CODE = f.read()
with open(Path("agents/Agents_eval.md").resolve(), "r") as f:
    PROMPT_EVALUATE = f.read()


def prompt_user(state: AgentState) -> AgentState:
    """Get user description via CLI input."""
    if state.get("user_description"):
        return state

    description = input("Enter a Python function description:\n> ").strip()
    while not description:
        description = input("Description cannot be empty. Enter a Python function description:\n> ").strip()
    return {"user_description": description}


def generate_code(state: AgentState) -> AgentState:
    """Generate Python code using LLM based on user description."""
    llm_base_url = os.environ.get("LLM_BASE_URL", "")
    llm_name = os.environ.get("LLM_MODEL_NAME", "qwen3.6")
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm = ChatOpenAI(model=llm_name, temperature=0, api_key=llm_api_key, base_url=llm_base_url if llm_base_url else None)

    prompt = PROMPT_GENERATE_CODE.format(description=state["user_description"])
    response = llm.invoke(prompt)
    code = response.content.strip()

    # Extract code from markdown fences if present
    import re
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

    return {"generated_code": code}


def run_code(state: AgentState) -> AgentState:
    """Write generated code to a temp file and execute it."""
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
    except subprocess.TimeoutExpired:
        execution_result = {
            "stdout": "",
            "stderr": "Execution timed out after 30 seconds",
            "returncode": -1
        }
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)

    return {"execution_result": execution_result}


def evaluate(state: AgentState) -> AgentState:
    """Evaluate the generated code using LLM."""
    llm_name = __import__("os").environ.get("LLM_MODEL_NAME", "gpt-4o-mini")
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
    return {"evaluation": response.content.strip()}


def main():
    """Main entry point: build and run the LangGraph workflow."""
    # Build the graph
    graph_builder = StateGraph(AgentState)

    # Add nodes
    graph_builder.add_node("prompt_user", prompt_user)
    graph_builder.add_node("generate_code", generate_code)
    graph_builder.add_node("run_code", run_code)
    graph_builder.add_node("evaluate", evaluate)

    # Set entry point and edges (linear chain)
    graph_builder.set_entry_point("prompt_user")
    graph_builder.add_edge("prompt_user", "generate_code")
    graph_builder.add_edge("generate_code", "run_code")
    graph_builder.add_edge("run_code", "evaluate")
    graph_builder.add_edge("evaluate", END)

    # Compile the graph
    app = graph_builder.compile()

    # Initialize state (empty - prompt_user will get input)
    initial_state: AgentState = {}

    # Run the workflow
    print("=" * 60)
    print("  Python Code Generator & Evaluator")
    print("=" * 60)
    print()

    result = app.invoke(initial_state)

    # Display results
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print("\n📝 User Description:")
    print(f"   {result['user_description']}")

    print("\n💻 Generated Code:")
    print("-" * 40)
    print(result["generated_code"])
    print("-" * 40)

    exec_result = result["execution_result"]
    print("\n⚡ Execution Results:")
    if exec_result["stdout"]:
        print(f"\n   Standard Output:\n   {exec_result['stdout']}")
    if exec_result["stderr"]:
        print(f"\n   Standard Error:\n   {exec_result['stderr']}")
    print(f"   Return Code: {exec_result['returncode']}")

    print("\n📊 Evaluation:")
    print("-" * 40)
    print(result["evaluation"])
    print("-" * 40)
    print()


if __name__ == "__main__":
    main()
