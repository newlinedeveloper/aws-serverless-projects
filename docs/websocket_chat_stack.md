# WebSocket Chat Stack

## Overview

The WebSocket Chat Stack implements a real-time chat application using API Gateway WebSocket API, Lambda functions for connection management and message handling, and DynamoDB for storing connections and messages. It supports multiple chat rooms, user presence, and message broadcasting.

## Architecture

```
Client → API Gateway WebSocket → Lambda Handlers → DynamoDB
                ↓
        Connection Management
                ↓
        Message Broadcasting
```

## Resources

### 1. API Gateway WebSocket API
- **Name**: `chat-websocket-api`
- **Stage**: `prod`
- **Routes**:
  - `$connect`: Handle new connections
  - `$disconnect`: Handle disconnections
  - `$default`: Handle messages
- **Purpose**: Manages WebSocket connections and message routing

### 2. DynamoDB Tables

#### Connections Table
- **Name**: `websocket-connections`
- **Partition Key**: `connection_id` (String)
- **TTL**: Enabled (auto-cleanup stale connections)
- **Billing**: Pay-per-request
- **Purpose**: Tracks active WebSocket connections

#### Messages Table
- **Name**: `websocket-messages`
- **Partition Key**: `room` (String)
- **Sort Key**: `timestamp` (String)
- **GSI**: `user-timestamp-index` (query by user_id)
- **TTL**: Enabled (auto-cleanup old messages)
- **Billing**: Pay-per-request
- **Purpose**: Stores chat messages

### 3. Lambda Functions

#### Connect Handler
- **Name**: `websocket-connect`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Purpose**: Handles new WebSocket connections, stores connection info, sends welcome message

#### Disconnect Handler
- **Name**: `websocket-disconnect`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Purpose**: Cleans up connection records when client disconnects

#### Default Handler
- **Name**: `websocket-default`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Purpose**: Processes incoming messages, stores them, and broadcasts to all connected clients

## Data Flow

1. **Connection**:
   - Client connects to WebSocket endpoint
   - `$connect` route triggers Connect Lambda
   - Connection ID stored in DynamoDB
   - Welcome message sent to client

2. **Message Handling**:
   - Client sends message via WebSocket
   - `$default` route triggers Default Lambda
   - Message parsed and validated
   - Message stored in DynamoDB
   - Message broadcasted to all connected clients in the same room

3. **Disconnection**:
   - Client disconnects
   - `$disconnect` route triggers Disconnect Lambda
   - Connection record removed from DynamoDB

## Message Format

### Incoming Message (Client → Server)
```json
{
  "action": "sendMessage",
  "room": "general",
  "user_id": "user123",
  "message": "Hello, world!"
}
```

### Outgoing Message (Server → Client)
```json
{
  "action": "message",
  "room": "general",
  "user_id": "user123",
  "message": "Hello, world!",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.websocket_chat_stack import WebSocketChatStack
   
   WebSocketChatStack(app, "WebSocketChatStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth WebSocketChatStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy WebSocketChatStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name WebSocketChatStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Get WebSocket Endpoint

```bash
WS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name WebSocketChatStack \
  --query "Stacks[0].Outputs[?OutputKey=='WebSocketApiEndpoint'].OutputValue" \
  --output text)

echo "WebSocket Endpoint: $WS_ENDPOINT"
```

### 2. Test with Python Script

```python
import websocket
import json
import time
import threading

ws_endpoint = "wss://<api-id>.execute-api.<region>.amazonaws.com/prod"

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connected!")
    # Wait for welcome message
    time.sleep(2)
    
    # Send a test message
    message = {
        "action": "sendMessage",
        "room": "general",
        "user_id": "test-user-1",
        "message": "Hello from Python!"
    }
    ws.send(json.dumps(message))
    print(f"Sent: {message}")

# Create WebSocket connection
ws = websocket.WebSocketApp(
    ws_endpoint,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Run in a separate thread
ws.run_forever()
```

### 3. Test with wscat (Node.js tool)

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c $WS_ENDPOINT

# After connecting, send a message:
{"action":"sendMessage","room":"general","user_id":"user123","message":"Hello!"}
```

### 4. Test with Complete Test Script

```bash
python tests/websocket_chat/test_websocket_chat.py
```

### 5. Verify Data in DynamoDB

**Check Connections:**
```bash
aws dynamodb scan \
  --table-name websocket-connections \
  --limit 10
```

**Check Messages:**
```bash
aws dynamodb scan \
  --table-name websocket-messages \
  --limit 10
```

**Query Messages by User:**
```bash
aws dynamodb query \
  --table-name websocket-messages \
  --index-name user-timestamp-index \
  --key-condition-expression "user_id = :user_id" \
  --expression-attribute-values '{":user_id":{"S":"user123"}}'
```

### 6. Test Multiple Clients

Open multiple terminal windows and connect to the same WebSocket endpoint. Messages sent from one client should be received by all other connected clients in the same room.

## Features

### Chat Rooms
- Messages are organized by room
- Clients can join multiple rooms
- Messages are only broadcasted to clients in the same room

### User Presence
- Connection tracking via DynamoDB
- Automatic cleanup of stale connections via TTL

### Message History
- All messages stored in DynamoDB
- Queryable by room or user
- TTL for automatic cleanup of old messages

## API Gateway WebSocket API Details

### Connection Management
- API Gateway maintains WebSocket connections
- Connection ID is unique per connection
- Connection ID is used to send messages back to clients

### Message Broadcasting
- Lambda uses `ApiGatewayManagementApi` to send messages
- Endpoint URL is constructed from request context
- Messages are sent to all active connections in a room

## Monitoring

### CloudWatch Logs
- Lambda function logs for each handler
- Connection and disconnection events
- Message processing logs

### CloudWatch Metrics
- API Gateway WebSocket metrics
- Lambda invocation metrics
- DynamoDB read/write metrics

## Cost Optimization

- **API Gateway**: Pay per message and connection-minute
- **Lambda**: Pay per invocation and compute time
- **DynamoDB**: Pay-per-request pricing
- **Data Transfer**: Pay for data transfer out

## Troubleshooting

### Connection Fails
- Verify WebSocket endpoint URL
- Check API Gateway stage is deployed
- Verify IAM permissions for Lambda

### Messages Not Received
- Check Lambda logs for errors
- Verify connection ID is stored in DynamoDB
- Check API Gateway Management API permissions
- Verify endpoint URL construction in Lambda

### Welcome Message Not Received
- Check Connect Lambda logs
- Verify connection record in DynamoDB
- Check API Gateway Management API endpoint

## Security Considerations

- **Authentication**: Add authentication in `$connect` route
- **Authorization**: Validate user permissions before processing messages
- **Rate Limiting**: Configure API Gateway throttling
- **Input Validation**: Validate message format and content

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy WebSocketChatStack
```

**Note**: DynamoDB tables with TTL enabled will automatically clean up old records.

