from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_logs as logs,
    aws_iam as iam,
)

import os

class EcsStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, cluster: ecs.Cluster, application_name: str, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        # ECS role attach
        self.ecs_principle = iam.ServicePrincipal('ecs-tasks.amazonaws.com')

        self.execution_role = iam.Role(
            self,
            'execution-role',
            assumed_by = self.ecs_principle
        )

        self.execution_role.add_managed_policy(
            policy = iam.ManagedPolicy.from_aws_managed_policy_name(
                managed_policy_name = 'AmazonEC2ContainerRegistryReadOnly'
            )
        )

        self.task_role = iam.Role(
            self,
            'task-role',
            assumed_by = self.ecs_principle
        )

        self.task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                managed_policy_name = 'service-role/AmazonECSTaskExecutionRolePolicy'
            )
        )

        ## logging setup
        self.log_group = logs.LogGroup(
            self,
            '/ecs/colorteller',
            retention = logs.RetentionDays.ONE_DAY,
            removal_policy = core.RemovalPolicy.DESTROY
        )

        self.web_ecs_logs = ecs.LogDriver.aws_logs(
            log_group = self.log_group,
            stream_prefix = '{name_space}-web'.format(name_space=application_name)
        )

        self.app_ecs_logs = ecs.LogDriver.aws_logs(
            log_group = self.log_group,
            stream_prefix = '{name_space}-app'.format(name_space=application_name)
        )

        ## task definitions
        self.taskdef = ecs.FargateTaskDefinition(
            self,
            '{name_space}_task'.format(name_space=application_name),
            execution_role = self.execution_role,
            task_role = self.task_role,
        )

        self.taskdef.add_container(
            'web',
            # cpu=512,
            # memory_limit_mib=1024,
            logging = self.web_ecs_logs,
            image = ecs.ContainerImage.from_registry(
                '{account_id}.dkr.ecr.ap-northeast-1.amazonaws.com/{name_space}/web'.format(
                    account_id = os.getenv('AWS_ACCOUNT_ID'),
                    name_space = application_name
                )
            )
        ).add_port_mappings(
            ecs.PortMapping(
                container_port = 80,
                protocol = ecs.Protocol.TCP
            )
        )

        self.taskdef.add_container(
            'app',
            # cpu=1024,
            # memory_limit_mib=1024,
            logging = self.app_ecs_logs,
            image = ecs.ContainerImage.from_registry(
                '{account_id}.dkr.ecr.ap-northeast-1.amazonaws.com/{name_space}/app'.format(
                    account_id = os.getenv('AWS_ACCOUNT_ID'),
                    name_space = application_name
                )
            )
        ).add_port_mappings(
            ecs.PortMapping(
                container_port = 9000,
                protocol = ecs.Protocol.TCP
            )
        )

        ## service
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            application_name,
            cluster = cluster,
            cpu = 1024, # 1 CPU
            memory_limit_mib = 2048, # 2GB RAM
            desired_count = 1,
            task_definition = self.taskdef,
        )


        ## service auto scaling

        self.fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer = ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection = ec2.Port.tcp(9000),
            description = 'Allow 9000 inbound from SG'
        )
        # Setup AutoScaling policy
        # memory utilization setup
        self.scaling =self.fargate_service.service.auto_scale_task_count(
            min_capacity = 1,
            max_capacity = 10
        )
        self.scaling.scale_on_cpu_utilization(
            'CpuScaling',
            target_utilization_percent = 60,
            scale_in_cooldown = core.Duration.seconds(60),
            scale_out_cooldown = core.Duration.seconds(60),
        )
        self.scaling.scale_on_memory_utilization(
            'MemoryScaling',
            target_utilization_percent =80,
            scale_in_cooldown = core.Duration.seconds(60),
            scale_out_cooldown = core.Duration.seconds(60),
        )

        # grant permissions
        # table.grant_read_write_data(taskdef.task_role)
        self.taskdef.add_to_task_role_policy(
            iam.PolicyStatement(
                effect = iam.Effect.ALLOW,
                resources = ['*'],
                actions = ['ssm:GetParameter']
            )
        )
        self.taskdef.add_to_task_role_policy(
            iam.PolicyStatement(
                effect = iam.Effect.ALLOW,
                resources =  ['*'],
                actions = [
                's3:GetObject',
                's3:PutObject',
                's3:ListBucket',
                's3:ListAllMyBuckets'
                ]
            )
        )
