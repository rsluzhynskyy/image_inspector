import boto3
import sys
import click
import botocore
import datetime
import csv
import json
import re
from io import BytesIO
import gzip

aws_account = {}
aws_accounts = []
ec2InstancesInfo = []
ec2ImagesInfo = []
ec2InstInfo = {}
ec2ImageInfo = {}
count = 0
profile = "infprod.okta.UsersElevated"
region = "us-east-1"
bucket_name = 'djif-infprod-policyengine'
current_year = str(datetime.date.today().year)
current_month = str(datetime.date.today().month)
current_day = str(datetime.date.today().day)

session = boto3.Session(profile_name=profile, region_name=region)
s3 = session.client('s3')
paginator = s3.get_paginator('list_objects')
result = paginator.paginate(Bucket=bucket_name, Prefix='ConfigLogs/', Delimiter='/')
get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))

for o in result.search('CommonPrefixes'):
    aws_account = {"account_name": (o.get('Prefix')).split('/')[1]}
    aws_accounts.append(aws_account)
    count = count + 1

for o in aws_accounts:
    result = paginator.paginate(Bucket=bucket_name,Prefix="ConfigLogs/"+o['account_name']+"/"+"AWSLogs/",Delimiter='/')
    for k in result.search('CommonPrefixes'):
        account_id = {"account_id": (k.get('Prefix')).split('/')[3]}
        o.update(account_id)

for o in aws_accounts:
    result = paginator.paginate(Bucket=bucket_name,Prefix="ConfigLogs/"+o['account_name']+"/"+"AWSLogs/"+o["account_id"]+"/Config/",Delimiter='/')
    for k in result.search('CommonPrefixes'):
        if re.match("^[a-z]{2}-[a-z]*-[0-9]{1}", (k.get('Prefix')).split('/')[5]):
            aws_region = (k.get('Prefix')).split('/')[5]
            result = paginator.paginate(Bucket=bucket_name,Prefix="ConfigLogs/"+o['account_name']+"/"+"AWSLogs/"+o["account_id"]+"/Config/"+aws_region+"/"+current_year+"/"+current_month+"/"+current_day+"/",Delimiter='/')
            for prefix in result.search('CommonPrefixes'):
                if prefix is not None:
                    if (prefix.get('Prefix')).split('/')[9] == 'ConfigSnapshot':
                        last_added = [obj['Key'] for obj in sorted(s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix.get('Prefix'))['Contents'], key=get_last_modified)][-1]
                        print("Subfolder: {0}".format(prefix.get('Prefix')))
                        print(last_added)
                        s3.download_file(Bucket = bucket_name, Key = last_added, Filename = 'temp.json.gz')
                        with gzip.open('temp.json.gz', 'rb') as f:
                            json_out = json.load(f)
                            for i in json_out['configurationItems']:
                                if i.get('ARN'):
                                    if 'arn:aws:ec2:' in i['ARN'] and 'instance' in i['ARN']:
                                        if i['tags'] is None:
                                            name = "NoName"
                                        else:
                                            try:
                                                if i['tags']['Name']:
                                                    name = i['tags']['Name']
                                            except KeyError as e:
                                                name = "NoName"
                                        ec2InstInfo = {
                                            'ID': i['configuration']['instanceId'],
                                            'Name': name,
                                            'Type': i['configuration']['instanceType'],
                                            'State': i['configuration']['state']['name'],
                                            'Launch Time': i['configuration']['launchTime'],
                                            'Private IP': i['configuration']['privateIpAddress'],
                                            'Image ID': i['configuration']['imageId'],
                                            'Availability Zone': i['availabilityZone'],
                                            'Region': i['awsRegion'],
                                            'Account ID': i['awsAccountId'],
                                            'Account Name': o['account_name'],
                                            'Tags': i['tags']
                                        }
                                if ec2InstInfo:
                                    ec2InstancesInfo.append(ec2InstInfo)
                                    f = open("instances.txt", "a")
                                    f.write(str(ec2InstInfo))
                                    f.write("\n")
                                ec2InstInfo = {}
                            f.close()

                            ec2InstInfo = {}
