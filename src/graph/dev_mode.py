import logging
import json
from typing import Any, Dict, Optional, List
from datetime import datetime
import os

# Configure logging
logger = logging.getLogger(__name__)

class DevModeLogger:
    """Development mode logger for tracking node inputs and outputs."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize the development mode logger.
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        self._ensure_log_dir()
        
    def _ensure_log_dir(self):
        """Ensure the log directory exists."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
    def _get_log_file(self, node_name: str) -> str:
        """Get the log file path for a node.
        
        Args:
            node_name: Name of the node
            
        Returns:
            Path to the log file
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"{node_name}_{timestamp}.log")
    
    def _extract_prompt_and_output(self, inputs: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract prompt and output from inputs if they exist.
        
        Args:
            inputs: Input data to the node
            
        Returns:
            Tuple of (prompt, output) if they exist
        """
        prompt = None
        output = None
        
        # Check for messages in inputs
        if "messages" in inputs:
            messages = inputs["messages"]
            if isinstance(messages, list):
                # Extract the last user message as prompt
                for msg in reversed(messages):
                    if hasattr(msg, "role") and msg.role == "user":
                        prompt = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get("role") == "user":
                        prompt = msg.get("content")
                        break
        
        # Check for output in various formats
        if "output" in inputs:
            output = inputs["output"]
        elif "response" in inputs:
            output = inputs["response"]
        elif "result" in inputs:
            output = inputs["result"]
            
        return prompt, output
    
    def log_node_execution(self, node_name: str, inputs: Dict[str, Any], outputs: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
        """Log node execution details.
        
        Args:
            node_name: Name of the node
            inputs: Input data to the node
            outputs: Output data from the node (if successful)
            error: Exception if the node failed
        """
        # Extract prompt and output
        prompt, input_output = self._extract_prompt_and_output(inputs)
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "inputs": inputs,
            "prompt": prompt,
            "input_output": input_output,
            "outputs": outputs if outputs is not None else None,
            "error": str(error) if error is not None else None
        }
        
        # Write to log file
        log_file = self._get_log_file(node_name)
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        # Also log to console for immediate feedback
        if error:
            logger.error(f"Node '{node_name}' failed: {error}")
            logger.error(f"Inputs: {inputs}")
            if prompt:
                logger.error(f"Prompt: {prompt}")
        else:
            logger.info(f"Node '{node_name}' executed successfully")
            logger.debug(f"Inputs: {inputs}")
            if prompt:
                logger.debug(f"Prompt: {prompt}")
            if input_output:
                logger.debug(f"Input Output: {input_output}")
            logger.debug(f"Outputs: {outputs}")

# Global instance
dev_logger = DevModeLogger()

def log_node_execution(node_name: str, inputs: Dict[str, Any], outputs: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
    """Convenience function to log node execution.
    
    Args:
        node_name: Name of the node
        inputs: Input data to the node
        outputs: Output data from the node (if successful)
        error: Exception if the node failed
    """
    dev_logger.log_node_execution(node_name, inputs, outputs, error) 