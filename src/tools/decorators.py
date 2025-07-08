import asyncio
import logging
import functools
from typing import Any, Callable, Type, TypeVar, List, Dict, Union
from functools import wraps
from src.utils.query_processor import (
    QueryProcessor,
    ToolDescription,
    QueryStrategy,
    QueryProcessingError,
)
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar("T")


def log_io(func: Callable) -> Callable:
    """
    A decorator that logs the input parameters and output of a tool function.
    Handles both synchronous and asynchronous functions.

    Args:
        func: The tool function to be decorated

    Returns:
        The wrapped function with input/output logging
    """

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Log input parameters
        func_name = func.__name__
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.info(f"Tool {func_name} called with parameters: {params}")

        # Execute the function
        result = func(*args, **kwargs)

        # Log the output
        logger.info(f"Tool {func_name} returned: {result}")

        return result

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Log input parameters
        func_name = func.__name__
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.info(f"Tool {func_name} called with parameters: {params}")

        # Execute the function
        result = await func(*args, **kwargs)

        # Log the output
        logger.info(f"Tool {func_name} returned: {result}")

        return result

    # Return the appropriate wrapper based on whether the function is async
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

# Global variable to store tool event callback
_tool_event_callback = None

def set_tool_event_callback(callback):
    """Set a callback function to be called when tools are used."""
    global _tool_event_callback
    _tool_event_callback = callback

def log_io_with_events(func: Callable) -> Callable:
    """
    A decorator that logs tool usage and emits events for real-time tracking.
    """
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__name__
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        
        # Log and emit start event
        logger.info(f"Tool {func_name} called with parameters: {params}")
        if _tool_event_callback:
            await _tool_event_callback({
                "type": "tool_start",
                "tool_name": func_name,
                "parameters": {k: v for k, v in kwargs.items()},
                "display_name": _get_tool_display_name(func_name)
            })

        # Execute the function
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        # Log and emit completion event
        logger.info(f"Tool {func_name} returned: {result}")
        if _tool_event_callback:
            await _tool_event_callback({
                "type": "tool_complete",
                "tool_name": func_name,
                "result": result,
                "display_name": _get_tool_display_name(func_name)
            })

        return result

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__name__
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        
        # Log start
        logger.info(f"Tool {func_name} called with parameters: {params}")

        # Execute the function
        result = func(*args, **kwargs)

        # Log completion
        logger.info(f"Tool {func_name} returned: {result}")

        return result

    # Return async wrapper if function is async, sync wrapper otherwise
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

def _get_tool_display_name(tool_name: str) -> str:
    """Get user-friendly display name for tools."""
    display_names = {
        "openai_search_tool": "Web Search",
        "crawl_tool": "Web Crawling",
        "arxiv_search": "Academic Search",
        "github_trending": "GitHub Trending",
        "python_repl": "Code Execution"
    }
    return display_names.get(tool_name, tool_name.replace("_", " ").title())


class LoggedToolMixin:
    """A mixin class that adds logging functionality to any tool."""

    def _log_operation(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """Helper method to log tool operations."""
        tool_name = self.__class__.__name__.replace("Logged", "")
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.debug(f"Tool {tool_name}.{method_name} called with parameters: {params}")

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Override _run method to add logging."""
        self._log_operation("_run", *args, **kwargs)
        result = super()._run(*args, **kwargs)
        logger.debug(
            f"Tool {self.__class__.__name__.replace('Logged', '')} returned: {result}"
        )
        return result


def create_logged_tool(base_tool_class: Type[T]) -> Type[T]:
    """
    Factory function to create a logged version of any tool class.

    Args:
        base_tool_class: The original tool class to be enhanced with logging

    Returns:
        A new class that inherits from both LoggedToolMixin and the base tool class
    """

    class LoggedTool(LoggedToolMixin, base_tool_class):
        pass

    # Set a more descriptive name for the class
    LoggedTool.__name__ = f"Logged{base_tool_class.__name__}"
    return LoggedTool


def process_queries(
    strategy: QueryStrategy, max_variations: int = 3, llm_type: str = "basic"
) -> Callable:
    """Decorator that adds query processing capabilities to tools."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract query and preserve other arguments
            query = None
            other_args = ()
            if args:
                query = args[0]
                other_args = args[1:]  # Preserve other positional args

            elif "query" in kwargs:
                query = kwargs.pop("query")  # Remove query, preserve other kwargs

            if not query:
                return await func(*args, **kwargs)

            try:
                # Create tool description and process queries
                tool_desc = ToolDescription(
                    name=func.__name__,
                    query_strategy=strategy,
                    max_variations=max_variations,
                )

                # Process queries with error handling
                processor = QueryProcessor(llm_type)
                try:
                    processed_queries = await processor.process_query(query, tool_desc)
                except QueryProcessingError as e:
                    logger.warning(
                        f"Query processing failed: {str(e)}. Using original query."
                    )
                    processed_queries = [query]

                # Execute function with each processed query
                results = []
                errors = []
                seen_results = set()  # For deduplication

                for processed_query in processed_queries:
                    try:
                        # Log the actual input parameters being passed to the tool
                        if args:
                            tool_args = (processed_query,) + other_args
                            logger.info(
                                f"Tool {func.__name__} called with args: {tool_args}, kwargs: {kwargs}"
                            )
                            result = await func(
                                processed_query, *other_args, **kwargs
                            )  # Include kwargs
                        else:
                            tool_kwargs = {"query": processed_query, **kwargs}
                            logger.info(
                                f"Tool {func.__name__} called with kwargs: {tool_kwargs}"
                            )
                            result = await func(query=processed_query, **kwargs)

                        if isinstance(result, dict) and "error" in result:
                            errors.append(result)
                        else:
                            results.append(result)
                    except Exception as e:
                        logger.error(
                            f"Error executing query '{processed_query}': {str(e)}"
                        )
                        errors.append({"error": str(e), "query": processed_query})

                # Handle results and errors
                if not results and errors:
                    return errors[0]

                if not results:
                    return {"error": "All query variations failed", "details": errors}

                # Combine results based on their type with deduplication
                if isinstance(results[0], (list, tuple)):
                    # Combine list results with deduplication
                    combined_results = []
                    for result in results:
                        for item in result:
                            item_str = str(item)  # Convert to string for comparison
                            if item_str not in seen_results:
                                seen_results.add(item_str)
                                combined_results.append(item)
                    return combined_results
                elif isinstance(results[0], dict):
                    # Combine dict results with smart merging
                    combined_result = results[0].copy()
                    for result in results[1:]:
                        for key, value in result.items():
                            if key not in combined_result:
                                combined_result[key] = value
                            elif isinstance(value, list):
                                # Extend lists with deduplication
                                existing = set(str(x) for x in combined_result[key])
                                for item in value:
                                    if str(item) not in existing:
                                        existing.add(str(item))
                                        combined_result[key].append(item)
                            elif value and value != combined_result[key]:
                                # Handle non-list values
                                if isinstance(combined_result[key], list):
                                    if str(value) not in set(
                                        str(x) for x in combined_result[key]
                                    ):
                                        combined_result[key].append(value)
                                else:
                                    combined_result[key] = [combined_result[key], value]
                    return combined_result
                else:
                    # For other types, return the first successful result
                    return results[0]

            except Exception as e:
                logger.error(f"Decorator error: {str(e)}")
                # Fall back to original function
                if args:
                    return await func(
                        query, *other_args, **kwargs
                    )  # Include kwargs in fallback
                else:
                    return await func(query=query, **kwargs)

        return wrapper

    return decorator
