import logging
from typing import List

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState, Task
from ..llm import get_llm
from ..tools import save_file

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = "You are a Technical Project Manager."
PROMPT = "Decompose this specification into atomic tasks:\n{project_specification}"

def tasker_node(state: AgentState):
    class TaskList(BaseModel):
        tasks: List[Task]

    logger.info(f"Agent_Invoked,'tasker_node','{state.get('project_specification', '').split('\n')[0]}'")

    llm = get_llm().with_structured_output(TaskList)
    prompt = PROMPT.format(project_specification=state['project_specification'])
    result = llm.invoke([SystemMessage(content=SYSTEM_MESSAGE), HumanMessage(content=prompt)])

    # Save the task list to the doc folder
    save_file('doc/Tasks.md', "\n".join([f"- {task.id}: {task.description}" for task in result.tasks]))
    
    return {"tasks": result.tasks}