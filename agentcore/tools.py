"""Tool utilities."""

from langchain_core.tools import tool


def create_tool(func):
    """Decorator to create a tool from a function."""
    return tool(func)

