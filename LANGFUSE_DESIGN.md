# Langfuse Integration Design

## Overview

[Langfuse](https://langfuse.com) is an open-source observability platform for LLM applications. This design outlines how to integrate Langfuse into LangGraphAgentCore for tracing, monitoring, and debugging.

## Why Langfuse?

- **Trace Visualization**: See the full execution flow of agent conversations
- **Cost Tracking**: Monitor token usage and API costs per session/user
- **Latency Analysis**: Identify slow tools or LLM calls
- **Debugging**: Replay and inspect failed conversations
- **Evaluation**: Score and compare agent responses over time

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Bedrock AgentCore Runtime                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  LangGraph Agent                                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │  CallbackHandler (langfuse)                              │  │ │
│  │  │  - on_llm_start/end → Langfuse Generation                │  │ │
│  │  │  - on_tool_start/end → Langfuse Span                     │  │ │
│  │  │  - on_chain_start/end → Langfuse Trace                   │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Async HTTP (batched)
                    ┌─────────────────────┐
                    │  Langfuse Cloud     │
                    │  or Self-Hosted     │
                    └─────────────────────┘
```

## Implementation Plan

### Phase 1: Basic Integration

#### 1.1 Add Dependencies

```txt
# bedrock/requirements.txt
langfuse>=2.0.0
```

#### 1.2 Configure Langfuse Client

```python
# bedrock/langfuse_config.py
import os
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

def get_langfuse_handler(session_id: str, user_id: str = None) -> CallbackHandler:
    """Create Langfuse callback handler for tracing."""
    return CallbackHandler(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        session_id=session_id,
        user_id=user_id,
        release=os.environ.get("AGENT_VERSION", "1.0.0"),
        trace_name="langgraph-agent",
    )
```

#### 1.3 Integrate with Agent Runtime

```python
# bedrock/agent_runtime.py
from langfuse_config import get_langfuse_handler

@app.entrypoint
async def invoke_agent(payload, context=None):
    session_id = data.get("session_id", "unknown")
    user_id = data.get("user_id")  # Optional
    
    # Create Langfuse handler
    langfuse_handler = get_langfuse_handler(
        session_id=session_id,
        user_id=user_id
    )
    
    config = {
        "configurable": {"thread_id": session_id},
        "callbacks": [langfuse_handler],  # Add to callbacks
    }
    
    if use_streaming:
        async for event in stream_agent_async(agent, input_data, config, session_id):
            yield event
    else:
        result = agent.invoke(input_data, config=config)
        yield result["messages"][-1].content
    
    # Flush traces before response completes
    langfuse_handler.flush()
```

### Phase 2: Enhanced Tracing

#### 2.1 Custom Spans for Tools

```python
# bedrock/agent_runtime.py
from langfuse.decorators import observe

@observe(name="code_interpreter")
def execute_code(code: str) -> str:
    """Execute Python code with Langfuse tracing."""
    # Tool implementation
    pass
```

#### 2.2 Add Metadata to Traces

```python
langfuse_handler = CallbackHandler(
    # ... base config ...
    metadata={
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "agent_version": os.environ.get("AGENT_VERSION"),
        "model": "anthropic.claude-sonnet-4-20250514",
    },
    tags=["langgraph", "bedrock-agentcore"],
)
```

#### 2.3 Score Conversations

```python
# After agent response, add scoring
langfuse = Langfuse()
langfuse.score(
    trace_id=langfuse_handler.get_trace_id(),
    name="user_feedback",
    value=1,  # 1 = positive, 0 = negative
    comment="User marked as helpful"
)
```

### Phase 3: BFF Integration (Optional)

Add request-level tracing in BFF for end-to-end visibility:

```python
# bff/app/middleware/langfuse_middleware.py
from langfuse import Langfuse
from fastapi import Request

langfuse = Langfuse()

async def trace_request(request: Request, call_next):
    trace = langfuse.trace(
        name="bff-request",
        metadata={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    response = await call_next(request)
    
    trace.update(
        output={"status_code": response.status_code}
    )
    
    return response
```

## Environment Variables

```bash
# Required
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Optional
LANGFUSE_HOST=https://cloud.langfuse.com  # Or self-hosted URL
LANGFUSE_RELEASE=1.0.0
LANGFUSE_DEBUG=false
```

## Data Flow

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ Trace: langgraph-agent                              │
│ session_id: abc123                                  │
│ user_id: user_456                                   │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ Generation: claude-sonnet                      │  │
│  │ prompt: "What is 5+5?"                        │  │
│  │ completion: "I'll calculate that..."          │  │
│  │ tokens: {input: 12, output: 45}              │  │
│  │ latency: 1.2s                                 │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ Span: tool_call (calculator)                  │  │
│  │ input: {"expression": "5+5"}                  │  │
│  │ output: "10"                                  │  │
│  │ latency: 0.05s                                │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ Generation: claude-sonnet                      │  │
│  │ prompt: "Tool result: 10"                     │  │
│  │ completion: "The result is 10."               │  │
│  │ tokens: {input: 8, output: 12}               │  │
│  │ latency: 0.8s                                 │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│ Total: 2.05s, 77 tokens, $0.0023                   │
└─────────────────────────────────────────────────────┘
```

## Deployment Options

### Option A: Langfuse Cloud (Recommended for Start)

- No infrastructure to manage
- Free tier: 50k observations/month
- Pro: $59/month for 1M observations

### Option B: Self-Hosted

```yaml
# docker-compose.yml
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://...
      NEXTAUTH_SECRET: ...
```

## Security Considerations

1. **Secrets Management**: Store Langfuse keys in AWS Secrets Manager
2. **Data Privacy**: Consider what data is sent to Langfuse (PII filtering)
3. **Network**: Ensure AgentCore can reach Langfuse endpoint

```python
# Example: PII filtering
from langfuse.callback import CallbackHandler

class FilteredCallbackHandler(CallbackHandler):
    def _filter_pii(self, text: str) -> str:
        # Remove emails, phone numbers, etc.
        import re
        text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', text)
        return text
    
    def on_llm_end(self, response, **kwargs):
        # Filter before sending to Langfuse
        response.generations[0].text = self._filter_pii(response.generations[0].text)
        super().on_llm_end(response, **kwargs)
```

## Implementation Steps

1. [ ] Sign up for Langfuse Cloud or deploy self-hosted
2. [ ] Add `langfuse` to `bedrock/requirements.txt`
3. [ ] Create `bedrock/langfuse_config.py`
4. [ ] Update `bedrock/agent_runtime.py` with callback handler
5. [ ] Add environment variables to AgentCore deployment
6. [ ] Deploy and verify traces appear in Langfuse dashboard
7. [ ] (Optional) Add BFF-level tracing
8. [ ] (Optional) Set up dashboards and alerts

## Expected Langfuse Dashboard

After integration, you'll see:
- **Traces**: Full conversation flows with timing
- **Generations**: Each LLM call with prompts/completions
- **Sessions**: Grouped by session_id for multi-turn conversations
- **Users**: Usage patterns per user (if user_id provided)
- **Costs**: Token usage and estimated costs
- **Latency**: P50/P95/P99 latency metrics

## References

- [Langfuse Docs](https://langfuse.com/docs)
- [LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)
- [LangGraph + Langfuse](https://langfuse.com/docs/integrations/langchain/example-python-langgraph)

