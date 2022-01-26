#!/usr/bin/env python3
import os
import jsii

import aws_cdk as cdk

from aws_cdk import (
    Aspects,
    CfnResource,
    aws_s3 as s3
)

from cdk_example.cdk_example_stack import CdkExampleAppStack

@jsii.implements(cdk.IAspect)
class ForceDeletion:
    def visit(self, scope):
        if isinstance(scope, CfnResource):
            scope.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

@jsii.implements(cdk.IAspect)
class S3BucketEncryptionEnablement:
    def visit(self, scope):
        if isinstance(scope, s3.CfnBucket):
            if type(scope.bucket_encryption) == type(None):
                print('='*40)
                print('DEFAULT ENCRYPTION MISSING -- APPLYING VIA ASPECTS!')
                print('='*40)
                scope.bucket_encryption = {
                    "serverSideEncryptionConfiguration": [
                        {
                            "serverSideEncryptionByDefault": {
                                "sseAlgorithm": "AES256"
                            }
                        }
                    ]
                }

app = cdk.App()
my_stack = CdkExampleAppStack(app, "CdkAspectsForceS3EncryptionExample",
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

Aspects.of(my_stack).add(S3BucketEncryptionEnablement())
Aspects.of(my_stack).add(ForceDeletion())

app.synth()
