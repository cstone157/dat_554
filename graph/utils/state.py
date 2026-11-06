from langchain_protocol import TypedDict

class AgentState(TypedDict, total=False):
    """State schema for the code generation agent."""
    agent_id: str
    eval_threshold: float
    # Maximum number of retries for the agent
    max_retries: int
    # Maximum number of tool calls for the agent
    max_tool_calls: int
    # Plan for the agentic workflow
    plan: str
    project_folder: str
    skip_user_prompt: bool
    # User-provided prompt for the agent
    user_prompt: str
    # List of pending tasks
    pending_tasks: list
    # List of completed tasks
    completed_tasks: list
    # Next task to be processed
    next_task: str
