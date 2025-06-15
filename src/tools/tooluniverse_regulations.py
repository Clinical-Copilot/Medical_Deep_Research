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
) -> dict:
    """Retrieve comprehensive safety warnings for a specific drug using its name."""
    return _run_tooluniverse_function("FDA_get_warnings_by_drug_name", {"drug_name": drug_name})
