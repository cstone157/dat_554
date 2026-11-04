from langchain_protocol import TypedDict

class AgentState(TypedDict, total=False):
    """State schema for the code generation agent."""
    agent_id: str
    eval_threshold: float
    max_retries: int
    # Plan for the agentic workflow
    plan: str
    project_folder: str
    skip_user_prompt: bool
    # User-provided prompt for the agent
    user_prompt: str
