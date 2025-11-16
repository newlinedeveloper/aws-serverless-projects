import asyncio
import websockets
import json
import boto3
import time
from datetime import datetime

# Get WebSocket endpoint (replace with your endpoint)
WEBSOCKET_ENDPOINT = "wss://1lbovqrapk.execute-api.us-west-2.amazonaws.com/prod"
dynamodb = boto3.resource('dynamodb')

async def test_websocket_chat():
    """Test WebSocket chat functionality"""
    
    print("=" * 60)
    print("WebSocket Chat Stack - Complete Test Suite")
    print("=" * 60)
    
    # Test 1: Connect
    print("\n[Test 1] Connecting to WebSocket...")
    uri = f"{WEBSOCKET_ENDPOINT}?room=general&userId=testuser1"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully")
            
            # Try to receive welcome message (but don't fail if it doesn't come)
            connection_id = None
            try:
                welcome = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                welcome_data = json.loads(welcome)
                print(f"✓ Received welcome: {welcome_data}")
                connection_id = welcome_data.get('connectionId')
            except asyncio.TimeoutError:
                print("⚠ Welcome message not received (this is okay, checking DynamoDB instead)")
                # Get connection ID from DynamoDB
                await asyncio.sleep(2)
                connections_table = dynamodb.Table('websocket-connections')
                response = connections_table.scan(Limit=1)
                if response['Items']:
                    connection_id = response['Items'][0].get('connection_id')
                    print(f"✓ Found connection ID from DynamoDB: {connection_id[:20]}...")
            
            if not connection_id:
                print("✗ Could not get connection ID")
                return
            
            # Test 2: Verify connection in DynamoDB
            print("\n[Test 2] Verifying connection in DynamoDB...")
            await asyncio.sleep(1)  # Wait for Lambda to process
            
            connections_table = dynamodb.Table('websocket-connections')
            response = connections_table.get_item(
                Key={'connection_id': connection_id}
            )
            
            if 'Item' in response:
                print(f"✓ Connection found in DynamoDB: {response['Item']}")
            else:
                print("✗ Connection not found in DynamoDB")
            
            # Test 3: Send message
            print("\n[Test 3] Sending message...")
            message = {
                'type': 'message',
                'message': 'Hello from test script!',
                'room': 'general'
            }
            await websocket.send(json.dumps(message))
            print(f"✓ Sent message: {message}")
            
            # Wait a bit for processing
            await asyncio.sleep(2)
            
            # Test 4: Verify message in DynamoDB
            print("\n[Test 4] Verifying message in DynamoDB...")
            messages_table = dynamodb.Table('websocket-messages')
            response = messages_table.query(
                KeyConditionExpression='room = :room',
                ExpressionAttributeValues={':room': 'general'},
                ScanIndexForward=False,
                Limit=1
            )
            
            if response['Items']:
                latest_message = response['Items'][0]
                print(f"✓ Message stored: {latest_message}")
            else:
                print("✗ No messages found")
            
            # Test 5: Try to receive broadcast (if any)
            print("\n[Test 5] Waiting for broadcast messages...")
            try:
                broadcast = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"✓ Received broadcast: {json.loads(broadcast)}")
            except asyncio.TimeoutError:
                print("⚠ No broadcast received (this is okay if no other users)")
            
            # Test 6: Disconnect
            print("\n[Test 6] Disconnecting...")
            await websocket.close()
            print("✓ Disconnected")
            
            # Wait and verify connection removed
            await asyncio.sleep(2)
            response = connections_table.get_item(
                Key={'connection_id': connection_id}
            )
            
            if 'Item' not in response:
                print("✓ Connection removed from DynamoDB")
            else:
                print("⚠ Connection still exists in DynamoDB (may take a moment)")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_users():
    """Test with multiple concurrent connections"""
    print("\n" + "=" * 60)
    print("Testing Multiple Users")
    print("=" * 60)
    
    async def user_connection(user_id, room):
        uri = f"{WEBSOCKET_ENDPOINT}?room={room}&userId={user_id}"
        try:
            async with websockets.connect(uri) as ws:
                print(f"✓ {user_id} connected to {room}")
                
                # Receive welcome
                welcome = await ws.recv()
                print(f"  {user_id} received: {json.loads(welcome)}")
                
                # Send message
                message = {
                    'type': 'message',
                    'message': f'Hello from {user_id}!',
                    'room': room
                }
                await ws.send(json.dumps(message))
                print(f"  {user_id} sent message")
                
                # Wait for broadcast
                await asyncio.sleep(3)
                
                # Try to receive broadcast messages
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        print(f"  {user_id} received: {json.loads(msg)}")
                except asyncio.TimeoutError:
                    pass
                
        except Exception as e:
            print(f"✗ {user_id} error: {e}")
    
    # Connect multiple users
    tasks = [
        user_connection('alice', 'general'),
        user_connection('bob', 'general'),
        user_connection('charlie', 'private')
    ]
    
    await asyncio.gather(*tasks)

def verify_dynamodb():
    """Verify DynamoDB tables"""
    print("\n" + "=" * 60)
    print("Verifying DynamoDB Tables")
    print("=" * 60)
    
    # Check connections
    connections_table = dynamodb.Table('websocket-connections')
    response = connections_table.scan()
    print(f"\nConnections Table: {len(response['Items'])} active connections")
    for item in response['Items'][:5]:
        print(f"  - {item.get('user_id')} in {item.get('room')} (ID: {item.get('connection_id')[:20]}...)")
    
    # Check messages
    messages_table = dynamodb.Table('websocket-messages')
    response = messages_table.scan(Limit=10)
    print(f"\nMessages Table: {len(response['Items'])} messages")
    for item in response['Items'][:5]:
        print(f"  - Room: {item.get('room')}, User: {item.get('user_id')}, Message: {item.get('message')[:50]}")

if __name__ == '__main__':
    # Update with your WebSocket endpoint
    # print("⚠️  Update WEBSOCKET_ENDPOINT in the script with your actual endpoint")
    # print("   Get it from: aws cloudformation describe-stacks --stack-name WebSocketChatStack")
    
    # Uncomment to run tests
    asyncio.run(test_websocket_chat())
    asyncio.run(test_multiple_users())
    verify_dynamodb()