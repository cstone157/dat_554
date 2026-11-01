from langchain_protocol import TypedDict

class AgentState(TypedDict, total=False):
    """State schema for the code generation agent."""
    user_prompt: str
    skip_user_prompt: bool