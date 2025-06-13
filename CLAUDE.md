# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands
- Format code: `make format`
- Lint code: `make lint`
- Run all tests: `make test`
- Run single test: `uv run pytest tests/path/to/test_file.py::test_function`
- Run with coverage: `make coverage`
- Development server: `make serve`
- Dev mode with LangGraph: `make langgraph-dev`

## Running the Application
- CLI mode: `python main.py "Your research question"`
- Interactive mode: `python main.py --interactive`
- With custom parameters: `python main.py --max_plan_iterations 3 --max_step_num 5 "Question"`
- Development mode: `export MEDDR_DEV_MODE=true` before running
- API server: `python server.py` or `make serve`

## Architecture Overview

MedDR is a LangGraph-based multi-agent research system with a modular architecture:

### Core Components
- **Graph Structure**: Built on LangGraph with StateGraph managing workflow between agents
- **State Management**: Centralized state (`src/graph/types.py`) tracks messages, plans, and observations
- **Agent System**: Multi-agent workflow with specialized roles and tools
- **Configuration**: Configurable parameters via `src/config/configuration.py` and environment variables

### Agent Workflow
The system follows this graph-based flow:
1. **Coordinator** (`coordinator_node`): Entry point, delegates to planner when research is needed
2. **Planner** (`planner_node`): Creates structured execution plans, determines if enough context exists
3. **Human Feedback** (`human_feedback_node`): Handles plan approval (auto-accepted by default)
4. **Research Team** (`research_team_node`): Routes between researcher and coder based on step type
5. **Researcher** (`researcher_node`): Web search, crawling, information gathering with MCP tool integration
6. **Coder** (`coder_node`): Python code execution and analysis
7. **Reporter** (`reporter_node`): Generates final reports from collected observations

### Key Files
- `src/workflow.py`: Main workflow execution and logging setup
- `src/graph/builder.py`: Graph construction and compilation
- `src/graph/nodes.py`: All node implementations and agent coordination
- `src/agents/agents.py`: Agent factory using create_react_agent
- `src/server/app.py`: FastAPI server for chat streaming and additional features

### Tool Integration
- **Built-in Tools**: Web search (configurable engines), crawling, Python REPL
- **MCP Integration**: Dynamic tool loading from MCP servers via `langchain-mcp-adapters`
- **Tool Assignment**: Tools assigned to specific agents via configuration

## Code Style Guidelines
- Python 3.12+ required
- Black formatting with 88 character line length
- Use absolute imports
- Follow existing modular, graph-based architecture
- Use type hints for function parameters and returns
- Error handling: Use appropriate try/except blocks with specific exceptions
- Naming: snake_case for variables/functions, PascalCase for classes
- Testing: Write pytest tests for new functionality
- Include docstrings for all functions and classes
- Proper error logging using the logging module

When developing, ensure pre-commit hooks pass (formatting and linting).