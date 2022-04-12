import boto3
import json
from datetime import datetime, timedelta, date
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

ddb_client = boto3.client('dynamodb')
paginator = ddb_client.get_paginator('query')
ses_client = boto3.client("ses")

table_name = os.environ['ANALYTICS_DDB_TABLE']
site_list = os.environ['SITE_LIST']
email_sender = os.environ['EMAIL_SENDER']
email_recipient = os.environ['EMAIL_RECIPIENT']

WEEKLY = 7

def send_email(ses_client, website, email_recipient, email_sender, analytics_data):
    charset = "UTF-8"
    todays_date = get_today()
    email_lines = [
        '<html>',
        '<head></head>',
        f'<h3>Analytics Summary {todays_date}</h3>',
        '<table style="border: 1px solid;">'
    ]
    colors = ['#F2F2F2','#FFFFFF']
    formatted_data = [f'<tr style="background-color: {colors[idx%2]};">{item}</tr>' for idx, item in enumerate(analytics_data)]
    email_lines.extend(formatted_data)
    email_lines.extend([
        '</table>'
        '<p>or</p>',
        '</body>',
        '</html>'
    ])
    subject_line = f'🖥️📈 {website} Analytics Summary {todays_date}'    
    response = ses_client.send_email(
        Destination={
            'ToAddresses': [
                email_recipient,
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
        Source=f'AWS Analytics <{email_sender}>',
    )
    return response

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
            reported = []
            header_fields = [
                'date',
                #'website',
                'path',
                'ip_address',
                'lat',
                'lon',
                'zip',
                'city',
                'region',
                'region_name',
                #'country',
                'country_code',
                #'timezone',
                'edge_location',
                'time',
                'isp',
                #'as',
                'org'
            ]
            reported.append(f'<td>{"</td><td>".join(header_fields)}</td>')
            for item in in_range:
                relevant_fields = [
                    item['CLOUDFRONT#date']['S'],
                    #item['CLOUDFRONT#x-host-header']['S'],
                    item['CLOUDFRONT#cs-uri-stem']['S'],
                    item['CLOUDFRONT#c-ip']['S'],
                    item['IP_INFO#lat']['S'],
                    item['IP_INFO#lon']['S'],
                    item['IP_INFO#zip']['S'],
                    item['IP_INFO#city']['S'],
                    item['IP_INFO#region']['S'],
                    item['IP_INFO#regionName']['S'],
                    #item['IP_INFO#country']['S'],
                    item['IP_INFO#countryCode']['S'],
                    #item['IP_INFO#timezone']['S'],
                    item['CLOUDFRONT#x-edge-location']['S'],
                    item['CLOUDFRONT#time']['S'],
                    item['IP_INFO#isp']['S'],
                    #item['IP_INFO#as']['S'],
                    item['IP_INFO#org']['S']
                ]
                reported.append(f'<td>{"</td><td>".join(relevant_fields)}</td>')
            items.extend(reported)
            if out_of_range or not in_range:
                break
        result[site] = items
        send_email(ses_client, site, email_recipient, email_sender, items)
    return result

def lambda_handler(event, context):
    result = get_visits(7, site_list)
    print(f'{result=}')
    return {
        'statusCode': 200,
        'body': 'Shalom Haverim!'
    }