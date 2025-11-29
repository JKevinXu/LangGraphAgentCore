#!/usr/bin/env python3
"""CDK App for BFF infrastructure."""
import os
import aws_cdk as cdk
from stacks.bff_stack import BffStack

app = cdk.App()

# Get configuration from context or environment
region = app.node.try_get_context("region") or os.environ.get("AWS_REGION", "us-west-2")
agent_runtime_arn = app.node.try_get_context("agent_runtime_arn") or os.environ.get("AGENT_RUNTIME_ARN", "")
domain_name = app.node.try_get_context("domain_name")

BffStack(
    app,
    "LangGraphBffStack",
    env=cdk.Environment(region=region),
    agent_runtime_arn=agent_runtime_arn,
    domain_name=domain_name,
)

app.synth()

