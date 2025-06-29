import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union

from .mcp_discovery_agent import MCPDiscoveryAgent
from .mcp_config_generator import generate_mcp_config_from_markdown
from .mcp_validator import MCPValidator, ToolAlignmentResult
from src.tools.crawl import crawl_tool

logger = logging.getLogger(__name__)

@dataclass
class MCPCandidate:
    url: str
    crawl_success: bool = False
    crawl_error: Optional[str] = None
    markdown_content: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    validation_result: Optional[ToolAlignmentResult] = None
    validation_feedback: Optional[str] = None
    iterations: int = 0
    success: bool = False
    log: List[str] = field(default_factory=list)

@dataclass
class ValidationFeedback:
    missing_tools: List[str]
    error: Optional[str] = None
    def to_prompt(self) -> str:
        if self.error:
            return f"Validation error: {self.error}"
        if self.missing_tools:
            return (
                f"The following required tools were missing: {', '.join(self.missing_tools)}. "
                "Please refine the configuration to include these tools if possible."
            )
        return ""

@dataclass
class OrchestrationLogEntry:
    step: str
    message: str
    candidate_url: Optional[str] = None
    iteration: Optional[int] = None

class AutoMCPOrchestrator:
    """
    Orchestrates discovery, config generation, and validation of MCP servers.
    """
    def __init__(self, user_requirements: Dict[str, Any], llm_type: str = "basic"):
        self.user_requirements = user_requirements
        self.llm_type = llm_type
        self.discovery_agent = MCPDiscoveryAgent(llm_type=llm_type)
        self.validator = MCPValidator()
        self.max_iterations = 5
        self.candidates: List[MCPCandidate] = []
        self.logs: List[OrchestrationLogEntry] = []

    async def orchestrate(self) -> Dict[str, Any]:
        """
        Main orchestration entrypoint. Returns best config or failure report.
        """
        query = self._build_discovery_query()
        urls = await self.discovery_agent.discover_mcp_servers(query)
        if not urls:
            self._log("discovery", "No MCP server URLs found.")
            return {"success": False, "reason": "No MCP server URLs found.", "logs": self.logs}
        # URL filtering (only GitHub URLs for now to narrow down the search)
        urls = [url for url in urls if "github.com" in url]
        if not urls:
            self._log("discovery", "No GitHub URLs found after filtering.")
            return {"success": False, "reason": "No GitHub URLs found after filtering.", "logs": self.logs}
        # Prioritize URLs 
        for url in urls:
            candidate = MCPCandidate(url=url)
            self._log("candidate_start", f"Evaluating candidate: {url}", url)
            for iteration in range(1, self.max_iterations + 1):
                candidate.iterations = iteration
                self._log("iteration", f"Iteration {iteration} for {url}", url, iteration)
                # Crawl
                crawl_result = crawl_tool(url)
                if isinstance(crawl_result, dict) and "crawled_content" in crawl_result:
                    candidate.crawl_success = True
                    candidate.markdown_content = crawl_result["crawled_content"]
                else:
                    candidate.crawl_success = False
                    candidate.crawl_error = str(crawl_result)
                    self._log("crawl_fail", f"Crawl failed: {candidate.crawl_error}", url, iteration)
                    break  # Fail fast for this server
                # Config generation (with feedback if any)
                feedback_prompt = self._build_feedback_prompt(candidate)
                config = self._generate_config(candidate.markdown_content, feedback_prompt)
                if not config or not isinstance(config, dict):
                    self._log("config_fail", "Config generation failed.", url, iteration)
                    continue  # Try again if possible
                # Extract config dict for this server
                mcp_servers = config.get("mcp_servers", {})
                if not mcp_servers:
                    self._log("config_fail", "No mcp_servers found in config.", url, iteration)
                    continue
                # Use the first server in the config (extend if multiple supported)
                server_name, server_cfg = next(iter(mcp_servers.items()))
                # Inject user requirements (e.g., required tools)
                if "enabled_tools" in self.user_requirements:
                    server_cfg["enabled_tools"] = self.user_requirements["enabled_tools"]
                candidate.config = server_cfg
                validation_result = await self.validator.validate_tool_alignment(server_cfg)
                candidate.validation_result = validation_result
                if not validation_result.missing_tools:
                    candidate.success = True
                    self._log("success", f"Valid MCP config found for {url}", url, iteration)
                    self.candidates.append(candidate)
                    break  # Success for this server
                else:
                    feedback = ValidationFeedback(missing_tools=validation_result.missing_tools)
                    candidate.validation_feedback = feedback.to_prompt()
                    self._log("validation_feedback", candidate.validation_feedback, url, iteration)
            self.candidates.append(candidate)
        # Select best candidate aka no missing tools
        best = next((c for c in self.candidates if c.success), None)
        if best:
            return {"success": True, "config": best.config, "url": best.url, "logs": self.logs}
        # If none fully succeeded, return detailed failure report
        failure_report = [self._candidate_report(c) for c in self.candidates]
        return {"success": False, "reason": "No valid MCP config found.", "candidates": failure_report, "logs": self.logs}

    def _build_discovery_query(self) -> str:
        # Use discovery_query if provided, else fallback to old logic
        if "discovery_query" in self.user_requirements:
            return self.user_requirements["discovery_query"]
        base = "MCP server Model Context Protocol"
        if "enabled_tools" in self.user_requirements:
            tools = ", ".join(self.user_requirements["enabled_tools"])
            return f"{base} with tools: {tools}"
        return base

    def _build_feedback_prompt(self, candidate: MCPCandidate) -> str:
        # Build feedback string for config refinement
        if candidate.validation_feedback:
            return candidate.validation_feedback
        return ""

    def _generate_config(self, markdown_content: str, feedback: str) -> Optional[Dict[str, Any]]:
        # Extend config generator to accept feedback for iterative refinement
        if feedback:
            prompt = f"{markdown_content}\n\n# Feedback for refinement:\n{feedback}"
            return generate_mcp_config_from_markdown(prompt, llm_type=self.llm_type)
        else:
            return generate_mcp_config_from_markdown(markdown_content, llm_type=self.llm_type)

    def _log(self, step: str, message: str, candidate_url: Optional[str] = None, iteration: Optional[int] = None):
        entry = OrchestrationLogEntry(step=step, message=message, candidate_url=candidate_url, iteration=iteration)
        self.logs.append(entry)
        logger.info(f"[{step}] {message} (url={candidate_url}, iter={iteration})")

    def _candidate_report(self, candidate: MCPCandidate) -> Dict[str, Any]:
        return {
            "url": candidate.url,
            "crawl_success": candidate.crawl_success,
            "crawl_error": candidate.crawl_error,
            "iterations": candidate.iterations,
            "validation_result": (
                {
                    "inputted_tools": candidate.validation_result.inputted_tools,
                    "actual_tools": candidate.validation_result.actual_tools,
                    "missing_tools": candidate.validation_result.missing_tools,
                } if candidate.validation_result else None
            ),
            "validation_feedback": candidate.validation_feedback,
            "success": candidate.success,
            "log": candidate.log,
        } 