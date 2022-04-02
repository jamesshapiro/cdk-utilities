from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_certificatemanager as certificatemanager,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    Aws, CfnOutput, Duration,
    aws_s3 as s3,
)
import aws_cdk as cdk
from constructs import Construct

STACK_NAME = 'PasswordProtectedWebsiteExampleStack'
class PasswordProtectedWebsiteExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        with open(".cdk-params") as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form: key_name=value
            # e.g. hosted_zone_id=Z048XXXXXXXXXXX
            # e.g. subdomain=private.examplewebsite.com
            subdomain = [line for line in lines if line.startswith('subdomain=')][0].split('=')[1]
            hosted_zone_id = [line for line in lines if line.startswith('hosted_zone_id=')][0].split('=')[1]
        ddb_table = dynamodb.Table(
            self, "s3-tunes-table",
            partition_key=dynamodb.Attribute(name="PK1", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK1", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
        CfnOutput(self, "DDBTableName", value=ddb_table.table_name)
        ######## FRONT-END PRIVATE WEBSITE ########
        zone = route53.HostedZone.from_hosted_zone_attributes(self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=subdomain
        )

        site_bucket = s3.Bucket(
            self, f'{subdomain}-bucket',
        )
        certificate = certificatemanager.DnsValidatedCertificate(
            self, f'{subdomain}-certificate',
            domain_name=subdomain,
            hosted_zone=zone,
            subject_alternative_names=[f'www.{subdomain}']
        )

        AUTHORIZER_FUNCTION_NAME = 'Authorizer'
        STACK_NAME_CHARS_LIMIT = 25
        STACK_PREFIX = STACK_NAME[:STACK_NAME_CHARS_LIMIT]
        
        domain_names = [subdomain, f'www.{subdomain}']
        authorizer_function = cloudfront.experimental.EdgeFunction(self, AUTHORIZER_FUNCTION_NAME,
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('lambda_edge'),
            handler='authorizer.lambda_handler',
        )
        statement_1 = iam.PolicyStatement(
            actions=['iam:GetRole*','iam:ListRolePolicies'],
            resources=[f'arn:aws:iam::{Aws.ACCOUNT_ID}:role/{STACK_PREFIX}-{AUTHORIZER_FUNCTION_NAME}FnServiceRole*']
        )
        statement_2 = iam.PolicyStatement(
            actions=['dynamodb:GetItem'],
            resources=[ddb_table.table_arn]
        )

        authorizer_function.add_to_role_policy(statement_1)
        authorizer_function.add_to_role_policy(statement_2)
        
        distribution = cloudfront.Distribution(
            self, f'{subdomain}-distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                edge_lambdas=[
                    cloudfront.EdgeLambda(
                        function_version=authorizer_function.current_version,
                        event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    )
                ]
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                )
            ],
            comment=f'{subdomain} S3 HTTPS',
            default_root_object='index.html',
            domain_names=domain_names,
            certificate=certificate
        )

        CfnOutput(self, f'{subdomain}-cf-distribution', value=distribution.distribution_id)
        a_record_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(distribution))
        route53.ARecord(
            self, f'{subdomain}-alias-record',
            zone=zone,
            target=a_record_target,
            record_name=subdomain
        )
        CfnOutput(self, f'{subdomain}-bucket-name', value=site_bucket.bucket_name)
        
