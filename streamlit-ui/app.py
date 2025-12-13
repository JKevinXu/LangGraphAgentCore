"""
Streamlit Chat UI for LangGraphAgentCore BFF

Run with: streamlit run app.py
"""
import streamlit as st
import httpx
import json
import uuid
from typing import Generator

# Page config
st.set_page_config(
    page_title="LangGraph Agent Chat",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
    }
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid #333;
        margin-bottom: 1rem;
    }
    .tool-call {
        background-color: rgba(147, 197, 253, 0.3);
        border-left: 3px solid #3b82f6;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        font-size: 0.85rem;
        color: #000000;
    }
    .tool-result {
        background-color: rgba(134, 239, 172, 0.3);
        border-left: 3px solid #10b981;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        font-size: 0.85rem;
        color: #000000;
    }
    .tool-events-container {
        margin-bottom: 0.75rem;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Hard-coded BFF endpoint (deployed ALB)
BFF_ENDPOINT = "http://LangGr-BffSe-aO1aJ7AQgiMd-1474248023.us-west-2.elb.amazonaws.com"

# Initialize session state - session_id must be at least 33 characters for AgentCore
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-session-{uuid.uuid4().hex}"

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # New Conversation button - generates new session ID
    if st.button("🆕 New Conversation", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"streamlit-session-{uuid.uuid4().hex}"
        st.rerun()
    
    st.divider()
    
    # Streaming toggle
    use_streaming = st.toggle("Enable Streaming", value=True)
    
    # Show tool events toggle
    show_tools = st.toggle("Show Tool Events", value=True)
    
    # Connection test
    if st.button("🔗 Test Connection", use_container_width=True):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{BFF_ENDPOINT}/health")
                if response.status_code == 200:
                    st.success("✅ Connected!")
                else:
                    st.error(f"❌ Status: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Failed: {e}")
    
    st.divider()
    
    # Display current session info
    st.caption(f"**Session ID:**")
    st.code(st.session_state.session_id[:20] + "...", language=None)
    
    st.divider()
    st.caption("LangGraphAgentCore BFF UI")

# Use hard-coded endpoint
bff_url = BFF_ENDPOINT
session_id = st.session_state.session_id

# Main header
st.markdown("""
<div class="main-header">
    <h1>🤖 LangGraph Agent</h1>
    <p>Chat with your AI agent powered by AWS Bedrock</p>
</div>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def stream_response(bff_url: str, prompt: str, session_id: str, show_tools: bool = True) -> Generator[dict, None, None]:
    """
    Stream response from BFF using SSE.
    
    SSE Events from BFF:
    - event: start - Session started
    - event: agent_start - Agent processing started
    - event: tool_start - Tool being called
    - event: tool_end - Tool finished
    - event: message - Content chunk (may be partial or final)
    - event: done - Streaming complete
    - event: error - Error occurred
    
    Yields:
        Dict with event type and data
    """
    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{bff_url}/v1/chat/stream",
                json={"message": prompt, "session_id": session_id},
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status_code != 200:
                    yield {"type": "error", "content": f"HTTP {response.status_code}"}
                    return
                
                buffer = ""
                
                for chunk in response.iter_text():
                    buffer += chunk
                    
                    # Process complete SSE events (separated by double newlines)
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        
                        if not event_str.strip():
                            continue
                        
                        # Parse event type and data
                        event_type = "message"
                        data = {}
                        
                        for line in event_str.strip().split("\n"):
                            if line.startswith("event: "):
                                event_type = line[7:].strip()
                            elif line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                except json.JSONDecodeError:
                                    data = {"content": line[6:]}
                        
                        # Yield event based on type
                        if event_type == "tool_start" and show_tools:
                            yield {
                                "type": "tool_start",
                                "tool": data.get("tool", "unknown"),
                                "args": data.get("args", {})
                            }
                        
                        elif event_type == "tool_end" and show_tools:
                            yield {
                                "type": "tool_end",
                                "tool": data.get("tool", "unknown"),
                                "result": data.get("result", "")
                            }
                        
                        elif event_type == "message":
                            content = data.get("content", "")
                            if content:
                                yield {
                                    "type": "message",
                                    "content": content,
                                    "partial": data.get("partial", True),
                                    "final": data.get("final", False)
                                }
                        
                        elif event_type == "error":
                            yield {"type": "error", "content": data.get("error", "Unknown error")}
                            return
                        
                        elif event_type == "done":
                            return
                            
    except httpx.TimeoutException:
        yield {"type": "error", "content": "Request timed out. Please try again."}
    except httpx.ConnectError:
        yield {"type": "error", "content": "Could not connect to BFF. Is the service running?"}
    except Exception as e:
        yield {"type": "error", "content": str(e)}


def get_response(bff_url: str, prompt: str, session_id: str) -> str:
    """Get blocking response from BFF."""
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{bff_url}/v1/chat",
                json={"message": prompt, "session_id": session_id}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("message", str(data))
            else:
                return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {e}"


# Chat input
if prompt := st.chat_input("Type your message..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        if use_streaming:
            # Streaming response with tool events
            response_container = st.container()
            tool_events_placeholder = response_container.empty()
            response_placeholder = response_container.empty()
            
            full_response = ""
            tool_events_html = []
            
            for event in stream_response(bff_url, prompt, session_id, show_tools):
                event_type = event.get("type")
                
                if event_type == "tool_start":
                    tool_name = event.get("tool", "unknown")
                    args = event.get("args", {})
                    args_str = json.dumps(args) if args else ""
                    tool_events_html.append(f'<div class="tool-call">🔧 Calling <b>{tool_name}</b>({args_str})</div>')
                    # Update tool events display
                    tool_events_placeholder.markdown(
                        f'<div class="tool-events-container">{"".join(tool_events_html)}</div>',
                        unsafe_allow_html=True
                    )
                
                elif event_type == "tool_end":
                    tool_name = event.get("tool", "unknown")
                    result = event.get("result", "")
                    # Truncate long results
                    display_result = result[:100] + "..." if len(str(result)) > 100 else result
                    tool_events_html.append(f'<div class="tool-result">✅ <b>{tool_name}</b> → {display_result}</div>')
                    # Update tool events display
                    tool_events_placeholder.markdown(
                        f'<div class="tool-events-container">{"".join(tool_events_html)}</div>',
                        unsafe_allow_html=True
                    )
                
                elif event_type == "message":
                    content = event.get("content", "")
                    if content:
                        full_response = content
                        # Show response with cursor (keep tool events visible)
                        response_placeholder.markdown(full_response + " ▌")
                
                elif event_type == "error":
                    full_response = f"Error: {event.get('content', 'Unknown error')}"
                    response_placeholder.error(full_response)
            
            # Final display without cursor (tool events remain visible)
            if full_response:
                response_placeholder.markdown(full_response)
            else:
                response_placeholder.markdown("*No response received*")
        else:
            # Blocking response
            with st.spinner("Thinking..."):
                full_response = get_response(bff_url, prompt, session_id)
            st.markdown(full_response)
        
        # Clean up response for storage - handle escaped quotes and newlines
        clean_response = full_response.strip()
        if clean_response.startswith('"') and clean_response.endswith('"'):
            clean_response = clean_response[1:-1]
        clean_response = clean_response.replace('\\"', '"').replace('\\n', '\n')
        st.session_state.messages.append({"role": "assistant", "content": clean_response})


# Footer
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.caption(f"Session: `{session_id[:20]}...`")
with col2:
    st.caption(f"Messages: {len(st.session_state.messages)}")
