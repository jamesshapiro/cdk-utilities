import boto3
import re
import datetime
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
import datetime
from botocore.signers import CloudFrontSigner

email_address_regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

EDGE_REGION  = 'us-east-1'
key_id       = os.environ['KEY_ID']
sender_email = os.environ['SENDER_EMAIL']
ses_client   = boto3.client('ses', region_name=EDGE_REGION)
ssm_client   = boto3.client('ssm', region_name=EDGE_REGION)
# TODO: Define in SSM / possibly replace with CF URL
SIGNING_URL = os.environ['SIGNING_URL']
APP_NAME = 'athens-email-gated-demo'
PRIVATE_KEY_PARAM_NAME = f'{APP_NAME}-private-key'
PUBLIC_KEY_PARAM_NAME = f'{APP_NAME}-public-key'
private_key = ssm_client.get_parameter(Name=PRIVATE_KEY_PARAM_NAME, WithDecryption=False)['Parameter']['Value']
public_key  = ssm_client.get_parameter(Name=PUBLIC_KEY_PARAM_NAME, WithDecryption=False)['Parameter']['Value']

signing_url = f'https://{SIGNING_URL}/auth'
content = """<\!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Successful request</title>
  </head>
  <body>
    <p>Email with authentication token sent</p>
  </body>
</html>"""

response = {
    'status': '200',
    'statusDescription': 'OK',
    'body': content,
    'headers': {
        'cache-control': [
            {'key': 'Cache-Control', 'value': 'max-age=100'}
        ],
        'content-type': [
            {'key': 'Content-Type', 'value': 'text/html'}
        ]
    }
}
error = {
    'status': '204',
    'statusDescription': 'Error',
    'body': 'Email is not valid',
    'bodyEncoding': 'text',
    'headers': {
        'content-type': [
            {'key': 'Content-Type', 'value': 'text/html'}
        ]
    }
}
cache = {}

def validate_email(allowed_domains, email):
    if len(email.split('@')) != 2:
        return False
    _, domain = email.split('@')
    return re.fullmatch(email_address_regex, email) and domain in allowed_domains

def load_parameter(name, client, with_decryption=False):
    response = client.get_parameter(
        Name=name,
        WithDecryption=with_decryption
    )
    return response['Parameter']['Value']

def rsa_signer(message):
    PRIVATE_KEY_PARAM_NAME = f'{APP_NAME}-private-key'
    sk = ssm_client.get_parameter(Name=PRIVATE_KEY_PARAM_NAME, WithDecryption=False)['Parameter']['Value']
    with open('/tmp/sk', 'w') as wf:
        wf.write(sk)
    with open('/tmp/sk', 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
        return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

def send_email(public_key, private_key, email, key_id):
    cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)
    current_time = datetime.datetime.utcnow()
    expire_date = current_time + datetime.timedelta(minutes = 5)
    signed_url = cloudfront_signer.generate_presigned_url(signing_url, date_less_than=expire_date)
    print(signed_url)
    response = ses_client.send_email(
        Source=sender_email,
        Destination={
            'ToAddresses': [
                email,
            ]
        },
        Message={
            'Subject': {
                'Data': f'Signed URL! {signed_url}',
            },
            'Body': {
                'Text': {
                    'Data': signed_url,
                }
            }
        }
    )

def lambda_handler(event, context):
    if 'queryStringParameters' not in event or 'email' not in event['queryStringParameters']:
        return error
    email = event['queryStringParameters']['email']
    allowed_domains = 'gmail.com'
    if not validate_email(allowed_domains, email):
        return error
    send_email(public_key, private_key, email, key_id)
    return response

"""
    const signedUrl = cloudFront.getSignedUrl({
        url: signingUrl,
        expires: Math.floor((new Date()).getTime() / 1000) + (60 * 60 * 1) // Current Time in UTC + time in seconds, (60 * 60 * 1 = 1 hour)
    });

    const params = {
        Destination: {
            ToAddresses: [
                email
            ]
        },
        Message: {
            Body: {
                Html: {
                    Data: signedUrl,
                    Charset: 'UTF-8'
                }
            },
            Subject: {
                Data: '[stars on AWS] Login credentials for ' + email,
                Charset: 'UTF-8'
            }
        },
        Source: SENDER
    };
    await ses.sendEmail(params).promise();
};
"""