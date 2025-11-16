import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Create a new item
    """
    table_name = os.environ['TABLE_NAME']
    table = dynamodb.Table(table_name)
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        if 'name' not in body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Name is required'})
            }
        
        # Generate item ID
        item_id = f"item_{datetime.utcnow().timestamp()}"
        
        # Create item
        item = {
            'id': item_id,
            'name': body['name'],
            'description': body.get('description', ''),
            'status': body.get('status', 'active'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Add optional fields
        if 'price' in body:
            item['price'] = Decimal(str(body['price']))
        
        if 'tags' in body:
            item['tags'] = body['tags']
        
        # Save to DynamoDB
        table.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Item created successfully',
                'item': {k: str(v) if isinstance(v, Decimal) else v for k, v in item.items()}
            }, default=str)
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

