"""
Test script for streaming functionality.

Usage:
    python test_streaming.py
"""
import asyncio
import json
from agent_runtime import stream_agent, invoke_agent
from streaming_utils import StreamEventType


async def test_basic_streaming():
    """Test basic streaming without token-level streaming."""
    print("=" * 60)
    print("TEST 1: Basic Streaming (Step-level)")
    print("=" * 60)
    
    payload = {
        "prompt": "What is 25 * 4?",
        "session_id": "test-stream-1",
        "actor_id": "test-user",
        "stream_tokens": False
    }
    
    print(f"\nPrompt: {payload['prompt']}\n")
    print("Streaming events:")
    print("-" * 60)
    
    event_count = 0
    async for event_str in stream_agent(payload):
        event_count += 1
        # Parse SSE format
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data = json.loads(lines[1].replace("data: ", ""))
            
            print(f"[{event_type}]", json.dumps(data, indent=2))
    
    print(f"\n✅ Received {event_count} events")
    print("=" * 60)
    print()


async def test_token_streaming():
    """Test token-level streaming."""
    print("=" * 60)
    print("TEST 2: Token-Level Streaming")
    print("=" * 60)
    
    payload = {
        "prompt": "Explain what 2+2 equals in one sentence.",
        "session_id": "test-stream-2",
        "actor_id": "test-user",
        "stream_tokens": True
    }
    
    print(f"\nPrompt: {payload['prompt']}\n")
    print("Streaming events:")
    print("-" * 60)
    
    token_count = 0
    async for event_str in stream_agent(payload):
        # Parse SSE format
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data = json.loads(lines[1].replace("data: ", ""))
            
            if event_type == StreamEventType.LLM_TOKEN:
                token_count += 1
                print(f"Token {token_count}: {data.get('token', '')}")
            else:
                print(f"[{event_type}]", json.dumps(data, indent=2))
    
    print(f"\n✅ Received {token_count} tokens")
    print("=" * 60)
    print()


async def test_tool_streaming():
    """Test streaming with tool execution."""
    print("=" * 60)
    print("TEST 3: Tool Execution Streaming")
    print("=" * 60)
    
    payload = {
        "prompt": "Calculate the square root of 144 and tell me the result.",
        "session_id": "test-stream-3",
        "actor_id": "test-user",
        "stream_tokens": False
    }
    
    print(f"\nPrompt: {payload['prompt']}\n")
    print("Streaming events:")
    print("-" * 60)
    
    tool_events = []
    async for event_str in stream_agent(payload):
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data = json.loads(lines[1].replace("data: ", ""))
            
            if "TOOL" in event_type:
                tool_events.append((event_type, data))
                print(f"🔧 [{event_type}]", json.dumps(data, indent=2))
            else:
                print(f"[{event_type}]", json.dumps(data, indent=2))
    
    print(f"\n✅ Tool events: {len(tool_events)}")
    print("=" * 60)
    print()


async def test_error_handling():
    """Test error handling in streaming."""
    print("=" * 60)
    print("TEST 4: Error Handling")
    print("=" * 60)
    
    payload = {
        "prompt": "Calculate 1/0",  # This should trigger calculator error
        "session_id": "test-stream-4",
        "actor_id": "test-user",
        "stream_tokens": False
    }
    
    print(f"\nPrompt: {payload['prompt']}\n")
    print("Streaming events:")
    print("-" * 60)
    
    error_count = 0
    async for event_str in stream_agent(payload):
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data = json.loads(lines[1].replace("data: ", ""))
            
            if event_type == StreamEventType.ERROR:
                error_count += 1
                print(f"❌ [{event_type}]", json.dumps(data, indent=2))
            else:
                print(f"[{event_type}]", json.dumps(data, indent=2))
    
    print(f"\n✅ Handled {error_count} error(s)")
    print("=" * 60)
    print()


def test_blocking_invoke():
    """Test backward compatibility with blocking invoke."""
    print("=" * 60)
    print("TEST 5: Backward Compatibility (Blocking)")
    print("=" * 60)
    
    payload = {
        "prompt": "What is 10 + 5?",
        "session_id": "test-blocking-1",
        "actor_id": "test-user"
    }
    
    print(f"\nPrompt: {payload['prompt']}\n")
    print("Invoking agent (blocking)...")
    
    response = invoke_agent(payload)
    
    print(f"\nResponse: {response}")
    print("\n✅ Blocking invocation successful")
    print("=" * 60)
    print()


async def test_memory_streaming():
    """Test streaming with memory/session continuity."""
    print("=" * 60)
    print("TEST 6: Streaming with Memory")
    print("=" * 60)
    
    session_id = "test-memory-stream"
    
    # First message
    payload1 = {
        "prompt": "My name is Alice and I like pizza.",
        "session_id": session_id,
        "actor_id": "test-user",
        "stream_tokens": False
    }
    
    print(f"\nMessage 1: {payload1['prompt']}")
    print("Streaming...")
    
    async for event_str in stream_agent(payload1):
        if "AGENT_END" in event_str:
            lines = event_str.strip().split("\n")
            data = json.loads(lines[1].replace("data: ", ""))
            print(f"Response: {data.get('output', '')[:100]}...")
            break
    
    # Second message (should remember)
    payload2 = {
        "prompt": "What is my name?",
        "session_id": session_id,
        "actor_id": "test-user",
        "stream_tokens": False
    }
    
    print(f"\nMessage 2: {payload2['prompt']}")
    print("Streaming...")
    
    async for event_str in stream_agent(payload2):
        if "AGENT_END" in event_str:
            lines = event_str.strip().split("\n")
            data = json.loads(lines[1].replace("data: ", ""))
            response = data.get('output', '')
            print(f"Response: {response}")
            
            # Check if agent remembered
            if "Alice" in response:
                print("\n✅ Memory working! Agent remembered the name.")
            else:
                print("\n⚠️  Memory may not be working correctly.")
            break
    
    print("=" * 60)
    print()


async def run_all_tests():
    """Run all streaming tests."""
    print("\n" + "=" * 60)
    print("STREAMING FUNCTIONALITY TESTS")
    print("=" * 60 + "\n")
    
    # Test 1: Basic streaming
    await test_basic_streaming()
    await asyncio.sleep(1)
    
    # Test 2: Token streaming (if callbacks work)
    # await test_token_streaming()
    # await asyncio.sleep(1)
    
    # Test 3: Tool execution
    await test_tool_streaming()
    await asyncio.sleep(1)
    
    # Test 4: Error handling
    await test_error_handling()
    await asyncio.sleep(1)
    
    # Test 5: Backward compatibility
    test_blocking_invoke()
    await asyncio.sleep(1)
    
    # Test 6: Memory continuity
    await test_memory_streaming()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())

