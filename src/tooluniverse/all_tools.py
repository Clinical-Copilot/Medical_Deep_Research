# #!/usr/bin/env python3

# """
# Script to print all available tools in ToolUniverse.
# Run this to see what biomedical tools are available.
# """

# from tooluniverse.execute_function import ToolUniverse


# def print_all_tools():
#     """Print all available ToolUniverse tools with their descriptions."""
#     print("Loading ToolUniverse...")
#     engine = ToolUniverse()
#     engine.load_tools()

#     # Get list of all available tools
#     tool_name_list, tool_desc_list = engine.refresh_tool_name_desc()

#     print(f"\nTotal ToolUniverse tools available: {len(tool_name_list)}")
#     print("=" * 80)
#     print()

#     # Print all tools with descriptions
#     for i, (name, desc) in enumerate(zip(tool_name_list, tool_desc_list), 1):
#         print(f"{i:3d}. {name}")
#         print(f"     {desc}")
#         print()


# if __name__ == "__main__":
#     print_all_tools()
