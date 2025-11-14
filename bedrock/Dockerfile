FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY bedrock/requirements.txt .
COPY requirements.txt requirements-base.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agentcore/ ./agentcore/
COPY bedrock/agent_runtime.py .
COPY bedrock/agent_bedrock.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the agent
CMD ["python", "agent_runtime.py"]

