import boto3
import os

ses_client = boto3.client("ses")
dynamodb_client = boto3.client("dynamodb")

approve_comment_endpoint = os.environ['APPROVE_COMMENT_ENDPOINT']
reject_comment_endpoint = os.environ['REJECT_COMMENT_ENDPOINT']
unsubscribe_endpoint = os.environ['REJECT_COMMENT_ENDPOINT']

def send_email(ses_client, comment_validator_email, recipient_email, comment_text, token, my_ulid, commenter_email=None):
    token = token.replace('+','%2B')
    charset = "UTF-8"
    email_lines = [
        '<html>',
        '<head></head>',
        '<h3>Do you want to approve this comment?</h3>',
        f'<p>Comment: {comment_text}</p>',
        f'<p><a href="{approve_comment_endpoint}?token={token}">CONFIRM</a> or <a href="{reject_comment_endpoint}?token={token}">DENY</a></p>',
        '<p>or</p>',
        '<p><a href="{unsubscribe_endpoint}">Unsubscribe Forever</p>',
        '</body>',
        '</html>'
    ]
    subject_line = f'Confirm JS Comment: {my_ulid[-6:]}'
    if commenter_email:
        email_lines[3:3] = [f'<p>By: {commenter_email}</p>']
        subject_line = f'Review JS Comment: {my_ulid[-6:]}'
    
    
    response = ses_client.send_email(
        Destination={
            'ToAddresses': [
                recipient_email,
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': charset,
                    'Data': '\n'.join(email_lines),
                }
            },
            'Subject': {
                'Charset': charset,
                'Data': subject_line
            },
        },
        Source=f'JS Comments <{comment_validator_email}>',
    )
    return response

def lambda_handler(event, context):
    commenter_email = None
    print(f'{event=}')
    if event['is_moderator'] == 'true':
        commenter_email = event['commenter_email']
    my_input = event['input']
    recipient_email = my_input['recipient_email']
    comment_validator_email = my_input['comment_validator_email']
    comment_text = my_input['comment_text']
    token = event['token']
    my_ulid = my_input['ulid']['Payload']['ulid']
    response = send_email(ses_client, comment_validator_email, recipient_email, comment_text, token, my_ulid, commenter_email)
    print(response)
    return