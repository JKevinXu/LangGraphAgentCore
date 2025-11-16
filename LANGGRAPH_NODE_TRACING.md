# LangGraph Node-Level Tracing

## Overview

LangGraph node-level tracing has been enabled using **LangSmith's OpenTelemetry integration**. This provides detailed visibility into your graph execution.

## What Node-Level Tracing Captures

### Before (Basic Tracing):
- ✅ Bedrock model invocations
- ✅ Tool executions
- ✅ AgentCore runtime spans
- ❌ **No visibility into LangGraph internals**

### After (Node-Level Tracing):
- ✅ **Individual node executions** (`chatbot`, `tools`)
- ✅ **State transitions** between nodes
- ✅ **Conditional edge decisions** (tools_condition)
- ✅ **Graph execution flow**
- ✅ **Node timing and latency**
- ✅ **State snapshots** at each node

## Configuration

### 1. Dependencies Added
```python
# requirements.txt
langsmith[otel]>=0.4.0
opentelemetry-instrumentation-langchain>=0.45.0
```

### 2. Runtime Configuration
```python
# agent_runtime.py
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
```

## What You'll See in Traces

### Span Hierarchy:
```
📦 AgentCore Runtime Invocation
  └─ 🔵 LangGraph Execution
      ├─ 🟢 Node: chatbot (start)
      │   └─ 🔷 Bedrock: InvokeModel
      │       └─ 🟡 Tool Decision: tools_condition
      ├─ 🟢 Node: tools
      │   └─ 🔧 Tool: calculator
      └─ 🟢 Node: chatbot (final)
          └─ 🔷 Bedrock: InvokeModel
              └─ 📤 Response
```

### Trace Attributes:
- **Node name**: Which LangGraph node is executing
- **Node type**: chatbot, tools, etc.
- **Node duration**: Time spent in each node
- **State data**: Messages, tool results
- **Edge conditions**: Which path was taken

## How to Deploy

Redeploy your agent to apply the changes:

```bash
cd /Users/kevinxu/ws9/LangGraphAgentCore/bedrock
agentcore launch
```

Wait for deployment to complete, then invoke the agent. Node-level spans will appear in:
- **CloudWatch Logs**: `/aws/bedrock-agentcore/runtimes/agent_runtime-1qAGZg6YWk-DEFAULT/otel-rt-logs`
- **GenAI Observability Dashboard**: Traces tab will show expanded spans
- **X-Ray**: Detailed service map with LangGraph nodes

## Example Trace

When you ask "What is 100 + 50?", you'll see:

1. **Span**: `graph.invoke` (LangGraph execution start)
2. **Span**: `node.chatbot` (LLM decides to use calculator)
   - Duration: ~1.5s
   - Attributes: `node.name=chatbot`, `state.messages.count=2`
3. **Span**: `bedrock.invoke_model` (Claude 3.7 Sonnet call)
   - Model: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
   - Tokens: input=150, output=45
4. **Span**: `node.tools` (Tool execution)
   - Duration: ~0.05s
   - Tool: `calculator`
5. **Span**: `tool.calculator` (Actual calculation)
   - Input: `100 + 50`
   - Output: `150`
6. **Span**: `node.chatbot` (Final response generation)
   - Duration: ~0.8s
   - Result: "The result is 150"

## Benefits

### Debugging:
- **Identify slow nodes**: See which node takes longest
- **Track state evolution**: Monitor how state changes across nodes
- **Catch edge errors**: See which conditional paths are taken

### Optimization:
- **Node performance**: Optimize slow nodes
- **Unnecessary loops**: Detect inefficient graph traversals
- **Token usage**: Track LLM calls per node

### Monitoring:
- **Production insights**: Understand real user flows
- **Error tracking**: Pinpoint exact node where failures occur
- **Cost attribution**: See which nodes consume most resources

## Viewing Traces

### CloudWatch GenAI Observability:
```
https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#genai-observability:
```

Navigate to:
1. **Your agent**: `agent_runtime-1qAGZg6YWk`
2. **Traces tab**: Expand any trace
3. **Node spans**: Click on individual LangGraph nodes

### OTEL Logs:
```bash
aws logs filter-log-events \
  --log-group-name "/aws/bedrock-agentcore/runtimes/agent_runtime-1qAGZg6YWk-DEFAULT" \
  --log-stream-names "otel-rt-logs" \
  --region us-west-2 \
  --filter-pattern "node"
```

## References

- [LangSmith OpenTelemetry Documentation](https://docs.smith.langchain.com/observability/opentelemetry)
- [AgentCore Observability Samples](../amazon-bedrock-agentcore-samples/01-tutorials/06-AgentCore-observability/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

