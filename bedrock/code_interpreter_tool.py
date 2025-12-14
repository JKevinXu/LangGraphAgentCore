"""
AgentCore Code Interpreter Tool integration for LangGraph agents.

This module provides a code execution tool that integrates with
Amazon Bedrock AgentCore Code Interpreter service.
"""

import os
from typing import Optional
from langchain_core.tools import tool
from bedrock_agentcore.tools.code_interpreter_client import code_session, CodeInterpreter
from datetime import datetime


# Configuration
REGION = os.environ.get("AWS_REGION", "us-west-2")


class CodeInterpreterToolWrapper:
    """
    Wrapper for AgentCore Code Interpreter tool that provides LangGraph-compatible tools.
    
    This class initializes the AgentCore Code Interpreter and exposes it as a LangChain tool
    that can be used with LangGraph agents.
    """
    
    def __init__(self, region: str = REGION):
        """
        Initialize the Code Interpreter Tool.
        
        Args:
            region: AWS region where AgentCore Code Interpreter is available
        """
        self.region = region
        self._initialized = False
        self._test_passed = False
        
    def initialize(self):
        """
        Lazy initialization of the AgentCore Code Interpreter tool.
        
        This is separate from __init__ to allow graceful handling of
        initialization failures (e.g., missing permissions, unavailable region).
        """
        if not self._initialized:
            try:
                # Test that we can create a code interpreter session
                from bedrock_agentcore.tools.code_interpreter_client import code_session as _test
                self._initialized = True
                self._test_passed = True
                print(f"✅ AgentCore Code Interpreter initialized in region: {self.region}")
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize AgentCore Code Interpreter: {e}")
                print("   Code Interpreter tool will not be available.")
                self._initialized = True
                self._test_passed = False
                
    def get_tool(self):
        """
        Get the code interpreter tool as a LangChain-compatible tool.
        
        Returns:
            LangChain tool for code execution, or None if initialization failed
        """
        if not self._initialized:
            self.initialize()
            
        if self._test_passed:
            return execute_code
        return None


# Global code interpreter tool instance
_code_interpreter_wrapper = CodeInterpreterToolWrapper(region=REGION)


def get_code_interpreter_tool():
    """
    Get the initialized code interpreter tool.
    
    Returns:
        LangChain-compatible code interpreter tool, or None if unavailable
        
    Example:
        >>> code_tool = get_code_interpreter_tool()
        >>> if code_tool:
        >>>     tools = [calculator, weather, code_tool]
        >>> else:
        >>>     tools = [calculator, weather]
    """
    return _code_interpreter_wrapper.get_tool()


@tool
def execute_code(code: str) -> str:
    """
    Execute Python code in a secure sandboxed environment using AgentCore Code Interpreter.
    
    This tool allows the agent to:
    - Run Python code safely
    - Perform data analysis and computations
    - Generate visualizations
    - Work with files and data
    - Use Python packages (NumPy, Pandas, Matplotlib, etc.)
    
    Args:
        code: Python code to execute as a string
    
    Returns:
        Result of the code execution including stdout, stderr, and exit code
        
    Example:
        >>> result = execute_code(
        ...     code="import numpy as np\\nprint(np.array([1,2,3]).mean())"
        ... )
    """
    import json
    
    try:
        # Execute code using AgentCore Code Interpreter
        # Reference: https://github.com/awslabs/amazon-bedrock-agentcore-samples
        with code_session(REGION) as code_client:
            response = code_client.invoke("executeCode", {
                "code": code,
                "language": "python",
                "clearContext": False  # Maintain state between executions
            })
            
            # Process the streaming response
            result_text = ""
            for event in response["stream"]:
                event_result = event.get("result", {})
                
                # Extract structured content if available
                structured = event_result.get("structuredContent", {})
                if structured:
                    stdout = structured.get("stdout", "")
                    stderr = structured.get("stderr", "")
                    exit_code = structured.get("exitCode", 0)
                    exec_time = structured.get("executionTime", "N/A")
                    
                    result_text = f"📤 Output:\n{stdout}" if stdout else ""
                    if stderr:
                        result_text += f"\n⚠️ Stderr:\n{stderr}"
                    if exit_code != 0:
                        result_text += f"\n❌ Exit code: {exit_code}"
                    else:
                        result_text += f"\n✅ Executed in {exec_time}ms"
                else:
                    # Fallback to content array
                    content = event_result.get("content", [])
                    for item in content:
                        if item.get("type") == "text":
                            result_text += item.get("text", "")
                
                # Return first result
                if result_text:
                    return result_text
            
            # If no result, return the raw response
            return json.dumps(response, default=str)
            
    except Exception as e:
        return f"❌ Error executing code: {str(e)}"


# For backward compatibility and direct usage
def create_code_interpreter_tool(region: Optional[str] = None):
    """
    Create a new code interpreter tool wrapper instance.
    
    Args:
        region: AWS region (defaults to AWS_REGION env var or us-west-2)
        
    Returns:
        CodeInterpreterToolWrapper instance
    """
    if region is None:
        region = REGION
    return CodeInterpreterToolWrapper(region=region)

