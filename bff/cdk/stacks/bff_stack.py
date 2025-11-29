"""
BFF Stack - ECS Fargate with ALB

Deploys BFF as a thin API router to Bedrock AgentCore.
"""
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
)
from constructs import Construct
from typing import Optional


class BffStack(Stack):
    """CDK Stack for BFF Service."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_runtime_arn: str,
        domain_name: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
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

        # API Keys secret (optional)
        api_keys_secret = secretsmanager.Secret(
            self, "ApiKeysSecret",
            secret_name="langgraph-bff/api-keys",
            description="API keys for BFF authentication (comma-separated)"
        )

        # ECS Cluster
        cluster = ecs.Cluster(
            self, "BffCluster",
            vpc=vpc,
            cluster_name="langgraph-bff-cluster",
            container_insights=True
        )

        # Docker image from local Dockerfile
        docker_image = ecr_assets.DockerImageAsset(
            self, "BffImage",
            directory="../",
            file="Dockerfile"
        )

        # Task Role for Bedrock access
        task_role = iam.Role(
            self, "BffTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # Grant Bedrock AgentCore access
        if agent_runtime_arn:
            task_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:InvokeAgentRuntime",
                    "bedrock-agentcore:GetAgentRuntime"
                ],
                resources=[agent_runtime_arn, f"{agent_runtime_arn}/*"]
            ))

        # Log Group
        log_group = logs.LogGroup(
            self, "BffLogGroup",
            log_group_name="/aws/ecs/langgraph-bff",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Fargate Service with ALB
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "BffService",
            cluster=cluster,
            service_name="langgraph-bff-service",
            cpu=256,
            memory_limit_mib=512,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(docker_image),
                container_port=8000,
                container_name="bff",
                task_role=task_role,
                environment={
                    "AWS_REGION": self.region,
                    "AGENT_RUNTIME_ARN": agent_runtime_arn or "",
                    "LOG_LEVEL": "INFO"
                },
                secrets={
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
            health_check_grace_period=Duration.seconds(60)
        )

        # Health check
        fargate_service.target_group.configure_health_check(
            path="/health",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3
        )

        # Auto scaling
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

        # Outputs
        CfnOutput(self, "LoadBalancerDns",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="ALB DNS name"
        )

        CfnOutput(self, "ServiceUrl",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description="BFF Service URL"
        )

        CfnOutput(self, "HealthEndpoint",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}/health",
            description="Health check endpoint"
        )

        CfnOutput(self, "ChatEndpoint",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}/v1/chat",
            description="Chat API endpoint"
        )

