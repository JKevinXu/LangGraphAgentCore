"""
Streamlit Chat UI for LangGraphAgentCore BFF

Run with: streamlit run app.py
"""
import streamlit as st
import httpx
import json
import uuid
from typing import Generator, Tuple

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
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        margin-left: 0.5rem;
    }
    .status-connected {
        background-color: #065f46;
        color: #d1fae5;
    }
    .status-disconnected {
        background-color: #991b1b;
        color: #fee2e2;
    }
    .tool-status {
        background-color: #1e3a5f;
        color: #93c5fd;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
        border-left: 3px solid #3b82f6;
    }
    .tool-result {
        background-color: #1a3d1a;
        color: #86efac;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
        border-left: 3px solid #22c55e;
    }
</style>
""", unsafe_allow_html=True)

# Hard-coded BFF endpoint (deployed ALB)
BFF_ENDPOINT = "http://LangGr-BffSe-aO1aJ7AQgiMd-1474248023.us-west-2.elb.amazonaws.com"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:24]}"

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # New Conversation button - generates new session ID
    if st.button("🆕 New Conversation", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:24]}"
        st.rerun()
    
    st.divider()
    
    # Streaming toggle
    use_streaming = st.toggle("Enable Streaming", value=True)
    
    # Show tool events toggle
    show_tool_events = st.toggle("Show Tool Events", value=True)
    
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
    st.code(st.session_state.session_id, language=None)
    
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


def stream_response(bff_url: str, prompt: str, session_id: str, show_tools: bool = True) -> Generator[Tuple[str, str], None, None]:
    """
    Stream response from BFF using SSE.
    
    SSE Events handled:
    - event: start - Session started
    - event: agent_start - Agent started processing
    - event: tool_start - Tool execution started
    - event: tool_end - Tool execution completed
    - event: message - Content from agent
    - event: done - Streaming complete
    - event: error - Error occurred
    
    Yields:
        Tuple of (event_type, content) for UI to handle
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
                    yield ("error", f"HTTP {response.status_code}")
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
                        
                        # Handle event types
                        if event_type == "message":
                            content = data.get("content", "")
                            if content:
                                yield ("message", content)
                        
                        elif event_type == "tool_start" and show_tools:
                            tool_name = data.get("tool", "unknown")
                            yield ("tool_start", f"🔧 Using **{tool_name}**...")
                        
                        elif event_type == "tool_end" and show_tools:
                            tool_name = data.get("tool", "unknown")
                            result = data.get("result", "")
                            # Truncate long results
                            if len(str(result)) > 100:
                                result = str(result)[:100] + "..."
                            yield ("tool_end", f"✅ **{tool_name}** → {result}")
                        
                        elif event_type == "agent_start":
                            yield ("status", "🤔 Thinking...")
                        
                        elif event_type == "error":
                            yield ("error", data.get("error", "Unknown error"))
                            return
                        
                        elif event_type == "done":
                            return
                            
    except httpx.TimeoutException:
        yield ("error", "Request timed out. Please try again.")
    except httpx.ConnectError:
        yield ("error", "Could not connect to BFF. Is the service running?")
    except Exception as e:
        yield ("error", str(e))


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
            # Use a container to hold all streaming content
            stream_container = st.container()
            
            with stream_container:
                status_placeholder = st.empty()
                tool_events_container = st.container()
                response_placeholder = st.empty()
            
            full_response = ""
            tool_events_html = []
            
            for event_type, content in stream_response(bff_url, prompt, session_id, show_tool_events):
                if event_type == "message":
                    full_response = content
                    status_placeholder.empty()
                    response_placeholder.markdown(full_response + " ▌")
                
                elif event_type == "tool_start":
                    tool_events_html.append(f'<div class="tool-status">{content}</div>')
                    with tool_events_container:
                        st.markdown("".join(tool_events_html), unsafe_allow_html=True)
                
                elif event_type == "tool_end":
                    # Replace the last tool_start with tool_end result
                    if tool_events_html:
                        tool_events_html[-1] = f'<div class="tool-result">{content}</div>'
                    else:
                        tool_events_html.append(f'<div class="tool-result">{content}</div>')
                    with tool_events_container:
                        st.markdown("".join(tool_events_html), unsafe_allow_html=True)
                
                elif event_type == "status":
                    status_placeholder.markdown(f"*{content}*")
                
                elif event_type == "error":
                    full_response = f"Error: {content}"
                    status_placeholder.empty()
                    response_placeholder.markdown(full_response)
            
            # Final display without cursor
            status_placeholder.empty()
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
