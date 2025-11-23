"""
AgentCore Browser Tool integration for LangGraph agents.

This module provides a browser automation tool that integrates with
Amazon Bedrock AgentCore Browser service, following the official AWS guide:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-onboarding.html
"""

import os
from typing import Optional
from langchain_core.tools import tool
from strands_tools.browser import AgentCoreBrowser


# Configuration
REGION = os.environ.get("AWS_REGION", "us-west-2")


class BrowserToolWrapper:
    """
    Wrapper for AgentCore Browser tool that provides LangGraph-compatible tools.
    
    This class initializes the AgentCore Browser and exposes it as a LangChain tool
    that can be used with LangGraph agents.
    """
    
    def __init__(self, region: str = REGION):
        """
        Initialize the Browser Tool.
        
        Args:
            region: AWS region where AgentCore Browser is available
        """
        self.region = region
        self._browser_tool = None
        self._initialized = False
        
    def initialize(self):
        """
        Lazy initialization of the AgentCore Browser tool.
        
        This is separate from __init__ to allow graceful handling of
        initialization failures (e.g., missing permissions, unavailable region).
        """
        if not self._initialized:
            try:
                self._browser_tool = AgentCoreBrowser(region=self.region)
                self._initialized = True
                print(f"✅ AgentCore Browser initialized in region: {self.region}")
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize AgentCore Browser: {e}")
                print("   Browser tool will not be available.")
                self._initialized = False
                
    def get_tool(self):
        """
        Get the browser tool as a LangChain-compatible tool.
        
        Returns:
            LangChain tool for browser automation, or None if initialization failed
        """
        if not self._initialized:
            self.initialize()
            
        if self._browser_tool and self._initialized:
            # The Strands AgentCoreBrowser provides a .browser attribute
            # that is a LangChain-compatible tool
            return self._browser_tool.browser
        return None


# Global browser tool instance
_browser_wrapper = BrowserToolWrapper(region=REGION)


def get_browser_tool():
    """
    Get the initialized browser tool.
    
    Returns:
        LangChain-compatible browser tool, or None if unavailable
        
    Example:
        >>> browser_tool = get_browser_tool()
        >>> if browser_tool:
        >>>     tools = [calculator, weather, browser_tool]
        >>> else:
        >>>     tools = [calculator, weather]
    """
    return _browser_wrapper.get_tool()


@tool
def browse_web(url: str, task: str) -> str:
    """
    Browse a web page and perform a task using AgentCore Browser.
    
    This tool allows the agent to:
    - Navigate to websites
    - Extract information from web pages
    - Search for content
    - Interact with web elements
    
    Args:
        url: The URL to navigate to (e.g., "https://example.com")
        task: Description of what to do on the page (e.g., "Find the product price")
    
    Returns:
        Result of the browsing task as a string
        
    Example:
        >>> result = browse_web(
        ...     url="https://docs.aws.amazon.com/bedrock-agentcore/",
        ...     task="What services does Bedrock AgentCore offer?"
        ... )
    """
    browser_tool = get_browser_tool()
    
    if not browser_tool:
        return "Error: AgentCore Browser is not available. Please check your AWS configuration and permissions."
    
    try:
        # Use the browser tool with the URL and task
        prompt = f"Navigate to {url} and {task}"
        result = browser_tool.invoke(prompt)
        return result
    except Exception as e:
        return f"Error browsing web: {str(e)}"


# For backward compatibility and direct usage
def create_browser_tool(region: Optional[str] = None):
    """
    Create a new browser tool wrapper instance.
    
    Args:
        region: AWS region (defaults to AWS_REGION env var or us-west-2)
        
    Returns:
        BrowserToolWrapper instance
    """
    if region is None:
        region = REGION
    return BrowserToolWrapper(region=region)

