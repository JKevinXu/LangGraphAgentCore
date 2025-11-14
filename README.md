# LangGraphAgentCore

A minimal framework for building AI agents with LangGraph.

## Installation

```bash
pip install -r requirements.txt
```

## Setup

1. Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

2. Edit `.env`:

```env
OPENAI_API_KEY=your-key-here
```

## Quick Start

```python
from agentcore import Agent, AgentConfig

# Create and run an agent
agent = Agent(AgentConfig(model="gpt-4"))
response = agent.run("What is LangGraph?")
print(response)
```

## With Tools

```python
from agentcore import Agent, AgentConfig, create_tool

@create_tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

agent = Agent(AgentConfig(model="gpt-4"))
agent.add_tool(calculator)

response = agent.run("What is 15 * 23?")
print(response)
```

## Example

Run the example:

```bash
python example.py
```

## AWS Bedrock Deployment

Deploy to AWS Bedrock Agent Core Runtime:

```bash
cd bedrock
./deploy.sh
```

See [bedrock/README.md](bedrock/README.md) for details.

## License

MIT
