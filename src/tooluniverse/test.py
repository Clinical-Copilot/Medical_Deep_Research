from tooluniverse.execute_function import ToolUniverse

engine = ToolUniverse()
engine.load_tools()

print("Tools loaded successfully.")

# Get list of available tools to debug
tool_name_list, tool_desc_list = engine.refresh_tool_name_desc()

print(f"Available tools ({len(tool_name_list)}):")
for i, (name, desc) in enumerate(zip(tool_name_list[:10], tool_desc_list[:10])):
    print(f"{i+1}. {name}: {desc[:100]}...")

# Search for drug-related tools
drug_tools = [name for name in tool_name_list if 'drug' in name.lower() or 'ingredient' in name.lower()]
print(f"\nDrug-related tools ({len(drug_tools)}):")
for tool in drug_tools[:5]:
    print(f"- {tool}")

# Try with an actual drug tool
drug_tool = "OpenTargets_get_drug_warnings_by_chemblId"
print(f"\nTesting drug tool: {drug_tool}")

try:
    result = engine.run_one_function({
        "name": drug_tool,
        "arguments": {
            "chemblId": "CHEMBL25"  # Aspirin ChEMBL ID
        }
    })
    print("Function executed successfully!")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")

# Test another drug tool
print(f"\nTesting drug mechanisms tool:")
try:
    result2 = engine.run_one_function({
        "name": "OpenTargets_get_drug_mechanisms_of_action_by_chemblId",
        "arguments": {
            "chemblId": "CHEMBL25"
        }
    })
    print("Drug mechanisms tool executed successfully!")
    print(f"Result: {result2}")
except Exception as e:
    print(f"Error: {e}")