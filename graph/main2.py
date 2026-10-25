#!/usr/bin/env python3
"""LangGraph application that generates, runs, and evaluates Python code based on user description."""

import argparse
import logging
import os
import uuid

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from utils.config import PROMPTS
from utils.files import update_project_folder, write_plan, create_venv
from utils.llm import get_llm, update_llm_config, invoke_llm_with_tools
from utils.log_filter import setup_global_logging, set_global_agent_id, add_file_handler
from utils.state import AgentState
from utils.user import prompt_user, prompt_user_feedback, ask_user
from utils.results import _generate_results_printout

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

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

    # Initialize state with CLI args; prompt_user will fill user_description
    initial_state: AgentState = {}
    initial_state["project_folder"] = args.project_folder
    initial_state["user_prompt"] = args.user_prompt
    initial_state["_skip_feedback"] = args.skip_feedback
    initial_state["current_task_index"] = 0
    initial_state["agent_id"] = agent_id

    initial_state["max_retries"] = args.max_retries
    initial_state["task_attempts"] = 0

    



if __name__ == "__main__":
    main()