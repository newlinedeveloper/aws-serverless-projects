import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Get an item by ID
    """
    table_name = os.environ['TABLE_NAME']
    table = dynamodb.Table(table_name)
    
    try:
        # Get item ID from path parameters
        item_id = event.get('pathParameters', {}).get('id', '')
        
        if not item_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Item ID is required'})
            }
        
        # Get item from DynamoDB
        response = table.get_item(Key={'id': item_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Item not found'})
            }
        
        item = response['Item']
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(item, default=str)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

