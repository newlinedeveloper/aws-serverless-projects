import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Update an item
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
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Build update expression
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        if 'name' in body:
            update_expression_parts.append('#name = :name')
            expression_attribute_names['#name'] = 'name'
            expression_attribute_values[':name'] = body['name']
        
        if 'description' in body:
            update_expression_parts.append('#description = :description')
            expression_attribute_names['#description'] = 'description'
            expression_attribute_values[':description'] = body['description']
        
        if 'status' in body:
            update_expression_parts.append('#status = :status')
            expression_attribute_names['#status'] = 'status'
            expression_attribute_values[':status'] = body['status']
        
        if 'price' in body:
            update_expression_parts.append('#price = :price')
            expression_attribute_names['#price'] = 'price'
            expression_attribute_values[':price'] = Decimal(str(body['price']))
        
        if 'tags' in body:
            update_expression_parts.append('#tags = :tags')
            expression_attribute_names['#tags'] = 'tags'
            expression_attribute_values[':tags'] = body['tags']
        
        # Always update updated_at
        update_expression_parts.append('#updated_at = :updated_at')
        expression_attribute_names['#updated_at'] = 'updated_at'
        expression_attribute_values[':updated_at'] = datetime.utcnow().isoformat()
        
        if not update_expression_parts:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No fields to update'})
            }
        
        # Update item
        response = table.update_item(
            Key={'id': item_id},
            UpdateExpression='SET ' + ', '.join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_item = response.get('Attributes', {})
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Item updated successfully',
                'item': updated_item
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

