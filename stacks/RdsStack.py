from aws_cdk import (
    core,
    aws_rds as rds,
    aws_ec2 as ec2
)

import os
from dotenv import load_dotenv

class RdsStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, security_group: ec2.SecurityGroup, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        self.mysql = rds.DatabaseInstance(
            self,
            '{project_name}-RDS'.format(project_name=os.getenv('PROJECT_NAME')),
            master_username = os.getenv('DB_USERNAME'),
            master_user_password = core.SecretValue.plain_text(os.getenv('DB_PASSWORD')),
            database_name = os.getenv('DB_DATABASE'),
            engine = rds.DatabaseInstanceEngine.MYSQL,
            vpc = vpc,
            vpc_placement = {
                'subnet_type': ec2.SubnetType.PUBLIC
            },
            port = int(os.getenv('DB_PORT')),
            instance_identifier = '{project_name}-MYSQL'.format(project_name=os.getenv('PROJECT_NAME')),
            instance_type = ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO),
            removal_policy = core.RemovalPolicy.DESTROY,
            deletion_protection = False,
            cloudwatch_logs_exports = ['error', 'general', 'slowquery'],
            security_groups = [security_group]
        )

        self.mysql.connections.allow_from(
            security_group,
            port_range = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description = 'Allow MySQL access from Query Lambda (because Aurora actually exposes PostgreSQL/MySQL on port 3306)'
        )