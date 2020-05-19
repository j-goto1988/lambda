import boto3
import os
import sys
import uuid
from urllib.parse import unquote_plus
from PIL import Image
import PIL.Image
import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        image.thumbnail(tuple(x / 2 for x in image.size))
        image.save(resized_path)

def get_id(table_name):
    table = dynamodb.Table('ids')
    data = table.update_item(
        Key = {
            'table_name': table_name
        },
        UpdateExpression = 'ADD id :id_val',
        ExpressionAttributeValues = {
            ':id_val': 1
        },
        ReturnValues = "UPDATED_NEW"
    )
    
    res = table.get_item(
        Key = {
            'table_name': table_name
        }
    )
    return res['Item']['id']

def insert_dynamodb(id, upload_path):
    table= dynamodb.Table('s3_images')
    now = datetime.datetime.now()
    table.put_item(
        Item = {
            'id': id,
            'upload_path': upload_path,
            'created_at': now.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        tmpkey = key.replace('/', '')
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)
        upload_path = '/tmp/resized-{}'.format(tmpkey)
        s3_client.download_file(bucket, key, download_path)
        resize_image(download_path, upload_path)
        s3_client.upload_file(upload_path, '{}-resized'.format(bucket), key)
        
        id = get_id('s3_images')
        insert_dynamodb(id, upload_path)