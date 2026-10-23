import os
import logging

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()

# Load the logger
logger = logging.getLogger(__name__)

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "qwen3.6")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_TEMPERATURE = os.environ.get("LLM_TEMPERATURE", 0.2)

OPEN_AI = None

def get_llm_config():
    """
    Get the current LLM configuration from environment variables.

    Returns a dictionary containing the base URL, model name, and API key.
    """

    return {
        "base_url": LLM_BASE_URL,
        "model_name": LLM_MODEL_NAME,
        "api_key": LLM_API_KEY,
        "temperature": LLM_TEMPERATURE,
    }

def get_llm(temperature=None):
    """
    Get an instance of the ChatOpenAI LLM with the specified temperature.

    Args:
        temperature (float, optional): The temperature setting for the LLM. Defaults to LLM_TEMPERATURE.

    Returns:
        ChatOpenAI: An instance of the ChatOpenAI LLM.
    """
    global OPEN_AI
    if temperature is not None and temperature != LLM_TEMPERATURE:
        llm_config = get_llm_config()
        llm_config["temperature"] = temperature
        logger.info("Cutom LLM configuration: %s", llm_config())
        return ChatOpenAI(
            model=llm_config["model_name"],
            temperature=llm_config["temperature"],
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
        )
    if OPEN_AI is None:
        update_llm_config()

    return OPEN_AI

def update_llm_config(base_url=None, model_name=None, api_key=None, temperature=None): 
    """
    Update the LLM configuration with the provided values.

    Args:
        base_url (str, optional): The base URL for the LLM API.
        model_name (str, optional): The name of the LLM model.
        api_key (str, optional): The API key for accessing the LLM service.
        temperature (float, optional): The temperature setting for the LLM.
    """
    
    global LLM_BASE_URL, LLM_MODEL_NAME, LLM_API_KEY, LLM_TEMPERATURE, OPEN_AI
    if base_url is not None:
        LLM_BASE_URL = base_url
    if model_name is not None:
        LLM_MODEL_NAME = model_name
    if api_key is not None:
        LLM_API_KEY = api_key
    if temperature is not None:
        LLM_TEMPERATURE = temperature

    logger.info("Updated LLM configuration: %s", get_llm_config())
    OPEN_AI = ChatOpenAI(
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
    )

def invoke_llm_with_tools(llm, messages: list, tools: list, max_tool_calls: int = 10) -> str:
    """Invoke LLM with tool support, executing tool calls in a loop.

    Args:
        llm: The LLM instance (bound with tools if needed).
        messages: List of message dicts for the conversation.
        tools: List of LangChain tools to bind.
        max_tool_calls: Maximum number of tool call rounds to prevent infinite loops.

    Returns:
        The final text content from the LLM response.
    """
    logger.info("Invoking LLM with tools. Max tool calls: %d", max_tool_calls)
    tool_map = {t.name: t for t in tools}
    tool_call_count = 0

    while tool_call_count < max_tool_calls:
        response = llm.invoke(messages)

        # Check if the response contains tool calls
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            return response.content.strip()

        # Execute each tool call and add results to messages
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")

            logger.info("Executing tool: %s with args: %s", tool_name, tool_args)

            if tool_name in tool_map:
                tool_result = tool_map[tool_name].invoke(tool_args)
                logger.info("Tool '%s' returned: %s", tool_name, tool_result[:200] if len(str(tool_result)) > 200 else tool_result)
            else:
                tool_result = f"Error: Unknown tool '{tool_name}'"

            # Add assistant response with tool calls to messages
            messages.append(response)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "content": str(tool_result),
                "tool_call_id": tool_call_id,
            })

        tool_call_count += 1

    logger.warning("Reached max tool calls (%d); returning last response content", max_tool_calls)
    print(messages)
    return response.content.strip()