import logging

from langchain_core.messages import HumanMessage, SystemMessage

from ..tools import save_file

from ..state import AgentState
from ..llm import get_llm

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = """You are an Enterprise Architect.  Design a plan to implement the user request in detail.  
The plan should include detailed steps, considerations, and potential challenges.
The language that you should use is Python."""
PROMPT = "Define an architectural spec for: {user_request}"

def planner_node(state: AgentState):
    logger.info(f"Agent_Invoked,'planner_node','{state.get('user_request', '').split('\n')[0]}'")
    
    llm = get_llm()
    prompt = PROMPT.format(user_request=state['user_request'])
    res = llm.invoke([SystemMessage(content=SYSTEM_MESSAGE), HumanMessage(content=prompt)])

    # Save the project specification to the doc folder
    save_file('doc/Plan.md', res.content)
    
    return {
        "project_specification": res.content,
        "issues": []
    }