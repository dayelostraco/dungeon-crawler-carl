from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_efs as efs,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
)


class AchievementStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- VPC ---
        vpc = ec2.Vpc(
            self, "Vpc",
            max_azs=2,
            nat_gateways=1,
        )

        # --- DNS + TLS ---
        domain_name = "achievement.sigilark.com"

        hosted_zone = route53.HostedZone.from_lookup(
            self, "Zone",
            domain_name="sigilark.com",
        )

        certificate = acm.Certificate(
            self, "Cert",
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone),
        )

        # --- EFS ---
        file_system = efs.FileSystem(
            self, "DataFs",
            vpc=vpc,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_30_DAYS,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
        )

        access_point = file_system.add_access_point(
            "DataAccessPoint",
            path="/achievement-data",
            create_acl=efs.Acl(owner_uid="1000", owner_gid="1000", permissions="755"),
            posix_user=efs.PosixUser(uid="1000", gid="1000"),
        )

        # --- Secrets Manager (pre-created, referenced by name) ---
        anthropic_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "AnthropicKey", "achievement-intercom/anthropic-api-key",
        )
        elevenlabs_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "ElevenLabsKey", "achievement-intercom/elevenlabs-api-key",
        )
        elevenlabs_voice_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "ElevenLabsVoice", "achievement-intercom/elevenlabs-voice-id",
        )

        # --- Docker Image ---
        image_asset = ecr_assets.DockerImageAsset(
            self, "AppImage",
            directory="..",  # repo root (where Dockerfile lives)
            exclude=["cdk", "finetune_data", "finetune_output", ".venv",
                      "reference_audio", "transcripts", "original_source",
                      "output", ".git", "__pycache__"],
        )

        # --- ECS Cluster ---
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        # --- Task Definition ---
        task_def = ecs.FargateTaskDefinition(
            self, "TaskDef",
            cpu=512,       # 0.5 vCPU
            memory_limit_mib=1024,  # 1 GB
        )

        # EFS volume
        task_def.add_volume(
            name="data-volume",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point.access_point_id,
                    iam="ENABLED",
                ),
            ),
        )

        # Grant EFS access to task role
        file_system.grant_root_access(task_def.task_role)

        # --- Container ---
        log_group = logs.LogGroup(
            self, "Logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        container = task_def.add_container(
            "App",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            logging=ecs.LogDrivers.aws_logs(
                log_group=log_group,
                stream_prefix="achievement",
            ),
            environment={
                "MODEL": "claude-opus-4-5",
                "MAX_TOKENS": "400",
                "OUTPUT_DIR": "/app/data/output",
                "ARCHIVE_FILE": "/app/data/achievements.json",
            },
            secrets={
                "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(anthropic_secret),
                "ELEVENLABS_API_KEY": ecs.Secret.from_secrets_manager(elevenlabs_secret),
                "ELEVENLABS_VOICE_ID": ecs.Secret.from_secrets_manager(elevenlabs_voice_secret),
            },
            port_mappings=[ecs.PortMapping(container_port=8000)],
        )

        container.add_mount_points(
            ecs.MountPoint(
                container_path="/app/data",
                source_volume="data-volume",
                read_only=False,
            ),
        )

        # --- ALB + Fargate Service ---
        alb = elbv2.ApplicationLoadBalancer(
            self, "Alb",
            vpc=vpc,
            internet_facing=True,
        )

        service = ecs.FargateService(
            self, "Service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            assign_public_ip=False,
            platform_version=ecs.FargatePlatformVersion.LATEST,
        )

        # Allow EFS access from ECS tasks
        file_system.connections.allow_default_port_from(service)

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

        # HTTPS listener with TLS
        https_listener = alb.add_listener(
            "HttpsListener",
            port=443,
            certificates=[certificate],
        )
        https_listener.add_targets(
            "EcsTarget",
            port=8000,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path="/api/achievements",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
        )

        # --- DNS Record ---
        route53.ARecord(
            self, "DnsRecord",
            zone=hosted_zone,
            record_name="achievement",
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb)),
        )

        # --- Outputs ---
        cdk.CfnOutput(self, "Url", value=f"https://{domain_name}")
        cdk.CfnOutput(self, "AlbDns", value=alb.load_balancer_dns_name)
        cdk.CfnOutput(self, "EfsId", value=file_system.file_system_id)
