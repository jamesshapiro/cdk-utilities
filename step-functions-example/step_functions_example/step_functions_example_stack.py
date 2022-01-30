from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    custom_resources as custom_resources,
)

import aws_cdk as cdk
from constructs import Construct

class StepFunctionsExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        with open('.cdk-params') as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form (note the required country code in phone #):
            # NotificationPhone=+12223334444
            # NotificationEmail=jeff@example.com
            validator_email = [line for line in lines if line.startswith('validator_email')][0].split('=')[1]
            recipient_email = [line for line in lines if line.startswith('recipient_email')][0].split('=')[1]
            account_id = [line for line in lines if line.startswith('account_id')][0].split('=')[1]
        ddb_table = dynamodb.Table(
            self, 'CDKSFNDemo',
            partition_key=dynamodb.Attribute(name='PK1', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='SK1', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
        ddb_table.add_global_secondary_index(
            index_name='GSI1',
            partition_key=dynamodb.Attribute(name='GSI1PK', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='GSI1SK', type=dynamodb.AttributeType.STRING)
        )

        ulid_layer = lambda_.LayerVersion(
            self,
            'cdk-sfn-demo-ulid-python-38-layer',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            code=lambda_.Code.from_asset('layers/my-Python38-ulid.zip'),
            compatible_architectures=[lambda_.Architecture.X86_64]
        )
        challenge_email_function_cdk = lambda_.Function(
            self, 'cdk-sfn-demo-challenge-email',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('resources'),
            handler='challenge_email.lambda_handler',
            environment=dict(
                APPROVE_COMMENT_ENDPOINT='APPROVE_COMMENT_ENDPOINT',
                REJECT_COMMENT_ENDPOINT='REJECT_COMMENT_ENDPOINT',
                UNSUBSCRIBE_ENDPOINT='REJECT_COMMENT_ENDPOINT',
            ),
            timeout=cdk.Duration.seconds(30),
            memory_size=128
        )

        generate_ulid_function_cdk = lambda_.Function(
            self, 'cdk-sfn-demo-generate-ulid',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('resources'),
            handler='generate_ulid.lambda_handler',
            timeout=cdk.Duration.seconds(30),
            memory_size=128,
            layers=[ulid_layer]
        )

        ddb_table.grant_write_data(challenge_email_function_cdk)

        ses_crud_policy = iam.Policy(
            self, 'cdk-sfn-demo-ses-policy',
            statements=[iam.PolicyStatement(
                actions=['ses:GetIdentityVerificationAttributes','ses:SendEmail','ses:SendRawEmail','ses:VerifyEmailIdentity'],
                resources=[f'arn:aws:ses:us-east-1:{account_id}:identity/{validator_email}']
            )]
        )
        challenge_email_function_cdk.role.attach_inline_policy(ses_crud_policy)

        with open('resources/custom_resource.py') as f:
            is_complete_code = f.read()

        is_complete_handler=lambda_.Function(
            self, 
            id="ReminderCustomResourceCDK",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_inline(is_complete_code),
            handler="index.lambda_handler",
            # environment=dict(
            #     API_KEY_ID=api_key.key_id,
            # ),
            timeout=cdk.Duration.seconds(30),
            memory_size=128
        )

        my_provider = custom_resources.Provider(
            self, "MyProvider",
            on_event_handler=is_complete_handler,
            is_complete_handler=is_complete_handler
        )

        custom_resource = cdk.CustomResource(
            scope=self,
            id='MyCustomResource',
            service_token=my_provider.service_token,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::JamesResource",
        )

        # api = apigateway.RestApi(
        #     self,
        #     'cdk-sfn-demo',
        #     description='CDK step function demo in CDK.'
        # )
