from aws_cdk import (
    Stack,
    aws_s3 as s3,
    Aws, CfnOutput, Duration,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as certificatemanager,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
)
from constructs import Construct

class CDKEmailGatedPrivateSiteDemoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        with open(".cdk-params") as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form: key_name=value
            subdomain = [line for line in lines if line.startswith('subdomain=')][0].split('=')[1]
            hosted_zone_id = [line for line in lines if line.startswith('hosted_zone_id=')][0].split('=')[1]
            zone_name = [line for line in lines if line.startswith('zone_name=')][0].split('=')[1]

        app_name = 'athens-email-gated-demo'

        site_bucket = s3.Bucket(
            self, f'{app_name}-bucket',
        )

        domain_names = [subdomain]

        zone = route53.HostedZone.from_hosted_zone_attributes(self, "HostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=zone_name
        )

        certificate = certificatemanager.DnsValidatedCertificate(
            self, f'{subdomain}-certificate',
            domain_name=subdomain,
            hosted_zone=zone
        )

        distribution = cloudfront.Distribution(
            self, f'{app_name}-distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                # edge_lambdas=[
                #     cloudfront.EdgeLambda(
                #         function_version=authorizer_function.current_version,
                #         event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                #     )
                # ]
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                )
            ],
            comment=f'{app_name} S3 HTTPS',
            default_root_object='index.html',
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
