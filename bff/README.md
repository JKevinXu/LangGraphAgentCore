# LangGraphAgentCore BFF

Thin API router/proxy layer for LangGraph Agent on AWS Bedrock AgentCore.

## Overview

This BFF (Backend-for-Frontend) is a simple API gateway that:
- Receives HTTP/WebSocket requests from clients
- Forwards them to AWS Bedrock AgentCore
- Returns responses with streaming support
- Handles authentication and rate limiting

**No agent logic** - just routing.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| POST | `/v1/chat` | Send message (blocking) |
| POST | `/v1/chat/stream` | Send message (SSE streaming) |
| WS | `/v1/ws/chat` | WebSocket chat |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AWS_REGION=us-west-2
export AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/YOUR-AGENT

# Run locally
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
# Build
docker build -t langgraph-bff .

# Run
docker run -p 8000:8000 \
  -e AWS_REGION=us-west-2 \
  -e AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:... \
  langgraph-bff
```

## Deploy with CDK

```bash
cd cdk

# Install CDK dependencies
pip install -r requirements.txt

# Bootstrap (first time)
cdk bootstrap

# Deploy
cdk deploy --context agent_runtime_arn=arn:aws:bedrock-agentcore:...

# Destroy
cdk destroy
```

## API Usage

### Chat (Blocking)

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?", "session_id": "test-1"}'
```

### Chat (Streaming)

```bash
curl -X POST http://localhost:8000/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain AI", "session_id": "test-1"}'
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/v1/ws/chat');
ws.onopen = () => ws.send(JSON.stringify({
  message: "Hello!",
  session_id: "ws-session-1"
}));
ws.onmessage = (e) => console.log(e.data);
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | us-west-2 |
| `AGENT_RUNTIME_ARN` | Bedrock AgentCore ARN | - |
| `API_KEYS` | Comma-separated API keys | - |
| `RATE_LIMIT_REQUESTS` | Requests per window | 100 |
| `RATE_LIMIT_WINDOW` | Window in seconds | 60 |
| `LOG_LEVEL` | Logging level | INFO |

## Project Structure

```
bff/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── routes/              # API endpoints
│   │   ├── health.py        # Health checks
│   │   ├── chat.py          # Blocking chat
│   │   ├── stream.py        # SSE streaming
│   │   └── websocket.py     # WebSocket
│   ├── services/
│   │   └── agent_client.py  # Bedrock client (proxy)
│   └── middleware/
│       ├── auth.py          # API key auth
│       └── rate_limit.py    # Rate limiting
├── cdk/                     # CDK infrastructure
├── Dockerfile
├── requirements.txt
└── README.md
```

