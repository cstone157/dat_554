import logging

from langgraph.graph import END, StateGraph

from .agents import router_node, planner_node, tasker_node, coder_node
from .state import AgentState


logger = logging.getLogger(__name__)

def generate_graph():
    """
    Generate a state graph for the agent.

    Returns:
        A StateGraph instance representing the agent's state transitions.
    """
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("router", router_node)
    graph_builder.add_node("planner", planner_node)
    graph_builder.add_node("tasker", tasker_node)
    graph_builder.add_node("coder", coder_node)
    
    # Set entry point
    graph_builder.set_entry_point("router")

    # Add edges between nodes
    graph_builder.add_edge("planner", "router")
    graph_builder.add_edge("tasker", "router")
    graph_builder.add_edge("coder", END)
    
    # Add conditional edges
    graph_builder.add_conditional_edges(
        "router",
        lambda state: state["next_node"],
        {
            "Planner": "planner",
            "Tasker": "tasker",
            "Coder": "coder",
            # "Evaluator": "Evaluator",
            # "Final_Test": "Final_Test",
            "COMPLETE": END
        }
    )


    # Build the final graph from the builder
    graph = graph_builder.compile()

    return graph
