# TxAgent Tool Integration Research

## Phase 1: Research & Understanding

### 1. TxAgent Overview

**Purpose**: TxAgent is an AI agent designed for "precision therapeutics" that generates personalized treatment recommendations by leveraging multi-step reasoning and real-time biomedical knowledge retrieval.

**Key Capabilities**:
- Analyzes drug interactions at molecular, pharmacokinetic, and clinical levels
- Identifies drug contraindications based on patient characteristics
- Retrieves and synthesizes evidence from multiple biomedical sources
- Executes structured function calls across 211 tools
- Performs clinical reasoning and cross-source validation

**Architecture & Components**:
- Built on ToolUniverse: A comprehensive collection of 211 biomedical tools
- Utilizes multi-agent systems for dataset generation:
  - ToolGen: Transforms APIs into agent-compatible tools
  - QuestionGen: Generates relevant questions from documents
  - TraceGen: Generates step-by-step reasoning traces

**Access & Integration**:
```bash
pip install tooluniverse
pip install txagent
```
- Available on GitHub, HuggingFace, and arXiv
- Supports demos and script-based interactions

**Performance**:
- 92.1% accuracy in drug reasoning tasks
- Outperforms GPT-4o by up to 25.8%
- Handles drug name variants with <0.01 variance

**Target Use Cases**:
- Personalized treatment strategy development
- Drug interaction assessment
- Clinical decision support
- Therapeutic reasoning across complex medical scenarios

### 2. ToolUniverse Analysis

**Tool Composition**:
- Contains 211 biomedical tools
- Focused on "drugs and diseases"
- Linked to trusted sources:
  - US FDA-approved drugs (since 1939)
  - Open Targets
  - Monarch Initiative

**Organization**:
- Part of the TxAgent ecosystem
- Designed specifically for "Agentic AI"
- Enables complex therapeutic reasoning tasks

**Installation**:
```bash
# From source
python -m pip install . --no-cache-dir

# From PyPI
pip install tooluniverse
```

**Integration Interfaces**:
- **Python SDK**: For programmatic interaction
- **MCP Server**: For remote tool execution
- Compatible with AI agent systems
- Supports integration with platforms like Claude Desktop App

**Tool Categories** (Biomedical Focus):
- Drug discovery tools
- Clinical insights tools
- Therapeutic reasoning tools
- FDA drug database access
- Disease-drug interaction analysis

### 3. CAMEL-AI MCP Integration Patterns

**Configuration**:
```bash
export DEFAULT_MODEL_PLATFORM_TYPE=<your preferred platform>
```

**Tool Loading**:
```bash
pip install 'camel-ai[rag,web_tools,document_tools]'
```

**Available Tool Categories**:
- Web Tools: DuckDuckGo, Wikipedia, WolframAlpha
- Communication Tools: Slack, Discord, Telegram
- Data Tools: Pandas, OpenBB, Stripe
- Research Tools: arXiv, Google Scholar

**MCP-Specific Components**:
- MCP toolkit: `camel.toolkits.mcp_toolkit`
- Cookbook example: "Agents with SQL MCP Server"

**Best Practices**:
- Use environment variables for configuration
- Combine relevant tool extras based on project needs
- Leverage specific toolkits for enhanced functionality

## Integration Strategy for MedDR

### Current MedDR Tool Architecture
Based on analysis of `src/graph/nodes.py`, `src/tools/`, and `src/config/tools.py`:

**Existing Tools**:
- `crawl_tool`: Web crawling functionality
- `python_repl_tool`: Python code execution
- `get_web_search_tool`: Configurable search (Arxiv, Tavily, Brave)

**MCP Integration Pattern** (lines 46-82 in `src/graph/nodes.py`):
```python
mcp_servers = {}
enabled_tools = {}

# Load MCP server configurations
for server_name, server_config in config["configurable"]["mcp_settings"]["servers"].items():
    if server_config["enabled_tools"] and "researcher" in server_config["add_to_agents"]:
        mcp_servers[server_name] = {
            k: v for k, v in server_config.items()
            if k in ("transport", "command", "args", "url", "env")
        }

# Initialize MCP client
client = MultiServerMCPClient(mcp_servers)
tools = await client.get_tools()
```

**Agent Assignment Pattern**:
- Tools are assigned to specific agents (researcher, coder, etc.)
- Configuration via `mcp_settings.servers[].add_to_agents`

### Recommended Integration Path

**Option 1: MCP Server Integration** (Recommended)
- Leverage ToolUniverse's MCP server capability
- Follow existing MCP pattern in MedDR
- Benefits: Clean separation, scalable, follows established architecture

**Option 2: Direct Python SDK Integration**
- Import ToolUniverse directly as Python tools
- Create wrapper functions in `src/tools/txagent_tools.py`
- Benefits: Direct access, simpler setup

**Next Steps**:
1. Test ToolUniverse MCP server setup
2. Map TxAgent tools to MedDR agents (researcher for drug discovery, coder for analysis)
3. Create configuration templates
4. Implement integration following existing patterns