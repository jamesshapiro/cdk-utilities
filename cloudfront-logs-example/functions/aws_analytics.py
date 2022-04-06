import boto3
import json
import io
import gzip
import json
import requests

from urllib.parse import unquote_plus
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = unquote_plus(record['object']['key'])
    #print(f'{event=}')
    #print(f'{bucket}{key}')
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read()
    #with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as f:
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as f:
        cloudfront_logs = f.read().splitlines()
    cloudfront_logs = [line.decode("utf-8") for line in cloudfront_logs]
    version_line = cloudfront_logs[0]
    fields_key = cloudfront_logs[1]
    log_keys = fields_key.split()[1:]
    log_entries = cloudfront_logs[2:]
    for log in log_entries:
        log_values = log.split()
        record = dict(zip(log_keys, log_values))
        for key in record:
            print(f'>    {key}: {record[key]}')
        ip_address = record['c-ip']
        r = requests.get(f'http://ip-api.com/json/{ip_address}')
        ip_info = json.loads(r.text)
        for key in ip_info:
            print(f'~ {key}: {ip_info[key]}')
        print(ip_info)
        print('\n===\n=========================\n===\n')
    return {
        'statusCode': 200,
        'body': 'Shalom Haverim!'
    }