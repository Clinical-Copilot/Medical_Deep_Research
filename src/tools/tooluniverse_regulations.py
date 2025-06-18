# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import logging
from typing import Annotated, Optional

from langchain_core.tools import tool
from .decorators import log_io

from tooluniverse.execute_function import ToolUniverse

from .output_parser import dict2md

logger = logging.getLogger(__name__)

engine = ToolUniverse()
engine.load_tools()

def _run_tooluniverse_function(function_name: str, arguments: dict) -> str:
    """Helper function to run ToolUniverse functions with error handling."""
    try:
        raw_result = engine.run_one_function({
            "name": function_name,
            "arguments": arguments
        })
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
    return _run_tooluniverse_function("FDA_get_warnings_by_drug_name", {"drug_name": drug_name})

@tool
@log_io
def get_boxed_warning_info_by_drug_name(
    drug_name: Annotated[str, "Name of the drug (e.g., 'aspirin')"],
    limit: Annotated[int, "Maximum number of results to return"] = 10,
    skip: Annotated[int, "Number of results to skip for pagination"] = 0
) -> str:
    """Retrieve boxed warning information for a specific drug by name."""
    return _run_tooluniverse_function("get_boxed_warning_info_by_drug_name", {
        "drug_name": drug_name,
        "limit": limit,
        "skip": skip
    })

@tool
@log_io
def get_drug_names_by_controlled_substance_DEA_schedule(
    controlled_substance_schedule: Annotated[str, "DEA controlled substance schedule (e.g., 'Schedule I', 'Schedule II')"],
    limit: Annotated[int, "Maximum number of results to return"] = 10,
    skip: Annotated[int, "Number of results to skip for pagination"] = 0
) -> str:
    """Retrieve drug names by their controlled substance DEA schedule classification."""
    return _run_tooluniverse_function("get_drug_names_by_controlled_substance_DEA_schedule", {
        "controlled_substance_schedule": controlled_substance_schedule,
        "limit": limit,
        "skip": skip
    })
