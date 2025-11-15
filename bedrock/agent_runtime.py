"""
AWS Bedrock Agent Core Runtime integration for LangGraphAgentCore.

This module enables deploying your LangGraph agents to AWS Bedrock Agent Core Runtime.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
import math
import operator

# Initialize the Bedrock Agent Core App
app = BedrockAgentCoreApp()


# Define tools using LangChain's @tool decorator
@tool
def calculator(expression: str) -> str:
    """
    Calculate the result of a mathematical expression.
    
    Args:
        expression: A mathematical expression as a string (e.g., "2 + 3 * 4", "sqrt(16)")
    
    Returns:
        The result of the calculation as a string
    """
    try:
        # Define safe functions that can be used in expressions
        safe_dict = {
            "__builtins__": {},
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow,
            # Math functions
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10, "exp": math.exp,
            "pi": math.pi, "e": math.e,
            "ceil": math.ceil, "floor": math.floor,
        }
        
        # Evaluate the expression safely
        result = eval(expression, safe_dict)
        return str(result)
        
    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: Invalid value - {str(e)}"
    except SyntaxError:
        return "Error: Invalid mathematical expression"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_weather(location: str) -> str:
    """
    Get weather for a location (demo implementation).
    
    Args:
        location: The location to get weather for
        
    Returns:
        Weather description
    """
    return f"The weather in {location} is sunny!"


# Create agent with Bedrock model
def create_agent():
    """Create and configure the LangGraph agent with Bedrock."""
    
    # Initialize Bedrock LLM
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        model_kwargs={"temperature": 0.7}
    )
    
    # Bind tools to the LLM
    tools = [calculator, get_weather]
    llm_with_tools = llm.bind_tools(tools)
    
    # System message
    system_message = "You're a helpful assistant. You can do simple math calculations and tell the weather."
    
    # Define the chatbot node
    def chatbot(state: MessagesState):
        # Add system message if not already present
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Create the graph
    graph_builder = StateGraph(MessagesState)
    
    # Add nodes
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))
    
    # Add edges
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")
    
    # Set entry point
    graph_builder.set_entry_point("chatbot")
    
    # Compile the graph
    return graph_builder.compile()


# Initialize the agent
agent = create_agent()


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
    
    # Invoke the agent with LangGraph
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    
    # Extract the final message content
    return response["messages"][-1].content


if __name__ == "__main__":
    # This allows testing locally
    app.run()

