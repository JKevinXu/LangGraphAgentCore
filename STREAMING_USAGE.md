# Streaming Response Usage Guide

Complete guide for using streaming responses with LangGraphAgentCore.

## Quick Start

### Basic Streaming Request

```python
import asyncio
from bedrock.agent_runtime import stream_agent

async def main():
    payload = {
        "prompt": "What is 25 * 4?",
        "session_id": "my-session",
        "stream": True
    }
    
    async for event in stream_agent(payload):
        print(event)

asyncio.run(main())
```

### Non-Streaming (Backward Compatible)

```python
from bedrock.agent_runtime import invoke_agent

payload = {
    "prompt": "What is 25 * 4?",
    "session_id": "my-session"
}

response = invoke_agent(payload)
print(response)
```

## Event Types

### AGENT_START
Emitted when the agent begins processing.

```json
{
  "type": "agent_start",
  "data": {
    "session_id": "my-session",
    "actor_id": "user-123",
    "timestamp": "2025-11-28T10:00:00Z"
  }
}
```

### AGENT_STEP
Emitted for each step in the agent's execution.

```json
{
  "type": "agent_step",
  "data": {
    "step": 2,
    "node": "chatbot",
    "content": "I'll calculate that for you.",
    "type": "ai"
  }
}
```

**Message Types:**
- `human` - User input
- `ai` - Agent response
- `tool` - Tool execution result

### AGENT_END
Emitted when processing completes.

```json
{
  "type": "agent_end",
  "data": {
    "output": "The result of 25 * 4 is 100.",
    "steps": 4,
    "metrics": {
      "tokens": 0,
      "tool_calls": 1,
      "errors": 0
    },
    "timestamp": "2025-11-28T10:00:05Z"
  }
}
```

### ERROR
Emitted when an error occurs.

```json
{
  "type": "error",
  "data": {
    "error": "Tool execution failed",
    "type": "ToolError",
    "timestamp": "2025-11-28T10:00:03Z"
  }
}
```

## Advanced Usage

### Token-Level Streaming

Enable token-by-token streaming (when supported by LLM):

```python
payload = {
    "prompt": "Explain photosynthesis",
    "session_id": "my-session",
    "stream": True,
    "stream_tokens": True  # Enable token streaming
}

async for event in stream_agent(payload):
    # Handle LLM_TOKEN events
    if "llm_token" in event:
        token_data = parse_sse_event(event)
        print(token_data['token'], end='', flush=True)
```

### Memory Continuity

Streaming preserves session memory:

```python
# First message
payload1 = {
    "prompt": "My name is Alice",
    "session_id": "alice-session",
    "stream": True
}

async for event in stream_agent(payload1):
    pass  # Process events

# Second message - agent remembers
payload2 = {
    "prompt": "What's my name?",
    "session_id": "alice-session",  # Same session
    "stream": True
}

async for event in stream_agent(payload2):
    pass  # Agent will respond with "Alice"
```

### Custom Data

Include custom data in streaming requests:

```python
payload = {
    "prompt": "Recommend a movie",
    "session_id": "my-session",
    "stream": True,
    "preferences": {
        "genre": "sci-fi",
        "rating": "PG-13"
    },
    "custom_data": {
        "user_id": "123",
        "timestamp": "2025-11-28T10:00:00Z"
    }
}
```

## Client Examples

### Python with httpx

```python
import httpx
import json

async def stream_request():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'POST',
            'https://your-agent.amazonaws.com/stream',
            json={
                "prompt": "What is 2+2?",
                "session_id": "web-session",
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
```

### JavaScript (Browser)

```javascript
const payload = {
  prompt: "Calculate 15 * 8",
  session_id: "web-session",
  stream: true
};

const response = await fetch('/invoke', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('event:')) {
      const eventType = line.replace('event: ', '');
    } else if (line.startsWith('data:')) {
      const data = JSON.parse(line.replace('data: ', ''));
      console.log(eventType, data);
    }
  }
}
```

### React Component

```javascript
import { useState, useEffect } from 'react';

function StreamingChat() {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  
  const sendMessage = async (prompt) => {
    const response = await fetch('/invoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        session_id: 'react-session',
        stream: true
      })
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop(); // Keep incomplete line in buffer
      
      for (const line of lines) {
        if (line.startsWith('event:')) {
          const [eventLine, dataLine] = line.split('\n');
          const eventType = eventLine.replace('event: ', '');
          const data = JSON.parse(dataLine.replace('data: ', ''));
          
          if (eventType === 'agent_step' && data.type === 'ai') {
            setCurrentMessage(data.content);
          } else if (eventType === 'agent_end') {
            setMessages(prev => [...prev, data.output]);
            setCurrentMessage('');
          }
        }
      }
    }
  };
  
  return (
    <div>
      {messages.map((msg, i) => <div key={i}>{msg}</div>)}
      {currentMessage && <div className="streaming">{currentMessage}</div>}
    </div>
  );
}
```

## Testing

### Run Local Tests

```bash
cd bedrock
python3 test_streaming.py
```

### Test Individual Features

```python
# Test basic streaming
python3 -c "
import asyncio
from agent_runtime import stream_agent

async def test():
    payload = {'prompt': 'What is 5+5?', 'stream': True}
    async for event in stream_agent(payload):
        print(event)

asyncio.run(test())
"
```

### Test in Production

```bash
# Deploy
agentcore launch

# Test non-streaming (backward compatible)
agentcore invoke '{"prompt": "Hello"}'

# For streaming, use custom client or SDK
```

## Error Handling

### Handle Connection Errors

```python
async def stream_with_retry(payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            async for event in stream_agent(payload):
                yield event
            break  # Success
        except ConnectionError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

### Handle Timeout

```python
import asyncio

async def stream_with_timeout(payload, timeout=60):
    try:
        async with asyncio.timeout(timeout):
            async for event in stream_agent(payload):
                yield event
    except asyncio.TimeoutError:
        yield format_sse_event('error', {
            'error': 'Request timeout',
            'timeout': timeout
        })
```

### Parse SSE Events Safely

```python
def parse_sse_event(event_str):
    """Safely parse SSE event."""
    try:
        lines = event_str.strip().split('\n')
        event_type = lines[0].replace('event: ', '')
        data = json.loads(lines[1].replace('data: ', ''))
        return {'type': event_type, 'data': data}
    except (IndexError, json.JSONDecodeError) as e:
        return {'type': 'error', 'data': {'error': f'Parse error: {e}'}}
```

## Performance Tips

### Buffer Tokens

For token-level streaming, buffer tokens to reduce network overhead:

```python
from streaming_utils import TokenBuffer

buffer = TokenBuffer(buffer_size=10)

async for event in stream_agent(payload):
    if event.type == 'llm_token':
        buffered = buffer.add(event.data['token'])
        if buffered:
            # Send buffered tokens
            yield buffered

# Don't forget to flush
final = buffer.flush()
if final:
    yield final
```

### Connection Pooling

Reuse HTTP connections for multiple streaming requests:

```python
import httpx

async with httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=10)
) as client:
    # Multiple streaming requests reuse connection
    for prompt in prompts:
        async with client.stream(...) as response:
            # Process stream
            pass
```

### Handle Backpressure

For slow clients, implement backpressure:

```python
import asyncio

async def stream_with_backpressure(payload, max_queue_size=100):
    queue = asyncio.Queue(maxsize=max_queue_size)
    
    async def producer():
        async for event in stream_agent(payload):
            await queue.put(event)
        await queue.put(None)  # Sentinel
    
    async def consumer():
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
    
    producer_task = asyncio.create_task(producer())
    async for event in consumer():
        yield event
    await producer_task
```

## Monitoring

### Collect Metrics

```python
from callbacks import MetricsCallback

# Metrics are automatically collected
async for event in stream_agent(payload):
    if event.type == 'agent_end':
        metrics = event.data['metrics']
        print(f"Tokens: {metrics['tokens']}")
        print(f"Tool calls: {metrics['tool_calls']}")
        print(f"Errors: {metrics['errors']}")
```

### CloudWatch Logs

```bash
# Tail streaming logs
aws logs tail /aws/bedrock-agentcore/runtimes/langgraph_agent-1NyH76Cfc7-DEFAULT \
  --log-stream-name-prefix "2025/11/28/[runtime-logs]" \
  --follow | grep -i "stream"
```

### Custom Callbacks

```python
from callbacks import BaseStreamCallback

class CustomCallback(BaseStreamCallback):
    async def on_llm_start(self, serialized, prompts, **kwargs):
        # Log to your monitoring service
        logger.info("LLM started", extra={"prompts": prompts})
    
    async def on_tool_start(self, serialized, input_str, **kwargs):
        # Track tool usage
        metrics.increment("tool.invoked", tags=["tool:" + serialized["name"]])
```

## Troubleshooting

### Streaming Not Working

1. Check if `stream: true` is in payload
2. Verify async context (must use `asyncio.run()`)
3. Check network connectivity
4. Review CloudWatch logs for errors

### Events Not Parsing

1. Verify SSE format (event: TYPE\ndata: JSON\n\n)
2. Check JSON structure in data field
3. Handle incomplete events in buffer

### Memory Not Persisting

1. Ensure same `session_id` across requests
2. Verify `AGENTCORE_MEMORY_ID` is set
3. Check IAM permissions for memory access

### Performance Issues

1. Enable token buffering for token streaming
2. Use connection pooling for multiple requests
3. Implement backpressure for slow clients
4. Consider increasing timeout values

## Best Practices

1. **Always Handle Errors**: Wrap streaming in try-catch
2. **Set Timeouts**: Prevent hanging connections
3. **Buffer Wisely**: Balance latency vs throughput
4. **Close Connections**: Clean up resources properly
5. **Monitor Metrics**: Track performance and errors
6. **Test Locally First**: Use `test_streaming.py`
7. **Session Management**: Use meaningful session IDs
8. **Backward Compatibility**: Support non-streaming fallback

## References

- [LangGraph Streaming](https://langchain-ai.github.io/langgraph/how-tos/stream-values/)
- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [STREAMING_RESPONSE_DESIGN.md](STREAMING_RESPONSE_DESIGN.md) - Design document
- [bedrock/streaming_client_example.py](bedrock/streaming_client_example.py) - More examples

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review test cases in `test_streaming.py`
3. See examples in `streaming_client_example.py`
4. Open GitHub issue with logs and reproduction steps

