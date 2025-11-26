"""
AWS Bedrock Agent Core Runtime integration for LangGraphAgentCore.

This module enables deploying your LangGraph agents to AWS Bedrock Agent Core Runtime.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph.graph import StateGraph, MessagesState, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph_checkpoint_aws import AgentCoreMemorySaver
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime
from typing import Annotated, TypedDict, AsyncIterator
import math
import operator
import os
import asyncio
from browser_tool import get_browser_tool
from code_interpreter_tool import get_code_interpreter_tool
from streaming_utils import StreamEvent, StreamEventType, format_sse_event
from callbacks import create_callbacks, MetricsCallback

# Enable LangSmith OpenTelemetry integration for LangGraph node-level tracing
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"

# Configuration
REGION = os.environ.get("AWS_REGION", "us-west-2")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", None)

# Initialize the Bedrock Agent Core App
app = BedrockAgentCoreApp()


# Custom State with Dynamic Data in Memory Event Body
class CustomAgentState(TypedDict):
    """
    Extended state that stores custom data directly in memory event body.
    All fields here are persisted in the checkpoint and loaded on next turn.
    """
    # Standard messages (required)
    messages: Annotated[list, add_messages]
    
    # Custom dynamic data stored in checkpoint body
    user_preferences: dict      # User preferences and settings
    custom_data: dict           # Any custom application data
    browsing_history: list      # Browser tool usage history with results
    code_execution_history: list  # Code interpreter execution history


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
    """Create and configure the LangGraph agent with Bedrock and memory support."""
    
    # Initialize Bedrock LLM
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        model_kwargs={"temperature": 0.7}
    )
    
    # Get browser tool (optional - gracefully degrades if unavailable)
    browser_tool = get_browser_tool()
    
    # Get code interpreter tool (optional - gracefully degrades if unavailable)
    code_tool = get_code_interpreter_tool()
    
    # Bind tools to the LLM
    tools = [calculator, get_weather]
    if browser_tool:
        tools.append(browser_tool)
        print("✅ Browser tool enabled")
    if code_tool:
        tools.append(code_tool)
        print("✅ Code Interpreter tool enabled")
    
    if not browser_tool and not code_tool:
        print("ℹ️  Advanced tools not available - agent will run with calculator and weather only")
    
    llm_with_tools = llm.bind_tools(tools)
    
    # System message
    system_message = """You're a helpful assistant with the following capabilities:
- Perform mathematical calculations
- Check weather information
- Browse websites and extract information (when available)
- Execute Python code in a secure environment (when available)

When browsing the web, navigate to URLs and extract the requested information accurately.
When executing code, write clear, well-commented Python code and explain the results."""
    
    # Define the chatbot node with custom state handling
    def chatbot(state: CustomAgentState):
        # Add system message if not already present
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages
        
        # Access custom dynamic data from state (persists from previous turns!)
        user_prefs = state.get("user_preferences", {})
        browsing_history = state.get("browsing_history", [])
        code_execution_history = state.get("code_execution_history", [])
        
        # Use custom data to personalize the system message
        context_additions = []
        if user_prefs:
            context_additions.append(f"\nUser preferences: {user_prefs}")
        if browsing_history:
            # Add recent browsing history to context (last 5 entries)
            recent_history = browsing_history[-5:]
            history_summary = "\n".join([
                f"- {entry['timestamp']}: Browsed {entry.get('url', 'N/A')} - {entry.get('summary', 'N/A')}"
                for entry in recent_history
            ])
            context_additions.append(f"\nRecent browsing history:\n{history_summary}")
        if code_execution_history:
            # Add recent code execution history to context (last 5 entries)
            recent_code = code_execution_history[-5:]
            code_summary = "\n".join([
                f"- {entry['timestamp']}: Executed code - {entry.get('summary', 'N/A')}"
                for entry in recent_code
            ])
            context_additions.append(f"\nRecent code executions:\n{code_summary}")
        
        if context_additions:
            messages[0] = SystemMessage(content=system_message + "".join(context_additions))
        
        response = llm_with_tools.invoke(messages)
        
        # Return updated state - fields not returned are preserved automatically
        return {"messages": [response]}
    
    # Create the graph with CustomAgentState
    graph_builder = StateGraph(CustomAgentState)
    
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
    
    # Initialize checkpointer for short-term memory persistence
    # Memory ID is optional - if not provided, memory features will be disabled
    checkpointer = None
    if MEMORY_ID:
        try:
            checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)
            print(f"✅ Short-term memory enabled with Memory ID: {MEMORY_ID}")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize memory checkpointer: {e}")
            print("   Agent will run without memory persistence.")
    else:
        print("ℹ️  Memory ID not configured. Agent will run without memory persistence.")
        print("   Set AGENTCORE_MEMORY_ID environment variable to enable memory.")
    
    # Compile the graph with checkpointer (if available)
    return graph_builder.compile(checkpointer=checkpointer)


# Initialize the agent
agent = create_agent()


@app.entrypoint
def invoke_agent(payload, context=None):
    """
    Entrypoint for AWS Bedrock Agent Core Runtime.
    
    This function is called by the runtime when the agent is invoked.
    
    Args:
        payload: Dictionary with keys:
            - 'prompt': User message (required)
            - 'session_id': Session ID for conversation continuity (optional)
            - 'actor_id': Actor ID for user/agent identification (optional)
        context: AgentCore runtime context (optional, contains memory_id)
        
    Returns:
        Agent's response string
    """
    user_input = payload.get("prompt", "")
    session_id = payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-actor")
    
    # Get memory ID from context if available (AgentCore passes it here)
    memory_id = MEMORY_ID  # First try environment variable
    if context and hasattr(context, 'memory_id'):
        memory_id = context.memory_id
        print(f"✅ Using memory from context: {memory_id}")
    
    # Prepare the input - only include custom fields if explicitly provided
    # This allows merging with existing state instead of overwriting
    input_data = {
        "messages": [HumanMessage(content=user_input)],
    }
    
    # Add custom data fields if provided in payload
    if "preferences" in payload:
        input_data["user_preferences"] = payload["preferences"]
    
    if "custom_data" in payload:
        input_data["custom_data"] = payload["custom_data"]
    
    if "browsing_history" in payload:
        input_data["browsing_history"] = payload["browsing_history"]
    
    if "code_execution_history" in payload:
        input_data["code_execution_history"] = payload["code_execution_history"]
    
    # If memory is enabled, pass configuration with thread_id and actor_id
    if memory_id:
        config = {
            "configurable": {
                "thread_id": session_id,  # Maps to Bedrock AgentCore session_id
                "actor_id": actor_id,      # Maps to Bedrock AgentCore actor_id
            },
            # Optional: Additional metadata (separate from state)
            "metadata": {
                "request_timestamp": datetime.now().isoformat(),
                "request_source": payload.get("source", "api"),
            }
        }
        print(f"🔗 Using memory: {memory_id} for session: {session_id}")
        # Invoke with memory configuration
        response = agent.invoke(input_data, config=config)
    else:
        print("ℹ️  No memory configured, running without persistence")
        # Invoke without memory configuration
        response = agent.invoke(input_data)
    
    # Extract the final message content
    return response["messages"][-1].content


async def stream_agent(payload, context=None) -> AsyncIterator[str]:
    """
    Streaming entrypoint for AWS Bedrock Agent Core Runtime.
    
    This function streams events as Server-Sent Events (SSE) format.
    
    Args:
        payload: Dictionary with keys:
            - 'prompt': User message (required)
            - 'session_id': Session ID for conversation continuity (optional)
            - 'actor_id': Actor ID for user/agent identification (optional)
            - 'stream_tokens': Enable token-by-token streaming (optional, default: False)
        context: AgentCore runtime context (optional, contains memory_id)
        
    Yields:
        str: SSE-formatted events
    """
    user_input = payload.get("prompt", "")
    session_id = payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-actor")
    stream_tokens = payload.get("stream_tokens", False)
    
    # Get memory ID from context if available
    memory_id = MEMORY_ID
    if context and hasattr(context, 'memory_id'):
        memory_id = context.memory_id
    
    # Prepare the input
    input_data = {
        "messages": [HumanMessage(content=user_input)],
    }
    
    # Add custom data fields if provided in payload
    if "preferences" in payload:
        input_data["user_preferences"] = payload["preferences"]
    
    if "custom_data" in payload:
        input_data["custom_data"] = payload["custom_data"]
    
    if "browsing_history" in payload:
        input_data["browsing_history"] = payload["browsing_history"]
    
    if "code_execution_history" in payload:
        input_data["code_execution_history"] = payload["code_execution_history"]
    
    # Set up event queue for callbacks
    event_queue = asyncio.Queue()
    
    # Create callbacks
    callbacks = create_callbacks(
        enable_console=False,
        enable_metrics=True,
        event_queue=event_queue if stream_tokens else None
    )
    
    # Build configuration
    config = {
        "metadata": {
            "request_timestamp": datetime.now().isoformat(),
            "request_source": payload.get("source", "api"),
        }
    }
    
    if memory_id:
        config["configurable"] = {
            "thread_id": session_id,
            "actor_id": actor_id,
        }
    
    if stream_tokens and callbacks:
        config["callbacks"] = callbacks
    
    # Emit start event
    yield format_sse_event(
        StreamEventType.AGENT_START,
        {
            "session_id": session_id,
            "actor_id": actor_id,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    try:
        # Start async task to consume callback events
        async def emit_callback_events():
            """Consume events from callback queue."""
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        
        # Stream events from LangGraph
        step_count = 0
        async for event in agent.astream(input_data, config=config, stream_mode="values"):
            step_count += 1
            
            # Emit step event
            if "messages" in event:
                messages = event["messages"]
                if messages:
                    last_msg = messages[-1]
                    
                    # Emit agent step with message content
                    yield format_sse_event(
                        StreamEventType.AGENT_STEP,
                        {
                            "step": step_count,
                            "node": "chatbot",
                            "content": last_msg.content if hasattr(last_msg, 'content') else str(last_msg),
                            "type": last_msg.type if hasattr(last_msg, 'type') else "unknown"
                        }
                    )
            
            # If token streaming is enabled, also emit from callback queue
            if stream_tokens and not event_queue.empty():
                try:
                    callback_event = event_queue.get_nowait()
                    yield callback_event.to_sse()
                except asyncio.QueueEmpty:
                    pass
        
        # Get final response
        final_response = event.get("messages", [])[-1] if event and "messages" in event else None
        final_content = final_response.content if final_response and hasattr(final_response, 'content') else ""
        
        # Get metrics if available
        metrics = {}
        for callback in callbacks:
            if isinstance(callback, MetricsCallback):
                metrics = callback.get_metrics()
                break
        
        # Emit end event
        yield format_sse_event(
            StreamEventType.AGENT_END,
            {
                "output": final_content,
                "steps": step_count,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        # Emit error event
        yield format_sse_event(
            StreamEventType.ERROR,
            {
                "error": str(e),
                "type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
        )


@app.entrypoint
def invoke_agent_streaming(payload, context=None):
    """
    Streaming entrypoint wrapper for sync compatibility.
    
    Args:
        payload: Request payload with 'stream' flag
        context: AgentCore runtime context
        
    Returns:
        Response (streaming or blocking based on payload)
    """
    # Check if streaming is requested
    if payload.get("stream", False):
        # Return async generator for streaming
        return stream_agent(payload, context)
    else:
        # Use regular blocking invoke
        return invoke_agent(payload, context)


if __name__ == "__main__":
    # This allows testing locally
    app.run()

