#!/usr/bin/env python3
import os

import aws_cdk as cdk

from email_gated_private_website_example.email_gated_private_website_example_stack import EmailGatedPrivateWebsiteExampleStack


app = cdk.App()
EmailGatedPrivateWebsiteExampleStack(app, "EmailGatedPrivateWebsiteExampleStack",
    env={'region': 'us-east-1'}
)

app.synth()
