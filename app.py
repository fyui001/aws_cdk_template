from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_logs,
    aws_ecr as ecr,
    aws_rds as rds,
    aws_s3 as s3,
    aws_kms as kms,
    aws_route53 as route53,
)

import os
from dotenv import load_dotenv

from stacks.CodepipelineStack import CodepipelineStack

class AutoScalingFargateService(core.Stack):

    def __init__(self, scope: core.App, name: str, **kwargs) -> None:
        super().__init__(scope, name, **kwargs)

        # vpc create
        vpc = ec2.Vpc(
            self,
            '{project_name}-VPC'.format(project_name=os.getenv('PROJECT_NAME')),
            max_azs=2,
            cidr=os.getenv('AWS_VPC_CIDR'),
        )

        vpc.add_gateway_endpoint(
            's3endpoint',
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        cluster = ecs.Cluster(
            self,
            'Cluster',
            cluster_name='{project_name}-ecs-cluster'.format(project_name=os.getenv('PROJECT_NAME')),
            vpc=vpc,
        )

        sg_db = ec2.SecurityGroup(
            self,
            'RDSSG',
            vpc=vpc,
            allow_all_outbound=True,
            description='Allow DS access Security Group'
        )
        sg_db.add_ingress_rule(
            peer=ec2.Peer.ipv4('182.171.74.66/32'),
            connection = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description='Allow MySQL access from Dimageshare'
        )
        sg_db.add_ingress_rule(
            peer = ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description='Allow MySQL access from ECS'
        )

        '''key_db = kms.Key.from_key_arn(
            self,
            'key_db',
            key_arn='arn:aws:kms:ap-northeast-1:170013962578:key/9b4d3b78-0b37-4f84-a086-983634575975'
        )'''

        mysql = rds.DatabaseInstance(
            self,
            '{project_name}-RDS'.format(project_name=os.getenv('PROJECT_NAME')),
            master_username=os.getenv('DB_USERNAME'),
            master_user_password=core.SecretValue.plain_text(os.getenv('DB_PASSWORD')),
            database_name=os.getenv('DB_DATABASE'),
            engine=rds.DatabaseInstanceEngine.MYSQL,
            vpc=vpc,
            ## public accessibility　パブリックアクセシビリティをyesにする設定値がないためvpc_lacementで設定
            ## public ip attached　RDSにパブリックIPを付与する設定
            vpc_placement={
                'subnet_type': ec2.SubnetType.PUBLIC
            },
            port=int(os.getenv('DB_PORT')),
            instance_identifier='{project_name}-MYSQL'.format(project_name=os.getenv('PROJECT_NAME')),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO),
            removal_policy=core.RemovalPolicy.DESTROY,
            deletion_protection=False,
            cloudwatch_logs_exports=['error', 'general', 'slowquery'],
        )

        mysql.connections.allow_from(
            sg_db,
            port_range = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description = 'Allow MySQL access from Query Lambda (because Aurora actually exposes PostgreSQL/MySQL on port 3306)'
        )

        ### コードビルドstack ###
        print(mysql.db_instance_endpoint_address)
        CodepipelineStack(
            scope,
            id = 'CodepipelineStack',
            rds_endpoint = mysql.db_instance_endpoint_address
        )

        ########################

        # ECS role attach
        ecs_principle = iam.ServicePrincipal('ecs-tasks.amazonaws.com')

        execution_role = iam.Role(
            self,
            'execution-role',
            assumed_by=ecs_principle
        )
        execution_role.add_managed_policy(policy = iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='AmazonEC2ContainerRegistryReadOnly')
        )
        task_role = iam.Role(
            self,
            'task-role',
            assumed_by=ecs_principle
        )

        task_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(
            managed_policy_name='service-role/AmazonECSTaskExecutionRolePolicy')
        )


        ## logging setup
        '''log_group = aws_logs.LogGroup(
            self,
            '/ecs/colorteller',
            retention=aws_logs.RetentionDays.ONE_DAY,
            removal_policy=core.RemovalPolicy.DESTROY
        )

        web_ecs_logs = ecs.LogDriver.aws_logs(
            log_group=log_group,
            stream_prefix='{name_space}-web'.format(name_space=os.getenv('ADMIN_APPLICATION_NAMESPACE'))
        )

        app_ecs_logs = ecs.LogDriver.aws_logs(
            log_group=log_group,
            stream_prefix='{name_space}-app'.format(name_space=os.getenv('ADMIN_APPLICATION_NAMESPACE'))
        )'''

        api_log_group = aws_logs.LogGroup(
            self, '/ecs/colorteller-api',
            retention=aws_logs.RetentionDays.ONE_DAY,
            removal_policy=core.RemovalPolicy.DESTROY
        )
        api_web_ecs_logs = ecs.LogDriver.aws_logs(
            log_group=api_log_group,
            stream_prefix='{name_space}-web'.format(name_space=os.getenv('API_APPLICATION_NAMESPACE'))
        )
        api_app_ecs_logs = ecs.LogDriver.aws_logs(
            log_group=api_log_group,
            stream_prefix='{name_space}-app'.format(name_space=os.getenv('API_APPLICATION_NAMESPACE'))
        )


        ## ECR repository create

        # admin
        '''ecr.Repository(
            self,
            'WebImageRepository',
            image_scan_on_push=True,
            repository_name='{name_space}/web'.format(name_space=os.getenv('ADMIN_APPLICATION_NAMESPACE'))
        )

        ecr.Repository(
            self,
            'AppImageRepository',
            image_scan_on_push=True,
            repository_name='{name_space}/app'.format(name_space=os.getenv('ADMIN_APPLICATION_NAMESPACE'))
        )'''

        # api
        ecr.Repository(
            self,
            'WebImageRepository',
            image_scan_on_push=True,
            repository_name='{name_space}/web'.format(name_space=os.getenv('API_APPLICATION_NAMESPACE'))
        )

        ecr.Repository(
            self,
            'AppImageRepository',
            image_scan_on_push=True,
            repository_name='{name_space}/app'.format(name_space=os.getenv('API_APPLICATION_NAMESPACE'))
        )

        # Application Load Balancer

        ## task definitions
        # admin
        '''taskdef = ecs.FargateTaskDefinition(
            self,
            '{name_space}_task'.format(name_space=os.getenv('ADMIN_APPLICATION_NAMESPACE')),
            execution_role=execution_role,
            task_role=task_role,
        )

        taskdef.add_container(
            'web',
            # cpu=512,
            # memory_limit_mib=1024,
            logging=web_ecs_logs,
            image=ecs.ContainerImage.from_registry(
                '{account_id}.dkr.ecr.ap-northeast-1.amazonaws.com/{name_space}/web'.format(
                    account_id = os.getenv('AWS_ACCOUNT_ID'),
                    name_space = os.getenv('ADMIN_APPLICATION_NAMESPACE')
                )
            )
        ).add_port_mappings(
            ecs.PortMapping(
                container_port=80,
                protocol=ecs.Protocol.TCP
            )
        )

        taskdef.add_container(
            'app',
            # cpu=1024,
            # memory_limit_mib=1024,
            logging=app_ecs_logs,
            image=ecs.ContainerImage.from_registry(
                '{account_id}.dkr.ecr.ap-northeast-1.amazonaws.com/{name_space}/app'.format(
                    account_id = os.getenv('AWS_ACCOUNT_ID'),
                    name_space = os.getenv('ADMIN_APPLICATION_NAMESPACE')
                )
            )
        ).add_port_mappings(
            ecs.PortMapping(
                container_port=9000,
                protocol=ecs.Protocol.TCP
            )
        )'''

        # api
        api_taskdef = ecs.FargateTaskDefinition(
            self,
            '{name_space}_task'.format(name_space=os.getenv('API_APPLICATION_NAMESPACE')),
            execution_role=execution_role,
            task_role=task_role,
        )

        api_taskdef.add_container(
            'web',
            # cpu=512,
            # memory_limit_mib=1024,
            logging=api_web_ecs_logs,
            image=ecs.ContainerImage.from_registry(
                '{account_id}.dkr.ecr.ap-northeast-1.amazonaws.com/{name_space}/web'.format(
                    account_id = os.getenv('AWS_ACCOUNT_ID'),
                    name_space = os.getenv('API_APPLICATION_NAMESPACE')
                )
            )
        ).add_port_mappings(
            ecs.PortMapping(
                container_port=80,
                protocol=ecs.Protocol.TCP
            )
        )

        api_taskdef.add_container(
            'app',
            # cpu=1024,
            # memory_limit_mib=1024,
            logging=api_app_ecs_logs,
            image=ecs.ContainerImage.from_registry(
                '{account_id}.dkr.ecr.ap-northeast-1.amazonaws.com/{name_space}/app'.format(
                    account_id = os.getenv('AWS_ACCOUNT_ID'),
                    name_space = os.getenv('API_APPLICATION_NAMESPACE')
                )
            )
        ).add_port_mappings(
            ecs.PortMapping(
                container_port=9000,
                protocol=ecs.Protocol.TCP
            )
        )

        ## service
        '''fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            os.getenv('ADMIN_APPLICATION_NAMESPACE'),
            cluster=cluster,
            cpu=1024, # 1 CPU
            memory_limit_mib=2048, # 2GB RAM
            desired_count=1,
            task_definition=taskdef,
            # task_image_options=web_task_image_option,
        )'''

        api_fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            os.getenv('API_APPLICATION_NAMESPACE'),
            cluster=cluster,
            cpu=1024, # 1 CPU
            memory_limit_mib=2048, # 2GB RAM
            desired_count=1,
            task_definition=api_taskdef,
            # task_image_options=web_task_image_option,
        )

        ## service auto scaling

        # admin
        '''fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer = ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection = ec2.Port.tcp(9000),
            description='Allow 9000 inbound from SG'
        )
        # Setup AutoScaling policy
        # memory utilization setup
        scaling = fargate_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=10
        )
        scaling.scale_on_cpu_utilization(
            'CpuScaling',
            target_utilization_percent=60,
            scale_in_cooldown=core.Duration.seconds(60),
            scale_out_cooldown=core.Duration.seconds(60),
        )
        scaling.scale_on_memory_utilization(
            'MemoryScaling',
            target_utilization_percent=80,
            scale_in_cooldown=core.Duration.seconds(60),
            scale_out_cooldown=core.Duration.seconds(60),
        )'''

        # api
        api_fargate_service.service.connections.security_groups[0].add_ingress_rule(
            peer = ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection = ec2.Port.tcp(9000),
            description='Allow 9000 inbound from SG'
        )
        # Setup AutoScaling policy
        # memory utilization setup
        api_scaling = api_fargate_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=10
        )
        api_scaling.scale_on_cpu_utilization(
            'CpuScaling',
            target_utilization_percent=60,
            scale_in_cooldown=core.Duration.seconds(60),
            scale_out_cooldown=core.Duration.seconds(60),
        )
        api_scaling.scale_on_memory_utilization(
            'MemoryScaling',
            target_utilization_percent=80,
            scale_in_cooldown=core.Duration.seconds(60),
            scale_out_cooldown=core.Duration.seconds(60),
        )

        # grant permissions
        # table.grant_read_write_data(taskdef.task_role)
        api_taskdef.add_to_task_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=['*'],
                actions=['ssm:GetParameter']
            )
        )
        api_taskdef.add_to_task_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources= ['*'],
                actions=[
                's3:GetObject',
                's3:PutObject',
                's3:ListBucket',
                's3:ListAllMyBuckets'
                ]
            )
        )

        # Store parameters in SSM
        ssm.StringParameter(
            self,
            'ECS_CLUSTER_NAME',
            parameter_name='ECS_CLUSTER_NAME',
            string_value=cluster.cluster_name,
        )
        ssm.StringParameter(
            self,
            'ECS_TASK_VPC_SUBNET_1',
            parameter_name='ECS_TASK_VPC_SUBNET_1',
            string_value=vpc.public_subnets[0].subnet_id
        )

        # core.CfnOutput(self, 'ECR', value=ecr.Repository)
        core.CfnOutput(
            self,
            'ClusterName',
            value=cluster.cluster_name
        )
        '''core.CfnOutput(
            self,
            'LoadBalancerDNS{name_space}'.format(name_space=os.getenv('ADMIN_APPLICATION_NAMESPACE')),
             value=fargate_service.load_balancer.load_balancer_dns_name
        )'''

        core.CfnOutput(
            self,
            'LoadBalancerDNS{name_space}'.format(name_space=os.getenv('API_APPLICATION_NAMESPACE')),
             value=api_fargate_service.load_balancer.load_balancer_dns_name
        )



def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(base_path, '.env')
    load_dotenv(dotenv_path)

    app = core.App()
    AutoScalingFargateService(
        app,
        os.getenv('PROJECT_NAME'),
        env = {
            "region": os.getenv('AWS_DEFAULT_REGION'),
            "account": os.getenv('AWS_ACCOUNT_ID'),
        }
    )
    app.synth()

if __name__ == '__main__':
    main()