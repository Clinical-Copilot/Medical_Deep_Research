import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, List, Any
from src.tools.decorators import process_queries
from src.utils.query_processor import QueryStrategy

# Mock tool functions for testing
@process_queries(strategy=QueryStrategy.PARAPHRASE, max_variations=2)
async def mock_search_tool(query: str) -> Dict[str, Any]:
    """Mock search tool that returns a dict result"""
    return {
        "query": query,
        "answer": f"Answer for {query}",
        "urls": [f"http://example.com/result1?q={query}"]
    }

@process_queries(strategy=QueryStrategy.EXPAND, max_variations=2)
async def mock_list_tool(query: str) -> List[str]:
    """Mock tool that returns a list result"""
    return [f"Result 1 for {query}", f"Result 2 for {query}"]

@process_queries(strategy=QueryStrategy.DIRECT)
async def mock_error_tool(query: str) -> Dict[str, Any]:
    """Mock tool that sometimes returns errors"""
    if "error" in query.lower():
        return {"error": "Something went wrong"}
    return {"result": f"Success for {query}"}

# Tests
@pytest.mark.asyncio
async def test_decorator_dict_result_combination():
    """Test how the decorator combines dictionary results"""
    result = await mock_search_tool("test query")
    
    assert isinstance(result, dict)
    assert "query" in result
    assert "answer" in result
    assert "urls" in result
    assert isinstance(result["urls"], list)

@pytest.mark.asyncio
async def test_decorator_list_result_combination():
    """Test how the decorator combines list results"""
    result = await mock_list_tool("test query")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(item, str) for item in result)

@pytest.mark.asyncio
async def test_decorator_error_handling():
    """Test how the decorator handles errors"""
    # Test successful case
    success_result = await mock_error_tool("normal query")
    assert "result" in success_result
    
    # Test error case
    error_result = await mock_error_tool("error case")
    assert "error" in error_result

@pytest.mark.asyncio
async def test_decorator_empty_query():
    """Test how the decorator handles empty queries"""
    result = await mock_search_tool("")
    assert isinstance(result, dict)
    assert "query" in result

@pytest.mark.asyncio
async def test_decorator_query_extraction():
    """Test query extraction from different argument formats"""
    # Test positional argument
    result1 = await mock_search_tool("test1")
    assert "test1" in result1["query"]
    
    # Test keyword argument
    result2 = await mock_search_tool(query="test2")
    assert "test2" in result2["query"]

@pytest.mark.asyncio
async def test_decorator_with_additional_args():
    """Test decorator with functions that have additional arguments"""
    @process_queries(strategy=QueryStrategy.DIRECT)
    async def tool_with_args(query: str, extra: str = "default") -> Dict[str, Any]:
        return {"query": query, "extra": extra}
    
    result = await tool_with_args("test", extra="custom")
    assert result["query"] == "test"
    assert result["extra"] == "custom"

@pytest.mark.asyncio
async def test_decorator_result_deduplication():
    """Test that the decorator properly deduplicates results"""
    @process_queries(strategy=QueryStrategy.PARAPHRASE, max_variations=3)
    async def tool_with_dupes(query: str) -> List[str]:
        # Return duplicate results
        return ["result1", "result1", "result2"]
    
    result = await tool_with_dupes("test query")
    # Check that duplicates are removed when combining results
    assert len(set(result)) == len(result)

@pytest.mark.asyncio
async def test_decorator_partial_failures():
    """Test handling of partial failures in query variations"""
    @process_queries(strategy=QueryStrategy.PARAPHRASE, max_variations=3)
    async def sometimes_fails(query: str) -> Dict[str, Any]:
        if "fail" in query:
            return {"error": "Failed query"}
        return {"result": f"Success for {query}"}
    
    # Should still get results even if some variations fail
    result = await sometimes_fails("test with fail")
    assert isinstance(result, dict)
    assert ("result" in result or "error" in result)

@pytest.mark.asyncio
async def test_decorator_llm_failure_recovery():
    """Test recovery from LLM failures in query processing"""
    with patch("src.utils.query_processor.QueryProcessor.process_query") as mock_process:
        mock_process.side_effect = Exception("LLM failed")
        
        result = await mock_search_tool("test query")
        assert isinstance(result, dict)
        assert "query" in result  # Should still work with original query 