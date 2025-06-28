import json
import pytest
from unittest.mock import patch, MagicMock

with patch("src.llms.llm.get_llm_by_type", return_value=MagicMock()):
    from langgraph.types import Command
    from src.config import SearchEngine
    from langchain_core.messages import HumanMessage

# Mock data
MOCK_SEARCH_RESULTS = [
    {"title": "Test Title 1", "content": "Test Content 1"},
    {"title": "Test Title 2", "content": "Test Content 2"},
]


@pytest.fixture
def mock_state():
    return {
        "messages": [HumanMessage(content="test query")],
        "background_investigation_results": None,
    }


@pytest.fixture
def mock_configurable():
    mock = MagicMock()
    mock.max_search_results = 5
    return mock


@pytest.fixture
def mock_config():
    return MagicMock()


@pytest.fixture
def patch_config_from_runnable_config(mock_configurable):
    with patch(
        "src.graph.nodes.Configuration.from_runnable_config",
        return_value=mock_configurable,
    ):
        yield
