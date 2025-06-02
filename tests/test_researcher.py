import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.tools import crawl_tool, get_web_search_tool
from langgraph.prebuilt import create_react_agent

# Configure logging to only show INFO level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

async def test_weather():
    """Test the weather assistant functionality."""
    # Create the agent with custom model and tool
    tools = [get_weather]
    model = get_llm_by_type(AGENT_LLM_MAP["researcher"])
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt="You are a helpful weather assistant",
        name="weather_assistant"
    )

    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "What is the weather in San Francisco?"
        }]
    })
    
    messages = result.get("messages", [])
    assert messages, "No messages were returned"
    logger.info(f"Last message: {messages[-1].get('content', '')}")

async def test_research():
    """Test the research assistant functionality."""
    # Create the agent with both tools
    tools = [crawl_tool]
    model = get_llm_by_type(AGENT_LLM_MAP["researcher"])
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt="""You are a research assistant that helps gather comprehensive information from multiple sources.""",
        name="research_assistant"
    )
    
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": """Please help me find information about Geoffrey Hinton's research work. 
            Use both arxiv and crawl to find the information.
            Make sure to clearly label which information comes from which source."""
        }]
    })
    
    messages = result.get("messages", [])
    assert messages, "No messages were returned"
    
    # Log the results for inspection
    logger.info(f"Number of messages: {len(messages)}")
    for message in messages:
        logger.info(f"Message content: {message}")

if __name__ == "__main__":
    # asyncio.run(test_weather())
    asyncio.run(test_research())