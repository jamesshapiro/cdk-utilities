import boto3
import json
import io
import gzip
import json
import requests
import os

from urllib.parse import unquote_plus
s3_client = boto3.client('s3')
ddb_client = boto3.client('dynamodb')
table_name = os.environ['ANALYTICS_DDB_TABLE']

def lambda_handler(event, context):
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = unquote_plus(record['object']['key'])
    response = s3_client.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read()
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
        host = record['x-host-header']
        path = record['cs-uri-stem']
        date_time = f'{record["date"]}_{record["time"]}'
        request_id = record['x-edge-request-id']
        pk1 = f'HOST#{host}#PATH#{path}'
        sk1 = f'DATETIME#{date_time}#REQUEST_ID#{request_id}'
        record_kwargs = {f'CLOUDFRONT#{key}': {'S': str(record[key])} for key in record}
        ip_info_kwargs = {f'IP_INFO#{key}': {'S': str(ip_info[key])} for key in ip_info}
        kwargs = {
            'PK1': {'S': pk1},
            'SK1': {'S': sk1},
        }
        kwargs.update(record_kwargs)
        kwargs.update(ip_info_kwargs)
        ddb_client.put_item(
            TableName=table_name,
            Item=kwargs
        )
    return {
        'statusCode': 200,
        'body': 'Shalom Haverim!'
    }