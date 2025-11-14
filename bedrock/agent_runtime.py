"""
AWS Bedrock Agent Core Runtime integration for LangGraphAgentCore.

This module enables deploying your LangGraph agents to AWS Bedrock Agent Core Runtime.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agentcore import Agent, AgentConfig, create_tool

# Initialize the Bedrock Agent Core App
app = BedrockAgentCoreApp()


# Example tools
@create_tool
def calculator(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@create_tool
def get_weather(location: str) -> str:
    """Get weather for a location (demo)."""
    return f"The weather in {location} is sunny!"


# Create agent with Bedrock model
def create_bedrock_agent():
    """Create agent configured for AWS Bedrock."""
    config = AgentConfig(
        model="anthropic.claude-3-sonnet-20240229-v1:0",  # Bedrock model ID
        temperature=0.7,
        max_iterations=10
    )
    
    agent = Agent(config=config)
    agent.add_tool(calculator)
    agent.add_tool(get_weather)
    
    return agent


# Initialize agent
agent = create_bedrock_agent()


@app.entrypoint
def invoke_agent(payload):
    """
    Entrypoint for AWS Bedrock Agent Core Runtime.
    
    This function is called by the runtime when the agent is invoked.
    
    Args:
        payload: Dictionary with 'prompt' key containing user message
        
    Returns:
        Agent's response string
    """
    user_input = payload.get("prompt", "")
    
    # Invoke the agent
    response = agent.run(user_input)
    
    return response


if __name__ == "__main__":
    # This allows testing locally
    app.run()

