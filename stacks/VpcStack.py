from aws_cdk import (
    core,
    aws_ec2 as ec2,
)

import os
from dotenv import load_dotenv

class VpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        ## vpc create
        self.vpc = ec2.Vpc(
            self,
            '{project_name}-VPC'.format(project_name = os.getenv('PROJECT_NAME')),
            max_azs = 2,
            cidr = os.getenv('AWS_VPC_CIDR')
        )

        self.vpc.add_gateway_endpoint(
            's3endpoint',
            service = ec2.GatewayVpcEndpointAwsService.S3
        )

        self.rds_sg = ec2.SecurityGroup(
            self,
            'RDSSG',
            allow_all_outbound = True,
            description = 'Allow DS access Security Group',
            vpc = self.vpc
        )

        self.rds_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4('182.171.74.66/32'),
            connection = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description='Allow MySQL access from Dimageshare'
        )

        self.rds_sg.add_ingress_rule(
            peer = ec2.Peer.ipv4('14.177.64.134/32'),
            connection = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description = 'Allow MySQL access from Dimageshare'
        )

        self.rds_sg.add_ingress_rule(
            peer = ec2.Peer.ipv4('182.171.83.178/32'),
            connection = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description = 'Allow MySQL access from Dimageshare'
        )

        self.rds_sg.add_ingress_rule(
            peer = ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection = ec2.Port.tcp(int(os.getenv('DB_PORT'))),
            description = 'Allow MySQL access from ECS'
        )
