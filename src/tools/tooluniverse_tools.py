# # The project is built upon Bytedance MedDR
# # SPDX-License-Identifier: MIT

import logging
from typing import Annotated, Optional

from langchain_core.tools import tool
from .decorators import log_io

logger = logging.getLogger(__name__)

# Global ToolUniverse engine instance
_engine = None


def get_tooluniverse_engine():
    """Get or create a ToolUniverse engine instance."""
    global _engine
    if _engine is None:
        try:
            from tooluniverse.execute_function import ToolUniverse

            _engine = ToolUniverse()
            _engine.load_tools()
            logger.info(f"ToolUniverse initialized with {len(_engine.all_tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize ToolUniverse: {e}")
            raise
    return _engine


def _run_tooluniverse_function(function_name: str, arguments: dict) -> dict:
    """Helper function to run ToolUniverse functions with error handling."""
    try:
        engine = get_tooluniverse_engine()
        result = engine.run_one_function(
            {"name": function_name, "arguments": arguments}
        )
        return result
    except Exception as e:
        error_msg = f"Failed to execute {function_name}. Error: {repr(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


@tool
@log_io
def get_drug_warnings(
    chembl_id: Annotated[str, "ChEMBL ID of the drug (e.g., 'CHEMBL25' for aspirin)"],
) -> str:
    """Retrieve safety warnings for a specific drug using its ChEMBL ID."""
    result = _run_tooluniverse_function(
        "OpenTargets_get_drug_warnings_by_chemblId", {"chemblId": chembl_id}
    )
    return result


@tool
@log_io
def get_drug_mechanisms(
    chembl_id: Annotated[str, "ChEMBL ID of the drug (e.g., 'CHEMBL25' for aspirin)"],
) -> str:
    """Retrieve the mechanisms of action for a specific drug using its ChEMBL ID."""
    result = _run_tooluniverse_function(
        "OpenTargets_get_drug_mechanisms_of_action_by_chemblId", {"chemblId": chembl_id}
    )
    return result


@tool
@log_io
def get_drugs_for_disease(
    disease_efo_id: Annotated[
        str, "EFO ID of the disease (e.g., 'EFO_0000685' for rheumatoid arthritis)"
    ],
    limit: Annotated[Optional[int], "Maximum number of results to return"] = 10,
) -> str:
    """Retrieve known drugs associated with a specific disease using its EFO ID."""
    arguments = {"diseaseEfoId": disease_efo_id}
    if limit is not None:
        arguments["limit"] = limit

    result = _run_tooluniverse_function(
        "OpenTargets_get_associated_drugs_by_disease_efoId", arguments
    )
    return result


@tool
@log_io
def get_disease_targets(
    disease_efo_id: Annotated[
        str, "EFO ID of the disease (e.g., 'EFO_0000685' for rheumatoid arthritis)"
    ],
    limit: Annotated[Optional[int], "Maximum number of results to return"] = 10,
) -> str:
    """Find targets associated with a specific disease using its EFO ID."""
    arguments = {"diseaseEfoId": disease_efo_id}
    if limit is not None:
        arguments["limit"] = limit

    result = _run_tooluniverse_function(
        "OpenTargets_get_associated_targets_by_disease_efoId", arguments
    )
    return result


@tool
@log_io
def get_target_disease_evidence(
    target_ensembl_id: Annotated[str, "Ensembl ID of the target gene"],
    disease_efo_id: Annotated[str, "EFO ID of the disease"],
    limit: Annotated[Optional[int], "Maximum number of results to return"] = 10,
) -> str:
    """Explore evidence that supports a specific target-disease association."""
    arguments = {"targetEnsemblId": target_ensembl_id, "diseaseEfoId": disease_efo_id}
    if limit is not None:
        arguments["limit"] = limit

    result = _run_tooluniverse_function(
        "OpenTargets_target_disease_evidence", arguments
    )
    return result


@tool
@log_io
def get_similar_drugs(
    chembl_id: Annotated[str, "ChEMBL ID of the drug"],
    limit: Annotated[Optional[int], "Maximum number of results to return"] = 10,
) -> str:
    """Retrieve similar drugs for a given drug ChEMBL ID."""
    arguments = {"drugChemblId": chembl_id}
    if limit is not None:
        arguments["limit"] = limit

    result = _run_tooluniverse_function(
        "OpenTargets_get_similar_entities_by_drug_chemblId", arguments
    )
    return result


@tool
@log_io
def get_drug_withdrawal_status(
    chembl_id: Annotated[str, "ChEMBL ID of the drug"],
) -> str:
    """Check if a drug has been withdrawn or has black box warnings."""
    result = _run_tooluniverse_function(
        "OpenTargets_get_drug_withdrawn_blackbox_status_by_chemblId",
        {"chemblId": chembl_id},
    )
    return result


# List all available ToolUniverse tools for dynamic discovery
@tool
@log_io
def list_available_biomedical_tools() -> str:
    """List all available biomedical tools in ToolUniverse for reference."""
    try:
        engine = get_tooluniverse_engine()
        tool_name_list, tool_desc_list = engine.refresh_tool_name_desc()

        # Group tools by category
        categories = {
            "Drug Tools": [],
            "Disease Tools": [],
            "Target Tools": [],
            "Other Tools": [],
        }

        for name, desc in zip(tool_name_list, tool_desc_list):
            if "drug" in name.lower():
                categories["Drug Tools"].append(f"- {name}: {desc[:100]}...")
            elif "disease" in name.lower():
                categories["Disease Tools"].append(f"- {name}: {desc[:100]}...")
            elif "target" in name.lower():
                categories["Target Tools"].append(f"- {name}: {desc[:100]}...")
            else:
                categories["Other Tools"].append(f"- {name}: {desc[:100]}...")

        result = f"Total tools: {len(tool_name_list)}\n\n"
        for category, tools in categories.items():
            if tools:
                result += f"{category} ({len(tools)}):\n"
                result += "\n".join(tools[:5])  # Show first 5 in each category
                if len(tools) > 5:
                    result += f"\n... and {len(tools) - 5} more\n"
                result += "\n\n"

        return result
    except Exception as e:
        error_msg = f"Failed to list tools. Error: {repr(e)}"
        logger.error(error_msg)
        return error_msg
