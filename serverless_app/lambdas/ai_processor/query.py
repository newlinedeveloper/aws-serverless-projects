import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Query AI processing results from DynamoDB
    """
    table_name = os.environ['RESULTS_TABLE_NAME']
    table = dynamodb.Table(table_name)
    
    query_params = event.get('queryStringParameters') or {}
    file_name = query_params.get('file_name', '')
    
    try:
        if file_name:
            # Query specific file
            response = table.query(
                KeyConditionExpression='file_name = :fn',
                ExpressionAttributeValues={':fn': file_name},
                ScanIndexForward=False,
                Limit=1
            )
            items = response.get('Items', [])
        else:
            # Scan all items (limit to 100)
            response = table.scan(Limit=100)
            items = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'count': len(items),
                'results': items
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

