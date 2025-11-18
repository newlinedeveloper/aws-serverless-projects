# Serverless REST API Stack

## Overview

The Serverless REST API Stack implements a production-ready REST API backend with authentication using AWS API Gateway, Lambda functions for CRUD operations, DynamoDB for data storage, and Amazon Cognito for user authentication and authorization.

## Architecture

```
Client → API Gateway → Cognito Authorizer → Lambda Functions → DynamoDB
                              ↓
                        User Pool
```

## Resources

### 1. API Gateway REST API
- **Name**: `serverless-api`
- **Stage**: `prod`
- **CORS**: Enabled for all origins
- **Throttling**: 100 requests/second, burst 200
- **Endpoints**:
  - `POST /items` - Create item (Authenticated)
  - `GET /items` - List items (Public)
  - `GET /items/{id}` - Get item (Public)
  - `PUT /items/{id}` - Update item (Authenticated)
  - `DELETE /items/{id}` - Delete item (Authenticated)

### 2. Amazon Cognito

#### User Pool
- **Name**: `serverless-api-users`
- **Self Sign-Up**: Enabled
- **Sign-In Aliases**: Email and Username
- **Auto-Verify**: Email
- **Password Policy**:
  - Minimum length: 8 characters
  - Requires lowercase, uppercase, digits, and symbols
- **Purpose**: User authentication and management

#### User Pool Client
- **Name**: `serverless-api-client`
- **Auth Flows**: USER_PASSWORD_AUTH, USER_SRP
- **Generate Secret**: False (public client)
- **Purpose**: Application client for authentication

#### Identity Pool
- **Name**: `serverless-api-identity`
- **Unauthenticated Identities**: Disabled
- **Purpose**: Provides AWS credentials for authenticated users

### 3. DynamoDB Table
- **Name**: `serverless-api-items`
- **Partition Key**: `id` (String)
- **GSI**: `status-created-index`
  - Partition Key: `status` (String)
  - Sort Key: `created_at` (String)
- **Billing**: Pay-per-request
- **Purpose**: Stores API items/data

### 4. Lambda Functions

#### Create Item Lambda
- **Name**: `api-create-item`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Authorization**: Cognito (Required)
- **Purpose**: Creates new items

#### Get Item Lambda
- **Name**: `api-get-item`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Authorization**: None (Public)
- **Purpose**: Retrieves item by ID

#### List Items Lambda
- **Name**: `api-list-items`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Authorization**: None (Public)
- **Purpose**: Lists all items with optional filtering

#### Update Item Lambda
- **Name**: `api-update-item`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Authorization**: Cognito (Required)
- **Purpose**: Updates existing items

#### Delete Item Lambda
- **Name**: `api-delete-item`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Authorization**: Cognito (Required)
- **Purpose**: Deletes items

## API Endpoints

### POST /items (Authenticated)
Create a new item.

**Request:**
```json
{
  "name": "Test Item",
  "description": "Item description",
  "status": "active",
  "price": 29.99,
  "tags": ["test", "sample"]
}
```

**Response:**
```json
{
  "message": "Item created successfully",
  "item": {
    "id": "item_1234567890.123",
    "name": "Test Item",
    "description": "Item description",
    "status": "active",
    "price": "29.99",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00"
  }
}
```

### GET /items (Public)
List all items with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Limit results (default: 100)

**Response:**
```json
{
  "count": 2,
  "items": [
    {
      "id": "item_1234567890.123",
      "name": "Test Item",
      "status": "active"
    }
  ]
}
```

### GET /items/{id} (Public)
Get a specific item by ID.

**Response:**
```json
{
  "id": "item_1234567890.123",
  "name": "Test Item",
  "description": "Item description",
  "status": "active",
  "price": "29.99",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

### PUT /items/{id} (Authenticated)
Update an existing item.

**Request:**
```json
{
  "name": "Updated Item",
  "description": "Updated description",
  "status": "inactive",
  "price": 39.99
}
```

**Response:**
```json
{
  "message": "Item updated successfully",
  "item": {
    "id": "item_1234567890.123",
    "name": "Updated Item",
    "status": "inactive"
  }
}
```

### DELETE /items/{id} (Authenticated)
Delete an item.

**Response:**
```json
{
  "message": "Item deleted successfully",
  "id": "item_1234567890.123"
}
```

## Authentication Flow

1. **User Registration**:
   - User signs up via Cognito User Pool
   - Email verification (if auto-verify disabled)

2. **User Authentication**:
   - User authenticates with username/password
   - Cognito returns ID token, access token, refresh token

3. **API Request**:
   - Include ID token in `Authorization` header: `Bearer <id-token>`
   - API Gateway validates token with Cognito
   - Request proceeds if token is valid

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.serverless_api_stack import ServerlessApiStack
   
   ServerlessApiStack(app, "ServerlessApiStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth ServerlessApiStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy ServerlessApiStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name ServerlessApiStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Create Test User

```bash
# Get User Pool ID and Client ID
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name ServerlessApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name ServerlessApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
  --output text)

# Create user
aws cognito-idp sign-up \
  --client-id $CLIENT_ID \
  --username testuser \
  --password TestPass123! \
  --user-attributes Name=email,Value=test@example.com

# Confirm user (if auto-verify is disabled)
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id $USER_POOL_ID \
  --username testuser
```

### 2. Authenticate and Get Token

```bash
# Authenticate
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --client-id $CLIENT_ID \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=TestPass123!)

# Extract ID token
ID_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.IdToken')

echo "ID Token: $ID_TOKEN"
```

### 3. Test Public Endpoints

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name ServerlessApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)

# List items (Public)
curl -X GET "$API_ENDPOINT/items" | jq

# List items with filter
curl -X GET "$API_ENDPOINT/items?status=active" | jq
```

### 4. Test Authenticated Endpoints

```bash
# Create item (Authenticated)
curl -X POST "$API_ENDPOINT/items" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Item",
    "description": "This is a test item",
    "status": "active",
    "price": 29.99,
    "tags": ["test", "sample"]
  }' | jq

# Get item ID from response
ITEM_ID="item_<timestamp>"  # Replace with actual ID

# Get item (Public)
curl -X GET "$API_ENDPOINT/items/$ITEM_ID" | jq

# Update item (Authenticated)
curl -X PUT "$API_ENDPOINT/items/$ITEM_ID" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Item",
    "description": "Updated description",
    "status": "inactive"
  }' | jq

# Delete item (Authenticated)
curl -X DELETE "$API_ENDPOINT/items/$ITEM_ID" \
  -H "Authorization: Bearer $ID_TOKEN" | jq
```

### 5. Test Authentication Requirement

```bash
# Try to create item without token (should fail)
curl -X POST "$API_ENDPOINT/items" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}' 

# Should return 401 Unauthorized
```

### 6. Verify Data in DynamoDB

```bash
# Scan items table
aws dynamodb scan --table-name serverless-api-items --limit 10

# Query by status using GSI
aws dynamodb query \
  --table-name serverless-api-items \
  --index-name status-created-index \
  --key-condition-expression "status = :status" \
  --expression-attribute-values '{":status":{"S":"active"}}'
```

### 7. Run Complete Test Script

```bash
python tests/serverless_api/test_serverless_api.py
```

## Security Features

### Authentication
- Cognito User Pool for user management
- JWT tokens for API authentication
- Token validation at API Gateway

### Authorization
- Public endpoints: GET /items, GET /items/{id}
- Protected endpoints: POST, PUT, DELETE require authentication

### CORS
- Enabled for all origins (configure for production)
- Allowed methods: GET, POST, PUT, DELETE, OPTIONS
- Allowed headers: Content-Type, Authorization, X-Amz-Date, X-Api-Key

### Rate Limiting
- Throttling: 100 requests/second
- Burst: 200 requests

## Monitoring

### CloudWatch Logs
- API Gateway access logs
- Lambda function logs
- Cognito authentication logs

### CloudWatch Metrics
- API Gateway request metrics
- Lambda invocation metrics
- DynamoDB read/write metrics
- Cognito sign-in metrics

## Cost Optimization

- **API Gateway**: Pay per API call and data transfer
- **Lambda**: Pay per invocation and compute time
- **DynamoDB**: Pay-per-request pricing
- **Cognito**: Pay per MAU (Monthly Active User) after free tier

### Cost Optimization Tips
- Use API Gateway caching for frequently accessed data
- Optimize Lambda memory allocation
- Use DynamoDB on-demand pricing for variable workloads
- Implement request throttling

## Troubleshooting

### Authentication Fails
- Verify user exists in Cognito User Pool
- Check token expiration
- Verify token format in Authorization header
- Check Cognito User Pool configuration

### 401 Unauthorized
- Verify ID token is valid
- Check token expiration
- Verify API Gateway authorizer configuration
- Check Cognito User Pool client settings

### 500 Internal Server Error
- Check Lambda function logs
- Verify DynamoDB permissions
- Check for exceptions in Lambda execution
- Verify table name in Lambda environment variables

### CORS Errors
- Verify CORS configuration in API Gateway
- Check allowed origins, methods, headers
- Verify preflight OPTIONS request handling

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy ServerlessApiStack
```

**Note**: 
- Cognito User Pool users will be deleted
- DynamoDB table will be deleted (data will be lost)
- API Gateway API will be deleted

