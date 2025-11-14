#!/bin/bash
# Deploy LangGraphAgentCore to AWS Bedrock Agent Core Runtime

set -e

echo "🚀 Deploying LangGraphAgentCore to AWS Bedrock Agent Core Runtime"
echo "=================================================================="

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required for runtime deployment"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is required"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Test agent locally (optional)
read -p "Test agent locally first? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧪 Testing agent locally..."
    python agent_runtime.py --local-test
fi

# Deploy to Bedrock Agent Core Runtime
echo ""
echo "🚢 Deploying to AWS Bedrock Agent Core Runtime..."

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Create ECR repository if it doesn't exist
REPO_NAME="langgraph-agentcore"
echo ""
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION

# Build and push Docker image
echo ""
echo "🐳 Building Docker image..."
docker build -t $REPO_NAME:latest -f Dockerfile ..

echo "Pushing to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker tag $REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Configure your agent in AWS Bedrock Agent Core console"
echo "  2. Set up IAM roles and permissions"
echo "  3. Invoke your agent using the SDK or API"
echo ""
echo "ECR Image: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"

