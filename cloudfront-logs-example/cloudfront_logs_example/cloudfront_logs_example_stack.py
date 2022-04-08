from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as certificatemanager,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_cloudfront_origins as origins,
    aws_lambda_event_sources as lambda_event_sources,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    CfnOutput, Duration, RemovalPolicy
)
from constructs import Construct
import aws_cdk as cdk

class CloudfrontLogsExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        with open('.cdk-params') as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form:
            # key=value
            subdomain_name = [line for line in lines if line.startswith('subdomain=')][0].split('=')[1]
            hosted_zone_id = [line for line in lines if line.startswith('hosted_zone_id=')][0].split('=')[1]
            zone_name = [line for line in lines if line.startswith('zone_name')][0].split('=')[1]
        site_bucket = s3.Bucket(
            self, 'bucket',
        )

        zone = route53.HostedZone.from_hosted_zone_attributes(self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=zone_name
        )

        certificate = certificatemanager.DnsValidatedCertificate(
            self, 'certificate',
            domain_name=subdomain_name,
            hosted_zone=zone
        )

        cloudfront_logs_bucket = s3.Bucket(self, "cloudfront-logs")

        distribution = cloudfront.Distribution(
            self, 'distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            ),
            comment='S3 HTTPS example',
            default_root_object='index.html',
            domain_names=[subdomain_name],
            certificate=certificate,
            enable_logging=True,
            log_bucket=cloudfront_logs_bucket,
            log_file_prefix="cloudfront-logs-example-distribution-access-logs/",
            log_includes_cookies=True
        )

        a_record_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(distribution))
        
        route53.ARecord(
            self, 'alias-record',
            zone=zone,
            target=a_record_target,
            record_name=subdomain_name
        )

        CfnOutput(self, f'{subdomain_name}-bucket-name', value=site_bucket.bucket_name)

        requests_layer = lambda_.LayerVersion(self,'Requests39Layer',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            code=lambda_.Code.from_asset('layers/requestspython39.zip'),
            compatible_architectures=[lambda_.Architecture.X86_64]
        )

        ddb_table = dynamodb.Table(
            self, 'Table',
            partition_key=dynamodb.Attribute(name='PK1', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='SK1', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute='TTL_EXPIRATION',
            removal_policy=RemovalPolicy.DESTROY
        )

        aws_log_analytics_data_function = lambda_.Function(
            self, "aws-log-analytics-data-function",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("functions"),
            handler="aws_analytics.lambda_handler",
            environment={
                'ANALYTICS_DDB_TABLE': ddb_table.table_name
            },
            timeout=Duration.seconds(30),
            layers=[requests_layer]
        )

        cloudfront_logs_bucket.grant_read(aws_log_analytics_data_function)

        aws_log_analytics_data_function.add_event_source(
            lambda_event_sources.S3EventSource(
                cloudfront_logs_bucket,
                events=[s3.EventType.OBJECT_CREATED],
            )
        )

        ddb_table.grant_write_data(aws_log_analytics_data_function)
        


