# AgentCore re:Invent 2025: New Features Integration Guide

This guide provides an overview of the three major capabilities announced at AWS re:Invent 2025—**Policy**, **Evaluations**, and **Memory**—and how they integrate with LangGraphAgentCore.

---

## Executive Summary

| Feature | Purpose | Status | Key Benefit |
|---------|---------|--------|-------------|
| **Policy** | Natural language operational boundaries | Preview | Governance without code |
| **Evaluations** | 13 pre-built agent performance monitors | Available | Out-of-the-box quality monitoring |
| **Memory** | Episodic memory for personalization | Available | Agents that learn and remember |

**Bottom Line**: These features address the #1 blocker for enterprise AI adoption—trust and control.

---

## Policy in AgentCore

### What It Does

Policy enables developers to define what an agent can and cannot do using **natural language** instead of code or complex IAM policies.

### Key Capabilities

- **Natural Language Rules**: Write policies in plain English
- **Gateway Enforcement**: Policies intercept every agent action automatically  
- **Violation Logging**: All blocked actions are logged for audit
- **Human Escalation**: Define triggers for human review

### Example Policy Structure

```
This agent assists with customer inquiries.

Restrictions:
- Only access data for the authenticated customer
- Cannot process refunds over $200 without approval
- Must not store payment information in memory

Escalation Triggers:
- Billing disputes
- Account security concerns
```

### Integration Points

| Integration | Description |
|-------------|-------------|
| AgentCore Gateway | Automatic enforcement layer |
| CloudWatch Logs | Violation audit trail |
| SNS | Real-time violation alerts |

### References

- [AWS re:Invent 2025 - Scale agent tools with Amazon Bedrock AgentCore Gateway (AIM3313)](https://www.youtube.com/watch?v=DlIHB8i6uyE)
- [AgentCore Gateway Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)

---

## AgentCore Evaluations

### What It Does

Provides 13 pre-built evaluation systems that continuously monitor agent behavior across correctness, safety, and quality dimensions.

### The 13 Evaluators

**Correctness (5)**
| Evaluator | Measures |
|-----------|----------|
| Task Completion | Did the agent complete the user's request? |
| Response Accuracy | Is the information factually correct? |
| Instruction Following | Does the agent follow its system prompt? |
| Tool Selection Accuracy | Did the agent choose the right tools? |
| Tool Usage Correctness | Were tools called with correct parameters? |

**Safety (4)**
| Evaluator | Measures |
|-----------|----------|
| Harmful Content | Inappropriate or dangerous content |
| PII Exposure | Personal information leakage |
| Prompt Injection | Adversarial input detection |
| Off-Topic | Domain boundary violations |

**Quality (4)**
| Evaluator | Measures |
|-----------|----------|
| Response Relevance | Does the response address the question? |
| Response Coherence | Is the response well-structured? |
| Groundedness | Are claims supported by sources? |
| Tone Appropriateness | Does tone match expectations? |

### How It Works

1. **Sampling**: Configurable percentage of interactions evaluated (e.g., 10%)
2. **Parallel Assessment**: Multiple evaluators run simultaneously
3. **Threshold Alerts**: Get notified when scores drop below thresholds
4. **Dashboard**: View trends and drill into specific failures

### Recommended Thresholds

| Category | Threshold | Rationale |
|----------|-----------|-----------|
| Safety evaluators | 0.0 (zero tolerance) | No harmful content acceptable |
| Task completion | 0.85 | Allow for edge cases |
| Tool accuracy | 0.90 | High bar for reliability |
| Quality metrics | 0.75 | Baseline with improvement goals |

### Integration Points

| Integration | Description |
|-------------|-------------|
| CloudWatch Metrics | Real-time monitoring |
| CloudWatch Dashboard | Visualization |
| SNS Alerts | Threshold notifications |
| Langfuse (optional) | Unified observability |

### References

- [AgentCore Evaluations Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html)
- [CloudWatch Integration Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/)

---

## AgentCore Memory

### What It Does

Enables agents to retain and utilize information from past interactions, transforming stateless tools into personalized assistants.

### Memory Types

| Type | Description | Example |
|------|-------------|---------|
| **User Preferences** | Settings and choices | "Prefers window seats" |
| **Interaction History** | Past conversation context | "Discussed Project Alpha on Dec 5" |
| **Learned Behaviors** | Patterns observed over time | "Usually needs Python examples" |

### How It Works

1. **Interaction Logging**: Conversations automatically logged
2. **Memory Extraction**: System identifies memorable information
3. **Memory Storage**: Stored with user context and timestamps
4. **Memory Retrieval**: Relevant memories surfaced in future sessions
5. **Memory Decay**: Old/unused memories deprioritized

### Privacy Controls

| Control | Description |
|---------|-------------|
| **Consent** | Require opt-in for memory collection |
| **Visibility** | Users can view stored memories |
| **Deletion** | Users can request memory deletion (GDPR) |
| **Retention** | Automatic expiration policies |
| **Scope Limits** | Restrict memorizable information types |

### Integration with LangGraphAgentCore

LangGraphAgentCore already uses `AgentCoreMemorySaver` for short-term memory:

| Current | Enhanced (re:Invent 2025) |
|---------|---------------------------|
| Session-based memory | Cross-session episodic memory |
| Conversation history | User preferences + learned behaviors |
| Thread-scoped | User-scoped with privacy controls |

### References

- [AgentCore Memory Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- [LangGraph Checkpoint Documentation](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [MEMORY_SUPPORT.md](./MEMORY_SUPPORT.md) - Current implementation guide

---

## Combined Architecture

### How Features Work Together

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AgentCore Gateway                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Policy    │  │   Memory    │  │ Evaluations │         │
│  │ Enforcement │  │  Retrieval  │  │   Sampling  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AgentCore Runtime                          │
│          (LangGraph + Bedrock + Tools + Langfuse)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Tool Execution                           │
│        (APIs, databases via AgentCore Gateway)               │
└─────────────────────────────────────────────────────────────┘
```

### Enterprise Example: Customer Service Agent

| Feature | Configuration |
|---------|---------------|
| **Policy** | "Only access customer's own data, max $100 refunds, escalate billing disputes" |
| **Memory** | Remember contact preferences, track ongoing cases, note communication style |
| **Evaluations** | Monitor resolution rate, track policy violations, measure satisfaction |

---

## Early Adopter Results

Organizations shared their AgentCore experiences at re:Invent 2025:

| Organization | Result |
|--------------|--------|
| **Cox Automotive** | Scaled from experimentation to production in one month |
| **PGA TOUR** | Major improvements in content generation speed |
| **MongoDB** | Reduced operational complexity with managed infrastructure |

---

## Getting Started Checklist

### Prerequisites

- [ ] AWS Account with Bedrock access
- [ ] AgentCore enabled in your region (us-west-2, us-east-1)
- [ ] Existing agent runtime deployed
- [ ] IAM permissions for Policy, Evaluations, Memory APIs

### Setup Steps

1. **Enable Features in Console**
   - Navigate to Bedrock AgentCore in AWS Console
   - Enable Policy, Evaluations, Memory for your runtime

2. **Configure Policy** (Preview)
   - Define natural language boundaries
   - Test with sample interactions
   - Monitor violation logs

3. **Configure Evaluations**
   - Select evaluators to enable
   - Set sampling rate (start with 10%)
   - Configure alert thresholds

4. **Configure Memory**
   - Enable episodic memory
   - Set retention policies
   - Configure consent requirements

5. **Monitor & Iterate**
   - Review CloudWatch dashboards
   - Analyze evaluation trends
   - Refine policies based on violations

---

## Best Practices Summary

### Policy

| Practice | Why |
|----------|-----|
| Start permissive, tighten gradually | Avoid blocking legitimate use cases |
| Use clear, unambiguous language | Reduce false positives |
| Include examples in policy | Help enforcement accuracy |
| Test before production | Catch issues early |

### Evaluations

| Practice | Why |
|----------|-----|
| Start with low sampling (5-10%) | Reduce cost while learning |
| Zero tolerance for safety | No compromise on harmful content |
| Create dashboards early | Establish baselines |
| Integrate with existing observability | Unified monitoring |

### Memory

| Practice | Why |
|----------|-----|
| Always require consent | Privacy compliance |
| Implement deletion workflows | GDPR/CCPA requirements |
| Quality over quantity | Better retrieval relevance |
| Set retention policies | Control storage costs |

---

## References & Resources

### AWS Documentation

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Gateway Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [Response Streaming Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html)

### re:Invent 2025 Sessions

- [AIM3313: Scale agent tools with Amazon Bedrock AgentCore Gateway](https://www.youtube.com/watch?v=DlIHB8i6uyE)
- [AWS News: re:Invent 2025 AI Updates](https://www.aboutamazon.com/news/aws/aws-re-invent-2025-ai-news-updates)

### Third-Party Resources

- [TechCrunch: AWS announces new capabilities for its AI agent builder](https://techcrunch.com/2025/12/02/aws-announces-new-capabilities-for-its-ai-agent-builder/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Langfuse Observability](https://langfuse.com/docs)

### LangGraphAgentCore Documentation

- [README.md](./README.md) - Project overview
- [MEMORY_SUPPORT.md](./MEMORY_SUPPORT.md) - Current memory implementation
- [STREAMING_IMPLEMENTATION.md](./STREAMING_IMPLEMENTATION.md) - Streaming architecture
- [LANGFUSE_DESIGN.md](./LANGFUSE_DESIGN.md) - Observability integration

### AWS SDKs

- [boto3 bedrock-agentcore](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore.html)
- [AWS SDK for Python (Boto3)](https://aws.amazon.com/sdk-for-python/)

---

## What's Next

Based on re:Invent announcements, expect continued investment in:

| Capability | Description |
|------------|-------------|
| Multi-agent orchestration | Coordinating multiple specialized agents |
| Policy templates | Industry-specific compliance frameworks |
| Enhanced observability | Deeper CloudWatch and X-Ray integration |
| Cross-account sharing | Deploy agents across organizational boundaries |

---

*Document created: December 2025*  
*Based on AWS re:Invent 2025 announcements*
