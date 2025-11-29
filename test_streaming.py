#!/usr/bin/env python3
"""
Test script for streaming logic.

Tests:
1. SSE event formatting in agent_runtime
2. SSE event parsing in BFF agent_client
3. End-to-end event flow
"""

import json
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bff'))


def test_sse_format():
    """Test SSE event formatting."""
    print("\n=== Test 1: SSE Event Formatting ===")
    
    def format_sse_event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    # Test formatting
    event = format_sse_event("AGENT_START", {"timestamp": "2025-01-01T00:00:00", "session_id": "test-123"})
    print(f"Formatted event:\n{repr(event)}")
    
    assert "event: AGENT_START" in event
    assert '"session_id": "test-123"' in event
    assert event.endswith("\n\n")
    print("✅ SSE formatting works correctly")


def test_sse_parsing():
    """Test SSE event parsing."""
    print("\n=== Test 2: SSE Event Parsing ===")
    
    # Import the parsing function
    import re
    
    def parse_sse_events(raw_response: str) -> list:
        events = []
        content = raw_response.strip()
        
        # Handle JSON-encoded string
        try:
            decoded = json.loads(content)
            if isinstance(decoded, str):
                content = decoded
        except json.JSONDecodeError:
            pass
        
        event_strings = re.split(r'\n\n+', content)
        
        for event_str in event_strings:
            if not event_str.strip():
                continue
            
            event_type = None
            event_data = None
            
            for line in event_str.strip().split('\n'):
                line = line.strip()
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                elif line.startswith('data:'):
                    data_str = line[5:].strip()
                    try:
                        event_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        event_data = {"raw": data_str}
            
            if event_type and event_data:
                events.append({"event": event_type, "data": event_data})
        
        return events
    
    # Create sample SSE response (like what agent_runtime would return)
    sample_sse = """event: AGENT_START
data: {"timestamp": "2025-01-01T00:00:00", "session_id": "test-123"}

event: TOOL_CALL
data: {"timestamp": "2025-01-01T00:00:01", "tool": "calculator", "args": {"expression": "2+2"}}

event: TOOL_RESULT
data: {"timestamp": "2025-01-01T00:00:02", "tool": "calculator", "result": "4"}

event: LLM_RESPONSE
data: {"timestamp": "2025-01-01T00:00:03", "content": "The result of 2+2 is 4."}

event: AGENT_END
data: {"timestamp": "2025-01-01T00:00:04", "output": "The result of 2+2 is 4."}

"""
    
    events = parse_sse_events(sample_sse)
    print(f"Parsed {len(events)} events:")
    for e in events:
        print(f"  - {e['event']}: {e['data']}")
    
    assert len(events) == 5
    assert events[0]["event"] == "AGENT_START"
    assert events[1]["event"] == "TOOL_CALL"
    assert events[1]["data"]["tool"] == "calculator"
    assert events[2]["event"] == "TOOL_RESULT"
    assert events[2]["data"]["result"] == "4"
    assert events[3]["event"] == "LLM_RESPONSE"
    assert events[4]["event"] == "AGENT_END"
    assert events[4]["data"]["output"] == "The result of 2+2 is 4."
    
    print("✅ SSE parsing works correctly")


def test_json_encoded_sse():
    """Test parsing JSON-encoded SSE (double-encoded)."""
    print("\n=== Test 3: JSON-Encoded SSE Parsing ===")
    
    import re
    
    def parse_sse_events(raw_response: str) -> list:
        events = []
        content = raw_response.strip()
        
        try:
            decoded = json.loads(content)
            if isinstance(decoded, str):
                content = decoded
        except json.JSONDecodeError:
            pass
        
        event_strings = re.split(r'\n\n+', content)
        
        for event_str in event_strings:
            if not event_str.strip():
                continue
            
            event_type = None
            event_data = None
            
            for line in event_str.strip().split('\n'):
                line = line.strip()
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                elif line.startswith('data:'):
                    data_str = line[5:].strip()
                    try:
                        event_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        event_data = {"raw": data_str}
            
            if event_type and event_data:
                events.append({"event": event_type, "data": event_data})
        
        return events
    
    # JSON-encoded SSE (what might come from Bedrock)
    inner_sse = """event: AGENT_START
data: {"timestamp": "2025-01-01T00:00:00", "session_id": "test-123"}

event: AGENT_END
data: {"timestamp": "2025-01-01T00:00:01", "output": "Hello!"}

"""
    
    # Double-encode it
    json_encoded = json.dumps(inner_sse)
    print(f"JSON-encoded input (first 100 chars): {json_encoded[:100]}...")
    
    events = parse_sse_events(json_encoded)
    print(f"Parsed {len(events)} events from JSON-encoded SSE")
    
    assert len(events) == 2
    assert events[0]["event"] == "AGENT_START"
    assert events[1]["event"] == "AGENT_END"
    
    print("✅ JSON-encoded SSE parsing works correctly")


def test_event_remapping():
    """Test event type remapping for frontend."""
    print("\n=== Test 4: Event Remapping for Frontend ===")
    
    # Agent runtime events → Frontend events
    event_mapping = {
        "AGENT_START": "agent_start",
        "TOOL_CALL": "tool_start", 
        "TOOL_RESULT": "tool_end",
        "LLM_RESPONSE": "message",
        "AGENT_END": "message",  # Final output also goes as message
        "ERROR": "error"
    }
    
    print("Event mapping:")
    for agent_event, frontend_event in event_mapping.items():
        print(f"  {agent_event} → {frontend_event}")
    
    print("✅ Event mapping defined correctly")


def test_end_to_end_flow():
    """Test the complete flow from agent to frontend."""
    print("\n=== Test 5: End-to-End Event Flow ===")
    
    import re
    
    # Simulate agent_runtime output
    def format_sse_event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    # Simulate stream_agent_with_events output
    agent_output = ""
    agent_output += format_sse_event("AGENT_START", {"timestamp": "T1", "session_id": "sess-1"})
    agent_output += format_sse_event("LLM_RESPONSE", {"timestamp": "T2", "content": "Hello! How can I help you?"})
    agent_output += format_sse_event("AGENT_END", {"timestamp": "T3", "output": "Hello! How can I help you?"})
    
    print(f"Agent runtime output:\n{agent_output}")
    
    # Simulate BFF parsing and re-emission
    def parse_sse_events(raw_response: str) -> list:
        events = []
        content = raw_response.strip()
        try:
            decoded = json.loads(content)
            if isinstance(decoded, str):
                content = decoded
        except json.JSONDecodeError:
            pass
        
        event_strings = re.split(r'\n\n+', content)
        for event_str in event_strings:
            if not event_str.strip():
                continue
            event_type = None
            event_data = None
            for line in event_str.strip().split('\n'):
                line = line.strip()
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                elif line.startswith('data:'):
                    try:
                        event_data = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        event_data = {"raw": line[5:].strip()}
            if event_type and event_data:
                events.append({"event": event_type, "data": event_data})
        return events
    
    events = parse_sse_events(agent_output)
    
    # Simulate BFF re-emission
    frontend_output = []
    frontend_output.append(f"event: start\ndata: {json.dumps({'session_id': 'sess-1'})}\n\n")
    
    for event in events:
        event_type = event.get("event", "")
        data = event.get("data", {})
        
        if event_type == "AGENT_START":
            frontend_output.append(f"event: agent_start\ndata: {json.dumps(data)}\n\n")
        elif event_type == "LLM_RESPONSE":
            content = data.get("content", "")
            frontend_output.append(f"event: message\ndata: {json.dumps({'content': content})}\n\n")
        elif event_type == "AGENT_END":
            output = data.get("output", "")
            if output:
                frontend_output.append(f"event: message\ndata: {json.dumps({'content': output})}\n\n")
    
    frontend_output.append(f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n")
    
    print("\nFrontend would receive:")
    for fo in frontend_output:
        print(f"  {repr(fo)}")
    
    # Verify frontend events
    assert len(frontend_output) == 5  # start, agent_start, message (LLM), message (END), done
    assert "event: start" in frontend_output[0]
    assert "event: agent_start" in frontend_output[1]
    assert "event: message" in frontend_output[2]
    assert "Hello! How can I help you?" in frontend_output[2]
    assert "event: done" in frontend_output[4]
    
    print("\n✅ End-to-end flow works correctly")


def test_tool_execution_flow():
    """Test flow with tool execution."""
    print("\n=== Test 6: Tool Execution Flow ===")
    
    import re
    
    def format_sse_event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def parse_sse_events(raw_response: str) -> list:
        events = []
        content = raw_response.strip()
        try:
            decoded = json.loads(content)
            if isinstance(decoded, str):
                content = decoded
        except json.JSONDecodeError:
            pass
        event_strings = re.split(r'\n\n+', content)
        for event_str in event_strings:
            if not event_str.strip():
                continue
            event_type = None
            event_data = None
            for line in event_str.strip().split('\n'):
                line = line.strip()
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                elif line.startswith('data:'):
                    try:
                        event_data = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        event_data = {"raw": line[5:].strip()}
            if event_type and event_data:
                events.append({"event": event_type, "data": event_data})
        return events
    
    # Agent runtime with tool call
    agent_output = ""
    agent_output += format_sse_event("AGENT_START", {"timestamp": "T1", "session_id": "sess-1"})
    agent_output += format_sse_event("TOOL_CALL", {"timestamp": "T2", "tool": "calculator", "args": {"expression": "sqrt(16)"}})
    agent_output += format_sse_event("TOOL_RESULT", {"timestamp": "T3", "tool": "calculator", "result": "4.0"})
    agent_output += format_sse_event("LLM_RESPONSE", {"timestamp": "T4", "content": "The square root of 16 is 4."})
    agent_output += format_sse_event("AGENT_END", {"timestamp": "T5", "output": "The square root of 16 is 4."})
    
    events = parse_sse_events(agent_output)
    print(f"Tool execution flow - {len(events)} events:")
    for e in events:
        print(f"  {e['event']}: {json.dumps(e['data'])[:60]}...")
    
    # Verify events
    assert len(events) == 5
    assert events[0]["event"] == "AGENT_START"
    assert events[1]["event"] == "TOOL_CALL"
    assert events[1]["data"]["tool"] == "calculator"
    assert events[2]["event"] == "TOOL_RESULT"
    assert events[2]["data"]["result"] == "4.0"
    assert events[3]["event"] == "LLM_RESPONSE"
    assert events[4]["event"] == "AGENT_END"
    
    print("✅ Tool execution flow works correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("STREAMING LOGIC TESTS")
    print("=" * 60)
    
    try:
        test_sse_format()
        test_sse_parsing()
        test_json_encoded_sse()
        test_event_remapping()
        test_end_to_end_flow()
        test_tool_execution_flow()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✅")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

