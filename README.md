# MedDR

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](./README.md)

> Originated from Open Source, give back to Open Source.

**MedDR** (**M**edical **D**eep **R**esearch) is a Deep Research for medical domain. It builds upon the incredible work of the open source community. Our goal is to combine language models with specialized tools for tasks like web search, crawling, and Python code execution.

## Project Logic and Structure

The project follows a modular, graph-based architecture for deep research tasks. Here's how it works:

### 1. Entry Point (`main.py`)
- The main entry point that handles user input and initializes the workflow
- Sets up logging and configuration
- Manages the execution of the research workflow

### 2. Workflow Management (`src/workflow.py`)
- Defines the high-level workflow structure
- Manages the execution flow between different components
- Handles logging and error management
- Coordinates between different agents and tools

### 3. Graph Structure
The system uses a directed graph where:
- Nodes represent different agents (Coordinator, Planner, Researcher, Coder)
- Edges define the flow of information and control
- State is passed between nodes to maintain context
- Each node can access specific tools based on its role

### 4. Node Level
MedDR implements a modular multi-agent system architecture designed for automated research and code analysis. The system is built on LangGraph, enabling a flexible state-based workflow where components communicate through a well-defined message passing system.

![Architecture Diagram](./assets/architecture.png)

The system employs a streamlined workflow with the following components:

1. **Coordinator**: The entry point that manages the workflow lifecycle

   - Initiates the research process based on user input
   - Delegates tasks to the planner when appropriate
   - Acts as the primary interface between the user and the system

2. **Planner**: Strategic component for task decomposition and planning

   - Analyzes research objectives and creates structured execution plans
   - Determines if enough context is available or if more research is needed
   - Manages the research flow and decides when to generate the final report

3. **Research Team**: A collection of specialized agents that execute the plan:

   - **Researcher**: Conducts web searches and information gathering using tools like web search engines, crawling and even MCP services.
   - **Coder**: Handles code analysis, execution, and technical tasks using Python REPL tool.
     Each agent has access to specific tools optimized for their role and operates within the LangGraph framework

4. **Reporter**: Final stage processor for research outputs
   - Aggregates findings from the research team
   - Processes and structures the collected information
   - Generates comprehensive research reports


## 📑 Table of Contents

- [🚀 Quick Start](#quick-start)
- [🏗️ Architecture](#architecture)
- [🛠️ Development](#development)
- [📚 Examples](#examples)
- [💖 Acknowledgments](#acknowledgments)

## Quick Start

MedDR is developed in Python. To ensure a smooth setup process, we recommend using the following tools:

### Environment Requirements

Make sure your system meets the following minimum requirements:

- **[Python](https://www.python.org/downloads/):** Version `3.12+`

### Setup

1. Clone the repository
2. Create and activate a virtual environment:
```bash
python -m venv meddr_env
source meddr_env/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
# Configure .env with your API keys
cp .env.example .env

# Configure conf.yaml for your LLM model and API keys
cp conf.yaml.example conf.yaml
```

## Full Stack Setup

To run both the frontend and backend together, follow these steps:

1. **Backend Setup**
```bash
# Make sure you're in the project root directory
cd /path/to/meddr/backend
```

activate your virtual environment

# Install backend dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --reload
```

2. **Frontend Setup**
```bash
# Open a new terminal window
cd path/to/meddr/frontend

# Install frontend dependencies
npm install

# Start the frontend development server
npm run dev
```

3. **Access the Application**
- Frontend will be available at: `http://localhost:3000`

4. **Environment Configuration**
- Make sure both `.env` and `conf.yaml` are properly configured
- Frontend environment variables should be set in `.env.local` in the frontend directory

## Development Mode

MedDR includes a development mode that helps track and debug node execution. When enabled, it logs detailed information about each node's inputs, prompts, outputs, and execution results to both the console and log files.

### Enabling Development Mode

To enable development mode, set the `MEDDR_DEV_MODE` environment variable to `true`:

```bash
export MEDDR_DEV_MODE=true
```

### Running Examples

```bash
# Run with a specific query
python3 main.py "What factors are influencing AI adoption in healthcare?"

# Run with custom planning parameters
python3 main.py --max_plan_iterations 3 "How does quantum computing impact cryptography?"

# Run in interactive mode
python3 main.py --interactive
```

### Logging

Logs are written to the `logs` directory:
- Main log file: `logs/meddr.log`
- Development mode logs include detailed execution information

> ## 🔔 Your task!
> I have set a testing file `test_researcher.py`
> This file includes the **researcher node's core functionality**.
> - It covers key aspects like **web search, crawling, and information gathering**.
> - Your task is to integrate tools that are similar to craw_tool, and focus on biomedical sources.

### Run the testing example:
```
python3 /Users/liyuan/Desktop/projects/meddr/tests/test_researcher.py
```

## Features

### Core Capabilities

- 🤖 **LLM Integration**
  - Supports integration of most models through [litellm](https://docs.litellm.ai/docs/providers)
  - Support for open source models like Qwen
  - OpenAI-compatible API interface
  - Multi-tier LLM system for different task complexities

### Tools and MCP Integrations

- 🔍 **Search and Retrieval**
  - Web search via Arxiv
  - Crawling with Jina
  - Advanced content extraction

- 🔗 **MCP Integration**
  - Expand capabilities for private domain access
  - Knowledge graph integration
  - Web browsing capabilities

### Human Collaboration

- 🧠 **Human-in-the-loop**
  - Interactive modification of research plans
  - Auto-acceptance of research plans
  - Natural language interaction

- 📝 **Report Post-Editing**
  - Notion-like block editing
  - AI-assisted refinements
  - Powered by [tiptap](https://tiptap.dev/)



## License

..

## Acknowledgments

MedDR uses code from following GitHub repositories. We are grateful to all the projects and contributors whose efforts have made MedDR possible.

### Key Contributors

- [List of key contributors]

