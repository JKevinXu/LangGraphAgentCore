# AWS Bedrock Agent Core Deployment

## ✅ Deployment Status

**Repository:** https://github.com/JKevinXu/LangGraphAgentCore

**Deployment Target:** AWS Bedrock Agent Core Runtime

**Status:** 🟢 Ready to Deploy

## 📦 What's Included

```
LangGraphAgentCore/
├── agentcore/              # Core agent framework
│   ├── agent.py            # LangGraph agent implementation
│   ├── tools.py            # Tool decorator
│   └── __init__.py         # Package exports
│
├── bedrock/                # Bedrock deployment files
│   ├── agent_runtime.py    # Runtime entrypoint (@app.entrypoint)
│   ├── agent_bedrock.py    # Bedrock-specific agent
│   ├── Dockerfile          # Container definition
│   ├── deploy.sh           # Automated deployment
│   ├── requirements.txt    # Bedrock dependencies
│   └── README.md           # Deployment guide
│
├── example.py              # Local testing
└── requirements.txt        # Core dependencies
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│         AWS Bedrock Agent Core Runtime              │
│                                                      │
│   ┌──────────────┐                                  │
│   │   Gateway    │                                  │
│   └──────┬───────┘                                  │
│          │                                          │
│          ▼                                          │
│   ┌─────────────────────────────┐                  │
│   │  LangGraphAgentCore         │                  │
│   │                             │                  │
│   │  ┌──────────┐  ┌─────────┐ │                  │
│   │  │LangGraph │  │ Bedrock │ │                  │
│   │  │ Workflow │──│ Claude  │ │                  │
│   │  └──────────┘  └─────────┘ │                  │
│   │                             │                  │
│   │  ┌───────────────────────┐ │                  │
│   │  │ Custom Tools          │ │                  │
│   │  │ - calculator          │ │                  │
│   │  │ - weather             │ │                  │
│   │  └───────────────────────┘ │                  │
│   └─────────────────────────────┘                  │
│          │                                          │
│          ▼                                          │
│   ┌──────────────┐                                 │
│   │  CloudWatch  │                                 │
│   │  Logs & Metrics                                │
│   └──────────────┘                                 │
└─────────────────────────────────────────────────────┘
```

## 🚀 Deployment Steps

### Prerequisites

1. **AWS Account** with Bedrock access
2. **AWS CLI** installed and configured
3. **Docker** installed and running
4. **Python 3.11+**
5. **IAM Permissions** for:
   - Amazon Bedrock
   - Amazon ECR
   - CloudWatch Logs
   - IAM roles

### Step 1: Configure AWS

```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity
```

### Step 2: Clone Repository

```bash
git clone https://github.com/JKevinXu/LangGraphAgentCore.git
cd LangGraphAgentCore/bedrock
```

### Step 3: Deploy

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
1. ✅ Check prerequisites (AWS CLI, Docker, credentials)
2. ✅ Install Python dependencies
3. ✅ Create ECR repository
4. ✅ Build Docker image
5. ✅ Push to Amazon ECR
6. ✅ Output deployment details

### Step 4: Configure in AWS Console

1. Navigate to **AWS Bedrock Agent Core** console
2. Create new agent using your ECR image
3. Configure IAM roles
4. Set up agent alias
5. Enable CloudWatch logging

### Step 5: Test Deployment

```python
import boto3

client = boto3.client('bedrock-agent-runtime')

response = client.invoke_agent(
    agentId='your-agent-id',
    agentAliasId='your-alias-id',
    sessionId='test-session',
    inputText='What is 15 * 23?'
)

print(response)
```

## 🎯 Deployment Features

| Feature | Status | Details |
|---------|--------|---------|
| **LangGraph Workflow** | ✅ | Full state graph support |
| **Bedrock Models** | ✅ | Claude, Titan, and more |
| **Tool Integration** | ✅ | @create_tool decorator |
| **Container Image** | ✅ | Optimized Dockerfile |
| **Auto-scaling** | ✅ | Managed by AWS |
| **Monitoring** | ✅ | CloudWatch integration |
| **Security** | ✅ | IAM and VPC support |
| **Deployment Script** | ✅ | One-command deploy |

## 📊 Bedrock Models

Your agent can use any of these Bedrock models:

### Claude Models (Recommended)
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced performance
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast and cost-effective
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable

### Amazon Titan Models
- `amazon.titan-text-express-v1` - Fast general text
- `amazon.titan-text-lite-v1` - Lightweight option

## 🔧 Configuration

### Agent Configuration

Edit `bedrock/agent_runtime.py`:

```python
config = AgentConfig(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    temperature=0.7,
    max_iterations=10
)
```

### Custom Tools

Add your own tools:

```python
@create_tool
def my_custom_tool(param: str) -> str:
    """Description of what the tool does."""
    # Your implementation
    return result

agent.add_tool(my_custom_tool)
```

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Agent Configuration  
AGENT_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=4096
```

## 📈 Monitoring

### CloudWatch Logs

View logs in AWS Console:
```
/aws/bedrock/agentcore/langgraph-agentcore
```

### Metrics

Monitor:
- Invocation count
- Latency
- Error rate
- Token usage
- Tool execution time

## 💰 Cost Optimization

1. **Use Haiku for simple tasks** - 10x cheaper than Opus
2. **Set appropriate max_tokens** - Reduce waste
3. **Cache frequently used data** - Reduce API calls
4. **Monitor usage** - Set billing alerts

## 🔍 Troubleshooting

### "Model not available"
**Solution:** Enable model access in AWS Bedrock console

### "Permission denied"
**Solution:** Check IAM roles have Bedrock permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

### "Docker build fails"
**Solution:** Ensure you're in the `LangGraphAgentCore` root directory when running deploy

### "ECR push fails"
**Solution:** Verify ECR permissions and re-authenticate:
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
```

## 📚 Additional Resources

- **Bedrock Agent Core Runtime Docs**: [AWS Documentation](https://docs.aws.amazon.com/bedrock/)
- **LangGraph Guide**: [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- **Sample Projects**: [Bedrock Agent Core Samples](https://github.com/awslabs/amazon-bedrock-agent-core-samples)

## 🎉 Deployment Complete

Once deployed, your agent is:
- ✅ Running on AWS managed infrastructure
- ✅ Auto-scaling based on demand
- ✅ Monitored via CloudWatch
- ✅ Secured with IAM
- ✅ Ready for production use

## 📞 Support

- **Issues**: https://github.com/JKevinXu/LangGraphAgentCore/issues
- **Docs**: See [bedrock/README.md](bedrock/README.md)
- **AWS Support**: Contact through AWS Console

---

**Last Updated:** 2025-11-14  
**Version:** 0.1.0  
**Deployment Target:** AWS Bedrock Agent Core Runtime
