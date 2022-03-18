import boto3
import re
import datetime

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner

email_address_regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

EDGE_REGION = 'us-east-1'
ses_client = boto3.client('ses', region_name=EDGE_REGION)
ssm_client = boto3.client('ssm', region_name=EDGE_REGION)
# TODO: Define in SSM
SENDER = 'no-reply@mail.weakerpotions.com'
# TODO: Define in SSM
SIGNING_URL = 'https://email-gated-private-site-demo.weakerpotions.com'
APP_NAME = 'athens-email-gated-demo'
PRIVATE_KEY_PARAM_NAME = f'{APP_NAME}-private-key'
PUBLIC_KEY_PARAM_NAME = f'{APP_NAME}-public-key'
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

def send_email(public_key, private_key, email):
    pass

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']

"""
const sendEmail = async(publicKey, privateKey, email) => {
    const cloudFront = new AWS.CloudFront.Signer(publicKey, privateKey);
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

exports.handler = async(event, context, callback) => {
    if (cache.allowedDomains == null) cache.allowedDomains = loadParameter('allowedDomains')
    if (cache.publicKey == null) cache.publicKey = loadParameter('publicKey');
    if (cache.privateKey == null) cache.privateKey = loadParameter('privateKey', true);

    const { allowedDomains, publicKey, privateKey } = cache;

    const request = event.Records[0].cf.request;
    if (request.method === 'GET') {
        const parameters = new URLSearchParams(request.querystring);
        if (parameters.has('email') === false) return error;
        const email = parameters.get('email');
        if (!validateEmail(allowedDomains, email)) return error;
        else {
            await sendEmail(publicKey, privateKey, email);
            return response;
        }
    }
    return error;
};"""