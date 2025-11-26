"""
Example streaming client for AWS Bedrock AgentCore.

This demonstrates how to consume streaming responses from the agent.
"""
import asyncio
import json
import sys


async def stream_request_example():
    """Example: Make a streaming request to the agent."""
    from agent_runtime import stream_agent
    
    payload = {
        "prompt": "Calculate 15 * 23 and explain the result",
        "session_id": "demo-session",
        "actor_id": "demo-user",
        "stream": True,
        "stream_tokens": False
    }
    
    print(f"🚀 Streaming request: {payload['prompt']}\n")
    print("=" * 70)
    
    async for event_str in stream_agent(payload):
        # Parse SSE format: "event: TYPE\ndata: JSON\n\n"
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data_str = lines[1].replace("data: ", "")
            data = json.loads(data_str)
            
            # Handle different event types
            if event_type == "agent_start":
                print(f"⏰ Agent started at {data['timestamp']}")
                print(f"   Session: {data['session_id']}")
                print("-" * 70)
            
            elif event_type == "agent_step":
                step = data['step']
                content = data.get('content', '')
                msg_type = data.get('type', 'unknown')
                
                if msg_type == 'human':
                    print(f"\n👤 User (Step {step}):")
                    print(f"   {content}")
                elif msg_type == 'ai':
                    print(f"\n🤖 Agent (Step {step}):")
                    print(f"   {content}")
                elif msg_type == 'tool':
                    print(f"\n🔧 Tool Result (Step {step}):")
                    print(f"   {content}")
            
            elif event_type == "agent_end":
                print("\n" + "-" * 70)
                print(f"✅ Agent completed in {data['steps']} steps")
                print(f"\n📝 Final Response:")
                print(f"   {data['output']}")
                
                if data.get('metrics'):
                    metrics = data['metrics']
                    print(f"\n📊 Metrics:")
                    print(f"   - Tool calls: {metrics.get('tool_calls', 0)}")
                    print(f"   - Errors: {metrics.get('errors', 0)}")
            
            elif event_type == "error":
                print(f"\n❌ Error: {data.get('error', 'Unknown error')}")
                print(f"   Type: {data.get('type', 'Unknown')}")
    
    print("=" * 70)


async def token_streaming_example():
    """Example: Stream tokens as they're generated."""
    from agent_runtime import stream_agent
    
    payload = {
        "prompt": "Explain what photosynthesis is in two sentences.",
        "session_id": "token-demo",
        "actor_id": "demo-user",
        "stream": True,
        "stream_tokens": True  # Enable token-level streaming
    }
    
    print(f"\n🚀 Token streaming request: {payload['prompt']}\n")
    print("=" * 70)
    print("Tokens: ", end="", flush=True)
    
    token_count = 0
    async for event_str in stream_agent(payload):
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data = json.loads(lines[1].replace("data: ", ""))
            
            if event_type == "llm_token":
                # Print token as it arrives
                token = data.get('token', '')
                print(token, end="", flush=True)
                token_count += 1
            
            elif event_type == "agent_end":
                print(f"\n\n✅ Streamed {token_count} tokens")
    
    print("=" * 70)


async def tool_progress_example():
    """Example: Monitor tool execution progress."""
    from agent_runtime import stream_agent
    
    payload = {
        "prompt": "What is the square root of 256 plus 10?",
        "session_id": "tool-demo",
        "actor_id": "demo-user",
        "stream": True
    }
    
    print(f"\n🚀 Tool execution monitoring: {payload['prompt']}\n")
    print("=" * 70)
    
    async for event_str in stream_agent(payload):
        if event_str.startswith("event:"):
            lines = event_str.strip().split("\n")
            event_type = lines[0].replace("event: ", "")
            data = json.loads(lines[1].replace("data: ", ""))
            
            if event_type == "tool_start":
                tool = data.get('tool', 'unknown')
                print(f"\n🔧 Tool '{tool}' starting...")
                print(f"   Input: {data.get('input', '')[:100]}")
            
            elif event_type == "tool_end":
                print(f"✅ Tool completed")
                print(f"   Output: {data.get('output', '')[:100]}")
            
            elif event_type == "agent_end":
                print(f"\n📝 Final: {data['output']}")
    
    print("=" * 70)


async def http_sse_client_example():
    """
    Example: HTTP client for Server-Sent Events.
    
    This shows how an external client would consume the streaming API.
    """
    print("\n🌐 HTTP SSE Client Example")
    print("=" * 70)
    print("""
# Using httpx (async HTTP client)
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        'POST',
        'https://your-agent-runtime.amazonaws.com/stream',
        json={
            "prompt": "What is 2+2?",
            "session_id": "web-session-1",
            "stream": True
        },
        timeout=60.0
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith('event:'):
                event_type = line.replace('event: ', '')
            elif line.startswith('data:'):
                data = json.loads(line.replace('data: ', ''))
                print(f"[{event_type}] {data}")

# Using JavaScript (browser)
const eventSource = new EventSource('/stream');

eventSource.addEventListener('agent_step', (e) => {
    const data = JSON.parse(e.data);
    console.log('Step:', data.step, data.content);
});

eventSource.addEventListener('agent_end', (e) => {
    const data = JSON.parse(e.data);
    console.log('Complete:', data.output);
    eventSource.close();
});
    """)
    print("=" * 70)


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("STREAMING CLIENT EXAMPLES")
    print("=" * 70)
    
    # Example 1: Basic streaming
    await stream_request_example()
    await asyncio.sleep(1)
    
    # Example 2: Token streaming (if enabled)
    # await token_streaming_example()
    # await asyncio.sleep(1)
    
    # Example 3: Tool progress
    await tool_progress_example()
    await asyncio.sleep(1)
    
    # Example 4: HTTP client
    await http_sse_client_example()
    
    print("\n✨ All examples completed!\n")


if __name__ == "__main__":
    asyncio.run(main())

