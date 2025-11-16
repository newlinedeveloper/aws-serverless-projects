import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    List all items with optional filtering
    """
    table_name = os.environ['TABLE_NAME']
    table = dynamodb.Table(table_name)
    
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        status = query_params.get('status', '')
        limit = int(query_params.get('limit', 100))
        
        # Scan table with optional filter
        if status:
            response = table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status},
                Limit=limit
            )
        else:
            response = table.scan(Limit=limit)
        
        items = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'count': len(items),
                'items': items
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

