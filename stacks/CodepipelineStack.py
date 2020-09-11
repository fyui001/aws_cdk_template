from aws_cdk import (
    core,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as actions,
    aws_iam as iam
)

import os
from dotenv import load_dotenv

class CodepipelineStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, rds_endpoint: str, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)
        print(rds_endpoint)
        pipeline = codepipeline.Pipeline(
            self,
            id=os.getenv('API_APPLICATION_NAMESPACE'),
            pipeline_name=os.getenv('API_APPLICATION_NAMESPACE'),
        )

        app_output = codepipeline.Artifact()
        git_hub_token = os.getenv('GIT_HUB_TOKEN')
        # SourceActionの諸々定義
        source_action = actions.GitHubSourceAction(
            action_name='SourceAction',
            oauth_token=core.SecretValue.plain_text(git_hub_token),
            owner=os.getenv('GIT_HUB_ACCOUNT'),
            repo=os.getenv('GIT_HUB_REPOSITORY'),
            branch=os.getenv('GIT_HUB_BRUNCH'),
            output=app_output,
            run_order=1
        )

        # BuildActionの定義
        build_action = codebuild.PipelineProject(
            self,
            id = '{project_name}BuildAction'.format(project_name=os.getenv('PROJECT_NAME')),
            environment = codebuild.BuildEnvironment(
                privileged = True
            ),
            build_spec = codebuild.BuildSpec.from_source_filename('aws/buildspec.yml'),
            # BuildActionの環境変数。適宜書き換え
            environment_variables = {
                'DB_HOST': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': str(os.getenv('DB_HOST')),
                },
                'DB_PORT': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': rds_endpoint,
                },
                'DB_DATABASE': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': str(os.getenv('DB_DATABASE')),
                },
                'DB_USERNAME': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': str(os.getenv('DB_USERNAME')),
                },
                os.getenv('AWS_SECRET_MANAGER'): {
                    'type': codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    'value': str(os.getenv('AWS_SECRET_MANAGER')),
                },
                'PROJECT_NAMESPACE': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': str(os.getenv('PROJECT_NAME')),
                },
                'AWS_DEFAULT_REGION': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': str(os.getenv('AWS_DEFAULT_REGION')),
                },
                'ENVIRONMENT': {
                    'type': codebuild.BuildEnvironmentVariableType.PLAINTEXT,
                    'value': str(os.getenv('ENVIRONMENT')),
                 },
            }
        )

        build_action.add_to_role_policy(iam.PolicyStatement(
            actions = ['service:BuildAction'],
            resources = [
                'arn:aws:iam::aws:policy/SecretsManagerReadWrite',
                'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess',
            ]
        ))

        application_deploy_action = actions.CodeBuildAction(
            project = build_action,
            input = app_output,
            action_name = 'BuildAction',
            run_order = 3
        )

        # pipelineのステージを作成して追加
        pipeline.add_stage(
            stage_name = 'SourceAction',
            actions = [source_action],
        )

        pipeline.add_stage(
            stage_name = 'BuildAction',
            actions = [application_deploy_action],
        )
