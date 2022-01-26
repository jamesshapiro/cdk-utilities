from aws_cdk import (
    Stack,
    aws_s3 as s3,
)
import os

from constructs import Construct

class CdkExampleAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket_1 = s3.Bucket(
            self, "my-encrypted-bucket",
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        bucket_1 = s3.Bucket(
            self, "my-unencrypted-bucket",
        )
