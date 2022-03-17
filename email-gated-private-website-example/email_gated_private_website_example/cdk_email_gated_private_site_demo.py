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
        pub_key = cloudfront.PublicKey(self, f"{app_name}MyPubKey",
            encoded_key=public_key
        )

        key_group = cloudfront.KeyGroup(self, f"{app_name}MyKeyGroup",
            items=[pub_key]
        )

        distribution = cloudfront.Distribution(
            self, f'{app_name}-distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                trusted_key_groups=[key_group]
                # edge_lambdas=[
                #     cloudfront.EdgeLambda(
                #         function_version=authorizer_function.current_version,
                #         event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                #     )
                # ]
            ),
            additional_behaviors={
                # public behavior 1
                "/login.html": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
                ),
                # public behavior 2
                "/assets/*": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
                ),
                # public behavior 3 -- tied to Lambda@Edge function eventually
                "/login": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
                ),
                # private behavior 1 -- tied to Lambda@Edge function eventually
                "/auth": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(site_bucket),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    trusted_key_groups=[key_group]
                ),
            },
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

