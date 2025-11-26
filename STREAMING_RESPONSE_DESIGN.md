# Streaming Response with Callback Handling - Design Document

## Problem Statement

Current implementation uses blocking request/response pattern. Need streaming responses for:
- Real-time user feedback
- Lower perceived latency
- Token-by-token LLM output
- Progress updates during tool execution

## Current Architecture

```
User Request → AWS Bedrock AgentCore → LangGraph Agent → Complete Response
                                           ↓
                                    Tools (blocking)
```

**Limitations:**
- User waits for complete response
- No intermediate feedback
- Poor UX for long-running operations

## Proposed Architecture

```
User Request → AWS Bedrock AgentCore → LangGraph Agent (streaming)
                    ↓                        ↓
               SSE/WebSocket          Event Callbacks
                    ↓                        ↓
                 Client              Tool Progress Updates
```

## LangGraph Streaming APIs

### 1. Stream Mode Options

```python
# Stream all events (most detailed)
for event in graph.stream(input, stream_mode="values"):
    print(event)

# Stream updates only
for event in graph.stream(input, stream_mode="updates"):
    print(event)

# Stream messages (for chat applications)
for event in graph.stream(input, stream_mode="messages"):
    print(event)
```

### 2. Async Streaming

```python
async def stream_agent(input_data):
    async for event in graph.astream(input_data, stream_mode="values"):
        yield event
```

## AWS Bedrock Streaming Integration

### Current Invoke Pattern

```python
# bedrock/agent_runtime.py (current)
def invoke_agent(payload):
    result = graph.invoke(input_data, config)
    return result
```

### Proposed Streaming Pattern

```python
# bedrock/agent_runtime.py (proposed)
async def stream_agent(payload):
    """Stream agent responses with callback support."""
    async for chunk in graph.astream(
        input_data,
        config,
        stream_mode="values"
    ):
        # Invoke callbacks
        await on_chunk_callback(chunk)
        yield format_chunk(chunk)
```

## Callback Design

### Event Types

```python
class StreamEvent:
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    LLM_TOKEN = "llm_token"
    LLM_END = "llm_end"
    ERROR = "error"
```

### Callback Interface

```python
class StreamCallback:
    """Base callback handler for streaming events."""
    
    async def on_agent_start(self, metadata: dict):
        """Called when agent starts processing."""
        pass
    
    async def on_llm_token(self, token: str, metadata: dict):
        """Called for each LLM token."""
        pass
    
    async def on_tool_start(self, tool_name: str, inputs: dict):
        """Called when tool execution starts."""
        pass
    
    async def on_tool_end(self, tool_name: str, outputs: dict):
        """Called when tool execution ends."""
        pass
    
    async def on_agent_end(self, final_output: dict):
        """Called when agent completes."""
        pass
    
    async def on_error(self, error: Exception):
        """Called on error."""
        pass
```

### Callback Registration

```python
# Register callbacks in config
config = {
    "configurable": {
        "thread_id": session_id,
        "actor_id": actor_id
    },
    "callbacks": [
        ConsoleCallback(),      # Log to console
        MetricsCallback(),      # Collect metrics
        WebSocketCallback(),    # Send to WebSocket
    ]
}
```

## Implementation Steps

### Phase 1: Core Streaming (Week 1)

1. **Update `agent_runtime.py`**
   ```python
   async def stream_handler(payload: dict):
       """Handle streaming requests."""
       async for event in graph.astream(input_data, config):
           yield format_event(event)
   ```

2. **Add streaming endpoint**
   ```python
   @app.post("/stream")
   async def stream_endpoint(request: Request):
       return StreamingResponse(
           stream_handler(await request.json()),
           media_type="text/event-stream"
       )
   ```

3. **Event formatting**
   ```python
   def format_event(event: dict) -> str:
       """Format event for SSE."""
       return f"data: {json.dumps(event)}\n\n"
   ```

### Phase 2: Callbacks (Week 2)

1. **Implement base callback class** in `bedrock/callbacks.py`
2. **Add LangChain callback integration**
   ```python
   from langchain.callbacks import AsyncCallbackHandler
   
   class AgentStreamCallback(AsyncCallbackHandler):
       async def on_llm_new_token(self, token: str, **kwargs):
           await self.emit_token(token)
   ```

3. **WebSocket handler** for real-time updates

### Phase 3: Tool Progress (Week 3)

1. **Update tool wrappers** to emit progress events
   ```python
   @tool
   async def browse_web(task: str, callbacks: list):
       await emit_event("tool_start", {"tool": "browse_web"})
       # ... tool execution ...
       await emit_event("tool_progress", {"status": "navigating"})
       # ... more work ...
       await emit_event("tool_end", {"result": result})
   ```

2. **Add progress tracking** to long-running tools

## API Design

### Request Format

```json
{
  "prompt": "What is the weather?",
  "session_id": "session-123",
  "stream": true,
  "callbacks": {
    "on_token": true,
    "on_tool": true,
    "on_error": true
  }
}
```

### Response Format (SSE)

```
event: agent_start
data: {"timestamp": "2025-11-26T10:00:00Z", "session_id": "session-123"}

event: llm_token
data: {"token": "The", "index": 0}

event: llm_token
data: {"token": " weather", "index": 1}

event: tool_start
data: {"tool": "get_weather", "inputs": {"location": "San Francisco"}}

event: tool_end
data: {"tool": "get_weather", "outputs": {"temp": 72, "condition": "sunny"}}

event: llm_token
data: {"token": " is", "index": 2}

event: agent_end
data: {"output": "The weather is sunny, 72°F", "tokens": 150}
```

### WebSocket Alternative

```javascript
// Client-side
const ws = new WebSocket('wss://runtime.bedrock-agentcore.us-west-2.amazonaws.com/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'llm_token':
      appendToken(data.token);
      break;
    case 'tool_start':
      showToolProgress(data.tool);
      break;
    case 'agent_end':
      finalizeResponse(data.output);
      break;
  }
};

ws.send(JSON.stringify({
  prompt: "What is the weather?",
  session_id: "session-123"
}));
```

## Error Handling

### Streaming Error Events

```python
try:
    async for event in graph.astream(input_data, config):
        yield event
except Exception as e:
    yield {
        "type": "error",
        "error": str(e),
        "timestamp": datetime.now().isoformat()
    }
finally:
    yield {"type": "stream_end"}
```

### Reconnection Strategy

```python
class StreamConfig:
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 300.0
    
    async def stream_with_retry(self, input_data):
        for attempt in range(self.max_retries):
            try:
                async for event in graph.astream(input_data):
                    yield event
                break
            except ConnectionError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
```

## Performance Considerations

### Optimization Strategies

1. **Buffering**: Buffer tokens before sending (balance latency vs throughput)
   ```python
   buffer = []
   buffer_size = 5
   
   for token in token_stream:
       buffer.append(token)
       if len(buffer) >= buffer_size:
           yield "".join(buffer)
           buffer.clear()
   ```

2. **Backpressure**: Handle slow clients
   ```python
   async def stream_with_backpressure(queue: asyncio.Queue):
       while True:
           try:
               event = await asyncio.wait_for(queue.get(), timeout=1.0)
               yield event
           except asyncio.TimeoutError:
               continue  # Client is slow, skip
   ```

3. **Connection Limits**: Max concurrent streams per agent

### Benchmarks (Target)

- **Time to First Token**: < 200ms
- **Token Throughput**: > 50 tokens/sec
- **Max Concurrent Streams**: 100+ per instance
- **Memory per Stream**: < 10MB

## Testing Strategy

### Unit Tests

```python
async def test_stream_tokens():
    events = []
    async for event in stream_agent({"prompt": "Hello"}):
        events.append(event)
    
    assert any(e['type'] == 'llm_token' for e in events)
    assert events[-1]['type'] == 'agent_end'
```

### Integration Tests

```python
async def test_tool_streaming():
    """Test tool execution emits progress events."""
    events = [e async for e in stream_agent({
        "prompt": "Browse https://example.com"
    })]
    
    tool_events = [e for e in events if e['type'].startswith('tool_')]
    assert len(tool_events) >= 2  # start and end
```

### Load Tests

```bash
# Simulate 100 concurrent streaming clients
artillery run streaming-load-test.yml
```

## Migration Path

### Backward Compatibility

```python
def invoke_agent(payload: dict):
    """Non-streaming invoke (backward compatible)."""
    if payload.get("stream", False):
        return stream_agent(payload)
    else:
        # Original blocking behavior
        return graph.invoke(input_data, config)
```

### Gradual Rollout

1. **Week 1**: Deploy streaming endpoint alongside existing
2. **Week 2**: Internal testing with callbacks
3. **Week 3**: Beta users opt-in to streaming
4. **Week 4**: Make streaming default with fallback

## File Changes Required

```
bedrock/
├── agent_runtime.py        # Add async stream_handler()
├── callbacks.py            # NEW: Callback handlers
├── streaming_utils.py      # NEW: SSE/WebSocket helpers
└── stream_endpoint.py      # NEW: Streaming API endpoint

tests/
├── test_streaming.py       # NEW: Streaming tests
└── test_callbacks.py       # NEW: Callback tests

STREAMING_RESPONSE_DESIGN.md  # This document
```

## References

- [LangGraph Streaming](https://langchain-ai.github.io/langgraph/how-tos/stream-values/)
- [LangChain Callbacks](https://python.langchain.com/docs/modules/callbacks/)
- [AWS Bedrock Streaming](https://docs.aws.amazon.com/bedrock/latest/userguide/streaming.html)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI Streaming](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

## Implementation Status

### ✅ Phase 1 Complete: Core Streaming Infrastructure

**Files Created:**
- `bedrock/streaming_utils.py` - SSE formatting, event types, and utilities
- `bedrock/callbacks.py` - Callback handlers for streaming events
- `bedrock/agent_runtime.py` - Updated with `stream_agent()` async function
- `bedrock/test_streaming.py` - Comprehensive test suite
- `bedrock/streaming_client_example.py` - Client usage examples

**Features Implemented:**
- ✅ Async streaming with `agent.astream()`
- ✅ Server-Sent Events (SSE) formatting
- ✅ Event types: AGENT_START, AGENT_STEP, AGENT_END, ERROR
- ✅ Backward compatibility (non-streaming still works)
- ✅ Error handling and graceful failures
- ✅ Memory/session continuity in streaming mode
- ✅ Metrics collection during streaming
- ✅ Step-by-step progress updates

**Testing:**
```bash
cd bedrock
python3 test_streaming.py
```

All tests passing:
- ✅ Basic streaming (step-level)
- ✅ Tool execution streaming
- ✅ Error handling
- ✅ Backward compatibility
- ✅ Memory continuity

### 🚧 Phase 2 Pending: Token-Level Streaming

**Status:** Callback integration prepared but requires:
- LLM token streaming support in Bedrock ChatBedrock
- Async callback handler registration in LangChain

**Note:** Current implementation provides step-level streaming which is sufficient for most use cases. Token-level streaming can be enabled by setting `stream_tokens: true` in the payload once LLM supports it.

### 📋 Phase 3: Production Readiness

**Remaining Tasks:**
1. Deploy streaming endpoint to AWS
2. Add streaming to observability dashboard
3. Load testing with concurrent streams
4. Documentation for external clients
5. WebSocket alternative (optional)

## Next Steps

1. ✅ ~~Review and approve this design~~
2. ✅ ~~Create implementation tickets~~
3. ✅ ~~Set up development branch~~
4. ✅ ~~Begin Phase 1 implementation~~
5. 🔄 Deploy and test on AWS Bedrock AgentCore
6. 🔄 Add streaming metrics to observability dashboard
7. 🔄 Client SDK updates for streaming support

