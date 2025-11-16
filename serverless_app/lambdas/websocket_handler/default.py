import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Handle WebSocket messages (default route)
    """
    connection_id = event['requestContext']['connectionId']
    connections_table_name = os.environ['CONNECTIONS_TABLE_NAME']
    messages_table_name = os.environ['MESSAGES_TABLE_NAME']
    
    # Get API Gateway endpoint from request context
    request_context = event['requestContext']
    domain = request_context.get('domainName')
    stage = request_context.get('stage')
    management_endpoint = f"https://{domain}/{stage}"
    
    apigateway = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=management_endpoint
    )
    
    connections_table = dynamodb.Table(connections_table_name)
    messages_table = dynamodb.Table(messages_table_name)
    
    try:
        # Parse message body
        body = json.loads(event.get('body', '{}'))
        message_type = body.get('type', 'message')
        message_content = body.get('message', '')
        room = body.get('room', 'default')
        
        # Get connection info
        connection_response = connections_table.get_item(
            Key={'connection_id': connection_id}
        )
        
        if 'Item' not in connection_response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Connection not found'})
            }
        
        connection_info = connection_response['Item']
        user_id = connection_info.get('user_id', 'anonymous')
        
        # Store message in DynamoDB
        message_id = f"{connection_id}_{datetime.utcnow().timestamp()}"
        messages_table.put_item(
            Item={
                'message_id': message_id,
                'room': room,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'connection_id': connection_id,
                'message': message_content,
                'type': message_type,
                'ttl': int((datetime.utcnow().timestamp() + 86400 * 7))  # 7 days TTL
            }
        )
        
        # Broadcast message to all connections in the same room
        if message_type == 'message':
            broadcast_message(apigateway, connections_table, room, {
                'type': 'message',
                'room': room,
                'user_id': user_id,
                'message': message_content,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Message processed'})
        }
        
    except Exception as e:
        print(f"Error in default handler: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def broadcast_message(apigateway, connections_table, room, message):
    """
    Broadcast message to all connections in a room
    """
    try:
        # Scan connections table for room members
        response = connections_table.scan(
            FilterExpression='room = :room',
            ExpressionAttributeValues={':room': room}
        )
        
        for connection in response.get('Items', []):
            try:
                apigateway.post_to_connection(
                    ConnectionId=connection['connection_id'],
                    Data=json.dumps(message)
                )
            except Exception as e:
                # Connection may have been closed
                print(f"Error sending to {connection['connection_id']}: {e}")
                # Optionally remove stale connection
                try:
                    connections_table.delete_item(
                        Key={'connection_id': connection['connection_id']}
                    )
                except:
                    pass
                    
    except Exception as e:
        print(f"Error broadcasting message: {e}")

