from aws_cdk import (
    core,
    aws_ecr as ecr
)

import os

class EcrStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, image_id_prefix: str, application_name: str, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        ecr.Repository(
            self,
            f'{image_id_prefix}WebImageRepository',
            image_scan_on_push=True,
            repository_name='{name_space}/web'.format(name_space=application_name)
        )

        ecr.Repository(
            self,
            f'{image_id_prefix}AppImageRepository',
            image_scan_on_push=True,
            repository_name='{name_space}/app'.format(name_space=application_name)
        )