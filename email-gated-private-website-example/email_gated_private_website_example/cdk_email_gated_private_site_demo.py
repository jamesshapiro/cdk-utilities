from aws_cdk import (
    Stack,
    aws_s3 as s3,
    Aws, CfnOutput, Duration,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as certificatemanager,
    aws_cloudfront_origins as origins,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_ssm as ssm,
    aws_lambda as lambda_,
)
import aws_cdk as cdk
from constructs import Construct

class CDKEmailGatedPrivateSiteDemoStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        APP_NAME = 'athens-email-gated-demo'
        PRIVATE_KEY_PARAM_NAME = f'{APP_NAME}-private-key'
        PUBLIC_KEY_PARAM_NAME = f'{APP_NAME}-public-key'
        PUBLIC_KEY_ID_PARAM_NAME = f'{APP_NAME}-public-key-id'

        with open('.cdk-params') as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form: key_name=value
            subdomain = [line for line in lines if line.startswith('subdomain=')][0].split('=')[1]
            hosted_zone_id = [line for line in lines if line.startswith('hosted_zone_id=')][0].split('=')[1]
            zone_name = [line for line in lines if line.startswith('zone_name=')][0].split('=')[1]
            email_domain = [line for line in lines if line.startswith('email_domain=')][0].split('=')[1]
            sender_email = [line for line in lines if line.startswith('sender_email=')][0].split('=')[1]
            signing_url = [line for line in lines if line.startswith('signing_url=')][0].split('=')[1]
        
        with open('private_key.pem') as f:
            private_key = f.read()
        public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyWJOwHFwYUHk8iL7oxX4
O/Eq8oYqZK5ylRNQce83V97dk9cgMEVnaWww3GxfFgLrUhXtrhhQev0QtKg1CZLm
jcsz+KYRpowvnYRywhh/voRUpp5Fos6c5/+AhsN/Wuex/WTYX22xlF6+g3ZYISem
f+bvhMuT1k/BcP7lIWU+DKs5GhWvQMlCnNqOVrlZ/zPD3EhyFUop3Vjk4oVIkgzK
yhO9XlGwPF1q3gw/UNRHQTLNNeNIFQBvdMjx8o1EMFqyfvq08PebnQDJcVyV/oGA
7tzJVuF5aB8s3HT2LE4x7nkw1INz5q6vj2xf34w3dK7bK6SBH+HITrPoLg9UwNVK
3QIDAQAB
-----END PUBLIC KEY-----
"""
        private_key_parameter = ssm.StringParameter(self, f'{APP_NAME}-private-key',
            description=f'{APP_NAME} Private Key',
            parameter_name=PRIVATE_KEY_PARAM_NAME,
            string_value=private_key
        )
        public_key_parameter = ssm.StringParameter(self, f'{APP_NAME}-public-key',
            description=f'{APP_NAME} Public Key',
            parameter_name=PUBLIC_KEY_PARAM_NAME,
            string_value=public_key
        )

        pub_key = cloudfront.PublicKey(self, f'{APP_NAME}MyPubKey',
            encoded_key=public_key
        )

        key_group = cloudfront.KeyGroup(self, f'{APP_NAME}MyKeyGroup',
            items=[pub_key]
        )

        public_key_id_parameter = ssm.StringParameter(self, f'{APP_NAME}-public-key-id',
            description=f'{APP_NAME} Public Key ID',
            parameter_name=PUBLIC_KEY_ID_PARAM_NAME,
            string_value=pub_key.public_key_id
        )

        api = apigateway.RestApi(
            self,
            'cdk-email-gated-website-demo',
            description='CDK Lambda Layer Factory.',
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )

        cryptography_38_layer = lambda_.LayerVersion(
            self,
            'Cryptography38Layer',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            code=lambda_.Code.from_asset('layers/crypto38-2022-3-19-17_47_28.zip'),
            compatible_architectures=[lambda_.Architecture.X86_64]
        )

        create_signed_url_function_cdk = lambda_.Function(
            self, 'CreateSignedUrlCDK',
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_asset('functions'),
            handler='create_signed_url.lambda_handler',
            environment={
                'KEY_ID': PUBLIC_KEY_ID_PARAM_NAME,
                'SENDER_EMAIL': sender_email,
                'SIGNING_URL': signing_url
            },
            layers=[cryptography_38_layer],
            timeout=Duration.seconds(30)
        )

        create_signed_url_policy = iam.Policy(
            self, 'cdk-create-signed-url-policy',
            statements=[
                iam.PolicyStatement(
                    actions=['ses:SendEmail','ses:SendRawEmail'],
                    resources=[
                        f'arn:aws:ses:{Aws.REGION}:{Aws.ACCOUNT_ID}:identity/{email_domain}'
                    ]
                ),
                iam.PolicyStatement(
                    actions=['ssm:GetParameter'],
                    resources=[
                        public_key_parameter.parameter_arn,
                        private_key_parameter.parameter_arn,
                        public_key_id_parameter.parameter_arn
                    ]
                ),
            ]
        )
        create_signed_url_function_cdk.role.attach_inline_policy(create_signed_url_policy)

        create_signed_url_integration = apigateway.LambdaIntegration(
            create_signed_url_function_cdk,
            proxy=True
        )

        create_signed_url_resource = api.root.add_resource(
            'create-signed-url',
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST"]
            )
        )

        create_signed_url_resource.add_method(
            'GET',
            create_signed_url_integration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )

        #CfnOutput(self, api.domain_name)

        site_bucket = s3.Bucket(
            self, f'{APP_NAME}-bucket',
        )

        domain_names = [subdomain]

        zone = route53.HostedZone.from_hosted_zone_attributes(self, 'HostedZone',
            hosted_zone_id=hosted_zone_id,
            zone_name=zone_name
        )

        certificate = certificatemanager.DnsValidatedCertificate(
            self, f'{subdomain}-certificate',
            domain_name=subdomain,
            hosted_zone=zone
        )

        authorizer_policy_statement = iam.PolicyStatement(
            actions=['ssm:GetParameter'],
            resources=[
                public_key_parameter.parameter_arn,
                private_key_parameter.parameter_arn,
                public_key_id_parameter.parameter_arn
            ]
        )
        #create_signed_url_function_cdk.role.attach_inline_policy(create_signed_url_policy)

        authorizer_function = cloudfront.experimental.EdgeFunction(self, "EmailGatedPrivateWebsiteAuthorizerCDK",
            runtime=lambda_.Runtime.NODEJS_14_X,
            code=lambda_.Code.from_asset('lambda_edge/authorizer'),
            handler='index.handler',
            timeout=Duration.seconds(5)
        )
        authorizer_function.add_to_role_policy(authorizer_policy_statement)

        distribution = cloudfront.Distribution(
            self, f'{APP_NAME}-distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                trusted_key_groups=[key_group],
                edge_lambdas=[
                    cloudfront.EdgeLambda(
                        function_version=authorizer_function.current_version,
                        event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    )
                ]
            ),
            additional_behaviors={
                # public behavior 1
                '/login.html': cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    # edge_lambdas=[
                    #     cloudfront.EdgeLambda(
                    #         function_version=authorizer_function.current_version,
                    #         event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    #     )
                    # ]
                ),
                '/static/*': cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    # edge_lambdas=[
                    #     cloudfront.EdgeLambda(
                    #         function_version=authorizer_function.current_version,
                    #         event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    #     )
                    # ]
                ),
                # public behavior 3 -- tied to Lambda@Edge function eventually
                '/login': cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    # edge_lambdas=[
                    #     cloudfront.EdgeLambda(
                    #         function_version=authorizer_function.current_version,
                    #         event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    #     )
                    # ]
                ),
                # private behavior 1 -- tied to Lambda@Edge function eventually
                '/auth*': cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    trusted_key_groups=[key_group],
                    edge_lambdas=[
                        cloudfront.EdgeLambda(
                            function_version=authorizer_function.current_version,
                            event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                        )
                    ]
                ),
            },
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path='/login.html',
                    ttl=Duration.minutes(30)
                )
            ],
            comment=f'{APP_NAME} S3 HTTPS',
            default_root_object='login.html',
            domain_names=domain_names,
            certificate=certificate
        )

        a_record_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(distribution))
        record = route53.ARecord(
            self, f'{subdomain}-alias-record',
            zone=zone,
            target=a_record_target,
            record_name=subdomain
        )

