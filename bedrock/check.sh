#!/bin/bash
# Pre-deployment check script for AWS Bedrock Agent Core

set -e

echo "🔍 LangGraphAgentCore - Pre-Deployment Check"
echo "=============================================="
echo ""

ERRORS=0
WARNINGS=0

# Function to check command
check_command() {
    if command -v $1 &> /dev/null; then
        echo "✅ $2: Found"
        return 0
    else
        echo "❌ $2: Not found"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check with warning
check_warning() {
    if eval $1 &> /dev/null; then
        echo "✅ $2: OK"
        return 0
    else
        echo "⚠️  $2: Issue detected"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# 1. Check Python
echo "1️⃣  Checking Python..."
if check_command python3 "Python 3"; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "   Version: $PYTHON_VERSION"
    
    # Check if version >= 3.9
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
        echo "   ✅ Version is compatible (>= 3.9)"
    else
        echo "   ⚠️  Version should be >= 3.9"
        WARNINGS=$((WARNINGS + 1))
    fi
fi
echo ""

# 2. Check pip
echo "2️⃣  Checking pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3: Found"
    PIP_VERSION=$(pip3 --version | awk '{print $2}')
    echo "   Version: $PIP_VERSION"
elif command -v pip &> /dev/null; then
    echo "✅ pip: Found"
    PIP_VERSION=$(pip --version | awk '{print $2}')
    echo "   Version: $PIP_VERSION"
else
    echo "❌ pip/pip3: Not found"
    echo "   Install: python3 -m ensurepip --upgrade"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 3. Check Docker
echo "3️⃣  Checking Docker..."
if check_command docker "Docker"; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    echo "   Version: $DOCKER_VERSION"
    
    # Check if Docker daemon is running
    if docker ps &> /dev/null; then
        echo "   ✅ Docker daemon is running"
    else
        echo "   ❌ Docker daemon is not running"
        echo "   Action: Start Docker Desktop"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# 4. Check AWS CLI
echo "4️⃣  Checking AWS CLI..."
if check_command aws "AWS CLI"; then
    AWS_VERSION=$(aws --version 2>&1 | awk '{print $1}')
    echo "   Version: $AWS_VERSION"
    
    # Check AWS credentials
    echo "   Checking AWS credentials..."
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
        REGION=$(aws configure get region 2>/dev/null || echo "not set")
        echo "   ✅ AWS credentials configured"
        echo "   Account ID: $ACCOUNT_ID"
        echo "   Region: $REGION"
        
        if [ "$REGION" = "not set" ]; then
            echo "   ⚠️  AWS region not set, will default to us-east-1"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo "   ❌ AWS credentials not configured or invalid"
        echo "   Action: Run 'aws configure'"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# 5. Check Bedrock access (if AWS credentials work)
if [ $ERRORS -eq 0 ]; then
    echo "5️⃣  Checking Bedrock access..."
    if aws bedrock list-foundation-models --region us-east-1 &> /dev/null 2>&1; then
        echo "✅ AWS Bedrock: Access confirmed"
        # Try to list Claude models
        CLAUDE_COUNT=$(aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `claude`)].modelId' --output text 2>/dev/null | wc -w)
        echo "   Found $CLAUDE_COUNT Claude models available"
    else
        echo "⚠️  AWS Bedrock: Cannot verify access"
        echo "   This may require Bedrock permissions in your AWS account"
        WARNINGS=$((WARNINGS + 1))
    fi
    echo ""
fi

# 6. Check required files
echo "6️⃣  Checking project files..."
FILES=(
    "agent_runtime.py"
    "agent_bedrock.py"
    "Dockerfile"
    "requirements.txt"
    "../agentcore/agent.py"
    "../agentcore/tools.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file: Found"
    else
        echo "❌ $file: Missing"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# 7. Summary
echo "=============================================="
echo "📊 Check Summary"
echo "=============================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "🎉 All checks passed! Ready to deploy."
    echo ""
    echo "Next step:"
    echo "  ./deploy.sh"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  $WARNINGS warning(s) detected, but can proceed"
    echo ""
    echo "You can deploy with:"
    echo "  ./deploy.sh"
    exit 0
else
    echo "❌ $ERRORS error(s) and $WARNINGS warning(s) detected"
    echo ""
    echo "Fix the errors above before deploying."
    echo ""
    echo "Common fixes:"
    echo "  • Docker not running: Open Docker Desktop"
    echo "  • AWS not configured: Run 'aws configure'"
    echo "  • pip not found: Run 'python3 -m ensurepip --upgrade'"
    exit 1
fi

