# AgentCore re:Invent 2025 Integration Guide

This guide documents how to integrate the three major new capabilities announced at AWS re:Invent 2025—**Policy**, **Evaluations**, and **Memory**—into your LangGraphAgentCore deployment.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Policy Integration](#policy-integration)
- [Evaluations Integration](#evaluations-integration)
- [Memory Integration](#memory-integration)
- [Combined Architecture](#combined-architecture)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)

---

## Overview

### What's New in AgentCore (re:Invent 2025)

| Feature | Purpose | Status | Impact on LangGraphAgentCore |
|---------|---------|--------|------------------------------|
| **Policy** | Natural language operational boundaries | Preview | Gateway-level enforcement |
| **Evaluations** | 13 pre-built agent performance monitors | Available | Automatic quality monitoring |
| **Memory** | Episodic memory for personalization | Available | Enhanced `AgentCoreMemorySaver` |

### Current LangGraphAgentCore Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Request                            │
│              (BFF / Direct API / Streamlit UI)                   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AgentCore Runtime                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 agent_runtime.py                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │  LangGraph   │  │   Bedrock    │  │    Tools     │  │   │
│  │  │   Workflow   │  │   Claude     │  │  (calc,etc)  │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AgentCoreMemorySaver                        │   │
│  │         (Short-term conversation memory)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Observability                               │
│            (Langfuse / CloudWatch / X-Ray)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Enhanced Architecture with re:Invent 2025 Features

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Request                            │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AgentCore Gateway                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    Policy    │  │   Memory     │  │ Evaluations  │         │
│  │ Enforcement  │  │  Retrieval   │  │   Sampling   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AgentCore Runtime                              │
│         (LangGraph + Bedrock + Tools + Langfuse)                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Execution                                │
│       (APIs, databases via AgentCore Gateway)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Versions

```bash
# requirements.txt additions
boto3>=1.35.0           # AgentCore SDK support
aioboto3>=13.0.0        # Async streaming support
langfuse>=2.0.0         # Observability integration
langgraph>=0.2.0        # LangGraph core
langchain-aws>=0.2.0    # Bedrock integration
```

### AWS Configuration

Ensure your AWS account has:
- Bedrock AgentCore enabled in your region
- Required IAM permissions for Policy, Evaluations, and Memory APIs
- Existing agent runtime deployed

### Environment Variables

```bash
# Core configuration
AWS_REGION=us-west-2
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/RUNTIME_ID

# New feature configuration
AGENTCORE_MEMORY_ID=your-memory-id
AGENTCORE_POLICY_ENABLED=true
AGENTCORE_EVALUATIONS_ENABLED=true

# Observability
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## Policy Integration

### Overview

Policy in AgentCore enables natural language governance rules that are enforced at the Gateway level, intercepting every agent action before execution.

### Step 1: Define Policy Configuration

Create `bedrock/policy_config.py`:

```python
"""
AgentCore Policy Configuration.

Defines operational boundaries for the LangGraph agent using natural language.
"""

import boto3
import json
from typing import Optional
import os


# Policy definition in natural language
AGENT_POLICY = """
This agent is a helpful assistant with calculator, weather, browsing, and code execution capabilities.

## Allowed Operations
- Perform mathematical calculations of any complexity
- Check weather for any location
- Browse public websites and extract information
- Execute Python code in sandbox for data analysis

## Restrictions
- Never access or reveal internal system configurations
- Cannot make HTTP requests to internal/private IP ranges
- Cannot execute code that modifies the filesystem
- Cannot access environment variables containing secrets
- Must not store user credentials or payment information

## Data Handling
- Only process data provided in the current session
- Cannot access data from other users' sessions
- Must redact any accidentally exposed PII before responding
- Cannot save user data to external systems without explicit consent

## Tool Usage Limits
- Browser tool: Max 10 page navigations per session
- Code interpreter: Max 60 seconds execution time per request
- Calculator: No restrictions

## Human Escalation
- Escalate any requests involving financial transactions
- Escalate requests that seem to probe for security vulnerabilities
- Escalate when user expresses frustration multiple times
"""


class PolicyManager:
    """Manages AgentCore Policy configuration and enforcement."""
    
    def __init__(
        self,
        agent_runtime_arn: Optional[str] = None,
        region: str = "us-west-2"
    ):
        self.region = region
        self.agent_runtime_arn = agent_runtime_arn or os.environ.get("AGENTCORE_RUNTIME_ARN")
        self.client = boto3.client('bedrock-agentcore', region_name=region)
        
    def create_or_update_policy(
        self,
        policy_name: str = "langgraph-agent-policy",
        policy_definition: str = AGENT_POLICY
    ) -> dict:
        """
        Create or update the agent policy.
        
        Args:
            policy_name: Unique name for the policy
            policy_definition: Natural language policy definition
            
        Returns:
            Policy creation/update response
        """
        try:
            # Check if policy exists
            existing = self._get_policy(policy_name)
            
            if existing:
                # Update existing policy
                response = self.client.update_policy(
                    agentRuntimeArn=self.agent_runtime_arn,
                    policyName=policy_name,
                    policyDefinition=policy_definition
                )
                print(f"✅ Policy '{policy_name}' updated successfully")
            else:
                # Create new policy
                response = self.client.create_policy(
                    agentRuntimeArn=self.agent_runtime_arn,
                    policyName=policy_name,
                    policyDefinition=policy_definition
                )
                print(f"✅ Policy '{policy_name}' created successfully")
                
            return response
            
        except Exception as e:
            print(f"❌ Policy operation failed: {e}")
            raise
    
    def _get_policy(self, policy_name: str) -> Optional[dict]:
        """Get existing policy by name."""
        try:
            return self.client.get_policy(
                agentRuntimeArn=self.agent_runtime_arn,
                policyName=policy_name
            )
        except self.client.exceptions.ResourceNotFoundException:
            return None
    
    def list_policies(self) -> list:
        """List all policies for this agent."""
        response = self.client.list_policies(
            agentRuntimeArn=self.agent_runtime_arn
        )
        return response.get('policies', [])
    
    def delete_policy(self, policy_name: str) -> None:
        """Delete a policy."""
        self.client.delete_policy(
            agentRuntimeArn=self.agent_runtime_arn,
            policyName=policy_name
        )
        print(f"✅ Policy '{policy_name}' deleted")
    
    def get_policy_violations(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_results: int = 100
    ) -> list:
        """
        Get policy violation logs for analysis.
        
        Returns list of violations with details about what action was blocked
        and which policy rule was triggered.
        """
        params = {
            'agentRuntimeArn': self.agent_runtime_arn,
            'maxResults': max_results
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        response = self.client.get_policy_violations(**params)
        return response.get('violations', [])


# Domain-specific policy templates
CUSTOMER_SERVICE_POLICY = """
This agent handles customer service inquiries.

## Allowed Operations
- View customer order history (authenticated user only)
- Check product availability and pricing
- Process returns for orders under 30 days
- Schedule callbacks with support team

## Restrictions
- Cannot access other customers' data
- Cannot modify account email or password
- Cannot issue refunds over $100 without manager approval
- Cannot access payment card details (only last 4 digits)
- Cannot share customer data with external systems

## Escalation Triggers
- Billing disputes
- Account security concerns
- Complaints about employees
- Legal or regulatory questions
"""


INTERNAL_IT_POLICY = """
This agent assists with internal IT support.

## Allowed Operations
- Password reset requests (triggers approval workflow)
- Software installation requests (from approved list)
- VPN access troubleshooting
- Hardware inventory queries

## Restrictions
- Cannot access production databases directly
- Cannot modify user permissions without ticket approval
- Cannot disable security monitoring or alerting
- Cannot access systems the requesting employee doesn't have permissions for
- Cannot share system credentials or access tokens

## Escalation Triggers
- Security incident reports
- Requests for admin access
- Infrastructure changes
- Data access requests for other employees
"""


def get_policy_for_use_case(use_case: str) -> str:
    """Get a pre-built policy template for common use cases."""
    policies = {
        'general': AGENT_POLICY,
        'customer_service': CUSTOMER_SERVICE_POLICY,
        'internal_it': INTERNAL_IT_POLICY,
    }
    return policies.get(use_case, AGENT_POLICY)


# CLI interface for policy management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AgentCore Policy Manager')
    parser.add_argument('action', choices=['create', 'list', 'delete', 'violations'])
    parser.add_argument('--name', default='langgraph-agent-policy')
    parser.add_argument('--use-case', default='general')
    
    args = parser.parse_args()
    
    manager = PolicyManager()
    
    if args.action == 'create':
        policy_def = get_policy_for_use_case(args.use_case)
        manager.create_or_update_policy(args.name, policy_def)
    elif args.action == 'list':
        policies = manager.list_policies()
        for p in policies:
            print(f"- {p['policyName']}: {p.get('status', 'unknown')}")
    elif args.action == 'delete':
        manager.delete_policy(args.name)
    elif args.action == 'violations':
        violations = manager.get_policy_violations()
        for v in violations:
            print(f"- {v['timestamp']}: {v['blockedAction']} - {v['violatedRule']}")
```

### Step 2: Integrate Policy Check in Agent Runtime

Update `bedrock/agent_runtime.py` to include policy-aware error handling:

```python
# Add to agent_runtime.py

from policy_config import PolicyManager

# Policy violation handler
def handle_policy_violation(violation: dict) -> str:
    """Generate user-friendly response when policy blocks an action."""
    action = violation.get('blockedAction', 'the requested action')
    reason = violation.get('violatedRule', 'policy restrictions')
    
    return (
        f"I'm unable to {action} due to {reason}. "
        "This is a safety measure to protect you and the system. "
        "If you believe this is an error, please contact support."
    )


# In invoke_agent, wrap tool execution with policy-aware handling
@app.entrypoint
def invoke_agent(payload, context=None):
    """Entrypoint with policy-aware error handling."""
    try:
        # ... existing code ...
        response = agent.invoke(input_data, config=config)
        return response["messages"][-1].content
        
    except PolicyViolationError as e:
        # Handle policy blocks gracefully
        return handle_policy_violation(e.violation_details)
```

### Step 3: Deploy Policy

```bash
# Deploy policy to your agent
cd bedrock
python policy_config.py create --name langgraph-agent-policy --use-case general
```

---

## Evaluations Integration

### Overview

AgentCore Evaluations provides 13 pre-built monitors that continuously assess agent performance across correctness, safety, and quality dimensions.

### Step 1: Configure Evaluations

Create `bedrock/evaluations_config.py`:

```python
"""
AgentCore Evaluations Configuration.

Configures the 13 pre-built evaluators for continuous agent monitoring.
"""

import boto3
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import os


class EvaluatorType(Enum):
    """Available AgentCore evaluators."""
    # Correctness
    TASK_COMPLETION = "task_completion"
    RESPONSE_ACCURACY = "response_accuracy"
    INSTRUCTION_FOLLOWING = "instruction_following"
    TOOL_SELECTION_ACCURACY = "tool_selection_accuracy"
    TOOL_USAGE_CORRECTNESS = "tool_usage_correctness"
    
    # Safety
    HARMFUL_CONTENT = "harmful_content"
    PII_EXPOSURE = "pii_exposure"
    PROMPT_INJECTION = "prompt_injection"
    OFF_TOPIC = "off_topic"
    
    # Quality
    RESPONSE_RELEVANCE = "response_relevance"
    RESPONSE_COHERENCE = "response_coherence"
    GROUNDEDNESS = "groundedness"
    TONE_APPROPRIATENESS = "tone_appropriateness"


@dataclass
class AlertConfig:
    """Configuration for evaluation alerts."""
    threshold: float
    channel: str  # 'sns', 'cloudwatch', 'slack', 'pagerduty'
    channel_config: Dict  # Channel-specific configuration


@dataclass
class EvaluatorConfig:
    """Configuration for a single evaluator."""
    enabled: bool = True
    alert: Optional[AlertConfig] = None
    custom_criteria: Optional[str] = None  # For customized evaluation criteria


class EvaluationsManager:
    """Manages AgentCore Evaluations configuration."""
    
    def __init__(
        self,
        agent_runtime_arn: Optional[str] = None,
        region: str = "us-west-2"
    ):
        self.region = region
        self.agent_runtime_arn = agent_runtime_arn or os.environ.get("AGENTCORE_RUNTIME_ARN")
        self.client = boto3.client('bedrock-agentcore', region_name=region)
    
    def configure_evaluations(
        self,
        sampling_rate: float = 0.1,
        evaluators: Optional[Dict[EvaluatorType, EvaluatorConfig]] = None,
        sns_topic_arn: Optional[str] = None
    ) -> dict:
        """
        Configure evaluations for the agent.
        
        Args:
            sampling_rate: Fraction of interactions to evaluate (0.0-1.0)
            evaluators: Configuration for each evaluator
            sns_topic_arn: SNS topic for alerts
            
        Returns:
            Configuration response
        """
        # Default configuration
        if evaluators is None:
            evaluators = self._get_default_evaluators()
        
        # Build evaluator configuration
        evaluator_configs = []
        for evaluator_type, config in evaluators.items():
            evaluator_config = {
                'evaluatorType': evaluator_type.value,
                'enabled': config.enabled,
            }
            
            if config.alert:
                evaluator_config['alertConfig'] = {
                    'threshold': config.alert.threshold,
                    'alertChannel': config.alert.channel,
                    'channelConfig': config.alert.channel_config
                }
            
            if config.custom_criteria:
                evaluator_config['customCriteria'] = config.custom_criteria
                
            evaluator_configs.append(evaluator_config)
        
        # Apply configuration
        response = self.client.configure_evaluations(
            agentRuntimeArn=self.agent_runtime_arn,
            samplingRate=sampling_rate,
            evaluators=evaluator_configs,
            alertSnsTopicArn=sns_topic_arn
        )
        
        print(f"✅ Evaluations configured with {len(evaluator_configs)} evaluators")
        print(f"   Sampling rate: {sampling_rate * 100}%")
        
        return response
    
    def _get_default_evaluators(self) -> Dict[EvaluatorType, EvaluatorConfig]:
        """Get default evaluator configuration."""
        return {
            # Correctness evaluators
            EvaluatorType.TASK_COMPLETION: EvaluatorConfig(
                enabled=True,
                alert=AlertConfig(
                    threshold=0.85,
                    channel='cloudwatch',
                    channel_config={'namespace': 'AgentCore/Evaluations'}
                )
            ),
            EvaluatorType.RESPONSE_ACCURACY: EvaluatorConfig(enabled=True),
            EvaluatorType.INSTRUCTION_FOLLOWING: EvaluatorConfig(enabled=True),
            EvaluatorType.TOOL_SELECTION_ACCURACY: EvaluatorConfig(
                enabled=True,
                alert=AlertConfig(
                    threshold=0.90,
                    channel='cloudwatch',
                    channel_config={'namespace': 'AgentCore/Evaluations'}
                )
            ),
            EvaluatorType.TOOL_USAGE_CORRECTNESS: EvaluatorConfig(enabled=True),
            
            # Safety evaluators (stricter thresholds)
            EvaluatorType.HARMFUL_CONTENT: EvaluatorConfig(
                enabled=True,
                alert=AlertConfig(
                    threshold=0.0,  # Zero tolerance
                    channel='sns',
                    channel_config={'priority': 'high'}
                )
            ),
            EvaluatorType.PII_EXPOSURE: EvaluatorConfig(
                enabled=True,
                alert=AlertConfig(
                    threshold=0.0,  # Zero tolerance
                    channel='sns',
                    channel_config={'priority': 'high'}
                )
            ),
            EvaluatorType.PROMPT_INJECTION: EvaluatorConfig(
                enabled=True,
                alert=AlertConfig(
                    threshold=0.0,  # Zero tolerance
                    channel='sns',
                    channel_config={'priority': 'high'}
                )
            ),
            EvaluatorType.OFF_TOPIC: EvaluatorConfig(
                enabled=True,
                alert=AlertConfig(
                    threshold=0.1,  # Allow 10% off-topic
                    channel='cloudwatch',
                    channel_config={'namespace': 'AgentCore/Evaluations'}
                )
            ),
            
            # Quality evaluators
            EvaluatorType.RESPONSE_RELEVANCE: EvaluatorConfig(enabled=True),
            EvaluatorType.RESPONSE_COHERENCE: EvaluatorConfig(enabled=True),
            EvaluatorType.GROUNDEDNESS: EvaluatorConfig(enabled=True),
            EvaluatorType.TONE_APPROPRIATENESS: EvaluatorConfig(
                enabled=True,
                custom_criteria="Professional but friendly tone suitable for technical support"
            ),
        }
    
    def get_evaluation_results(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        evaluator_types: Optional[List[EvaluatorType]] = None,
        max_results: int = 100
    ) -> dict:
        """
        Retrieve evaluation results for analysis.
        
        Returns:
            Evaluation results with scores and details
        """
        params = {
            'agentRuntimeArn': self.agent_runtime_arn,
            'maxResults': max_results
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        if evaluator_types:
            params['evaluatorTypes'] = [e.value for e in evaluator_types]
            
        return self.client.get_evaluation_results(**params)
    
    def get_evaluation_summary(self, time_period: str = "24h") -> dict:
        """
        Get aggregated evaluation summary.
        
        Args:
            time_period: '1h', '24h', '7d', '30d'
            
        Returns:
            Summary statistics for each evaluator
        """
        response = self.client.get_evaluation_summary(
            agentRuntimeArn=self.agent_runtime_arn,
            timePeriod=time_period
        )
        return response
    
    def create_evaluation_dashboard(self) -> str:
        """
        Create a CloudWatch dashboard for evaluation metrics.
        
        Returns:
            Dashboard ARN
        """
        cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "title": "Task Completion Rate",
                        "metrics": [
                            ["AgentCore/Evaluations", "TaskCompletionScore", 
                             "AgentRuntimeArn", self.agent_runtime_arn]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "title": "Safety Scores",
                        "metrics": [
                            ["AgentCore/Evaluations", "HarmfulContentScore",
                             "AgentRuntimeArn", self.agent_runtime_arn],
                            [".", "PIIExposureScore", ".", "."],
                            [".", "PromptInjectionScore", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "title": "Tool Accuracy",
                        "metrics": [
                            ["AgentCore/Evaluations", "ToolSelectionAccuracy",
                             "AgentRuntimeArn", self.agent_runtime_arn],
                            [".", "ToolUsageCorrectness", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region
                    }
                }
            ]
        }
        
        response = cloudwatch.put_dashboard(
            DashboardName=f"AgentCore-Evaluations-{self.agent_runtime_arn.split('/')[-1]}",
            DashboardBody=str(dashboard_body)
        )
        
        print(f"✅ Dashboard created: {response['DashboardArn']}")
        return response['DashboardArn']


# Integration with Langfuse for combined observability
class LangfuseEvaluationsSync:
    """Sync AgentCore evaluations with Langfuse for unified observability."""
    
    def __init__(self, evaluations_manager: EvaluationsManager):
        self.evaluations = evaluations_manager
        
        # Import Langfuse if available
        try:
            from langfuse import Langfuse
            self.langfuse = Langfuse()
            self.langfuse_enabled = True
        except ImportError:
            self.langfuse_enabled = False
            print("⚠️ Langfuse not available for evaluation sync")
    
    def sync_evaluations_to_langfuse(self, time_period: str = "1h") -> int:
        """
        Sync recent AgentCore evaluations to Langfuse as scores.
        
        This enables viewing evaluations alongside traces in Langfuse UI.
        """
        if not self.langfuse_enabled:
            return 0
        
        results = self.evaluations.get_evaluation_results(max_results=100)
        synced_count = 0
        
        for result in results.get('evaluations', []):
            trace_id = result.get('traceId')
            if not trace_id:
                continue
            
            # Add score to Langfuse trace
            self.langfuse.score(
                trace_id=trace_id,
                name=f"agentcore_{result['evaluatorType']}",
                value=result['score'],
                comment=result.get('details', '')
            )
            synced_count += 1
        
        self.langfuse.flush()
        print(f"✅ Synced {synced_count} evaluations to Langfuse")
        return synced_count


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AgentCore Evaluations Manager')
    parser.add_argument('action', choices=['configure', 'summary', 'dashboard', 'sync'])
    parser.add_argument('--sampling-rate', type=float, default=0.1)
    parser.add_argument('--sns-topic', default=None)
    
    args = parser.parse_args()
    
    manager = EvaluationsManager()
    
    if args.action == 'configure':
        manager.configure_evaluations(
            sampling_rate=args.sampling_rate,
            sns_topic_arn=args.sns_topic
        )
    elif args.action == 'summary':
        summary = manager.get_evaluation_summary()
        for evaluator, stats in summary.get('summaries', {}).items():
            print(f"{evaluator}: avg={stats['average']:.2f}, count={stats['count']}")
    elif args.action == 'dashboard':
        manager.create_evaluation_dashboard()
    elif args.action == 'sync':
        sync = LangfuseEvaluationsSync(manager)
        sync.sync_evaluations_to_langfuse()
```

### Step 2: Deploy Evaluations

```bash
# Configure evaluations with 10% sampling
cd bedrock
python evaluations_config.py configure --sampling-rate 0.1

# Create CloudWatch dashboard
python evaluations_config.py dashboard

# View summary
python evaluations_config.py summary
```

---

## Memory Integration

### Overview

AgentCore Memory now supports **episodic memory**—the ability to remember and learn from past interactions, enabling personalized responses over time.

### Current Memory in LangGraphAgentCore

We already use `AgentCoreMemorySaver` for short-term conversation memory:

```python
# From agent_runtime.py
from langgraph_checkpoint_aws import AgentCoreMemorySaver

checkpointer = AgentCoreMemorySaver(MEMORY_ID, region_name=REGION)
agent = graph_builder.compile(checkpointer=checkpointer)
```

### Step 1: Enhanced Memory Configuration

Create `bedrock/episodic_memory_config.py`:

```python
"""
AgentCore Episodic Memory Configuration.

Extends short-term memory with episodic memory for long-term personalization.
"""

import boto3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os


@dataclass
class MemoryEntry:
    """A single memory entry."""
    memory_id: str
    user_id: str
    memory_type: str  # 'preference', 'interaction', 'learned_behavior'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    importance_score: float = 0.5  # 0.0-1.0


@dataclass
class MemoryConfig:
    """Configuration for episodic memory."""
    enabled: bool = True
    memory_types: List[str] = field(default_factory=lambda: [
        'user_preferences',
        'interaction_history',
        'learned_behaviors'
    ])
    retention_days: int = 90
    require_consent: bool = True
    max_memories_per_user: int = 1000
    auto_extraction: bool = True  # Automatically extract memories from conversations


class EpisodicMemoryManager:
    """Manages AgentCore Episodic Memory."""
    
    def __init__(
        self,
        agent_runtime_arn: Optional[str] = None,
        region: str = "us-west-2"
    ):
        self.region = region
        self.agent_runtime_arn = agent_runtime_arn or os.environ.get("AGENTCORE_RUNTIME_ARN")
        self.client = boto3.client('bedrock-agentcore', region_name=region)
    
    def configure_memory(self, config: MemoryConfig) -> dict:
        """
        Configure episodic memory for the agent.
        
        Args:
            config: Memory configuration
            
        Returns:
            Configuration response
        """
        response = self.client.configure_memory(
            agentRuntimeArn=self.agent_runtime_arn,
            memoryConfig={
                'enabled': config.enabled,
                'memoryTypes': config.memory_types,
                'retentionDays': config.retention_days,
                'requireConsent': config.require_consent,
                'maxMemoriesPerUser': config.max_memories_per_user,
                'autoExtraction': config.auto_extraction
            }
        )
        
        print(f"✅ Episodic memory configured")
        print(f"   Memory types: {config.memory_types}")
        print(f"   Retention: {config.retention_days} days")
        
        return response
    
    def store_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict] = None,
        importance_score: float = 0.5
    ) -> str:
        """
        Store a memory entry.
        
        Args:
            user_id: User identifier
            memory_type: Type of memory ('preference', 'interaction', 'learned_behavior')
            content: Memory content
            metadata: Additional metadata
            importance_score: Importance for retrieval ranking (0.0-1.0)
            
        Returns:
            Memory entry ID
        """
        response = self.client.store_memory(
            agentRuntimeArn=self.agent_runtime_arn,
            userId=user_id,
            memoryType=memory_type,
            content=content,
            metadata=metadata or {},
            importanceScore=importance_score
        )
        
        return response['memoryId']
    
    def retrieve_memories(
        self,
        user_id: str,
        query: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        max_results: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """
        Retrieve relevant memories for a user.
        
        Args:
            user_id: User identifier
            query: Optional semantic search query
            memory_types: Filter by memory types
            max_results: Maximum memories to return
            min_importance: Minimum importance score
            
        Returns:
            List of relevant memory entries
        """
        params = {
            'agentRuntimeArn': self.agent_runtime_arn,
            'userId': user_id,
            'maxResults': max_results,
            'minImportance': min_importance
        }
        
        if query:
            params['semanticQuery'] = query
        if memory_types:
            params['memoryTypes'] = memory_types
            
        response = self.client.retrieve_memories(**params)
        
        return [
            MemoryEntry(
                memory_id=m['memoryId'],
                user_id=m['userId'],
                memory_type=m['memoryType'],
                content=m['content'],
                metadata=m.get('metadata', {}),
                created_at=m['createdAt'],
                last_accessed=m['lastAccessed'],
                access_count=m['accessCount'],
                importance_score=m['importanceScore']
            )
            for m in response.get('memories', [])
        ]
    
    def delete_user_memories(
        self,
        user_id: str,
        memory_types: Optional[List[str]] = None
    ) -> int:
        """
        Delete all memories for a user (GDPR compliance).
        
        Args:
            user_id: User identifier
            memory_types: Optional filter by types
            
        Returns:
            Number of memories deleted
        """
        params = {
            'agentRuntimeArn': self.agent_runtime_arn,
            'userId': user_id
        }
        
        if memory_types:
            params['memoryTypes'] = memory_types
            
        response = self.client.delete_user_memories(**params)
        
        deleted_count = response.get('deletedCount', 0)
        print(f"✅ Deleted {deleted_count} memories for user {user_id}")
        
        return deleted_count
    
    def get_user_memory_summary(self, user_id: str) -> dict:
        """
        Get a summary of memories stored for a user.
        
        Useful for privacy dashboards and user data requests.
        """
        response = self.client.get_user_memory_summary(
            agentRuntimeArn=self.agent_runtime_arn,
            userId=user_id
        )
        return response


class MemoryAwareAgent:
    """
    Wrapper that adds episodic memory capabilities to the LangGraph agent.
    
    This integrates with the existing AgentCoreMemorySaver for short-term memory
    while adding long-term episodic memory retrieval and storage.
    """
    
    def __init__(
        self,
        agent,  # The compiled LangGraph agent
        memory_manager: EpisodicMemoryManager
    ):
        self.agent = agent
        self.memory = memory_manager
    
    def invoke_with_memory(
        self,
        user_input: str,
        user_id: str,
        session_id: str,
        config: Optional[Dict] = None
    ) -> str:
        """
        Invoke the agent with episodic memory context.
        
        1. Retrieves relevant memories for the user
        2. Adds memory context to the system message
        3. Invokes the agent
        4. Extracts and stores new memories from the interaction
        """
        # Step 1: Retrieve relevant memories
        memories = self.memory.retrieve_memories(
            user_id=user_id,
            query=user_input,
            max_results=5
        )
        
        # Step 2: Build memory context
        memory_context = self._build_memory_context(memories)
        
        # Step 3: Invoke agent with memory context
        # The memory context is passed through the custom state
        input_data = {
            "messages": [HumanMessage(content=user_input)],
            "user_preferences": self._extract_preferences(memories),
            "custom_data": {"memory_context": memory_context}
        }
        
        # Build config
        full_config = {
            "configurable": {
                "thread_id": session_id,
                "actor_id": user_id,
            },
            **(config or {})
        }
        
        response = self.agent.invoke(input_data, config=full_config)
        result = response["messages"][-1].content
        
        # Step 4: Extract and store new memories
        self._extract_and_store_memories(
            user_id=user_id,
            user_input=user_input,
            agent_response=result
        )
        
        return result
    
    def _build_memory_context(self, memories: List[MemoryEntry]) -> str:
        """Build context string from memories."""
        if not memories:
            return ""
        
        context_parts = ["[User Memory Context]"]
        
        for memory in memories:
            if memory.memory_type == 'user_preferences':
                context_parts.append(f"• Preference: {memory.content}")
            elif memory.memory_type == 'interaction_history':
                context_parts.append(f"• Previous interaction: {memory.content}")
            elif memory.memory_type == 'learned_behaviors':
                context_parts.append(f"• Known behavior: {memory.content}")
        
        return "\n".join(context_parts)
    
    def _extract_preferences(self, memories: List[MemoryEntry]) -> dict:
        """Extract user preferences from memories."""
        prefs = {}
        for memory in memories:
            if memory.memory_type == 'user_preferences':
                # Parse preference from content
                # Format: "key: value" or just "value"
                if ':' in memory.content:
                    key, value = memory.content.split(':', 1)
                    prefs[key.strip()] = value.strip()
                else:
                    prefs[memory.content] = True
        return prefs
    
    def _extract_and_store_memories(
        self,
        user_id: str,
        user_input: str,
        agent_response: str
    ):
        """
        Extract memorable information from the interaction.
        
        Uses heuristics to identify:
        - User preferences (e.g., "I prefer...", "I like...")
        - Important facts (e.g., names, dates, recurring topics)
        - Interaction patterns
        """
        # Preference patterns
        preference_patterns = [
            "i prefer", "i like", "i always", "i never", "i usually",
            "my favorite", "my preference", "i want", "please always"
        ]
        
        user_input_lower = user_input.lower()
        
        # Check for preference statements
        for pattern in preference_patterns:
            if pattern in user_input_lower:
                # Store as preference
                self.memory.store_memory(
                    user_id=user_id,
                    memory_type='user_preferences',
                    content=user_input,
                    importance_score=0.7
                )
                break
        
        # Store interaction summary (for context in future sessions)
        interaction_summary = f"User asked about: {user_input[:100]}"
        self.memory.store_memory(
            user_id=user_id,
            memory_type='interaction_history',
            content=interaction_summary,
            importance_score=0.3
        )


# Example: Memory extraction prompts for LLM-based extraction
MEMORY_EXTRACTION_PROMPT = """
Analyze this conversation and extract any memorable information:

User: {user_input}
Assistant: {agent_response}

Extract the following if present:
1. User preferences (e.g., preferred formats, topics of interest)
2. Personal information the user shared (name, location, timezone, etc.)
3. Recurring patterns or behaviors
4. Important context for future interactions

Return as JSON:
{{
    "preferences": [{{ "type": "...", "value": "..." }}],
    "personal_info": [{{ "key": "...", "value": "..." }}],
    "patterns": ["..."],
    "context": ["..."]
}}

If nothing memorable, return: {{"preferences": [], "personal_info": [], "patterns": [], "context": []}}
"""


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AgentCore Episodic Memory Manager')
    parser.add_argument('action', choices=['configure', 'retrieve', 'delete', 'summary'])
    parser.add_argument('--user-id', default=None)
    parser.add_argument('--query', default=None)
    parser.add_argument('--retention-days', type=int, default=90)
    
    args = parser.parse_args()
    
    manager = EpisodicMemoryManager()
    
    if args.action == 'configure':
        config = MemoryConfig(
            retention_days=args.retention_days,
            auto_extraction=True
        )
        manager.configure_memory(config)
    elif args.action == 'retrieve':
        if not args.user_id:
            print("Error: --user-id required")
            exit(1)
        memories = manager.retrieve_memories(
            user_id=args.user_id,
            query=args.query
        )
        for m in memories:
            print(f"[{m.memory_type}] {m.content} (score: {m.importance_score})")
    elif args.action == 'delete':
        if not args.user_id:
            print("Error: --user-id required")
            exit(1)
        manager.delete_user_memories(args.user_id)
    elif args.action == 'summary':
        if not args.user_id:
            print("Error: --user-id required")
            exit(1)
        summary = manager.get_user_memory_summary(args.user_id)
        print(json.dumps(summary, indent=2))
```

### Step 2: Update Agent Runtime for Episodic Memory

Add episodic memory integration to `agent_runtime.py`:

```python
# Add to imports
from episodic_memory_config import EpisodicMemoryManager, MemoryAwareAgent

# Add after agent creation
episodic_memory = None
if os.environ.get("AGENTCORE_EPISODIC_MEMORY_ENABLED", "false").lower() == "true":
    try:
        episodic_memory = EpisodicMemoryManager()
        print("✅ Episodic memory enabled")
    except Exception as e:
        print(f"⚠️ Episodic memory not available: {e}")

# In invoke_agent, add memory retrieval
@app.entrypoint
def invoke_agent(payload, context=None):
    user_input = payload.get("prompt", "")
    session_id = payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-actor")
    
    # Retrieve episodic memories if enabled
    memory_context = ""
    if episodic_memory:
        try:
            memories = episodic_memory.retrieve_memories(
                user_id=actor_id,
                query=user_input,
                max_results=5
            )
            if memories:
                memory_context = "\n".join([
                    f"• {m.content}" for m in memories
                ])
        except Exception as e:
            print(f"⚠️ Memory retrieval failed: {e}")
    
    # Add memory context to custom_data
    input_data = {
        "messages": [HumanMessage(content=user_input)],
        "custom_data": {"episodic_memory": memory_context}
    }
    
    # ... rest of invoke logic ...
```

---

## Combined Architecture

### Full Integration Example

```python
"""
Complete integration of Policy, Evaluations, and Memory.

bedrock/integrated_agent.py
"""

import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from policy_config import PolicyManager, AGENT_POLICY
from evaluations_config import EvaluationsManager, EvaluatorType, EvaluatorConfig, AlertConfig
from episodic_memory_config import EpisodicMemoryManager, MemoryConfig
from agent_runtime import create_agent
from langfuse_config import get_langfuse_handler, update_trace_context, flush_langfuse


class IntegratedAgentCore:
    """
    Production-ready agent with Policy, Evaluations, and Memory.
    """
    
    def __init__(self):
        self.agent_runtime_arn = os.environ.get("AGENTCORE_RUNTIME_ARN")
        self.region = os.environ.get("AWS_REGION", "us-west-2")
        
        # Initialize components
        self.agent = create_agent()
        self.policy = PolicyManager(self.agent_runtime_arn, self.region)
        self.evaluations = EvaluationsManager(self.agent_runtime_arn, self.region)
        self.memory = EpisodicMemoryManager(self.agent_runtime_arn, self.region)
    
    def setup(self):
        """One-time setup of all components."""
        
        # 1. Configure Policy
        print("\n📋 Configuring Policy...")
        self.policy.create_or_update_policy(
            policy_name="langgraph-agent-policy",
            policy_definition=AGENT_POLICY
        )
        
        # 2. Configure Evaluations
        print("\n📊 Configuring Evaluations...")
        self.evaluations.configure_evaluations(
            sampling_rate=0.1,  # Evaluate 10% of interactions
            sns_topic_arn=os.environ.get("ALERT_SNS_TOPIC")
        )
        
        # 3. Configure Memory
        print("\n🧠 Configuring Memory...")
        self.memory.configure_memory(MemoryConfig(
            enabled=True,
            retention_days=90,
            require_consent=True,
            auto_extraction=True
        ))
        
        # 4. Create dashboard
        print("\n📈 Creating Dashboard...")
        self.evaluations.create_evaluation_dashboard()
        
        print("\n✅ Setup complete!")
    
    def invoke(self, payload: dict, context=None) -> str:
        """
        Invoke the agent with full integration.
        """
        user_input = payload.get("prompt", "")
        session_id = payload.get("session_id", "default-session")
        actor_id = payload.get("actor_id", "default-actor")
        
        # Step 1: Retrieve episodic memories
        memories = []
        try:
            memories = self.memory.retrieve_memories(
                user_id=actor_id,
                query=user_input,
                max_results=5
            )
        except Exception as e:
            print(f"⚠️ Memory retrieval failed: {e}")
        
        # Step 2: Build enriched input
        memory_context = "\n".join([f"• {m.content}" for m in memories])
        
        input_data = {
            "messages": [HumanMessage(content=user_input)],
            "custom_data": {
                "episodic_memory": memory_context,
                "session_id": session_id,
                "actor_id": actor_id
            }
        }
        
        # Step 3: Setup observability
        langfuse_handler = get_langfuse_handler()
        callbacks = [langfuse_handler] if langfuse_handler else []
        
        if langfuse_handler:
            update_trace_context(
                session_id=session_id,
                user_id=actor_id,
                metadata={
                    "memory_count": len(memories),
                    "request_source": payload.get("source", "api")
                }
            )
        
        # Step 4: Invoke agent (Policy is enforced at Gateway level)
        config = {
            "configurable": {
                "thread_id": session_id,
                "actor_id": actor_id,
            },
            "callbacks": callbacks
        }
        
        try:
            response = self.agent.invoke(input_data, config=config)
            result = response["messages"][-1].content
            
            # Step 5: Extract and store new memories
            self._extract_memories(actor_id, user_input, result)
            
            return result
            
        except PolicyViolationError as e:
            return f"I cannot complete this request: {e.reason}"
        
        finally:
            if langfuse_handler:
                flush_langfuse()
    
    def _extract_memories(self, user_id: str, user_input: str, response: str):
        """Extract and store memories from interaction."""
        try:
            # Simple preference extraction
            if any(p in user_input.lower() for p in ["i prefer", "i like", "i always"]):
                self.memory.store_memory(
                    user_id=user_id,
                    memory_type='user_preferences',
                    content=user_input[:200],
                    importance_score=0.7
                )
        except Exception as e:
            print(f"⚠️ Memory storage failed: {e}")


# Initialize and export
integrated_agent = IntegratedAgentCore()

# For deployment script
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        integrated_agent.setup()
    else:
        print("Usage: python integrated_agent.py setup")
```

---

## Migration Guide

### From Current LangGraphAgentCore to Enhanced Version

#### Step 1: Update Dependencies

```bash
# Add new dependencies
pip install boto3>=1.35.0

# Update requirements.txt
echo "boto3>=1.35.0" >> bedrock/requirements.txt
```

#### Step 2: Add Configuration Files

```bash
cd bedrock

# Create configuration files
touch policy_config.py
touch evaluations_config.py
touch episodic_memory_config.py
```

#### Step 3: Configure Environment

```bash
# Add to .env or deployment configuration
export AGENTCORE_POLICY_ENABLED=true
export AGENTCORE_EVALUATIONS_ENABLED=true
export AGENTCORE_EPISODIC_MEMORY_ENABLED=true
export ALERT_SNS_TOPIC=arn:aws:sns:us-west-2:ACCOUNT:agent-alerts
```

#### Step 4: Run Setup

```bash
# One-time setup
python integrated_agent.py setup
```

#### Step 5: Deploy

```bash
# Rebuild and deploy
./deploy.sh
```

---

## Best Practices

### Policy Best Practices

1. **Start Permissive, Tighten Gradually**
   - Begin with broad policies
   - Monitor violations to identify needed restrictions
   - Add specific rules based on real usage patterns

2. **Use Clear, Unambiguous Language**
   - Avoid vague terms like "sensitive data" without definition
   - Provide examples of allowed/disallowed actions

3. **Test Policies Before Production**
   - Run test interactions against new policies
   - Review violation logs for false positives

### Evaluations Best Practices

1. **Start with Low Sampling**
   - Begin at 5-10% sampling rate
   - Increase as you scale and need more data

2. **Set Appropriate Thresholds**
   - Safety evaluators: Zero tolerance (threshold = 0.0)
   - Correctness evaluators: 85-95% depending on use case
   - Quality evaluators: 70-85% with gradual improvement goals

3. **Alert Fatigue Prevention**
   - Start with fewer alerts, add as needed
   - Use severity levels (P1 for safety, P3 for quality)

### Memory Best Practices

1. **Privacy First**
   - Always require consent for memory storage
   - Provide clear user controls for viewing/deleting memories
   - Implement automatic retention policies

2. **Quality Over Quantity**
   - Filter low-quality memories before storage
   - Use importance scores to prioritize retrieval
   - Periodically clean up stale memories

3. **Memory Retrieval**
   - Limit retrieved memories per request (5-10)
   - Use semantic search for relevance
   - Don't overload context with too much memory

---

## Resources

- [AWS re:Invent 2025 - AgentCore Gateway (AIM3313)](https://www.youtube.com/watch?v=DlIHB8i6uyE)
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Langfuse Integration Guide](./LANGFUSE_DESIGN.md)
- [Memory Support Guide](./MEMORY_SUPPORT.md)
- [Streaming Implementation](./STREAMING_IMPLEMENTATION.md)

---

## Changelog

- **2025-12-08**: Initial document created based on re:Invent 2025 announcements
- Covers Policy (preview), Evaluations (available), Memory enhancements (available)

