import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Handle WebSocket disconnection
    """
    connection_id = event['requestContext']['connectionId']
    connections_table_name = os.environ['CONNECTIONS_TABLE_NAME']
    
    table = dynamodb.Table(connections_table_name)
    
    try:
        # Remove connection from table
        table.delete_item(
            Key={'connection_id': connection_id}
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Disconnected'})
        }
    except Exception as e:
        print(f"Error in disconnect handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

