import logging

from ..state import AgentState, Issue
from ..tools import linter_tool

logger = logging.getLogger(__name__)


def evaluator_node(state: AgentState):
    # Runs static verification
    logger.info(f"Agent_Invoked,'evaluator_node',''")
    code_content = state.get("workspace", {}).get("main.py", "")
    linter_result = linter_tool.invoke({"file_path": "main.py", "code": code_content})
    
    has_error = "SYNTAX_ERROR" in linter_result
    issues = []
    if has_error:
        issues.append(Issue(
            source_agent="Evaluator",
            severity="critical",
            description=linter_result,
            task_id=state.get("current_task_id")
        ))
    
    logger.info(f"Agent_Resolved,'evaluator_node',''")
    return {
        "evaluation_passed": not has_error,
        "issues": issues
    }