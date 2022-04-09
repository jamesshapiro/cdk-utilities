import boto3
import json

import os

ddb_client = boto3.client('dynamodb')
table_name = os.environ['ANALYTICS_DDB_TABLE']
site_list = os.environ['SITE_LIST']
paginator = ddb_client.get_paginator('query')
WEEKLY = 7

def get_traffic_for_date_range(last_n_days):
    sites = site_list.split(',')
    for site in sites:
        response_iterator = paginator.paginate(
            TableName=table_name,
            KeyConditionExpression='#pk1 = :pk1',
            ExpressionAttributeNames={
                '#pk1': 'PK1'
            },
            ExpressionAttributeValues={
                ':pk1': {'S': f'HOST#{site}#PATH#/'}
            },
            ScanIndexForward=True
        )
        for batch in response_iterator:
            for item in batch['Items']:
                print(item)

def lambda_handler(event, context):
    get_traffic_for_date_range(last_n_days=7)
    return {
        'statusCode': 200,
        'body': 'Shalom Haverim!'
    }