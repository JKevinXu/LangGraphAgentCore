"""
AWS Bedrock Agent Core Runtime integration for LangGraphAgentCore.

This module enables deploying your LangGraph agents to AWS Bedrock Agent Core Runtime.
Supports TRUE STREAMING via async generators as per AWS documentation.
Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph.graph import StateGraph, MessagesState, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph_checkpoint_aws import AgentCoreMemorySaver
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from datetime import datetime
from typing import Annotated, TypedDict, AsyncGenerator
import os
import json
from browser_tool import get_browser_tool
from code_interpreter_tool import get_code_interpreter_tool
from langfuse_config import get_langfuse_handler, update_trace_context, flush_langfuse

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


# Create agent with Bedrock model
def create_agent():
    """Create and configure the LangGraph agent with Bedrock and memory support."""
    
    # Initialize Bedrock LLM
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        model_kwargs={"temperature": 0.7}
    )
    
    # Get browser tool (enabled by default in supported regions)
    browser_tool = get_browser_tool()
    
    # Get code interpreter tool (enabled by default)
    code_tool = get_code_interpreter_tool()
    
    # Bind tools to the LLM - only AgentCore tools (browser + code interpreter)
    tools = []
    
    if browser_tool:
        tools.append(browser_tool)
        print("✅ Browser tool enabled (AgentCore Browser)")
    else:
        print("⚠️  Browser tool unavailable - check IAM permissions for bedrock-agentcore:ConnectBrowserAutomationStream")
    
    if code_tool:
        tools.append(code_tool)
        print("✅ Code Interpreter tool enabled (AgentCore Code Interpreter)")
    else:
        print("⚠️  Code Interpreter unavailable - check IAM permissions")
    
    if not tools:
        raise RuntimeError("No tools available! Check IAM permissions for AgentCore Browser and Code Interpreter.")
    
    llm_with_tools = llm.bind_tools(tools)
    
    # System message
    system_message = """You're a helpful assistant powered by AWS Bedrock AgentCore with the following capabilities:

1. **Code Interpreter** (execute_code): Execute Python code in a secure sandboxed environment
   - Run calculations, data analysis, and algorithms
   - Use libraries like NumPy, Pandas, Matplotlib
   - Generate visualizations and process data

2. **Web Browser** (browse_web): Browse websites and extract information
   - Navigate to URLs and extract content
   - Search for information online
   - Interact with web pages

When asked to calculate something, use the code interpreter to write and execute Python code.
When asked about current information or websites, use the browser tool.
Always explain your results clearly."""
    
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


def format_sse_event(event_type: str, data: dict) -> str:
    """Format an event as SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_agent_async(agent, input_data: dict, config: dict = None, session_id: str = "unknown", callbacks: list = None) -> AsyncGenerator[str, None]:
    """
    Stream agent execution events using async generator.
    
    Uses LangGraph's astream() for TRUE async streaming as per AWS docs:
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html
    
    Yields:
        SSE-formatted event strings as they happen in real-time
    """
    # Start event
    yield format_sse_event("AGENT_START", {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    })
    
    # Thinking event - immediate feedback while LLM reasons
    yield format_sse_event("THINKING", {
        "timestamp": datetime.now().isoformat(),
        "status": "reasoning",
        "message": "Analyzing your request..."
    })
    
    final_output = ""
    
    try:
        # Add callbacks to config if provided
        stream_config = config.copy() if config else {}
        if callbacks:
            stream_config["callbacks"] = callbacks
        
        # Use astream() for TRUE async streaming - events are yielded as they happen!
        async for event in agent.astream(input_data, config=stream_config, stream_mode="updates"):
            timestamp = datetime.now().isoformat()
            
            # Process each node's output immediately
            for node_name, node_output in event.items():
                if node_name == "chatbot":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    yield format_sse_event("TOOL_CALL", {
                                        "timestamp": timestamp,
                                        "tool": tool_call.get("name", "unknown"),
                                        "args": tool_call.get("args", {})
                                    })
                            else:
                                content = msg.content if hasattr(msg, 'content') else str(msg)
                                final_output = content
                                yield format_sse_event("LLM_RESPONSE", {
                                    "timestamp": timestamp,
                                    "content": content
                                })
                                
                elif node_name == "tools":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, ToolMessage):
                            yield format_sse_event("TOOL_RESULT", {
                                "timestamp": timestamp,
                                "tool": msg.name if hasattr(msg, 'name') else "unknown",
                                "result": msg.content if hasattr(msg, 'content') else str(msg)
                            })
        
        # End event
        yield format_sse_event("AGENT_END", {
            "timestamp": datetime.now().isoformat(),
            "output": final_output
        })
        
    except Exception as e:
        yield format_sse_event("ERROR", {
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })


@app.entrypoint
async def invoke_agent(payload, context=None):
    """
    Async entrypoint for AWS Bedrock Agent Core Runtime with TRUE STREAMING.
    
    Uses async generator pattern as per AWS documentation:
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html
    
    When stream=True, yields SSE events in real-time using async for.
    When stream=False, returns the final response string (blocking).
    
    Args:
        payload: Dictionary with keys:
            - 'prompt': User message (required)
            - 'session_id': Session ID for conversation continuity (optional)
            - 'actor_id': Actor ID for user/agent identification (optional)
            - 'stream': If True, returns SSE stream (optional, default False)
        context: AgentCore runtime context (optional, contains memory_id)
        
    Returns:
        If stream=True: Async generator yielding SSE events in real-time
        If stream=False: Agent's final response string
    """
    user_input = payload.get("prompt", "")
    session_id = payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-actor")
    use_streaming = payload.get("stream", False)
    
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
    
    # Initialize Langfuse callback handler for observability (v3 API)
    langfuse_handler = get_langfuse_handler()
    
    # Build callbacks list
    callbacks = []
    if langfuse_handler:
        callbacks.append(langfuse_handler)
        # Set trace context (session_id, user_id, etc.)
        update_trace_context(
            session_id=session_id,
            user_id=actor_id,
            metadata={"request_source": payload.get("source", "api")},
        )
    
    # Build config
    config = None
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
            },
        }
        print(f"🔗 Using memory: {memory_id} for session: {session_id}")
    else:
        print("ℹ️  No memory configured, running without persistence")
    
    # STREAMING MODE: Use async generator for TRUE real-time streaming
    if use_streaming:
        print("📡 TRUE ASYNC STREAMING enabled")
        # Yield events from async generator - each event is sent immediately!
        async for event in stream_agent_async(agent, input_data, config, session_id, callbacks):
            yield event
        
        # Flush Langfuse traces after streaming
        if langfuse_handler:
            flush_langfuse()
    else:
        # NON-STREAMING MODE: Blocking invoke, yield single result
        invoke_config = config.copy() if config else {}
        if callbacks:
            invoke_config["callbacks"] = callbacks
        
        if invoke_config:
            response = agent.invoke(input_data, config=invoke_config)
        else:
            response = agent.invoke(input_data)
        
        # Flush Langfuse traces before returning
        if langfuse_handler:
            flush_langfuse()
        
        yield response["messages"][-1].content


if __name__ == "__main__":
    # This allows testing locally
    app.run()

