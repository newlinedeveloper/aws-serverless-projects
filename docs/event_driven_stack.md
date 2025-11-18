# Event-Driven Stack

## Overview

The Event-Driven Stack implements a decoupled, event-driven architecture using AWS EventBridge, SNS, SQS, Step Functions, Lambda, and DynamoDB. It demonstrates microservices communication patterns, event sourcing, and complex workflow orchestration.

## Architecture

```
Event Sources → EventBridge → Rules → Lambda Handlers
                                      ↓
                              DynamoDB Tables
                                      ↓
                              SNS Notifications
                                      ↓
                              Step Functions (Workflows)
```

## Resources

### 1. EventBridge Custom Bus
- **Name**: `custom-event-bus`
- **Purpose**: Central event bus for routing events
- **Rules**: Filter and route events to different targets

### 2. SNS Topic
- **Name**: `event-notifications`
- **Purpose**: Publishes notifications for events
- **Subscriptions**: Can be configured with email, SMS, etc.

### 3. SQS Queues

#### Order Queue
- **Name**: `order-queue`
- **DLQ**: `order-dlq` (dead-letter queue)
- **Max Receive Count**: 3
- **Visibility Timeout**: 30 seconds
- **Purpose**: Async order processing

#### Inventory Queue
- **Name**: `inventory-queue`
- **DLQ**: `inventory-dlq` (dead-letter queue)
- **Max Receive Count**: 3
- **Visibility Timeout**: 30 seconds
- **Purpose**: Async inventory updates

### 4. DynamoDB Tables

#### Orders Table
- **Name**: `event-driven-orders`
- **Partition Key**: `order_id` (String)
- **Billing**: Pay-per-request
- **Purpose**: Stores order information

#### Inventory Table
- **Name**: `event-driven-inventory`
- **Partition Key**: `item_id` (String)
- **Billing**: Pay-per-request
- **Purpose**: Stores inventory items

### 5. Lambda Functions

#### Order Processor
- **Name**: `event-order-processor`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Event Source**: EventBridge (order events)
- **Purpose**: Processes order events, stores in DynamoDB, publishes notifications

#### Inventory Processor
- **Name**: `event-inventory-processor`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Event Source**: EventBridge (inventory events)
- **Purpose**: Processes inventory events, updates inventory table

#### Notification Processor
- **Name**: `event-notification-processor`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Event Source**: EventBridge (notification events)
- **Purpose**: Processes notification events, publishes to SNS

### 6. Step Functions State Machine
- **Name**: `event-driven-workflow`
- **Timeout**: 5 minutes
- **Tracing**: Enabled (X-Ray)
- **Workflow**: Parallel execution of order and inventory processing
- **Purpose**: Orchestrates complex workflows

### 7. EventBridge Rules

#### Order Event Rule
- **Name**: `order-events-rule`
- **Pattern**: `source: orders`, `detail-type: Order Created | Order Completed`
- **Target**: Order Processor Lambda
- **Purpose**: Routes order events to order processor

#### Inventory Event Rule
- **Name**: `inventory-events-rule`
- **Pattern**: `source: inventory`, `detail-type: Inventory Updated`
- **Target**: Inventory Processor Lambda
- **Purpose**: Routes inventory events to inventory processor

#### Notification Event Rule
- **Name**: `notification-events-rule`
- **Pattern**: `source: notifications`, `detail-type: Notification Sent`
- **Target**: Notification Processor Lambda
- **Purpose**: Routes notification events to notification processor

#### Workflow Event Rule
- **Name**: `workflow-events-rule`
- **Pattern**: `source: workflow`, `detail-type: Workflow Triggered`
- **Target**: Step Functions state machine
- **Purpose**: Triggers complex workflows

## Event Patterns

### Order Created Event
```json
{
  "source": "orders",
  "detail-type": "Order Created",
  "detail": {
    "order_id": "ORD-001",
    "customer_id": "CUST-001",
    "items": [
      {"item_id": "ITEM-001", "quantity": 2, "price": 29.99}
    ],
    "total": 59.98,
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

### Inventory Updated Event
```json
{
  "source": "inventory",
  "detail-type": "Inventory Updated",
  "detail": {
    "item_id": "ITEM-001",
    "quantity": 100,
    "action": "restock",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

### Workflow Triggered Event
```json
{
  "source": "workflow",
  "detail-type": "Workflow Triggered",
  "detail": {
    "workflow_id": "WF-001",
    "order_id": "ORD-001",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

## Data Flow

1. **Event Publishing**:
   - Events published to EventBridge custom bus
   - Events match event patterns in rules

2. **Event Routing**:
   - EventBridge rules filter events
   - Events routed to appropriate Lambda functions or Step Functions

3. **Processing**:
   - Lambda functions process events
   - Data stored in DynamoDB
   - Notifications published to SNS

4. **Workflow Orchestration**:
   - Step Functions orchestrates parallel processing
   - Order and inventory processing run in parallel

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.event_driven_stack import EventDrivenStack
   
   EventDrivenStack(app, "EventDrivenStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth EventDrivenStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy EventDrivenStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name EventDrivenStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Send Test Events to EventBridge

```bash
# Get event bus name
EVENT_BUS=$(aws cloudformation describe-stacks \
  --stack-name EventDrivenStack \
  --query "Stacks[0].Outputs[?OutputKey=='EventBusName'].OutputValue" \
  --output text)

# Send Order Created event
aws events put-events \
  --entries '[{
    "EventBusName": "'$EVENT_BUS'",
    "Source": "orders",
    "DetailType": "Order Created",
    "Detail": "{\"order_id\":\"ORD-001\",\"customer_id\":\"CUST-001\",\"items\":[{\"item_id\":\"ITEM-001\",\"quantity\":2,\"price\":29.99}],\"total\":59.98,\"timestamp\":\"2024-01-15T10:00:00Z\"}"
  }]'

# Send Inventory Updated event
aws events put-events \
  --entries '[{
    "EventBusName": "'$EVENT_BUS'",
    "Source": "inventory",
    "DetailType": "Inventory Updated",
    "Detail": "{\"item_id\":\"ITEM-001\",\"quantity\":100,\"action\":\"restock\",\"timestamp\":\"2024-01-15T10:00:00Z\"}"
  }]'

# Send Workflow Triggered event
aws events put-events \
  --entries '[{
    "EventBusName": "'$EVENT_BUS'",
    "Source": "workflow",
    "DetailType": "Workflow Triggered",
    "Detail": "{\"workflow_id\":\"WF-001\",\"order_id\":\"ORD-001\",\"timestamp\":\"2024-01-15T10:00:00Z\"}"
  }]'
```

### 2. Monitor Processing

**Check Lambda Logs:**
```bash
# Order Processor
aws logs tail /aws/lambda/event-order-processor --follow

# Inventory Processor
aws logs tail /aws/lambda/event-inventory-processor --follow

# Notification Processor
aws logs tail /aws/lambda/event-notification-processor --follow
```

**Check DynamoDB Tables:**
```bash
# Check Orders Table
ORDERS_TABLE=$(aws cloudformation describe-stacks \
  --stack-name EventDrivenStack \
  --query "Stacks[0].Outputs[?OutputKey=='OrdersTableName'].OutputValue" \
  --output text)

aws dynamodb scan --table-name $ORDERS_TABLE --limit 10

# Check Inventory Table
INVENTORY_TABLE=$(aws cloudformation describe-stacks \
  --stack-name EventDrivenStack \
  --query "Stacks[0].Outputs[?OutputKey=='InventoryTableName'].OutputValue" \
  --output text)

aws dynamodb scan --table-name $INVENTORY_TABLE --limit 10
```

**Check Step Functions Execution:**
```bash
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name EventDrivenStack \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --max-results 10
```

### 3. Subscribe to SNS Notifications

```bash
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name EventDrivenStack \
  --query "Stacks[0].Outputs[?OutputKey=='NotificationTopicArn'].OutputValue" \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### 4. Run Complete Test Script

```bash
python tests/event_driven/test_event_driven.py
```

## Event-Driven Patterns

### 1. Event Sourcing
- Events are the source of truth
- State is derived from events
- Events stored in EventBridge history

### 2. Pub/Sub Pattern
- Publishers send events to EventBridge
- Subscribers (Lambda functions) process events
- Decoupled communication

### 3. Event Routing
- EventBridge rules filter and route events
- Multiple targets can process same event
- Pattern matching for flexible routing

### 4. Saga Pattern
- Step Functions orchestrates multi-step workflows
- Compensating actions for failures
- Distributed transaction management

## Monitoring

### CloudWatch Metrics
- EventBridge rule invocations
- Lambda invocation metrics
- Step Functions execution metrics
- DynamoDB read/write metrics
- SNS publish metrics

### X-Ray Tracing
- Step Functions tracing enabled
- View distributed traces across services

## Cost Optimization

- **EventBridge**: First 1 million events/month free
- **Lambda**: Pay per invocation and compute time
- **Step Functions**: Pay per state transition
- **DynamoDB**: Pay-per-request pricing
- **SNS**: Pay per notification
- **SQS**: Pay per request (first 1 million free)

## Troubleshooting

### Events Not Processed
- Verify EventBridge rule patterns match events
- Check Lambda function logs
- Verify IAM permissions
- Check EventBridge event history

### Lambda Timeout
- Increase Lambda timeout
- Optimize Lambda code
- Check DynamoDB throttling

### Step Functions Not Triggered
- Verify workflow event rule pattern
- Check Step Functions permissions
- Verify event bus name

### No Data in DynamoDB
- Check Lambda execution logs
- Verify DynamoDB write permissions
- Check for exceptions in Lambda

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy EventDrivenStack
```

**Note**: SQS queues and SNS topics will be deleted. Make sure to unsubscribe from SNS topics first if needed.

