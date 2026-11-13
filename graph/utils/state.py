from typing import Annotated, Dict, List, Literal, Optional, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import operator


class Task(BaseModel):
    id: str = Field(description="Unique task identifier, e.g., TASK-01")
    title: str
    description: str
    dependencies: List[str] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    assigned_files: List[str] = Field(default_factory=list)


class Issue(BaseModel):
    source_agent: Literal[
        "Evaluator", "Final_Test", "Router", "Executor", "Code"
    ]
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    task_id: Optional[str] = None
    suggested_fix: Optional[str] = None


class ExecutionResult(BaseModel):
    task_id: str
    stdout: str
    stderr: str
    return_code: int
    duration_seconds: float
    docker_container: str


class AgentState(TypedDict):
    # ── Core Inputs ──────────────────────────────────────────────
    user_request: str                          # Raw user description
    project_specification: Optional[str]       # Structured plan from Plan agent

    # ── Task Tracking ────────────────────────────────────────────
    tasks: List[Task]                          # Decomposed task list
    current_task_id: Optional[str]             # Currently processing task
    completed_tasks: List[str]                 # Finished task IDs

    # ── Code & Execution ─────────────────────────────────────────
    workspace: Dict[str, str]                  # File path → content  # Consider deleting me
    execution_results: Annotated[
        List[ExecutionResult], operator.add   # Accumulated results
    ]

    # ── Evaluation ───────────────────────────────────────────────
    issues: Annotated[List[Issue], operator.add]  # Accumulated issues
    evaluation_passed: bool                    # Latest evaluator result
    final_test_passed: bool                    # Final test result

    # ── Orchestration Control ────────────────────────────────────
    workflow_phase: str                        # Current phase identifier
    iteration_count: int                       # Loop counter
    max_iterations: int                        # Safety limit (default 50)
    eval_periodicity: int                      # Run evaluator every N iterations (default 3)
    next_node: str                             # Next routing target
