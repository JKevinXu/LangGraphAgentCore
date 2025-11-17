# Short-Term Memory Support

LangGraphAgentCore now includes **short-term memory persistence** using AWS Bedrock AgentCore Memory. This enables your agents to maintain conversation context across multiple interactions within the same session.

## Overview

Short-term memory in LangGraph is handled through **checkpointing**, which saves:
- User and AI messages
- Graph execution state
- Tool invocations
- Additional metadata

Using the `AgentCoreMemorySaver` checkpointer, all conversation state is persisted to AWS Bedrock AgentCore Memory, ensuring continuity even through container restarts or application crashes.

## Features

- ✅ **Conversation Continuity** - Agents remember previous messages within a session
- ✅ **State Persistence** - Graph execution state preserved across invocations
- ✅ **Session Isolation** - Different sessions maintain separate conversation histories
- ✅ **Actor Support** - Multiple actors can have independent conversation threads
- ✅ **Automatic Checkpointing** - State saved automatically after each interaction
- ✅ **No Manual Management** - Fully managed by AWS infrastructure

## Prerequisites

Before enabling memory support, ensure you have:

1. **AWS Account** with Bedrock AgentCore access
2. **Configured AWS credentials** (boto3)
3. **An AgentCore Memory** resource created
4. **Required IAM permissions**:
   - `bedrock-agentcore:CreateEvent`
   - `bedrock-agentcore:ListEvents`
   - `bedrock-agentcore:RetrieveMemories`

## Configuration

### Step 1: Create an AgentCore Memory

First, create an AgentCore Memory resource in AWS:

```bash
aws bedrock-agentcore create-memory \
  --region us-west-2 \
  --memory-name "langgraph-agent-memory"
```

Note the `memory-id` from the response.

### Step 2: Set Environment Variable

Configure the Memory ID as an environment variable:

```bash
export AGENTCORE_MEMORY_ID="your-memory-id-here"
export AWS_REGION="us-west-2"
```

For Docker deployments, add to your `Dockerfile` or docker-compose:

```dockerfile
ENV AGENTCORE_MEMORY_ID=your-memory-id-here
ENV AWS_REGION=us-west-2
```

### Step 3: Deploy

The memory support is automatically enabled when `AGENTCORE_MEMORY_ID` is set. Deploy your agent as usual:

```bash
cd bedrock
./deploy.sh
```

## Usage

### Basic Usage with Memory

When invoking the agent, include `session_id` and `actor_id` in the payload:

```python
import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# First message in a conversation
payload = json.dumps({
    "prompt": "My name is Alice and I love pizza.",
    "session_id": "session-123",
    "actor_id": "user-alice"
})

response = client.invoke_agent_runtime(
    agentRuntimeArn='your-runtime-arn',
    runtimeSessionId='session-123',
    payload=payload,
    qualifier='DEFAULT'
)

# Second message - agent remembers previous context
payload = json.dumps({
    "prompt": "What is my name?",
    "session_id": "session-123",  # Same session ID
    "actor_id": "user-alice"
})

response = client.invoke_agent_runtime(
    agentRuntimeArn='your-runtime-arn',
    runtimeSessionId='session-123',
    payload=payload,
    qualifier='DEFAULT'
)
# Agent will respond: "Your name is Alice"
```

### Session Management

#### Same Session = Shared Memory

Messages with the same `session_id` share conversation history:

```python
# Message 1
{"prompt": "I like sushi", "session_id": "session-1", "actor_id": "alice"}

# Message 2 (remembers previous message)
{"prompt": "What do I like?", "session_id": "session-1", "actor_id": "alice"}
# Response: "You like sushi"
```

#### Different Session = Fresh Start

Messages with different `session_id` values start fresh:

```python
# Message 1 in session-1
{"prompt": "I like sushi", "session_id": "session-1", "actor_id": "alice"}

# Message 2 in session-2 (new conversation)
{"prompt": "What do I like?", "session_id": "session-2", "actor_id": "alice"}
# Response: "I don't have information about your preferences yet"
```

### Actor Management

The `actor_id` identifies who is interacting with the agent:

```python
# User Alice
{"prompt": "I like pizza", "session_id": "session-1", "actor_id": "alice"}

# User Bob (different actor, same session)
{"prompt": "What do I like?", "session_id": "session-1", "actor_id": "bob"}
# Response: "I don't have information about your preferences yet"
```

## Testing Memory Support

### Test Memory Continuity

Use the built-in memory test suite:

```bash
python test_runtime.py <runtime-arn> --test-memory
```

This will:
1. Send a message with user information
2. Ask the agent to recall that information
3. Verify memory persistence across multiple interactions

### Test with Custom Session

```bash
python test_runtime.py <runtime-arn> \
  --prompt "My name is Alice" \
  --session-id "test-session-1" \
  --actor-id "test-user"

# Follow-up in same session
python test_runtime.py <runtime-arn> \
  --prompt "What is my name?" \
  --session-id "test-session-1" \
  --actor-id "test-user"
```

## Running Without Memory

If you don't need memory support, simply don't set the `AGENTCORE_MEMORY_ID` environment variable. The agent will run normally without persistence:

```bash
# Memory disabled - agent runs stateless
unset AGENTCORE_MEMORY_ID
python bedrock/agent_runtime.py
```

You'll see this message on startup:
```
ℹ️  Memory ID not configured. Agent will run without memory persistence.
   Set AGENTCORE_MEMORY_ID environment variable to enable memory.
```

## Architecture

```
User Request
    ↓
AWS Bedrock Agent Core Runtime
    ↓
LangGraph Agent (with checkpointer)
    ↓
AgentCoreMemorySaver
    ↓
AWS Bedrock AgentCore Memory
    ├─→ Session State Storage
    ├─→ Message History
    └─→ Graph Execution State
```

## How It Works

1. **Checkpointing**: After each agent invocation, LangGraph creates a checkpoint containing:
   - All messages in the conversation
   - Current graph state
   - Tool invocation results
   - Metadata

2. **Storage**: The `AgentCoreMemorySaver` saves this checkpoint to AgentCore Memory using:
   - `thread_id` (session_id) - Identifies the conversation thread
   - `actor_id` - Identifies the participant

3. **Retrieval**: On subsequent invocations with the same `thread_id`, the checkpointer:
   - Loads the previous checkpoint
   - Restores conversation history
   - Continues from the last state

## Payload Format

### Required Fields
```json
{
  "prompt": "Your message here"
}
```

### Optional Fields (for memory)
```json
{
  "prompt": "Your message here",
  "session_id": "unique-session-identifier",
  "actor_id": "user-or-agent-identifier"
}
```

### Default Values
- `session_id`: defaults to `"default-session"`
- `actor_id`: defaults to `"default-actor"`

## IAM Permissions

Your agent runtime role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateEvent",
        "bedrock-agentcore:ListEvents",
        "bedrock-agentcore:RetrieveMemories"
      ],
      "Resource": "arn:aws:bedrock-agentcore:*:*:memory/your-memory-id"
    }
  ]
}
```

## Troubleshooting

### Memory Not Persisting

**Problem**: Agent doesn't remember previous messages

**Solutions**:
1. Verify `AGENTCORE_MEMORY_ID` is set correctly
2. Ensure you're using the same `session_id` across invocations
3. Check IAM permissions for the runtime role
4. Verify the Memory resource exists in your AWS account

### Memory ID Not Found

**Problem**: Error initializing AgentCoreMemorySaver

**Solutions**:
1. Verify the Memory ID is correct
2. Ensure the Memory exists in the specified region
3. Check that the runtime has access to the Memory resource

### Different Sessions Not Isolated

**Problem**: Different sessions seeing each other's history

**Solutions**:
1. Verify you're using different `session_id` values
2. Check that session IDs are being passed correctly in the payload
3. Ensure the agent is properly compiled with the checkpointer

## Best Practices

1. **Session ID Management**
   - Use meaningful session IDs (e.g., user-123-chat-456)
   - Maintain session IDs on the client side
   - Don't reuse session IDs across different conversations

2. **Actor ID Management**
   - Use consistent actor IDs for the same user/entity
   - Include user identifiers in actor IDs
   - Consider using format: `user-{user_id}` or `agent-{agent_name}`

3. **Memory Cleanup**
   - Implement session expiry on the client side
   - Use new session IDs for new conversations
   - Consider periodic cleanup of old sessions in AgentCore Memory

4. **Error Handling**
   - Always provide fallback behavior if memory fails to load
   - Log memory-related errors for debugging
   - Gracefully handle cases where memory is not configured

## Examples

### Multi-Turn Conversation

```python
session = "booking-123"
actor = "customer-456"

# Turn 1
invoke_agent({"prompt": "I want to book a flight to Tokyo", "session_id": session, "actor_id": actor})
# Response: "I can help with that! When would you like to travel?"

# Turn 2
invoke_agent({"prompt": "Next month on the 15th", "session_id": session, "actor_id": actor})
# Response: "Got it, you want to fly to Tokyo on the 15th of next month..."

# Turn 3
invoke_agent({"prompt": "What was my destination again?", "session_id": session, "actor_id": actor})
# Response: "Your destination is Tokyo"
```

### Multiple Concurrent Sessions

```python
# User Alice - Session 1
invoke_agent({"prompt": "I like coffee", "session_id": "alice-1", "actor_id": "alice"})

# User Bob - Session 2
invoke_agent({"prompt": "I like tea", "session_id": "bob-1", "actor_id": "bob"})

# Back to Alice
invoke_agent({"prompt": "What do I like?", "session_id": "alice-1", "actor_id": "alice"})
# Response: "You like coffee"

# Back to Bob
invoke_agent({"prompt": "What do I like?", "session_id": "bob-1", "actor_id": "bob"})
# Response: "You like tea"
```

## References

- [AWS Bedrock AgentCore Memory Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangChain x AWS GitHub Repo](https://github.com/langchain-ai/langchain-aws)

## Related Documentation

- [LANGGRAPH_NODE_TRACING.md](LANGGRAPH_NODE_TRACING.md) - Node-level observability
- [README.md](README.md) - Main project documentation
- [bedrock/README.md](bedrock/README.md) - Deployment guide

