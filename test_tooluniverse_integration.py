#!/usr/bin/env python3
"""Test script for ToolUniverse integration with MedDR."""

import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.tools.tooluniverse_tools import (
    get_drug_warnings,
    get_drug_mechanisms,
    list_available_biomedical_tools,
)

async def test_tooluniverse_tools():
    """Test ToolUniverse tools integration."""
    print("Testing ToolUniverse integration with MedDR...")
    
    # Test 1: List available tools
    print("\n1. Testing list_available_biomedical_tools:")
    try:
        result = list_available_biomedical_tools.invoke({})
        print(f"✅ Successfully listed tools")
        print(f"Result (first 500 chars): {str(result)[:500]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Drug warnings for aspirin
    print("\n2. Testing get_drug_warnings for aspirin (CHEMBL25):")
    try:
        result = get_drug_warnings.invoke({"chembl_id": "CHEMBL25"})
        print(f"✅ Successfully retrieved drug warnings")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Drug mechanisms for aspirin  
    print("\n3. Testing get_drug_mechanisms for aspirin (CHEMBL25):")
    try:
        result = get_drug_mechanisms.invoke({"chembl_id": "CHEMBL25"})
        print(f"✅ Successfully retrieved drug mechanisms")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 ToolUniverse integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_tooluniverse_tools())