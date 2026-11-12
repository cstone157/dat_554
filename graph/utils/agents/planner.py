import logging

from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState
from ..llm import get_llm

logger = logging.getLogger(__name__)

def planner_node(state: AgentState):
    logger.info(f",Agent_Invoked,'planner_node','{state.get('user_request', '').split('\n')[0]}'")
    
    llm = get_llm()
    prompt = f"Define an architectural spec for: {state['user_request']}"
    res = llm.invoke([SystemMessage(content="You are an Enterprise Architect."), HumanMessage(content=prompt)])
    
    return {
        "project_specification": res.content,
        "issues": []
    }