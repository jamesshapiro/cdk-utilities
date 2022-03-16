#!/usr/bin/env python3
import os

import aws_cdk as cdk

from email_gated_private_website_example.cdk_email_gated_private_site_demo import CDKEmailGatedPrivateSiteDemoStack


app = cdk.App()
CDKEmailGatedPrivateSiteDemoStack(app, "EmailGatedPrivateWebsiteExampleStack",
    env={'region': 'us-east-1'}
)

app.synth()
