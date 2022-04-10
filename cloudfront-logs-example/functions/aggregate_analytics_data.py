import boto3
import json
from datetime import datetime, timedelta, date

def get_month_to_date():
    start_date = get_start_of_month()
    end_date = get_today()
    if start_date == end_date:
        end_of_month = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=-1)
        begin_of_month = end_of_month.replace(day=1)
        return begin_of_month.date().isoformat(), end_date
    return start_date, end_date

def get_start_of_month():
    return date.today().replace(day=1).isoformat()

def get_last_n_days(n):
    return (date.today() - timedelta(days=n)).isoformat()

def get_today():
    return date.today().isoformat()

def get_yesterday():
    return (date.today() - timedelta(days=1)).isoformat()

import os

ddb_client = boto3.client('dynamodb')
table_name = os.environ['ANALYTICS_DDB_TABLE']
site_list = os.environ['SITE_LIST']
paginator = ddb_client.get_paginator('query')
WEEKLY = 7

def get_visits(last_n_days, site_list):
    sites = site_list.split(',')
    result = {}
    cutoff = get_last_n_days(last_n_days)
    print(f'{cutoff=}')
    for site in sites:
        items = []
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
            batch_items = batch['Items']
            in_range = [item for item in batch_items if item['SK1']['S'] >= f'DATETIME#{cutoff}_']
            out_of_range = [item for item in batch_items if item['SK1']['S'] < f'DATETIME#{cutoff}_']
            items.extend(in_range)
            if out_of_range or not in_range:
                break
        result[site] = items
    return result


def lambda_handler(event, context):
    result = get_visits(2, site_list)
    print(f'{result=}')
    return {
        'statusCode': 200,
        'body': 'Shalom Haverim!'
    }