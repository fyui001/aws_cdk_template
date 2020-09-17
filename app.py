from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_logs,
    aws_ecr as ecr,
    aws_s3 as s3,
)

import os
from dotenv import load_dotenv

from stacks.CodepipelineStack import CodepipelineStack
from stacks.VpcStack import VpcStack
from stacks.RdsStack import RdsStack
from stacks.EcsStack import EcsStack
from stacks.EcrStack import EcrStack

class AutoScalingFargateService(core.Stack):

    def __init__(self, scope: core.Construct, id: str):

        super().__init__(scope, id)

        ## ECR repository create
        # admin
        EcrStack(app, 'AdminEcrStack', 'Admin', os.getenv('ADMIN_APPLICATION_NAMESPACE'))

        # api
        EcrStack(app, 'ApiEcrStack', 'Api', os.getenv('API_APPLICATION_NAMESPACE'))

        ## VPC Stack
        vpc_stack = VpcStack(app, 'VpcStack')

        ## RDS Stack
        rds_stack = RdsStack(app, 'RdsStack', vpc_stack.vpc, vpc_stack.rds_sg)

        ## S3 bucket create
        s3_bucket = s3.Bucket(
            self,
            '{project_name}-S3bucket'.format(project_name=os.getenv('PROJECT_NAME')),
            bucket_name = '{prefix}-bucket'.format(prefix=os.getenv('AWS_BUCKET_PLEFIX'))
        )

        ## Codepipeline Stack

        # admin
        CodepipelineStack(
            app,
            id = 'AdminCodepipelineStack',
            rds_endpoint = rds_stack.mysql.db_instance_endpoint_address,
            secret_manager = os.getenv('ADMIN_SECRET_MANAGER'),
            application_name = os.getenv('ADMIN_APPLICATION_NAMESPACE'),
            repo = os.getenv('ADMIN_GIT_HUB_REPOSITORY'),
            s3_bucket_name = s3_bucket.bucket_name
        )

        # api
        CodepipelineStack(
            app,
            id = 'ApiCodepipelineStack',
            rds_endpoint = rds_stack.mysql.db_instance_endpoint_address,
            secret_manager = os.getenv('API_SECRET_MANAGER'),
            application_name = os.getenv('API_APPLICATION_NAMESPACE'),
            repo = os.getenv('API_GIT_HUB_REPOSITORY'),
            s3_bucket_name = s3_bucket.bucket_name
        )

        ## ECS Cluster
        cluster = ecs.Cluster(
            self,
            'ClusterStack',
            cluster_name = '{project_name}-ecs-cluster'.format(project_name=os.getenv('PROJECT_NAME')),
            vpc = vpc_stack.vpc
        )

        ## ECS Stack
        # admin
        EcsStack(
            app,
            id = 'AdminEcsStack',
            vpc = vpc_stack.vpc,
            cluster = cluster,
            application_name = os.getenv('ADMIN_APPLICATION_NAMESPACE')
        )

        # api
        EcsStack(
            app,
            id = 'ApiEcsStack',
            vpc = vpc_stack.vpc,
            cluster = cluster,
            application_name = os.getenv('API_APPLICATION_NAMESPACE')
        )


base_path = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(base_path, '.env')
load_dotenv(dotenv_path)

app = core.App()

AutoScalingFargateService(
    app,
    os.getenv('PROJECT_NAME'),
)

app.synth()