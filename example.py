"""Basic example of using LangGraphAgentCore."""

import os
from dotenv import load_dotenv
from agentcore import Agent, AgentConfig, create_tool

# Load environment variables
load_dotenv()

# Create a simple tool
@create_tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def main():
    print("=" * 60)
    print("LangGraphAgentCore - Basic Example")
    print("=" * 60)
    
    # Create agent
    agent = Agent(AgentConfig(model="gpt-4", temperature=0.7))
    
    # Add tool
    agent.add_tool(calculator)
    
    # Example queries
    queries = [
        "What is LangGraph?",
        "Calculate 15 * 23 + 42",
    ]
    
    for query in queries:
        print(f"\n💬 User: {query}")
        response = agent.run(query)
        print(f"🤖 Agent: {response}")
        print("-" * 60)


if __name__ == "__main__":
    main()

