import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_certificatemanager as acm,
)
from aws_cdk import (
    aws_cloudfront as cloudfront,
)
from aws_cdk import (
    aws_cloudfront_origins as origins,
)
from aws_cdk import (
    aws_cloudwatch as cloudwatch,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecr_assets as ecr_assets,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_route53 as route53,
)
from aws_cdk import (
    aws_route53_targets as targets,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)
from aws_cdk import (
    aws_sns as sns,
)
from constructs import Construct


class AchievementStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        mode: str = "prod",
        domain_name: str | None = None,
        hosted_zone_name: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        is_ephemeral = mode == "ephemeral"
        data_removal_policy = RemovalPolicy.DESTROY if is_ephemeral else RemovalPolicy.RETAIN
        use_custom_domain = bool(domain_name and hosted_zone_name)

        # --- VPC ---
        # No NAT gateway — tasks run in public subnets with public IPs.
        # Saves ~$32/month. Acceptable for a public-facing app with no
        # internal services to protect.
        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
            ],
        )

        # --- VPC Gateway Endpoints (free) ---
        # Route DynamoDB and S3 traffic through AWS internal network
        # instead of the public internet. Shaves ~50-100ms per call.
        vpc.add_gateway_endpoint(
            "DynamoEndpoint", service=ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )
        vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)

        # --- DNS + TLS (only when a custom domain is configured) ---
        hosted_zone = None
        certificate = None
        if use_custom_domain:
            hosted_zone = route53.HostedZone.from_lookup(
                self,
                "Zone",
                domain_name=hosted_zone_name,
            )
            certificate = acm.Certificate(
                self,
                "Cert",
                domain_name=domain_name,
                validation=acm.CertificateValidation.from_dns(hosted_zone),
            )

        # --- DynamoDB ---
        # Hardcoded table name only in prod (preserves the live `achievements`
        # table). Ephemeral lets CDK auto-name so multiple stacks can coexist.
        table = dynamodb.Table(
            self,
            "AchievementsTable",
            table_name=None if is_ephemeral else "achievements",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.NUMBER),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=data_removal_policy,
        )

        # --- S3 ---
        bucket = s3.Bucket(
            self,
            "AudioBucket",
            removal_policy=data_removal_policy,
            auto_delete_objects=is_ephemeral,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(90),
                        ),
                    ],
                ),
            ],
        )

        # --- CloudFront CDN for S3 audio ---
        # Edge-cached audio delivery — faster downloads globally, free at low volume.
        cdn = cloudfront.Distribution(
            self,
            "AudioCdn",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
        )

        # --- Secrets ---
        # Prod: reference pre-existing secrets by name (must be created first
        # via `make bootstrap` or `make set-secrets`).
        # Ephemeral: CDK creates fresh secrets with placeholder values that
        # the user updates post-deploy via `make set-secrets-ephemeral`.
        if is_ephemeral:
            anthropic_secret = secretsmanager.Secret(
                self,
                "AnthropicKey",
                description="Anthropic API key (placeholder — set after deploy)",
                secret_string_value=cdk.SecretValue.unsafe_plain_text("placeholder"),
                removal_policy=RemovalPolicy.DESTROY,
            )
            elevenlabs_secret = secretsmanager.Secret(
                self,
                "ElevenLabsKey",
                description="ElevenLabs API key (placeholder)",
                secret_string_value=cdk.SecretValue.unsafe_plain_text("placeholder"),
                removal_policy=RemovalPolicy.DESTROY,
            )
            elevenlabs_voice_secret = secretsmanager.Secret(
                self,
                "ElevenLabsVoice",
                description="ElevenLabs voice ID (placeholder)",
                secret_string_value=cdk.SecretValue.unsafe_plain_text("placeholder"),
                removal_policy=RemovalPolicy.DESTROY,
            )
        else:
            anthropic_secret = secretsmanager.Secret.from_secret_name_v2(
                self,
                "AnthropicKey",
                "achievement-intercom/anthropic-api-key",
            )
            elevenlabs_secret = secretsmanager.Secret.from_secret_name_v2(
                self,
                "ElevenLabsKey",
                "achievement-intercom/elevenlabs-api-key",
            )
            elevenlabs_voice_secret = secretsmanager.Secret.from_secret_name_v2(
                self,
                "ElevenLabsVoice",
                "achievement-intercom/elevenlabs-voice-id",
            )

        # --- Docker Image ---
        image_asset = ecr_assets.DockerImageAsset(
            self,
            "AppImage",
            directory="..",
            platform=ecr_assets.Platform.LINUX_AMD64,
            exclude=[
                "cdk",
                "finetune_data",
                "finetune_output",
                ".venv",
                "reference_audio",
                "transcripts",
                "original_source",
                "output",
                ".git",
                "__pycache__",
            ],
        )

        # --- ECS Cluster ---
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        # --- Task Definition ---
        task_def = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=1024,
            memory_limit_mib=2048,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.X86_64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        # Grant DynamoDB + S3 access to task role
        table.grant_read_write_data(task_def.task_role)
        bucket.grant_read_write(task_def.task_role)

        # --- Container ---
        log_group = logs.LogGroup(
            self,
            "Logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        task_def.add_container(
            "App",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            logging=ecs.LogDrivers.aws_logs(
                log_group=log_group,
                stream_prefix="achievement",
            ),
            environment={
                "MODEL": "claude-sonnet-4-6",
                "MAX_TOKENS": "400",
                "STORAGE_MODE": "cloud",
                "DYNAMODB_TABLE": table.table_name,
                "S3_BUCKET": bucket.bucket_name,
                "CDN_DOMAIN": cdn.distribution_domain_name,
                "OUTPUT_DIR": "/tmp/output",
            },
            secrets={
                "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(anthropic_secret),
                "ELEVENLABS_API_KEY": ecs.Secret.from_secrets_manager(elevenlabs_secret),
                "ELEVENLABS_VOICE_ID": ecs.Secret.from_secrets_manager(elevenlabs_voice_secret),
            },
            port_mappings=[ecs.PortMapping(container_port=8000)],
        )

        # --- ALB + Fargate Service ---
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=vpc,
            internet_facing=True,
            idle_timeout=Duration.seconds(120),
        )

        service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            assign_public_ip=True,
            platform_version=ecs.FargatePlatformVersion.LATEST,
        )

        health_check = elbv2.HealthCheck(
            path="/health",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        if certificate is not None:
            # HTTP → HTTPS redirect
            alb.add_listener(
                "HttpRedirect",
                port=80,
                default_action=elbv2.ListenerAction.redirect(
                    protocol="HTTPS",
                    port="443",
                    permanent=True,
                ),
            )
            # HTTPS listener with cert
            https_listener = alb.add_listener(
                "HttpsListener",
                port=443,
                certificates=[certificate],
            )
            https_listener.add_targets(
                "EcsTarget",
                port=8000,
                targets=[service],
                health_check=health_check,
            )
        else:
            # No cert / no custom domain — HTTP only.
            http_listener = alb.add_listener("HttpListener", port=80)
            http_listener.add_targets(
                "EcsTarget",
                port=8000,
                targets=[service],
                health_check=health_check,
            )

        # --- DNS Record ---
        if use_custom_domain and hosted_zone is not None:
            route53.ARecord(
                self,
                "DnsRecord",
                zone=hosted_zone,
                record_name=domain_name.split(".")[0],
                target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb)),
            )

        # --- CloudWatch Dashboard ---
        # Suffix the dashboard name in ephemeral so it doesn't collide with prod.
        dashboard_name = (
            "CrawlLog-Operations"
            if not is_ephemeral
            else f"CrawlLog-Operations-{construct_id}"
        )
        dashboard = cloudwatch.Dashboard(
            self,
            "OperationsDashboard",
            dashboard_name=dashboard_name,
        )

        # API latency — ALB target response time
        alb_latency = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="TargetResponseTime",
            dimensions_map={"LoadBalancer": alb.load_balancer_full_name},
            statistic="avg",
            period=Duration.minutes(5),
        )

        # Request count
        alb_requests = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="RequestCount",
            dimensions_map={"LoadBalancer": alb.load_balancer_full_name},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # HTTP 4xx/5xx errors
        alb_4xx = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="HTTPCode_Target_4XX_Count",
            dimensions_map={"LoadBalancer": alb.load_balancer_full_name},
            statistic="Sum",
            period=Duration.minutes(5),
        )
        alb_5xx = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="HTTPCode_Target_5XX_Count",
            dimensions_map={"LoadBalancer": alb.load_balancer_full_name},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # ECS CPU and memory
        ecs_cpu = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="CPUUtilization",
            dimensions_map={
                "ClusterName": cluster.cluster_name,
                "ServiceName": service.service_name,
            },
            statistic="avg",
            period=Duration.minutes(5),
        )
        ecs_memory = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="MemoryUtilization",
            dimensions_map={
                "ClusterName": cluster.cluster_name,
                "ServiceName": service.service_name,
            },
            statistic="avg",
            period=Duration.minutes(5),
        )

        # DynamoDB read/write capacity
        dynamo_reads = table.metric_consumed_read_capacity_units(
            period=Duration.minutes(5),
        )
        dynamo_writes = table.metric_consumed_write_capacity_units(
            period=Duration.minutes(5),
        )

        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="API Latency (avg response time)",
                left=[alb_latency],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="Request Count",
                left=[alb_requests],
                width=12,
            ),
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="HTTP Errors",
                left=[alb_4xx, alb_5xx],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="ECS CPU & Memory",
                left=[ecs_cpu],
                right=[ecs_memory],
                width=12,
            ),
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="DynamoDB Capacity",
                left=[dynamo_reads, dynamo_writes],
                width=12,
            ),
            cloudwatch.LogQueryWidget(
                title="Generator Retries (last 24h)",
                log_group_names=[log_group.log_group_name],
                query_lines=[
                    "fields @timestamp, @message",
                    "filter @message like /Banned content detected|Generation succeeded on attempt/",
                    "sort @timestamp desc",
                    "limit 50",
                ],
                width=12,
            ),
        )

        # --- Billing Alarm (prod only — account-wide signal) ---
        if not is_ephemeral:
            sns.Topic(self, "BillingAlertTopic")
            cloudwatch.Alarm(
                self,
                "BillingAlarm",
                metric=cloudwatch.Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    dimensions_map={"Currency": "USD"},
                    statistic="Maximum",
                    period=Duration.hours(6),
                ),
                threshold=75,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_description="Monthly AWS spend exceeded $75",
            )

        # --- Outputs ---
        if use_custom_domain:
            cdk.CfnOutput(self, "Url", value=f"https://{domain_name}")
        else:
            cdk.CfnOutput(self, "Url", value=f"http://{alb.load_balancer_dns_name}")
        cdk.CfnOutput(self, "TableName", value=table.table_name)
        cdk.CfnOutput(self, "BucketName", value=bucket.bucket_name)
        cdk.CfnOutput(self, "CdnDomain", value=cdn.distribution_domain_name)
        cdk.CfnOutput(self, "AlbDns", value=alb.load_balancer_dns_name)
        if is_ephemeral:
            cdk.CfnOutput(self, "AnthropicSecretArn", value=anthropic_secret.secret_arn)
            cdk.CfnOutput(self, "ElevenLabsSecretArn", value=elevenlabs_secret.secret_arn)
            cdk.CfnOutput(
                self, "ElevenLabsVoiceSecretArn", value=elevenlabs_voice_secret.secret_arn
            )
            cdk.CfnOutput(self, "ServiceName", value=service.service_name)
            cdk.CfnOutput(self, "ClusterName", value=cluster.cluster_name)
