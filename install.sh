#!/bin/bash
# Quick install script for LangGraphAgentCore

echo "🚀 Installing LangGraphAgentCore..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check for .env
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from example..."
    echo "OPENAI_API_KEY=your-key-here" > .env
    echo "📝 Please edit .env and add your OpenAI API key"
fi

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Add your API key to .env file"
echo "  2. Run: python example.py"

