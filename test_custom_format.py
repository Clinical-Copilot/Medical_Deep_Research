#!/usr/bin/env python3
"""
Test script for the custom format functionality
"""

import asyncio
from src.workflow import run_agent_workflow_async

async def test_custom_format():
    """Test the custom format functionality"""
    
    # Test with custom format requirements
    test_query = "What are the benefits of Python programming language?"
    custom_requirements = "Focus on technical details, include code examples, and provide a comparison with other languages"
    
    print("Testing custom format with requirements:", custom_requirements)
    print("=" * 60)
    
    try:
        result = await run_agent_workflow_async(
            user_input=test_query,
            output_format=custom_requirements,  # Pass requirements directly
            max_plan_iterations=1,
            max_step_num=2
        )
        
        print("\nFinal Report:")
        print("=" * 60)
        if "final_report" in result:
            print(result["final_report"])
        else:
            print("No final report found in result")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_custom_format()) 