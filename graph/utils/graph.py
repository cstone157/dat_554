import logging

from langgraph.graph import END, StateGraph

from .plan import generate_plan
from .task import generate_task
from .state import AgentState

logger = logging.getLogger(__name__)

def generate_graph():
    """
    Generate a state graph for the agent.

    Returns:
        A StateGraph instance representing the agent's state transitions.
    """
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("generate_plan", generate_plan)
    graph_builder.add_node("generate_task", generate_task)

    # Set entry point
    graph_builder.set_entry_point("generate_plan")

    # Add edges between nodes
    graph_builder.add_edge("generate_plan", "generate_task")
    graph_builder.add_edge("generate_task", END)

    # Build the final graph from the builder
    graph = graph_builder.compile()

    return graph
