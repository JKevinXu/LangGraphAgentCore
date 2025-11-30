# Streaming Implementation

This document describes the real-time streaming implementation for LangGraphAgentCore.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Bedrock AgentCore Runtime                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ @app.entrypoint                                                 │ │
│  │ async def invoke_agent(payload):                               │ │
│  │   async for event in agent.astream(...):                       │ │
│  │     yield format_sse_event(event)  ← Events sent immediately   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP Chunked Transfer (real-time)
┌─────────────────────────────────────────────────────────────────────┐
│                        BFF (aioboto3)                                │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐   │
│  │   FastAPI    │───▶│  AgentClient    │───▶│  Bedrock Client  │   │
│  │   Routes     │    │  (Producer)     │    │  invoke_agent_rt │   │
│  └──────────────┘    └─────────────────┘    └────────┬─────────┘   │
│         │                    │                       │             │
│         │              ┌─────▼─────┐                 │             │
│         │              │  AsyncIO  │◀────────────────┘             │
│         │              │   Queue   │   iter_chunks() - real-time   │
│         │              └─────┬─────┘                               │
│         │                    │                                     │
│         ▼                    ▼                                     │
│  ┌──────────────────────────────┐                                  │
│  │     SSE Generator            │                                  │
│  │  yield f"event: {}\n\n"      │                                  │
│  └──────────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼ text/event-stream
                      ┌────────┐
                      │ Client │
                      └────────┘
```

## Key Components

### 1. Agent Runtime (bedrock/agent_runtime.py)

Uses async generator pattern per [AWS documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html):

```python
@app.entrypoint
async def invoke_agent(payload, context=None):
    if use_streaming:
        async for event in stream_agent_async(agent, input_data, config, session_id):
            yield event
    else:
        yield agent.invoke(input_data)["messages"][-1].content
```

Streaming function uses LangGraph's `astream()`:

```python
async def stream_agent_async(agent, input_data, config, session_id):
    yield format_sse_event("AGENT_START", {...})
    
    async for event in agent.astream(input_data, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_name == "chatbot":
                # Handle AIMessage - tool calls or responses
                yield format_sse_event("TOOL_CALL", {...})
                yield format_sse_event("LLM_RESPONSE", {...})
            elif node_name == "tools":
                # Handle ToolMessage
                yield format_sse_event("TOOL_RESULT", {...})
    
    yield format_sse_event("AGENT_END", {...})
```

### 2. BFF Agent Client (bff/app/services/agent_client.py)

Uses **aioboto3** for TRUE async streaming (not boto3 which buffers):

```python
class AgentClient:
    def __init__(self):
        self.session = aioboto3.Session()  # aioboto3, not boto3!
```

Queue-based producer-consumer pattern:

```python
class StreamingCallbackHandler:
    def __init__(self, session_id: str):
        self.queue: asyncio.Queue = asyncio.Queue()
    
    async def push_event(self, event_type: str, data: dict):
        await self.queue.put(StreamEvent(event_type, data))
    
    async def get_event(self, timeout: float = 120.0):
        return await asyncio.wait_for(self.queue.get(), timeout=timeout)
    
    async def end_streaming(self):
        await self.queue.put(None)  # Sentinel
```

Producer iterates over response stream:

```python
async def _process_bedrock_stream(self, prompt, session_id, actor_id, callback):
    async with self.session.client("bedrock-agentcore") as client:
        response = await client.invoke_agent_runtime(...)
        streaming_body = response.get("response")
        
        # TRUE ASYNC STREAMING - chunks arrive in real-time
        async for chunk in streaming_body.iter_chunks():
            # Parse and push events to queue immediately
            await callback.push_event(event_type, event_data)
    
    await callback.end_streaming()
```

Consumer yields from queue:

```python
async def invoke_stream(self, prompt, session_id, actor_id):
    callback = StreamingCallbackHandler(session_id)
    
    # Spawn producer as background task
    producer_task = asyncio.create_task(
        self._process_bedrock_stream(prompt, session_id, actor_id, callback)
    )
    
    # Consumer: yield events from queue
    while True:
        event = await callback.get_event()
        if event is None:  # Sentinel
            break
        yield f"event: {event.event_type}\ndata: {json.dumps(event.data)}\n\n"
```

### 3. Frontend (bff/ui/app.py)

Streamlit UI handles SSE events:

```python
def stream_response(bff_url, prompt, session_id):
    with httpx.Client().stream("POST", url, ...) as response:
        for chunk in response.iter_text():
            # Parse SSE events
            yield {"type": event_type, **data}
```

Display with accumulation:

```python
for event in stream_response(...):
    if event["type"] == "agent_start":
        event_log.append("🤔 Thinking...")
    elif event["type"] == "tool_start":
        event_log.append(f"🔧 **{tool_name}**({args})")
    elif event["type"] == "tool_end":
        event_log.append(f"✅ Result: `{result}`")
    elif event["type"] == "message":
        response_placeholder.markdown(content + " ▌")
```

## SSE Event Format

### Agent Runtime → BFF

```
event: AGENT_START
data: {"timestamp": "...", "session_id": "..."}

event: TOOL_CALL
data: {"timestamp": "...", "tool": "calculator", "args": {"expression": "5+5"}}

event: TOOL_RESULT
data: {"timestamp": "...", "tool": "calculator", "result": "10"}

event: LLM_RESPONSE
data: {"timestamp": "...", "content": "The result is 10."}

event: AGENT_END
data: {"timestamp": "...", "output": "The result is 10."}
```

### BFF → Frontend

```
event: start
data: {"session_id": "..."}

event: agent_start
data: {"session_id": "...", "status": "started"}

event: tool_start
data: {"tool": "calculator", "args": {"expression": "5+5"}}

event: tool_end
data: {"tool": "calculator", "result": "10"}

event: message
data: {"content": "The result is 10.", "partial": true}

event: done
data: {"status": "complete"}
```

## Why aioboto3?

Standard `boto3` buffers the entire response before returning, even when using `iter_lines()`. This defeats streaming.

**Proof from logs:**

With boto3 (buffered):
```
00:55:23.419 - ALL events arrive at same millisecond
```

With aioboto3 (real-time):
```
01:10:16.790 - AGENT_START
01:10:18.595 - TOOL_CALL      (+1.8s real delay)
01:10:18.879 - TOOL_RESULT    (+0.3s real delay)
01:10:20.396 - LLM_RESPONSE   (+1.5s real delay)
```

## Dependencies

### Agent Runtime (bedrock/requirements.txt)
```
langgraph>=0.2.0
langchain-aws>=0.2.0
bedrock-agentcore>=1.0.0
```

### BFF (bff/requirements.txt)
```
fastapi>=0.109.0
aioboto3>=12.0.0  # NOT boto3!
httpx>=0.26.0
```

## Testing

```bash
# Test streaming endpoint
curl -X POST "http://<BFF_URL>/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "What is 5+5?", "session_id": "test-session-123456789012345"}' \
  --no-buffer
```

Expected output with real-time delays:
```
event: start
data: {"session_id": "test-session-123456789012345"}

event: agent_start
data: {"session_id": "test-session-123456789012345", "status": "started"}

[~2 second delay - LLM processing]

event: tool_start
data: {"tool": "calculator", "args": {"expression": "5 + 5"}}

event: tool_end
data: {"tool": "calculator", "result": "10"}

[~1.5 second delay - LLM response generation]

event: message
data: {"content": "The result of 5 + 5 is 10.", "partial": true}

event: done
data: {"status": "complete"}
```

## References

- [AWS Bedrock AgentCore Streaming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html)
- [LangGraph Streaming](https://langchain-ai.github.io/langgraph/how-tos/streaming-tokens/)
- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)

