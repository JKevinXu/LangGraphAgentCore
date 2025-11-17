# AWS Bedrock Agent Core Runtime Deployment

Deploy your LangGraphAgentCore to AWS Bedrock Agent Core Runtime.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock Agent Core                    │
│                                                               │
│  ┌──────────────┐         ┌─────────────────────────────┐   │
│  │   Runtime    │────────>│   LangGraphAgentCore        │   │
│  │   Gateway    │         │                             │   │
│  └──────────────┘         │  ┌──────────┐  ┌─────────┐  │   │
│         │                 │  │ LangGraph│──│Bedrock  │  │   │
│         │                 │  │  Workflow│  │Claude   │  │   │
│         ▼                 │  └──────────┘  └─────────┘  │   │
│  ┌──────────────┐         │                             │   │
│  │  Observability│         │  ┌───────────────────────┐ │   │
│  │  & Logging   │         │  │ Tools: calculator,    │ │   │
│  └──────────────┘         │  │        weather, etc   │ │   │
│                           │  └───────────────────────┘ │   │
└───────────────────────────└─────────────────────────────┘───┘
```

## Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured
- Docker installed
- Python 3.11+
- AWS credentials with permissions for:
  - Amazon Bedrock
  - Amazon ECR
  - AWS Lambda (for runtime)
  - IAM roles

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Test Locally

```bash
python agent_runtime.py
```

### 3. Deploy to AWS

```bash
chmod +x deploy.sh
./deploy.sh
```

## Configuration

### Using Bedrock Models

Edit `agent_runtime.py` to use different Bedrock models:

```python
config = BedrockAgentConfig(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",  # or other models
    temperature=0.7,
    max_tokens=4096,
    region="us-east-1"
)
```

### Available Bedrock Models

- `anthropic.claude-3-sonnet-20240229-v1:0`
- `anthropic.claude-3-haiku-20240307-v1:0`
- `anthropic.claude-3-opus-20240229-v1:0`
- `anthropic.claude-v2:1`
- `amazon.titan-text-express-v1`

## Project Structure

```
bedrock/
├── agent_runtime.py      # Runtime entrypoint with @app.entrypoint
├── agent_bedrock.py      # Bedrock-specific agent implementation
├── requirements.txt      # Dependencies
├── Dockerfile            # Container image
├── deploy.sh             # Deployment script
└── README.md             # This file
```

## Usage

### Local Testing

```python
from bedrock.agent_runtime import agent

response = agent.run("What is 15 * 23?")
print(response)
```

### Invoke via Bedrock Runtime

Once deployed, invoke using AWS SDK:

```python
import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Basic invocation
payload = json.dumps({"prompt": "What is the weather in Tokyo?"})
response = client.invoke_agent_runtime(
    agentRuntimeArn='your-runtime-arn',
    runtimeSessionId='session-123',
    payload=payload,
    qualifier='DEFAULT'
)

# With memory support
payload = json.dumps({
    "prompt": "What is the weather in Tokyo?",
    "session_id": "session-123",
    "actor_id": "user-alice"
})
response = client.invoke_agent_runtime(
    agentRuntimeArn='your-runtime-arn',
    runtimeSessionId='session-123',
    payload=payload,
    qualifier='DEFAULT'
)
```

## Features

✅ **LangGraph Integration** - Full LangGraph workflow support
✅ **Bedrock Models** - Native support for Claude and other models
✅ **Tool Support** - Use custom tools with `@create_tool`
✅ **Short-Term Memory** - Conversation persistence with AgentCore Memory
✅ **Runtime Compatibility** - Ready for Bedrock Agent Core Runtime
✅ **Observability** - Built-in logging and monitoring
✅ **Scalability** - Auto-scaling with AWS infrastructure

## Deployment Options

### Option 1: Automated Deployment (Recommended)

```bash
./deploy.sh
```

### Option 2: Manual Deployment

```bash
# Build Docker image
docker build -t langgraph-agentcore -f Dockerfile ..

# Tag and push to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com

docker tag langgraph-agentcore:latest ${AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/langgraph-agentcore:latest
docker push ${AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/langgraph-agentcore:latest
```

### Option 3: Using CDK/CloudFormation

See AWS Bedrock Agent Core documentation for infrastructure-as-code examples.

## Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=123456789012

# Agent Configuration
AGENT_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=4096

# Memory Configuration (Optional)
AGENTCORE_MEMORY_ID=your-memory-id-here  # Enable conversation persistence
```

### Enabling Memory Support

To enable short-term memory persistence:

1. Create an AgentCore Memory:
```bash
aws bedrock-agentcore create-memory \
  --region us-west-2 \
  --memory-name "langgraph-agent-memory"
```

2. Set the Memory ID:
```bash
export AGENTCORE_MEMORY_ID="your-memory-id"
```

3. Deploy the agent (memory will be automatically enabled)

See [../MEMORY_SUPPORT.md](../MEMORY_SUPPORT.md) for complete memory documentation.

## Monitoring & Observability

View logs in:
- AWS CloudWatch Logs
- Bedrock Agent Core Runtime console
- X-Ray traces (if enabled)

## Cost Optimization

- Use Claude Haiku for cost-effective operations
- Implement caching for repeated queries
- Set appropriate max_tokens limits
- Use session management

## Troubleshooting

### "Model not available"
Ensure Bedrock model access is enabled in your AWS account/region.

### "Permission denied"
Check IAM roles have required Bedrock permissions.

### "Docker build fails"
Ensure you're running from the LangGraphAgentCore root directory.

## Resources

- [AWS Bedrock Agent Core Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Bedrock Agent Core Samples](https://github.com/awslabs/amazon-bedrock-agent-core-samples)

## License

MIT License - see parent directory LICENSE file

