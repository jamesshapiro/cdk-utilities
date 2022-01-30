import aws_cdk as core
import aws_cdk.assertions as assertions

from step_functions_example.step_functions_example_stack import StepFunctionsExampleStack

# example tests. To run these tests, uncomment this file along with the example
# resource in step_functions_example/step_functions_example_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = StepFunctionsExampleStack(app, "step-functions-example")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
