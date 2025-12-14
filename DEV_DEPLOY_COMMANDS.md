# Development & Deployment Commands

Quick reference for developing and deploying LangGraphAgentCore.

---

## AgentCore Runtime

### Deploy to AWS
```bash
cd bedrock
agentcore launch -a langgraph_agent --auto-update-on-conflict
```

### Check Status
```bash
agentcore status
```

### Test Directly
```bash
agentcore invoke '{"prompt": "What is 5 * 7?", "stream": true}'
```

### View Logs
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/langgraph_agent-1NyH76Cfc7-DEFAULT \
  --log-stream-names otel-rt-logs --since 10m --follow
```

### Test with Python
```python
import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

payload = json.dumps({
    "prompt": "Calculate 15 * 7",
    "session_id": "test-session-12345678901234567890123456789",
    "stream": True
})

response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7",
    runtimeSessionId="test-session-12345678901234567890123456789",
    payload=payload,
    qualifier="DEFAULT"
)

print(response['response'].read().decode('utf-8'))
```

---

## BFF (Backend for Frontend)

### Deployed Endpoint
```
http://LangGr-BffSe-aO1aJ7AQgiMd-1474248023.us-west-2.elb.amazonaws.com
```

### Run Locally
```bash
cd bff
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

AGENT_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7" \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Test Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Chat (blocking)
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 5*7?", "session_id": "test-session-12345678901234567890123456789"}'

# Stream (SSE)
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate sqrt(144)", "session_id": "test-session-12345678901234567890123456789"}'
```

### Deploy BFF to AWS
```bash
cd bff/cdk
pip install -r requirements.txt
cdk deploy
```

---

## Streamlit Frontend

### Run Locally
```bash
cd streamlit-ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Access at: http://localhost:8501

---

## Key ARNs & Endpoints

| Resource | Value |
|----------|-------|
| **Agent Runtime ARN** | `arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7` |
| **BFF ALB** | `http://LangGr-BffSe-aO1aJ7AQgiMd-1474248023.us-west-2.elb.amazonaws.com` |
| **Memory ID** | `langgraph_agent_mem-o5nDQxAbkB` |
| **Region** | `us-west-2` |

---

## Streaming Events

When `stream: true`, the AgentCore returns SSE events:

| Event | Description |
|-------|-------------|
| `AGENT_START` | Agent processing started |
| `TOOL_CALL` | Tool being invoked with args |
| `TOOL_RESULT` | Tool execution result |
| `LLM_RESPONSE` | LLM generated response |
| `AGENT_END` | Agent completed |
| `ERROR` | Error occurred |

Each event includes a `timestamp` field (ISO 8601).

---

## Session ID Requirements

- **Minimum length:** 33 characters
- **Format:** alphanumeric with hyphens
- **Example:** `streamlit-session-a1b2c3d4e5f6g7h8i9j0k1l2m3n4`

---

## Observability

### GenAI Dashboard
https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core

### CloudWatch Logs
```bash
# Runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/langgraph_agent-1NyH76Cfc7-DEFAULT \
  --log-stream-names otel-rt-logs --since 1h

# BFF logs
aws logs tail /aws/ecs/langgraph-bff --since 10m
```

---

## Browser Tool IAM Permissions

To enable the AgentCore Browser tool, add this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:ConnectBrowserAutomationStream",
        "bedrock-agentcore:StartBrowserSession",
        "bedrock-agentcore:StopBrowserSession"
      ],
      "Resource": "*"
    }
  ]
}
```

**Supported Regions:** us-east-1, us-west-2, eu-central-1, ap-southeast-2

---

## Code Interpreter IAM Permissions

To enable the AgentCore Code Interpreter, add this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateCodeInterpreter",
        "bedrock-agentcore:StartCodeInterpreterSession",
        "bedrock-agentcore:InvokeCodeInterpreter",
        "bedrock-agentcore:StopCodeInterpreterSession",
        "bedrock-agentcore:DeleteCodeInterpreter",
        "bedrock-agentcore:ListCodeInterpreters",
        "bedrock-agentcore:GetCodeInterpreter"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/code-interpreter*"
    }
  ]
}
```

**Reference:** [AWS AgentCore Code Interpreter Tutorial](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/05-AgentCore-tools/01-Agent-Core-code-interpreter/)

---

## Common Issues

### "Invalid length for parameter runtimeSessionId"
Session ID must be at least 33 characters.

### "ModuleNotFoundError: No module named 'fastapi'"
Run `pip install -r requirements.txt` in the correct venv.

### Streaming not showing intermediate events
Ensure `stream: true` is in the payload and the agent runtime is deployed with streaming support.

