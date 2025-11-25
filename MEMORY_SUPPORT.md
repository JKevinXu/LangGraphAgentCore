# Memory Support with Browser Tool Integration

LangGraphAgentCore includes **comprehensive memory persistence** using AWS Bedrock AgentCore Memory. This enables your agents to maintain conversation context, user preferences, and browsing history across multiple interactions.

## Overview

Short-term memory in LangGraph is handled through **checkpointing**, which saves:
- User and AI messages
- Graph execution state
- Tool invocations
- Additional metadata

Using the `AgentCoreMemorySaver` checkpointer, all conversation state is persisted to AWS Bedrock AgentCore Memory, ensuring continuity even through container restarts or application crashes.

## Features

### Short-Term Memory (Conversation Context)
- ✅ **Conversation Continuity** - Agents remember previous messages within a session
- ✅ **State Persistence** - Graph execution state preserved across invocations
- ✅ **Session Isolation** - Different sessions maintain separate conversation histories
- ✅ **Actor Support** - Multiple actors can have independent conversation threads
- ✅ **Automatic Checkpointing** - State saved automatically after each interaction
- ✅ **No Manual Management** - Fully managed by AWS infrastructure

### Long-Term Memory (Custom State Data)
- ✅ **User Preferences** - Store and recall user settings across sessions
- ✅ **Browsing History** - Remember websites visited and information found
- ✅ **Custom Data Storage** - Persist any application-specific data
- ✅ **Context Enrichment** - Use historical data to enhance responses
- ✅ **Cross-Session Memory** - Data persists across different conversation sessions

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

## Browser Tool Memory Integration

### Overview

The browser tool is fully integrated with the agent's memory system, automatically storing browsing history and results for future reference. This enables the agent to:
- Remember previously visited websites
- Recall information found during browsing sessions
- Build knowledge across multiple web searches
- Reference past browsing results in current conversations

### How It Works

When the agent uses the `browse_web` tool, the browsing session details are stored in the conversation context:

```python
# Browsing result structure stored in memory
{
    "timestamp": "2025-11-24T14:30:00Z",
    "url": "https://example.com",
    "session_id": "01KAV46NDYCGRJ03TK3ZD0ZD6R",
    "task": "Navigate to example.com and find pricing",
    "status": "success"
}
```

### Memory Storage

Browsing history is maintained in two ways:

1. **Message History** (Short-term): Tool invocations and results are stored in the conversation messages
2. **Custom State** (Long-term): Browsing metadata is stored in the `browsing_history` field of the agent state

### Example: Using Browser Memory

```python
session = "research-session-1"
actor = "researcher-123"

# First browsing session
invoke_agent({
    "prompt": "Use the browse_web tool to search AWS documentation for AgentCore Browser features",
    "session_id": session,
    "actor_id": actor
})
# Agent browses and stores the results

# Later in the same session
invoke_agent({
    "prompt": "What did we learn about AgentCore Browser earlier?",
    "session_id": session,
    "actor_id": actor
})
# Agent recalls: "Earlier, we browsed the AWS documentation at https://docs.aws.amazon.com/..."
```

### Cross-Session Memory

Browsing history persists across different sessions when using the same thread_id:

```python
# Session 1: Initial research
invoke_agent({
    "prompt": "Browse https://aws.amazon.com/bedrock/ and summarize key features",
    "session_id": "research-2024-01",
    "actor_id": "team-a"
})

# Session 2: Follow-up (different day)
invoke_agent({
    "prompt": "What websites did we visit about Bedrock?",
    "session_id": "research-2024-01",  # Same session ID
    "actor_id": "team-a"
})
# Agent remembers the previous browsing session
```

### Custom State Fields

The agent state includes these custom fields that persist across invocations:

```python
class CustomAgentState:
    messages: list              # Standard conversation messages
    user_preferences: dict      # User settings and preferences
    custom_data: dict          # Application-specific data
    browsing_history: list     # Browser tool usage history
```

### Accessing Browsing History

The agent automatically includes recent browsing history in its context:

```python
# The system message is enhanced with browsing history:
"""
You're a helpful assistant with the following capabilities:
- Perform mathematical calculations
- Check weather information
- Browse websites and extract information (when available)

Recent browsing history:
- 2025-11-24T14:30:00Z: Browsed https://aws.amazon.com - AWS cloud services overview
- 2025-11-24T14:32:15Z: Browsed https://docs.aws.amazon.com - AgentCore documentation
"""
```

### Best Practices for Browser Memory

1. **Consistent Session IDs**: Use the same session ID for related browsing tasks
   ```python
   # Good: Related browsing tasks in one session
   session = "product-research-nov-2024"
   invoke_agent({"prompt": "Browse competitor A website", "session_id": session})
   invoke_agent({"prompt": "Browse competitor B website", "session_id": session})
   invoke_agent({"prompt": "Compare what we learned", "session_id": session})
   ```

2. **Descriptive Tasks**: Provide clear browsing instructions
   ```python
   # Good: Specific task
   "Navigate to https://aws.amazon.com/pricing/ and find the cost for Lambda functions"
   
   # Better: Task with context
   "Browse AWS Lambda pricing page and extract pricing tiers for our cost analysis"
   ```

3. **Memory Cleanup**: Start new sessions for unrelated browsing
   ```python
   # New project = new session
   invoke_agent({
       "prompt": "Browse React documentation",
       "session_id": "frontend-project-dec-2024",  # Different session
       "actor_id": "developer"
   })
   ```

4. **Leverage History**: Reference past browsing in follow-up questions
   ```python
   invoke_agent({
       "prompt": "Based on the websites we visited earlier, which service is most cost-effective?",
       "session_id": session
   })
   ```

### IAM Permissions for Browser Tool

Ensure your agent runtime role has browser-related permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AgentCoreBrowserAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:StartBrowserSession",
        "bedrock-agentcore:StopBrowserSession",
        "bedrock-agentcore:GetBrowserSession",
        "bedrock-agentcore:SendBrowserAction"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:*:aws:browser/*",
        "arn:aws:bedrock-agentcore:*:ACCOUNT_ID:browser/*"
      ]
    }
  ]
}
```

### Advanced: Custom State Management

You can extend the browsing history with custom metadata:

```python
# Include custom browsing data in payload
payload = {
    "prompt": "Browse the website",
    "session_id": "research-1",
    "browsing_history": [
        {
            "timestamp": "2025-11-24T10:00:00Z",
            "url": "https://example.com",
            "summary": "Found pricing: $99/month",
            "tags": ["pricing", "competitor-analysis"],
            "importance": "high"
        }
    ]
}
```

### Monitoring Browsing Memory

Check memory persistence through CloudWatch logs:

```bash
# View browsing-related logs
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR-RUNTIME-DEFAULT \
  --since 1h --follow | grep -i "browse\|browser"
```

### Limitations

1. **Memory Capacity**: AgentCore Memory has storage limits per session
2. **History Retention**: Old browsing history may be truncated to stay within limits
3. **Automation Pending**: Full Playwright web automation is under development
4. **Session Isolation**: Different sessions don't share browsing history

### Future Enhancements

Planned improvements for browser tool memory:

- ✨ Full Playwright automation for actual web scraping
- ✨ Screenshot capture and storage
- ✨ Structured data extraction
- ✨ Automatic summarization of browsed content
- ✨ Smart memory compression for long browsing histories
- ✨ Cross-reference detection between related browsing sessions

## Code Interpreter Memory Integration

### Overview

The Code Interpreter tool integrates seamlessly with the agent's memory system, automatically storing code execution history for future reference. This enables the agent to:
- Remember previously executed code snippets
- Recall computation results across sessions
- Build on previous analyses and calculations
- Reference past code executions in current conversations

### How It Works

When the agent uses the `execute_code` tool, the execution details are stored in the conversation context:

```python
# Code execution result structure stored in memory
{
    "timestamp": "2025-11-25T14:31:16Z",
    "code": "print('Hello World')",
    "output": "Hello World",
    "status": "success",
    "summary": "Executed Python code successfully"
}
```

### Memory Storage

Code execution history is maintained in two ways:

1. **Message History** (Short-term): Tool invocations and results are stored in the conversation messages
2. **Custom State** (Long-term): Code execution metadata is stored in the `code_execution_history` field of the agent state

### Example: Using Code Interpreter Memory

```python
session = "data-analysis-1"
actor = "analyst-456"

# First code execution
invoke_agent({
    "prompt": "Use execute_code to calculate the fibonacci sequence up to 10 terms",
    "session_id": session,
    "actor_id": actor
})
# Agent executes code and stores the results

# Later in the same session
invoke_agent({
    "prompt": "What was the last calculation we performed?",
    "session_id": session,
    "actor_id": actor
})
# Agent recalls: "Earlier, we calculated the fibonacci sequence..."
```

### Cross-Session Memory

Code execution history persists across different sessions when using the same thread_id:

```python
# Session 1: Initial data processing
invoke_agent({
    "prompt": "Write code to analyze sales data and calculate average revenue",
    "session_id": "quarterly-report-q4",
    "actor_id": "team-b"
})

# Session 2: Follow-up (different day)
invoke_agent({
    "prompt": "What code did we run for the revenue analysis?",
    "session_id": "quarterly-report-q4",  # Same session ID
    "actor_id": "team-b"
})
# Agent remembers the previous code execution
```

### Custom State Fields

The agent state includes a `code_execution_history` field that persists across invocations:

```python
class CustomAgentState:
    messages: list                    # Standard conversation messages
    user_preferences: dict            # User settings and preferences
    custom_data: dict                 # Application-specific data
    browsing_history: list            # Browser tool usage history
    code_execution_history: list      # Code Interpreter usage history
```

### Accessing Code Execution History

The agent automatically includes recent code execution history in its context:

```python
# The system message is enhanced with execution history:
"""
You're a helpful assistant with the following capabilities:
- Perform mathematical calculations
- Check weather information
- Browse websites and extract information (when available)
- Execute Python code to analyze data, perform calculations, or generate content (when available)

Recent code execution history:
- 2025-11-25T14:31:16Z: Executed code - Calculated factorial of 10
- 2025-11-25T14:31:56Z: Executed code - Generated prime numbers up to 50
"""
```

### Best Practices for Code Interpreter Memory

1. **Consistent Session IDs**: Use the same session ID for related code executions
   ```python
   # Good: Related computations in one session
   session = "ml-training-nov-2024"
   invoke_agent({"prompt": "Load and preprocess data", "session_id": session})
   invoke_agent({"prompt": "Train model on preprocessed data", "session_id": session})
   invoke_agent({"prompt": "Evaluate model performance", "session_id": session})
   ```

2. **Descriptive Code Tasks**: Provide clear execution instructions
   ```python
   # Good: Specific task
   "Write Python code to calculate the standard deviation of [1, 2, 3, 4, 5]"
   
   # Better: Task with context
   "Calculate std deviation of our test scores for the statistical report"
   ```

3. **Memory Cleanup**: Start new sessions for unrelated computations
   ```python
   # New project = new session
   invoke_agent({
       "prompt": "Analyze new dataset",
       "session_id": "customer-churn-dec-2024",  # Different session
       "actor_id": "data-scientist"
   })
   ```

4. **Leverage History**: Reference past executions in follow-up questions
   ```python
   invoke_agent({
       "prompt": "Based on the calculations we ran earlier, what's the trend?",
       "session_id": session
   })
   ```

### IAM Permissions for Code Interpreter

Ensure your agent runtime role has code interpreter permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AgentCoreCodeInterpreterAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:StartCodeInterpreterSession",
        "bedrock-agentcore:StopCodeInterpreterSession",
        "bedrock-agentcore:GetCodeInterpreterSession",
        "bedrock-agentcore:ExecuteCode",
        "bedrock-agentcore:GetCodeExecutionResult"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:*:aws:code-interpreter/*",
        "arn:aws:bedrock-agentcore:*:ACCOUNT_ID:code-interpreter/*"
      ]
    }
  ]
}
```

### Execution Environment

The Code Interpreter provides a sandboxed Python environment with:
- ✅ **NumPy, Pandas, Matplotlib** - Scientific computing libraries
- ✅ **Secure File I/O** - Within session scope
- ✅ **Network Isolation** - For security
- ✅ **Standard Library** - Full Python standard library access

### Advanced: Custom State Management

You can extend the code execution history with custom metadata:

```python
# Include custom execution data in payload
payload = {
    "prompt": "Execute code",
    "session_id": "analysis-1",
    "code_execution_history": [
        {
            "timestamp": "2025-11-25T10:00:00Z",
            "summary": "Calculated quarterly revenue growth: 15%",
            "tags": ["financial", "q4-analysis"],
            "importance": "high",
            "result_variables": {"growth_rate": 0.15}
        }
    ]
}
```

### Monitoring Code Execution Memory

Check memory persistence through CloudWatch logs:

```bash
# View code execution-related logs
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR-RUNTIME-DEFAULT \
  --since 1h --follow | grep -i "execute_code\|code interpreter"
```

### Limitations

1. **Memory Capacity**: AgentCore Memory has storage limits per session
2. **History Retention**: Old execution history may be truncated to stay within limits
3. **Session Isolation**: Different sessions don't share execution history
4. **Execution Timeout**: Long-running code executions may timeout
5. **Package Restrictions**: Only pre-installed libraries are available

### Use Cases

**Data Analysis**
```python
# Session for analyzing customer data
invoke_agent({
    "prompt": "Load customer_data.csv and calculate purchase frequency",
    "session_id": "customer-analysis-2024"
})

# Later: Build on previous analysis
invoke_agent({
    "prompt": "Using the frequency data from before, identify high-value customers",
    "session_id": "customer-analysis-2024"
})
```

**Scientific Computing**
```python
# Physics calculations
invoke_agent({
    "prompt": "Calculate projectile trajectory with initial velocity 50 m/s at 45 degrees",
    "session_id": "physics-sim-1"
})

# Follow-up
invoke_agent({
    "prompt": "Compare that trajectory with a 60-degree angle",
    "session_id": "physics-sim-1"
})
```

**Financial Modeling**
```python
# Build financial models incrementally
invoke_agent({
    "prompt": "Calculate NPV for project A with discount rate 8%",
    "session_id": "capital-budgeting-q4"
})

invoke_agent({
    "prompt": "Now calculate IRR for the same project",
    "session_id": "capital-budgeting-q4"
})
```

### Future Enhancements

Planned improvements for code interpreter memory:

- ✨ Variable persistence across code executions
- ✨ File upload/download capabilities
- ✨ Visualization storage and retrieval
- ✨ Code execution optimization hints
- ✨ Automatic code documentation
- ✨ Cross-reference detection between related executions
- ✨ Package installation support

## References

- [AWS Bedrock AgentCore Memory Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html)
- [AWS Bedrock AgentCore Browser Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-onboarding.html)
- [AWS Bedrock AgentCore Code Interpreter Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-onboarding.html)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangChain x AWS GitHub Repo](https://github.com/langchain-ai/langchain-aws)

## Related Documentation

- [LANGGRAPH_NODE_TRACING.md](LANGGRAPH_NODE_TRACING.md) - Node-level observability
- [README.md](README.md) - Main project documentation
- [bedrock/README.md](bedrock/README.md) - Deployment guide

