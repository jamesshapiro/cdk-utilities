from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as certificatemanager,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_cloudfront_origins as origins,
)
from constructs import Construct

class S3CloudfrontSslExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        with open('.cdk-params') as f:
            lines = f.read().splitlines()
            # .cdk-params should be of the form:
            # key=value
            subdomain_name = [line for line in lines if line.startswith('subdomain_name')][0].split('=')[1]
            hosted_zone_id = [line for line in lines if line.startswith('hosted_zone_id')][0].split('=')[1]
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
            certificate=certificate
        )

        a_record_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(distribution))
        
        route53.ARecord(
            self, 'alias-record',
            zone=zone,
            target=a_record_target,
            record_name=subdomain_name
        )

