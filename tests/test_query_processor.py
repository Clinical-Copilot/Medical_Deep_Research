import pytest
from unittest.mock import Mock, AsyncMock
from src.utils.query_processor import (
    QueryProcessor,
    QueryStrategy,
    ToolDescription,
    QueryProcessingError
)

# Mock LLM responses for different strategies
MOCK_PARAPHRASE_RESPONSE = """
- What are the symptoms of COVID-19
- What signs indicate someone has coronavirus
- What are the clinical manifestations of COVID-19
"""

MOCK_EXPAND_RESPONSE = """
- COVID-19 symptoms including fever, cough, loss of taste and smell
- coronavirus symptoms in adults and children
- SARS-CoV-2 clinical presentation and early warning signs
"""

@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing"""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock()
    return mock

@pytest.fixture
def query_processor(mock_llm):
    """Create a QueryProcessor with a mock LLM"""
    processor = QueryProcessor("basic")
    processor.llm = mock_llm
    return processor

@pytest.mark.asyncio
async def test_direct_strategy(query_processor):
    """Test that DIRECT strategy returns original query unchanged"""
    query = "What are the symptoms of COVID?"
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.DIRECT
    )
    
    result = await query_processor.process_query(query, tool_desc)
    
    assert result == [query]
    # Ensure LLM was not called
    query_processor.llm.ainvoke.assert_not_called()

@pytest.mark.asyncio
async def test_paraphrase_strategy(query_processor):
    """Test PARAPHRASE strategy generates variations"""
    query = "What are the symptoms of COVID?"
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.PARAPHRASE,
        max_variations=3
    )
    
    # Mock LLM response
    query_processor.llm.ainvoke.return_value.content = MOCK_PARAPHRASE_RESPONSE
    
    result = await query_processor.process_query(query, tool_desc)
    
    assert len(result) <= tool_desc.max_variations
    assert query in result  # Original query should be included
    assert all(isinstance(q, str) for q in result)  # All results should be strings
    assert all(len(q.strip()) > 0 for q in result)  # No empty queries

@pytest.mark.asyncio
async def test_expand_strategy(query_processor):
    """Test EXPAND strategy adds relevant context"""
    query = "What are the symptoms of COVID?"
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.EXPAND,
        max_variations=3
    )
    
    # Mock LLM response
    query_processor.llm.ainvoke.return_value.content = MOCK_EXPAND_RESPONSE
    
    result = await query_processor.process_query(query, tool_desc)
    
    assert len(result) <= tool_desc.max_variations
    assert query in result  # Original query should be included
    assert any("fever" in q.lower() for q in result)  # Should include expanded terms

@pytest.mark.asyncio
async def test_empty_query_handling(query_processor):
    """Test handling of empty queries"""
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.PARAPHRASE
    )
    
    with pytest.raises(QueryProcessingError):
        await query_processor.process_query("", tool_desc)
        
    with pytest.raises(QueryProcessingError):
        await query_processor.process_query("   ", tool_desc)

@pytest.mark.asyncio
async def test_llm_failure_handling(query_processor):
    """Test handling of LLM failures"""
    query = "What are the symptoms of COVID?"
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.PARAPHRASE
    )
    
    # Mock LLM failure
    query_processor.llm.ainvoke.side_effect = Exception("LLM failed")
    
    result = await query_processor.process_query(query, tool_desc)
    
    assert result == [query]  # Should fall back to original query

@pytest.mark.asyncio
async def test_query_validation(query_processor):
    """Test query validation logic"""
    query = "What are the symptoms of COVID?"
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.PARAPHRASE
    )
    
    # Mock LLM response with invalid queries
    query_processor.llm.ainvoke.return_value.content = """
    - 
    - a
    - valid query
    """
    
    result = await query_processor.process_query(query, tool_desc)
    
    assert "valid query" in result
    assert len([q for q in result if len(q) < 3]) == 0  # No short queries

@pytest.mark.asyncio
async def test_max_variations_limit(query_processor):
    """Test that max_variations limit is respected"""
    query = "What are the symptoms of COVID?"
    max_variations = 2
    tool_desc = ToolDescription(
        name="test_tool",
        query_strategy=QueryStrategy.PARAPHRASE,
        max_variations=max_variations
    )
    
    # Mock LLM response with more variations than allowed
    query_processor.llm.ainvoke.return_value.content = MOCK_PARAPHRASE_RESPONSE
    
    result = await query_processor.process_query(query, tool_desc)
    
    assert len(result) <= max_variations
    assert query in result  # Original query should still be included

def test_query_strategy_enum():
    """Test QueryStrategy enum values"""
    assert QueryStrategy.DIRECT.value == "direct"
    assert QueryStrategy.PARAPHRASE.value == "paraphrase"
    assert QueryStrategy.EXPAND.value == "expand"
    
def test_tool_description_defaults():
    """Test ToolDescription default values"""
    desc = ToolDescription(name="test", query_strategy=QueryStrategy.DIRECT)
    assert desc.max_variations == 3  # Default value
    
    desc = ToolDescription(
        name="test",
        query_strategy=QueryStrategy.PARAPHRASE,
        max_variations=5
    )
    assert desc.max_variations == 5  # Custom value 