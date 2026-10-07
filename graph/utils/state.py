from langchain_protocol import TypedDict

class AgentState(TypedDict, total=False):
    """State schema for the code generation agent."""
    user_prompt: str
    user_description: str
    plan: str
    pending_tasks: list[dict]
    completed_tasks: list[dict]
    plan_file_structure: str
    user_feedback: str
    generated_code: str
    execution_result: dict  # {stdout: str, stderr: str, returncode: int}
    evaluation: str
    model: str
    project_folder: str
    current_task_index: int
    review_result: str  # "pass" | "fail" | "poor_score"
    agent_id: str
    max_retries: int
    task_attempts: int  # retry count for the current task (0 before first run, incremented on each generate_code)