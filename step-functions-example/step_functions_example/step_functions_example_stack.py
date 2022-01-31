from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
)

import aws_cdk as cdk
from constructs import Construct

integ_approve_response = """
#set($inputRoot = $input.path('$'))
{"response": "comment submitted for approval!"}
"""

integ_reject_response = """
#set($inputRoot = $input.path('$'))
{"response": "comment rejected!"}
"""

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

        generate_ulid_function_cdk = lambda_.Function(
            self, 'cdk-sfn-demo-generate-ulid',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('resources'),
            handler='generate_ulid.lambda_handler',
            timeout=cdk.Duration.seconds(30),
            memory_size=128,
            layers=[ulid_layer]
        )

        ses_crud_policy = iam.Policy(
            self, 'cdk-sfn-demo-ses-policy',
            statements=[iam.PolicyStatement(
                actions=['ses:GetIdentityVerificationAttributes','ses:SendEmail','ses:SendRawEmail','ses:VerifyEmailIdentity'],
                resources=[f'arn:aws:ses:us-east-1:{account_id}:identity/{validator_email}']
            )]
        )

        generate_ulid_state = tasks.LambdaInvoke(self, "Generate ULID",
            lambda_function=generate_ulid_function_cdk,
            # Lambda's result is in the attribute `Payload`
            result_path="$.ulid",
            timeout=Duration.seconds(5)
        )
        

        api = apigateway.RestApi(
            self,
            'cdk-sfn-demo-comments-api',
            description='CDK step function demo in CDK.'
        )

        challenge_email_function_cdk = lambda_.Function(
            self, 'cdk-sfn-demo-challenge-email',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('resources'),
            handler='challenge_email.lambda_handler',
            environment=dict(
                APPROVE_COMMENT_ENDPOINT=f'https://{api.rest_api_id}.execute-api.us-east-1.amazonaws.com/prod/success/',
                REJECT_COMMENT_ENDPOINT=f'https://{api.rest_api_id}.execute-api.us-east-1.amazonaws.com/prod/failure/',
                UNSUBSCRIBE_ENDPOINT='REJECT_COMMENT_ENDPOINT',
            ),
            timeout=cdk.Duration.seconds(30),
            memory_size=128
        )

        ddb_table.grant_write_data(challenge_email_function_cdk)
        challenge_email_function_cdk.role.attach_inline_policy(ses_crud_policy)

        challenge_commenter_email_state = tasks.LambdaInvoke(self, "Challenge Commenter Email",
            lambda_function=challenge_email_function_cdk,
            integration_pattern=stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=stepfunctions.TaskInput.from_object({
                "token": stepfunctions.JsonPath.task_token,
                "input": stepfunctions.JsonPath.string_at("$"),
                "is_moderator": "false"
            }),
            result_path="$.taskresult",
            timeout=Duration.hours(1)
        )

        log_comment_state = tasks.DynamoPutItem(self, "Log Comment",
            item={
                "PK1": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.post_id")),
                "SK1": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.ulid.Payload.ulid")),
                "COMMENT_TEXT": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.comment_text")),
                "COMMENTER_EMAIL": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.commenter_email")),
                "COMMENTER_APPROVED": tasks.DynamoAttributeValue.from_string("true"),
                "MODERATOR_APPROVED": tasks.DynamoAttributeValue.from_string("false"),
            },
            table=ddb_table,
            result_path="$.ddb_result"
        )

        challenge_moderator_email_state = tasks.LambdaInvoke(self, "Challenge Moderator Email",
            lambda_function=challenge_email_function_cdk,
            integration_pattern=stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=stepfunctions.TaskInput.from_object({
                "token": stepfunctions.JsonPath.task_token,
                "input": stepfunctions.JsonPath.string_at("$"),
                "is_moderator": "true"
            }),
            result_path="$.moderatordecision",
            timeout=Duration.days(7)
        )

        publish_comment_state = tasks.DynamoUpdateItem(self, "Publish Comment",
            key={
                "PK1": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.post_id")),
                "SK1": tasks.DynamoAttributeValue.from_string(stepfunctions.JsonPath.string_at("$.ulid.Payload.ulid")),
            },
            table=ddb_table,
            expression_attribute_values={
                ":true_literal": tasks.DynamoAttributeValue.from_string("true")
            },
            expression_attribute_names={
                "#moderator_approved": "MODERATOR_APPROVED"
            },
            update_expression="SET #moderator_approved = :true_literal",
            result_path=None
        )

        definition = generate_ulid_state.next(challenge_commenter_email_state).next(log_comment_state).next(challenge_moderator_email_state).next(publish_comment_state)

        state_machine = stepfunctions.StateMachine(self, "cdk-sfn-demo-state-machine",
            definition=definition
        )

        credentials_role = iam.Role(
            self, 'cdk-sfn-demo-trigger-state-machine-role',
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )

        review_comment_role = iam.Role(
            self, 'cdk-sfn-demo-review-comment-state-machine-role',
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )

        trigger_state_machine_policy = iam.Policy(
            self, 'cdk-sfn-demo-trigger-state-machine-policy',
            statements=[iam.PolicyStatement(
                actions=['states:StartExecution'],
                resources=[state_machine.state_machine_arn]
            )]
        )

        review_comment_policy = iam.Policy(
            self, 'cdk-sfn-demo-review-comment-policy',
            statements=[iam.PolicyStatement(
                actions=['states:SendTaskSuccess','states:SendTaskFailure'],
                resources=[state_machine.state_machine_arn]
            )]
        )

        credentials_role.attach_inline_policy(trigger_state_machine_policy)
        review_comment_role.attach_inline_policy(review_comment_policy)

        entry_point = api.root.add_resource("entry-point")
        entry_point.add_method(
            'POST',
            integration=apigateway.AwsIntegration(
                service='states',
                action="StartExecution",
                integration_http_method="POST",
                options=apigateway.IntegrationOptions(
                    credentials_role=credentials_role,
                    request_templates={
                        "application/json": f'{{"input": "$util.escapeJavaScript($input.body)", "stateMachineArn": "{state_machine.state_machine_arn}"}}'
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(status_code="200")
                    ],
                )
            ),
            method_responses=[apigateway.MethodResponse(status_code="200")]
        )

        empty_model = api.add_model("GatewayEmptyModel",
            content_type="application/json",
            schema={}
        )

        success = api.root.add_resource("success")
        failure = api.root.add_resource("failure")
        success.add_method('GET',
            request_parameters={"method.request.querystring.token": True},
            integration=apigateway.AwsIntegration(
                service='states',
                integration_http_method="POST",
                action="SendTaskSuccess",
                options=apigateway.IntegrationOptions(
                    credentials_role=review_comment_role,
                    passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
                    request_templates={
                        "application/json": '{"output": "{\\"decision\\": \\"approve\\"}", "taskToken": "$input.params(\'token\')"}'
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(status_code="200", response_templates={"application/json": integ_approve_response})
                    ],
                )
            ),
            method_responses=[apigateway.MethodResponse(status_code="200",response_models={"application/json": empty_model})]
        )
        failure.add_method('GET',
            request_parameters={"method.request.querystring.token": True},
            integration=apigateway.AwsIntegration(
                service='states',
                integration_http_method="POST",
                action="SendTaskFailure",
                options=apigateway.IntegrationOptions(
                    credentials_role=review_comment_role,
                    passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
                    request_templates={
                        "application/json": '{"error": "rejected", "cause": "comment was rejected by commenter or moderator", "taskToken": "$input.params(\'token\')"}'
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(status_code="200", response_templates={"application/json": integ_reject_response})
                    ],
                )
            ),
            method_responses=[apigateway.MethodResponse(status_code="200",response_models={"application/json": empty_model})]
        )

        cdk.CfnOutput(
            self, "StepFunctionsApi",
            description="CDK SFN Demo Entry Point API",
            value = f'https://{api.rest_api_id}.execute-api.us-east-1.amazonaws.com/prod/entry-point/'
        )

