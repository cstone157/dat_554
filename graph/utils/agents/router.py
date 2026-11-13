import json
from typing import Literal, Optional

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..state import AgentState
from ..llm import get_llm

logger = logging.getLogger(__name__)

class RouterDecision(BaseModel):
    next_node: Literal["Planner", "Tasker", "Coder", "Evaluator", "Final_Test", "COMPLETE"] = Field(
        description="The target worker to route to next."
    )
    reasoning: str = Field(description="System diagnostic reasoning for this routing decision.")
    current_task_id: Optional[str] = Field(None, description="Selects or updates the current task ID to execute.")

ROUTER_SYSTEM_PROMPT = """You are the Lead Systems Architect and Routing Supervisor for an automated software engineering platform.
Evaluate the current system state and route control cleanly:
1. If no architectural plan exists -> Route to 'Planner'.
2. If a plan exists but no tasks are decomposed -> Route to 'Tasker'.
3. If tasks exist, identify the first 'pending' or 'failed' task -> Route to 'Coder' and specify `current_task_id`.
4. If code was recently committed -> Route to 'Evaluator'.
5. If Evaluator logged critical issues -> Route back to 'Coder'.
6. If all tasks are completed and Evaluator passed -> Route to 'Final_Test'.
7. If Final_Test passes cleanly -> Route to 'COMPLETE'.
8. If iterations exceed threshold -> Force 'COMPLETE' with appropriate issue logging.
"""

def router_node(state: AgentState):
    logger.info(f"Agent_Invoked,'router_node',''")

    # print(state)

    llm = get_llm().with_structured_output(RouterDecision)
    
    # State projection for token management
    summary = {
        "has_specification": state.get("project_specification") is not None,
        "task_count": len(state.get("tasks", [])),
        "tasks_status": [{"id": t.id, "status": t.status} for t in state.get("tasks", [])],
        "eval_passed": state.get("evaluation_passed", False),
        "test_passed": state.get("final_test_passed", False),
        "unresolved_issues": [i.dict() for i in state.get("issues", []) if i.severity == "critical"],
        "iterations": state.get("iteration_count", 0)
    }

    decision: RouterDecision = llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"System Snapshot:\n{json.dumps(summary, indent=2)}")
    ])
    
    return {
        "next_node": decision.next_node,
        "current_task_id": decision.current_task_id or state.get("current_task_id"),
        "iteration_count": state.get("iteration_count", 0) + 1
    }