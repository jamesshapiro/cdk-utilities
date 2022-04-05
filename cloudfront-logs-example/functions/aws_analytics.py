import boto3
import json
import io
import gzip
import json

from urllib.parse import unquote_plus
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = unquote_plus(record['object']['key'])
    print(f'{event=}')
    print(f'{bucket}{key}')
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read()
    #with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as f:
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as f:
        cloudfront_logs = f.read().splitlines()
    cloudfront_logs = [line.decode("utf-8") for line in cloudfront_logs]
    for log in cloudfront_logs:
        print(log)
    return {
        'statusCode': 200,
        'body': cloudfront_logs
    }