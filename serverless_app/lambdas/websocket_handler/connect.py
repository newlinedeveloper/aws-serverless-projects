import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Handle WebSocket connection
    """
    connection_id = event['requestContext']['connectionId']
    connections_table_name = os.environ['CONNECTIONS_TABLE_NAME']
    
    # Get API Gateway endpoint - construct from request context
    request_context = event['requestContext']
    domain = request_context.get('domainName')
    stage = request_context.get('stage')
    
    # Construct Management API endpoint
    management_endpoint = f"https://{domain}/{stage}"
    
    # Initialize API Gateway Management API client with correct endpoint
    apigateway = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=management_endpoint
    )
    
    table = dynamodb.Table(connections_table_name)
    
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        room = query_params.get('room', 'default')
        user_id = query_params.get('userId', 'anonymous')
        
        # Store connection information
        table.put_item(
            Item={
                'connection_id': connection_id,
                'connected_at': datetime.utcnow().isoformat(),
                'room': room,
                'user_id': user_id,
                'ttl': int((datetime.utcnow().timestamp() + 86400))  # 24 hours TTL
            }
        )
        
        print(f"Connection stored: {connection_id}, user: {user_id}, room: {room}")
        
        # Send welcome message
        try:
            welcome_message = {
                'type': 'welcome',
                'message': 'Connected to chat server',
                'connectionId': connection_id,
                'room': room,
                'userId': user_id
            }
            
            apigateway.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps(welcome_message)
            )
            print(f"Welcome message sent to {connection_id}")
        except Exception as e:
            print(f"Error sending welcome message: {e}")
            print(f"Endpoint: {management_endpoint}")
            print(f"Connection ID: {connection_id}")
            # Don't fail the connection if welcome message fails
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Connected'})
        }
    except Exception as e:
        print(f"Error in connect handler: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

