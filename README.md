# LangGraphAgentCore

A minimal LangGraph agent framework designed for deployment on **AWS Bedrock Agent Core Runtime**.

## Overview

LangGraphAgentCore provides a simple, production-ready agent framework built on LangGraph and optimized for AWS Bedrock Agent Core infrastructure.

## Architecture

```
AWS Bedrock Agent Core Runtime
       ↓
   LangGraphAgentCore
       ├─→ LangGraph Workflow
       ├─→ Bedrock Models (Claude, Titan)
       └─→ Custom Tools
       ↓
   CloudWatch Observability
```

## Quick Start

### Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured
- Docker installed
- Python 3.11+

### Deploy to AWS Bedrock

```bash
# Clone repository
git clone https://github.com/JKevinXu/LangGraphAgentCore.git
cd LangGraphAgentCore/bedrock

# Deploy to Bedrock Agent Core Runtime
./deploy.sh
```

### Local Testing (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Test locally before deploying
python agent_runtime.py
```

## Usage

### Create Agent with Tools

```python
from agentcore import Agent, AgentConfig, create_tool

# Define custom tools
@create_tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

# Create agent
agent = Agent(AgentConfig(
    model="anthropic.claude-3-sonnet-20240229-v1:0"
))
agent.add_tool(calculator)

# Run agent
response = agent.run("What is 15 * 23?")
```

### Invoke Deployed Agent

Once deployed to Bedrock Agent Core:

```python
import boto3

client = boto3.client('bedrock-agent-runtime')
response = client.invoke_agent(
    agentId='your-agent-id',
    agentAliasId='your-alias-id',
    sessionId='session-123',
    inputText='What is the weather in Tokyo?'
)
```

## Deployment

See [bedrock/README.md](bedrock/README.md) for complete deployment guide.

### Deployment Steps

1. **Configure AWS credentials**
   ```bash
   aws configure
   ```

2. **Deploy**
   ```bash
   cd bedrock
   ./deploy.sh
   ```

3. **Monitor in AWS Console**
   - Navigate to Bedrock Agent Core
   - View your deployed agent
   - Check CloudWatch logs

## Features

- ✅ **LangGraph Integration** - Full workflow support
- ✅ **Bedrock Models** - Claude, Titan, and more
- ✅ **Tool Support** - Easy custom tool creation
- ✅ **Production Ready** - Built for AWS infrastructure
- ✅ **Auto-scaling** - Managed by AWS
- ✅ **Observability** - CloudWatch integration
- ✅ **Secure** - IAM and VPC support

## Project Structure

```
LangGraphAgentCore/
├── agentcore/              # Core agent framework
│   ├── agent.py            # LangGraph agent
│   ├── tools.py            # Tool decorator
│   └── __init__.py         # Exports
├── bedrock/                # AWS Bedrock deployment
│   ├── agent_runtime.py    # Runtime entrypoint
│   ├── agent_bedrock.py    # Bedrock agent
│   ├── Dockerfile          # Container
│   ├── deploy.sh           # Deployment script
│   └── README.md           # Deployment guide
└── example.py              # Local testing
```

## Configuration

### Bedrock Models

Available models:
- `anthropic.claude-3-sonnet-20240229-v1:0`
- `anthropic.claude-3-haiku-20240307-v1:0`
- `anthropic.claude-3-opus-20240229-v1:0`
- `amazon.titan-text-express-v1`

### Environment Variables

```bash
AWS_REGION=us-east-1
AGENT_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AGENT_TEMPERATURE=0.7
```

## Documentation

- **Deployment Guide**: [bedrock/README.md](bedrock/README.md)
- **Deployment Status**: [DEPLOY.md](DEPLOY.md)
- **Example Usage**: [example.py](example.py)

## Resources

- [AWS Bedrock Documentation](https://aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Bedrock Agent Core Samples](https://github.com/awslabs/amazon-bedrock-agent-core-samples)

## License

MIT
