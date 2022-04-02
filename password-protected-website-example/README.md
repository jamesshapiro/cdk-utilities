# CDK Password-Protected Website Example

This CDK project creates a simple password-protected website using S3,
CloudFront, and DynamoDB.

Intended use cases are where you want to create an internal website
for your personal use or for internal use at your company, but you
don't want to deal with all of the overhead and hassle of using
an official identity store like Cognito

Steps:

1. cdk synth && cdk deploy. Note that S3 bucket is an output
2. run: `aws s3 cp index.html s3://[BUCKET_NAME]`
3. go to CloudFormation to retrieve the stack name and add it to .cdk-params as: <br /> stack_name=[STACK_NAME]
4. run add_credentials.py to create a username/password combo. You can have multiple. If you don't feel like inventing a password, use the default options to create a secure password on your behalf.
