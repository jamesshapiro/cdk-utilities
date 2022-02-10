import aws_cdk as core
import aws_cdk.assertions as assertions

from s3_cloudfront_ssl_example.s3_cloudfront_ssl_example_stack import S3CloudfrontSslExampleStack

# example tests. To run these tests, uncomment this file along with the example
# resource in s3_cloudfront_ssl_example/s3_cloudfront_ssl_example_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = S3CloudfrontSslExampleStack(app, "s3-cloudfront-ssl-example")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
