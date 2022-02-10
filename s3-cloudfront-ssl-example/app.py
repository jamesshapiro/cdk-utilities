#!/usr/bin/env python3
import jsii

import aws_cdk as cdk

from aws_cdk import (
    Aspects,
    CfnResource
)

@jsii.implements(cdk.IAspect)
class ForceDeletion:
    def visit(self, scope):
        if isinstance(scope, CfnResource):
            scope.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

from s3_cloudfront_ssl_example.s3_cloudfront_ssl_example_stack import S3CloudfrontSslExampleStack


app = cdk.App()
my_stack = S3CloudfrontSslExampleStack(app, "S3CloudfrontSslExampleStack")
Aspects.of(my_stack).add(ForceDeletion())

app.synth()
