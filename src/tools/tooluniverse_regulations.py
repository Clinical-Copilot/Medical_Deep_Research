import logging
import sys
import os
from typing import Annotated, Optional
from src.llms.llm import get_llm_by_type

from langchain_core.tools import tool
from .decorators import log_io

from tooluniverse.execute_function import ToolUniverse

from .output_parser import dict2md

logger = logging.getLogger(__name__)

# Suppress output during ToolUniverse initialization
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        # Redirect both stdout and stderr to /dev/null
        self._null_fd = open(os.devnull, 'w')
        sys.stdout = self._null_fd
        sys.stderr = self._null_fd
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original stdout and stderr
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._null_fd.close()

# Initialize ToolUniverse with suppressed output
with SuppressOutput():
    engine = ToolUniverse()
    engine.load_tools()

def parse_query(query: str, model) -> str:
    """
    Extracts the core drug name from a free-text query.
    """
    prompt = (
        "You are a helpful assistant that extracts only the drug name "
        "from biomedical queries. Return only the parsed drug name."
        f"\n\nQuery: \"{query}\""
    )
    response = model.invoke(prompt)
    return response.content.strip()

@tool
@log_io
def search_drug_warnings(
    query: Annotated[str, "Free-text query about drug safety warnings (e.g., 'What are the side effects of aspirin?')"],
) -> str:
    """
    Search FDA drug safety warnings based on a free-text biomedical query.

    Input: Free-text question or phrase about drug warnings.
    Output: Formatted warnings list including title, date, and description.
    """
    llm = get_llm_by_type("basic")
    # Parse the user's query to extract a standardized drug name
    drug_name = parse_query(query, llm)
    # Delegate to the underlying ToolUniverse function
    return _run_tooluniverse_function(
        "FDA_get_warnings_by_drug_name",
        {"drug_name": drug_name}
    )

def _run_tooluniverse_function(function_name: str, arguments: dict) -> str:
    """Helper function to run ToolUniverse functions with error handling."""
    try:
        raw_result = engine.run_one_function(
            {"name": function_name, "arguments": arguments}
        )
        result = dict2md(raw_result)
        return result
    except Exception as e:
        error_msg = f"Failed to execute {function_name}. Error: {repr(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

@tool
@log_io
def get_drug_warnings_by_drug_name(
    drug_name: Annotated[str, "Name of the drug (e.g., 'aspirin')"],
) -> str:
    """Retrieve comprehensive safety warnings for a specific drug using its name."""
    return _run_tooluniverse_function(
        "FDA_get_warnings_by_drug_name", {"drug_name": drug_name}
    )


@tool
@log_io
def get_boxed_warning_info_by_drug_name(
    drug_name: Annotated[str, "Name of the drug (e.g., 'aspirin')"],
    limit: Annotated[int, "Maximum number of results to return"] = 10,
    skip: Annotated[int, "Number of results to skip for pagination"] = 0,
) -> str:
    """Retrieve boxed warning information for a specific drug by name."""
    return _run_tooluniverse_function(
        "get_boxed_warning_info_by_drug_name",
        {"drug_name": drug_name, "limit": limit, "skip": skip},
    )


# @tool
# @log_io
# def get_drug_names_by_controlled_substance_DEA_schedule(
#     controlled_substance_schedule: Annotated[
#         str, "DEA controlled substance schedule (e.g., 'Schedule I', 'Schedule II')"
#     ],
#     limit: Annotated[int, "Maximum number of results to return"] = 10,
#     skip: Annotated[int, "Number of results to skip for pagination"] = 0,
# ) -> str:
#     """Retrieve drug names by their controlled substance DEA schedule classification."""
#     return _run_tooluniverse_function(
#         "get_drug_names_by_controlled_substance_DEA_schedule",
#         {
#             "controlled_substance_schedule": controlled_substance_schedule,
#             "limit": limit,
#             "skip": skip,
#         },
#     )

