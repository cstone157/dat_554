import logging

from ..state import AgentState, Issue
from ..tools import test_runner_tool

logger = logging.getLogger(__name__)


def final_test_node(state: AgentState):
    # Dynamic integration testing
    logger.info(f"Agent_Invoked,'final_test_node',''")
    test_result = test_runner_tool.invoke({"test_command": "pytest"})
    passed = "failed 0" in test_result
    
    issues = []
    if not passed:
        issues.append(Issue(
            source_agent="Final_Test",
            severity="critical",
            description=f"Runtime failure: {test_result}"
        ))
        
    logger.info(f"Agent_Resolved,'final_test_node',''")
    return {
        "final_test_passed": passed,
        "issues": issues
    }