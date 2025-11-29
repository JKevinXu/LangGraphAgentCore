# ECS Service with ALB as Backend-for-Frontend (BFF)

Design document for adding an ECS-based BFF layer to LangGraphAgentCore.

## Overview

This design adds a FastAPI-based Backend-for-Frontend (BFF) service deployed on Amazon ECS with an Application Load Balancer (ALB). The BFF provides a REST/WebSocket API for clients while internally communicating with AWS Bedrock AgentCore.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (us-west-2)                          │
│                                                                             │
│  ┌──────────┐                                                               │
│  │  Route53 │ api.yourdomain.com                                           │
│  └────┬─────┘                                                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │              Application Load Balancer (ALB)                 │           │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │           │
│  │  │ HTTPS Listener  │  │ WebSocket (wss) │                   │           │
│  │  │ Port 443        │  │ /ws/*           │                   │           │
│  │  └────────┬────────┘  └────────┬────────┘                   │           │
│  └───────────┼────────────────────┼─────────────────────────────┘           │
│              │                    │                                         │
│              ▼                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    ECS Cluster (Fargate)                     │           │
│  │  ┌─────────────────────────────────────────────────────────┐│           │
│  │  │                    BFF Service                          ││           │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       ││           │
│  │  │  │ Task 1  │ │ Task 2  │ │ Task 3  │ │ Task N  │       ││           │
│  │  │  │ FastAPI │ │ FastAPI │ │ FastAPI │ │ FastAPI │       ││           │
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       ││           │
│  │  └───────┼───────────┼───────────┼───────────┼─────────────┘│           │
│  │          │           │           │           │              │           │
│  │          └───────────┴─────┬─────┴───────────┘              │           │
│  └────────────────────────────┼─────────────────────────────────┘           │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                   Bedrock AgentCore Runtime                  │           │
│  │  ┌─────────────────────────────────────────────────────────┐│           │
│  │  │              LangGraph Agent (langgraph_agent)          ││           │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ││           │
│  │  │  │Calculator│ │ Weather  │ │ Browser  │ │Code Interp.│ ││           │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘ ││           │
│  │  └─────────────────────────────────────────────────────────┘│           │
│  │                              │                               │           │
│  │                              ▼                               │           │
│  │  ┌─────────────────────────────────────────────────────────┐│           │
│  │  │               AgentCore Memory                          ││           │
│  │  │         (Conversation & State Persistence)              ││           │
│  │  └─────────────────────────────────────────────────────────┘│           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  CloudWatch     │  │   ECR           │  │   Secrets       │             │
│  │  Logs & Metrics │  │   (Container)   │  │   Manager       │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Application Load Balancer (ALB)

**Purpose**: Entry point for all client traffic with SSL termination and routing.

| Feature | Configuration |
|---------|--------------|
| Listeners | HTTPS (443), HTTP (80 → redirect) |
| Target Group | ECS Service tasks on port 8000 |
| Health Check | `/health` endpoint |
| SSL Certificate | AWS ACM managed |
| Stickiness | Disabled (stateless) |

### 2. ECS Cluster (Fargate)

**Purpose**: Serverless container orchestration.

| Setting | Value |
|---------|-------|
| Launch Type | Fargate |
| CPU | 512 (0.5 vCPU) |
| Memory | 1024 MB |
| Min Tasks | 2 |
| Max Tasks | 10 |
| Auto-scaling | Target CPU 70% |

### 3. BFF Service (FastAPI)

**Purpose**: API gateway with streaming, auth, and rate limiting.

**Endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat` | Send message (blocking) |
| POST | `/v1/chat/stream` | Send message (streaming SSE) |
| WS | `/v1/ws/chat` | WebSocket chat |
| GET | `/v1/sessions/{id}` | Get session history |
| DELETE | `/v1/sessions/{id}` | Clear session |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |

## Implementation

### Project Structure

```
bff/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py             # Chat endpoints
│   │   ├── stream.py           # SSE streaming
│   │   ├── websocket.py        # WebSocket handler
│   │   ├── sessions.py         # Session management
│   │   └── health.py           # Health checks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_client.py     # Bedrock AgentCore client
│   │   └── session_store.py    # Session state (optional Redis)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py             # JWT/API key authentication
│   │   ├── rate_limit.py       # Rate limiting
│   │   ├── cors.py             # CORS configuration
│   │   └── logging.py          # Request logging
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py         # Request schemas
│   │   └── responses.py        # Response schemas
│   └── utils/
│       ├── __init__.py
│       └── streaming.py        # SSE helpers
├── tests/
│   ├── test_chat.py
│   ├── test_streaming.py
│   └── test_websocket.py
├── Dockerfile
├── requirements.txt
└── cdk/
    ├── app.py                  # CDK app entry point
    ├── cdk.json                # CDK configuration
    ├── requirements.txt        # CDK dependencies
    └── stacks/
        ├── __init__.py
        ├── vpc_stack.py        # VPC infrastructure
        ├── ecs_stack.py        # ECS cluster and service
        └── bff_stack.py        # Combined BFF stack
```

### Core Files

#### `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routes import chat, stream, websocket, sessions, health
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 BFF Service starting on {settings.HOST}:{settings.PORT}")
    yield
    # Shutdown
    print("👋 BFF Service shutting down")


app = FastAPI(
    title="LangGraphAgentCore BFF",
    description="Backend-for-Frontend for LangGraph Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(stream.router, prefix="/v1", tags=["Streaming"])
app.include_router(websocket.router, prefix="/v1", tags=["WebSocket"])
app.include_router(sessions.router, prefix="/v1", tags=["Sessions"])
```

#### `app/routes/chat.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse
from app.services.agent_client import AgentClient
from app.middleware.auth import get_current_user

router = APIRouter()
agent_client = AgentClient()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user)
):
    """Send a message and get a response (blocking)."""
    try:
        response = await agent_client.invoke(
            prompt=request.message,
            session_id=request.session_id or f"user-{user['id']}",
            actor_id=user['id']
        )
        return ChatResponse(
            message=response,
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### `app/routes/stream.py`

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.models.requests import ChatRequest
from app.services.agent_client import AgentClient
from app.middleware.auth import get_current_user

router = APIRouter()
agent_client = AgentClient()


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user: dict = Depends(get_current_user)
):
    """Send a message and stream the response (SSE)."""
    
    async def event_generator():
        async for event in agent_client.stream(
            prompt=request.message,
            session_id=request.session_id or f"user-{user['id']}",
            actor_id=user['id']
        ):
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

#### `app/routes/websocket.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_client import AgentClient
import json

router = APIRouter()
agent_client = AgentClient()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    session_id = None
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            session_id = message.get("session_id", session_id)
            prompt = message.get("message", "")
            
            # Stream response
            async for event in agent_client.stream(
                prompt=prompt,
                session_id=session_id
            ):
                await websocket.send_text(event)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
```

#### `app/services/agent_client.py`

```python
import boto3
import json
from typing import AsyncIterator
from app.config import settings


class AgentClient:
    """Client for AWS Bedrock AgentCore."""
    
    def __init__(self):
        self.client = boto3.client(
            'bedrock-agentcore',
            region_name=settings.AWS_REGION
        )
        self.runtime_arn = settings.AGENT_RUNTIME_ARN
    
    async def invoke(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> str:
        """Invoke agent (blocking)."""
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id
        })
        
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier='DEFAULT'
        )
        
        return response['body'].read().decode('utf-8')
    
    async def stream(
        self,
        prompt: str,
        session_id: str,
        actor_id: str = "default"
    ) -> AsyncIterator[str]:
        """Stream agent response (SSE)."""
        payload = json.dumps({
            "prompt": prompt,
            "session_id": session_id,
            "actor_id": actor_id,
            "stream": True
        })
        
        # Note: Actual streaming implementation depends on
        # Bedrock AgentCore streaming API availability
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier='DEFAULT'
        )
        
        # Convert to SSE format
        result = response['body'].read().decode('utf-8')
        yield f"event: message\ndata: {json.dumps({'content': result})}\n\n"
        yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
```

#### `app/middleware/auth.py`

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
import jwt


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT/API Key authentication middleware."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks
        if request.url.path in ["/health", "/ready", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Check API key
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key in settings.API_KEYS:
            request.state.user = {"id": "api-user", "type": "api_key"}
            return await call_next(request)
        
        # Check JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=["HS256"]
                )
                request.state.user = payload
                return await call_next(request)
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")
        
        raise HTTPException(status_code=401, detail="Authentication required")


async def get_current_user(request: Request) -> dict:
    """Dependency to get current authenticated user."""
    return getattr(request.state, "user", {"id": "anonymous"})
```

#### `app/middleware/rate_limit.py`

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.limit = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limit for health checks
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = request.headers.get("X-API-Key") or request.client.host
        
        # Clean old requests
        now = time.time()
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < self.window
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        # Record request
        self.requests[client_id].append(now)
        
        return await call_next(request)
```

#### `app/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # AWS
    AWS_REGION: str = "us-west-2"
    AGENT_RUNTIME_ARN: str = ""
    
    # Authentication
    JWT_SECRET: str = "your-secret-key"
    API_KEYS: List[str] = []
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()
```

#### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ app/

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `requirements.txt`

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
boto3>=1.34.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
httpx>=0.26.0
python-multipart>=0.0.6
```

### Infrastructure (AWS CDK)

#### `cdk/app.py`

```python
#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.bff_stack import BffStack

app = cdk.App()

BffStack(
    app, 
    "LangGraphBffStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-west-2"
    ),
    agent_runtime_arn=app.node.try_get_context("agent_runtime_arn"),
    domain_name=app.node.try_get_context("domain_name"),  # Optional
)

app.synth()
```

#### `cdk/cdk.json`

```json
{
  "app": "python3 app.py",
  "context": {
    "region": "us-west-2",
    "agent_runtime_arn": "arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/langgraph_agent-XXX"
  }
}
```

#### `cdk/requirements.txt`

```
aws-cdk-lib>=2.100.0
constructs>=10.0.0
```

#### `cdk/stacks/bff_stack.py`

```python
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
)
from constructs import Construct
from typing import Optional


class BffStack(Stack):
    """CDK Stack for BFF Service with ECS and ALB."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_runtime_arn: str,
        domain_name: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ===================
        # VPC
        # ===================
        vpc = ec2.Vpc(
            self, "BffVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # ===================
        # Secrets
        # ===================
        jwt_secret = secretsmanager.Secret(
            self, "JwtSecret",
            secret_name="langgraph-bff/jwt-secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"jwt_secret": ""}',
                generate_string_key="jwt_secret",
                password_length=64
            )
        )

        api_keys_secret = secretsmanager.Secret(
            self, "ApiKeysSecret",
            secret_name="langgraph-bff/api-keys",
            secret_string_value=cdk.SecretValue.unsafe_plain_text(
                "your-api-key-1,your-api-key-2"
            )
        )

        # ===================
        # ECS Cluster
        # ===================
        cluster = ecs.Cluster(
            self, "BffCluster",
            vpc=vpc,
            cluster_name="langgraph-bff-cluster",
            container_insights=True
        )

        # ===================
        # Docker Image
        # ===================
        docker_image = ecr_assets.DockerImageAsset(
            self, "BffImage",
            directory="../",  # Path to Dockerfile
            file="Dockerfile"
        )

        # ===================
        # Task Role (for Bedrock access)
        # ===================
        task_role = iam.Role(
            self, "BffTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for BFF ECS tasks to access Bedrock AgentCore"
        )

        # Grant Bedrock AgentCore access
        task_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock-agentcore:InvokeAgentRuntime",
                "bedrock-agentcore:GetAgentRuntime"
            ],
            resources=[agent_runtime_arn, f"{agent_runtime_arn}/*"]
        ))

        # ===================
        # Log Group
        # ===================
        log_group = logs.LogGroup(
            self, "BffLogGroup",
            log_group_name="/aws/ecs/langgraph-bff",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY
        )

        # ===================
        # Fargate Service with ALB
        # ===================
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "BffService",
            cluster=cluster,
            service_name="langgraph-bff-service",
            cpu=512,
            memory_limit_mib=1024,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(docker_image),
                container_port=8000,
                container_name="bff",
                task_role=task_role,
                environment={
                    "AWS_REGION": self.region,
                    "AGENT_RUNTIME_ARN": agent_runtime_arn,
                    "LOG_LEVEL": "INFO"
                },
                secrets={
                    "JWT_SECRET": ecs.Secret.from_secrets_manager(jwt_secret, "jwt_secret"),
                    "API_KEYS": ecs.Secret.from_secrets_manager(api_keys_secret)
                },
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="bff",
                    log_group=log_group
                )
            ),
            public_load_balancer=True,
            assign_public_ip=False,
            listener_port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_protocol=elbv2.ApplicationProtocol.HTTP,
            health_check_grace_period=Duration.seconds(60)
        )

        # ===================
        # Health Check
        # ===================
        fargate_service.target_group.configure_health_check(
            path="/health",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
            healthy_http_codes="200"
        )

        # ===================
        # Auto Scaling
        # ===================
        scaling = fargate_service.service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=10
        )

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60)
        )

        scaling.scale_on_request_count(
            "RequestScaling",
            requests_per_target=1000,
            target_group=fargate_service.target_group,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60)
        )

        # ===================
        # HTTPS (Optional - if domain provided)
        # ===================
        if domain_name:
            # Create/import hosted zone
            hosted_zone = route53.HostedZone.from_lookup(
                self, "HostedZone",
                domain_name=domain_name.split(".", 1)[1]  # Get root domain
            )

            # SSL Certificate
            certificate = acm.Certificate(
                self, "Certificate",
                domain_name=domain_name,
                validation=acm.CertificateValidation.from_dns(hosted_zone)
            )

            # HTTPS Listener
            https_listener = fargate_service.load_balancer.add_listener(
                "HttpsListener",
                port=443,
                protocol=elbv2.ApplicationProtocol.HTTPS,
                certificates=[certificate],
                default_target_groups=[fargate_service.target_group]
            )

            # Redirect HTTP to HTTPS
            fargate_service.listener.add_action(
                "HttpRedirect",
                action=elbv2.ListenerAction.redirect(
                    port="443",
                    protocol="HTTPS",
                    permanent=True
                )
            )

            # DNS Record
            route53.ARecord(
                self, "AliasRecord",
                zone=hosted_zone,
                record_name=domain_name,
                target=route53.RecordTarget.from_alias(
                    targets.LoadBalancerTarget(fargate_service.load_balancer)
                )
            )

        # ===================
        # Security Group Rules
        # ===================
        # Allow ALB to access ECS tasks
        fargate_service.service.connections.allow_from(
            fargate_service.load_balancer,
            ec2.Port.tcp(8000),
            "Allow ALB to ECS"
        )

        # ===================
        # Outputs
        # ===================
        CfnOutput(
            self, "LoadBalancerDns",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="ALB DNS name"
        )

        CfnOutput(
            self, "ServiceUrl",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description="BFF Service URL"
        )

        if domain_name:
            CfnOutput(
                self, "CustomDomain",
                value=f"https://{domain_name}",
                description="Custom domain URL"
            )

        CfnOutput(
            self, "ClusterArn",
            value=cluster.cluster_arn,
            description="ECS Cluster ARN"
        )

        CfnOutput(
            self, "ServiceArn",
            value=fargate_service.service.service_arn,
            description="ECS Service ARN"
        )
```

#### `cdk/stacks/vpc_stack.py` (Optional - Separate VPC)

```python
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
)
from constructs import Construct


class VpcStack(Stack):
    """Standalone VPC stack for BFF infrastructure."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "BffVpc",
            vpc_name="langgraph-bff-vpc",
            max_azs=3,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ],
            gateway_endpoints={
                "S3": ec2.GatewayVpcEndpointOptions(
                    service=ec2.GatewayVpcEndpointAwsService.S3
                )
            }
        )

        # VPC Endpoints for AWS services (reduce NAT costs)
        ec2.InterfaceVpcEndpoint(
            self, "EcrEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR
        )

        ec2.InterfaceVpcEndpoint(
            self, "EcrDockerEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
        )

        ec2.InterfaceVpcEndpoint(
            self, "LogsEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS
        )

        ec2.InterfaceVpcEndpoint(
            self, "SecretsEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER
        )

        # Outputs
        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        CfnOutput(
            self, "PublicSubnets",
            value=",".join([s.subnet_id for s in self.vpc.public_subnets])
        )
        CfnOutput(
            self, "PrivateSubnets",
            value=",".join([s.subnet_id for s in self.vpc.private_subnets])
        )
```

## Deployment

### Prerequisites

1. AWS CLI configured
2. AWS CDK installed (`npm install -g aws-cdk`)
3. Docker installed
4. Python 3.11+
5. Domain name (optional, for SSL)

### Deploy Steps

```bash
# 1. Navigate to CDK directory
cd bff/cdk

# 2. Install CDK dependencies
pip install -r requirements.txt

# 3. Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT_ID/us-west-2

# 4. Set context variables
export CDK_CONTEXT="--context agent_runtime_arn=arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/langgraph_agent-XXX"

# 5. Preview changes
cdk diff $CDK_CONTEXT

# 6. Deploy
cdk deploy $CDK_CONTEXT --require-approval never

# 7. Verify deployment
curl http://$(aws cloudformation describe-stacks \
  --stack-name LangGraphBffStack \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDns`].OutputValue' \
  --output text)/health
```

### Deploy with Custom Domain (HTTPS)

```bash
# Deploy with custom domain
cdk deploy \
  --context agent_runtime_arn="arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/langgraph_agent-XXX" \
  --context domain_name="api.yourdomain.com" \
  --require-approval never
```

### Useful CDK Commands

```bash
# List all stacks
cdk list

# Show differences
cdk diff

# Synthesize CloudFormation template
cdk synth > template.yaml

# Destroy stack
cdk destroy

# Watch for changes and auto-deploy (development)
cdk watch
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_REGION` | AWS region | Yes |
| `AGENT_RUNTIME_ARN` | Bedrock AgentCore ARN | Yes |
| `JWT_SECRET` | JWT signing secret | Yes |
| `API_KEYS` | Comma-separated API keys | No |
| `RATE_LIMIT_REQUESTS` | Requests per window | No (default: 100) |
| `RATE_LIMIT_WINDOW` | Window in seconds | No (default: 60) |

## API Reference

### Chat (Blocking)

```bash
curl -X POST https://api.yourdomain.com/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 15 * 23?",
    "session_id": "user-123"
  }'
```

**Response:**
```json
{
  "message": "The result of 15 * 23 = 345.",
  "session_id": "user-123"
}
```

### Chat (Streaming)

```bash
curl -X POST https://api.yourdomain.com/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing",
    "session_id": "user-123"
  }'
```

**Response (SSE):**
```
event: message
data: {"content": "Quantum computing is..."}

event: message
data: {"content": " a type of computation..."}

event: done
data: {"status": "complete"}
```

### WebSocket

```javascript
const ws = new WebSocket('wss://api.yourdomain.com/v1/ws/chat');

ws.onopen = () => {
  ws.send(JSON.stringify({
    session_id: 'user-123',
    message: 'Hello!'
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', event.data);
};
```

## Monitoring

### CloudWatch Metrics

- `ECS/CPUUtilization` - Task CPU usage
- `ECS/MemoryUtilization` - Task memory usage
- `ALB/RequestCount` - Total requests
- `ALB/TargetResponseTime` - Response latency
- `ALB/HTTPCode_Target_5XX_Count` - Error rate

### Alarms (CDK)

```python
from aws_cdk import aws_cloudwatch as cloudwatch, aws_sns as sns

# Create SNS topic for alerts
alerts_topic = sns.Topic(self, "AlertsTopic", topic_name="bff-alerts")

# High error rate alarm
cloudwatch.Alarm(
    self, "HighErrorRate",
    metric=fargate_service.load_balancer.metric_http_code_target(
        code=elbv2.HttpCodeTarget.TARGET_5XX_COUNT,
        period=Duration.minutes(1),
        statistic="Sum"
    ),
    threshold=10,
    evaluation_periods=2,
    alarm_name="bff-high-error-rate",
    alarm_description="High 5XX error rate detected",
    actions_enabled=True,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
)

# High latency alarm
cloudwatch.Alarm(
    self, "HighLatency",
    metric=fargate_service.target_group.metric_target_response_time(
        period=Duration.minutes(1),
        statistic="Average"
    ),
    threshold=2,  # 2 seconds
    evaluation_periods=3,
    alarm_name="bff-high-latency"
)

# CPU utilization alarm
cloudwatch.Alarm(
    self, "HighCpu",
    metric=fargate_service.service.metric_cpu_utilization(
        period=Duration.minutes(5),
        statistic="Average"
    ),
    threshold=90,
    evaluation_periods=2,
    alarm_name="bff-high-cpu"
)
```

### Logs

```bash
# Tail BFF logs
aws logs tail /aws/ecs/langgraph-bff --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/ecs/langgraph-bff \
  --filter-pattern "ERROR"
```

## Security

### Network Security

- ALB in public subnets (receives traffic)
- ECS tasks in private subnets (no direct internet)
- Security groups restrict traffic flow
- HTTPS only (HTTP redirects)

### Authentication

- JWT tokens for user authentication
- API keys for service-to-service
- Secrets stored in AWS Secrets Manager

### IAM Roles

- **ECS Execution Role**: Pull images, write logs
- **ECS Task Role**: Invoke Bedrock AgentCore, access secrets

## Cost Estimation

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| ECS Fargate (2 tasks) | ~$30 |
| ALB | ~$25 |
| NAT Gateway | ~$45 |
| CloudWatch Logs | ~$5 |
| **Total** | **~$105/month** |

*Costs vary by region and usage.*

## Implementation Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| 1 | FastAPI service setup | 2 days |
| 2 | Streaming & WebSocket | 1 day |
| 3 | Auth & rate limiting | 1 day |
| 4 | Terraform infrastructure | 2 days |
| 5 | Testing & deployment | 2 days |
| **Total** | | **~8 days** |

## Future Enhancements

- [ ] Redis for distributed rate limiting
- [ ] API versioning
- [ ] Request/response caching
- [ ] GraphQL endpoint
- [ ] OpenTelemetry tracing
- [ ] Blue/green deployments
- [ ] Multi-region deployment

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [CDK ECS Patterns](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ecs_patterns.html)
- [Bedrock AgentCore SDK](https://docs.aws.amazon.com/bedrock-agentcore/)

