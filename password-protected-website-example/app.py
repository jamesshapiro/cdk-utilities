#!/usr/bin/env python3
import os

import aws_cdk as cdk

from password_protected_website_example.password_protected_website_example_stack import PasswordProtectedWebsiteExampleStack

app = cdk.App()
PasswordProtectedWebsiteExampleStack(app, "PasswordProtectedWebsiteExampleStack",
    env={'region': 'us-east-1'}
)

app.synth()
