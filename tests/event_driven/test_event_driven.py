import boto3
import json
import time
from datetime import datetime

# Initialize clients
events = boto3.client('events')
dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')
sns = boto3.client('sns')
cloudformation = boto3.client('cloudformation')

def get_stack_outputs(stack_name):
    """Get stack outputs"""
    response = cloudformation.describe_stacks(StackName=stack_name)
    outputs = {o['OutputKey']: o['OutputValue'] 
               for o in response['Stacks'][0]['Outputs']}
    return outputs

def send_order_created_event(event_bus_name, order_id='ORD-001'):
    """Send order created event"""
    print("\n[Test 1] Sending Order Created Event...")
    
    event = {
        'Source': 'orders',
        'DetailType': 'Order Created',
        'Detail': json.dumps({
            'eventType': 'order.created',
            'data': {
                'orderId': order_id,
                'customerId': 'CUST-001',
                'items': [
                    {'productId': 'PROD-001', 'quantity': 2, 'price': 29.99},
                    {'productId': 'PROD-002', 'quantity': 1, 'price': 49.99}
                ],
                'total': 109.97,
                'createdAt': datetime.utcnow().isoformat() + 'Z'
            }
        }),
        'EventBusName': event_bus_name
    }
    
    response = events.put_events(Entries=[event])
    
    if response['FailedEntryCount'] == 0:
        print(f"✓ Order created event sent: {order_id}")
        return order_id
    else:
        print(f"✗ Failed to send event: {response['Entries'][0].get('ErrorMessage', 'Unknown')}")
        return None

def send_order_completed_event(event_bus_name, order_id):
    """Send order completed event"""
    print("\n[Test 2] Sending Order Completed Event...")
    
    event = {
        'Source': 'orders',
        'DetailType': 'Order Completed',
        'Detail': json.dumps({
            'eventType': 'order.completed',
            'data': {
                'orderId': order_id,
                'completedAt': datetime.utcnow().isoformat() + 'Z'
            }
        }),
        'EventBusName': event_bus_name
    }
    
    response = events.put_events(Entries=[event])
    
    if response['FailedEntryCount'] == 0:
        print(f"✓ Order completed event sent: {order_id}")
        return True
    else:
        print(f"✗ Failed to send event")
        return False

def send_inventory_event(event_bus_name, item_id='ITEM-001'):
    """Send inventory updated event"""
    print("\n[Test 3] Sending Inventory Updated Event...")
    
    event = {
        'Source': 'inventory',
        'DetailType': 'Inventory Updated',
        'Detail': json.dumps({
            'eventType': 'inventory.updated',
            'data': {
                'itemId': item_id,
                'quantity': 150,
                'updatedAt': datetime.utcnow().isoformat() + 'Z'
            }
        }),
        'EventBusName': event_bus_name
    }
    
    response = events.put_events(Entries=[event])
    
    if response['FailedEntryCount'] == 0:
        print(f"✓ Inventory updated event sent: {item_id}")
        return item_id
    else:
        print(f"✗ Failed to send event")
        return None

def send_notification_event(event_bus_name):
    """Send notification event"""
    print("\n[Test 4] Sending Notification Event...")
    
    event = {
        'Source': 'notifications',
        'DetailType': 'Notification Sent',
        'Detail': json.dumps({
            'data': {
                'id': 'NOTIF-001',
                'subject': 'Test Notification',
                'message': 'This is a test notification from Event-Driven Architecture',
                'priority': 'high',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }),
        'EventBusName': event_bus_name
    }
    
    response = events.put_events(Entries=[event])
    
    if response['FailedEntryCount'] == 0:
        print("✓ Notification event sent")
        return True
    else:
        print(f"✗ Failed to send event")
        return False

def verify_orders_table(table_name, order_id, wait_seconds=5):
    """Verify order was stored in DynamoDB"""
    print(f"\n[Test 5] Verifying Orders Table (waiting {wait_seconds}s)...")
    time.sleep(wait_seconds)
    
    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key={'order_id': order_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✓ Order found in DynamoDB:")
            print(f"  Order ID: {item.get('order_id')}")
            print(f"  Status: {item.get('status')}")
            print(f"  Customer: {item.get('customer_id')}")
            print(f"  Total: {item.get('total')}")
            return True
        else:
            print(f"✗ Order {order_id} not found in DynamoDB")
            return False
    except Exception as e:
        print(f"✗ Error querying orders table: {e}")
        return False

def verify_inventory_table(table_name, item_id, wait_seconds=5):
    """Verify inventory was updated"""
    print(f"\n[Test 6] Verifying Inventory Table (waiting {wait_seconds}s)...")
    time.sleep(wait_seconds)
    
    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key={'item_id': item_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✓ Inventory item found:")
            print(f"  Item ID: {item.get('item_id')}")
            print(f"  Quantity: {item.get('quantity')}")
            return True
        else:
            print(f"✗ Item {item_id} not found in inventory table")
            return False
    except Exception as e:
        print(f"✗ Error querying inventory table: {e}")
        return False

def test_step_functions_workflow(event_bus_name, state_machine_arn):
    """Test Step Functions workflow"""
    print("\n[Test 7] Testing Step Functions Workflow...")
    
    # Send workflow trigger event
    event = {
        'Source': 'workflow',
        'DetailType': 'Workflow Triggered',
        'Detail': json.dumps({}),
        'EventBusName': event_bus_name
    }
    
    response = events.put_events(Entries=[event])
    
    if response['FailedEntryCount'] == 0:
        print("✓ Workflow trigger event sent")
        
        # Wait for execution to start
        time.sleep(5)
        
        # List recent executions
        executions = stepfunctions.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1
        )
        
        if executions['executions']:
            execution = executions['executions'][0]
            execution_arn = execution['executionArn']
            status = execution['status']
            
            print(f"  Execution ARN: {execution_arn}")
            print(f"  Status: {status}")
            
            # Get execution details
            details = stepfunctions.describe_execution(executionArn=execution_arn)
            print(f"  Start Time: {details.get('startDate')}")
            
            if status == 'SUCCEEDED':
                print("✓ Workflow execution succeeded")
                return True
            elif status == 'RUNNING':
                print("⚠ Workflow still running")
                return True
            else:
                print(f"⚠ Workflow status: {status}")
                return False
        else:
            print("⚠ No executions found yet")
            return False
    else:
        print("✗ Failed to send workflow trigger event")
        return False

def check_lambda_logs(function_names, minutes=10):
    """Check Lambda function logs"""
    print("\n[Test 8] Checking Lambda Logs...")
    
    logs = boto3.client('logs')
    
    for function_name in function_names:
        log_group = f'/aws/lambda/{function_name}'
        print(f"\n  {function_name}:")
        
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (minutes * 60 * 1000)
            
            response = logs.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                limit=5
            )
            
            if response['events']:
                print(f"    ✓ Found {len(response['events'])} recent log events")
                for event in response['events'][-3:]:
                    message = event['message'].strip()
                    if 'Error' in message or 'error' in message.lower():
                        print(f"      ✗ {message[:150]}")
                    else:
                        print(f"      - {message[:100]}")
            else:
                print(f"    ⚠ No recent log events")
        except Exception as e:
            print(f"    ✗ Error checking logs: {e}")

def verify_sns_notifications(topic_arn):
    """Verify SNS notifications"""
    print("\n[Test 9] Verifying SNS Notifications...")
    
    try:
        # Check topic attributes
        response = sns.get_topic_attributes(TopicArn=topic_arn)
        print(f"✓ Topic found: {topic_arn}")
        print(f"  Subscriptions: {response['Attributes'].get('SubscriptionsConfirmed', '0')}")
        
        # List subscriptions
        subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        if subscriptions['Subscriptions']:
            print(f"  Active subscriptions: {len(subscriptions['Subscriptions'])}")
            for sub in subscriptions['Subscriptions']:
                print(f"    - {sub['Protocol']}: {sub['Endpoint']}")
        else:
            print("  ⚠ No subscriptions configured (notifications sent but no subscribers)")
        
        return True
    except Exception as e:
        print(f"✗ Error checking SNS: {e}")
        return False

def main():
    """Run complete event-driven architecture test"""
    print("\n" + "=" * 60)
    print("Event-Driven Architecture Stack - End-to-End Test Suite")
    print("=" * 60)
    
    # Get stack outputs
    try:
        outputs = get_stack_outputs('EventDrivenStack')
        event_bus_name = outputs['EventBusName']
        state_machine_arn = outputs['StateMachineArn']
        notification_topic = outputs['NotificationTopicArn']
        orders_table = outputs['OrdersTableName']
        inventory_table = outputs['InventoryTableName']
        
        print(f"\nStack Resources:")
        print(f"  Event Bus: {event_bus_name}")
        print(f"  State Machine: {state_machine_arn}")
        print(f"  Notification Topic: {notification_topic}")
        print(f"  Orders Table: {orders_table}")
        print(f"  Inventory Table: {inventory_table}")
    except Exception as e:
        print(f"✗ Error getting stack outputs: {e}")
        return
    
    # Run tests
    order_id = send_order_created_event(event_bus_name)
    if order_id:
        time.sleep(3)  # Wait for processing
        verify_orders_table(orders_table, order_id)
        
        # Send order completed
        send_order_completed_event(event_bus_name, order_id)
        time.sleep(3)
        verify_orders_table(orders_table, order_id)
    
    item_id = send_inventory_event(event_bus_name)
    if item_id:
        time.sleep(3)
        verify_inventory_table(inventory_table, item_id)
    
    send_notification_event(event_bus_name)
    time.sleep(3)
    
    test_step_functions_workflow(event_bus_name, state_machine_arn)
    
    check_lambda_logs([
        'event-order-processor',
        'event-inventory-processor',
        'event-notification-processor'
    ])
    
    verify_sns_notifications(notification_topic)
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check EventBridge rules: aws events list-rules --event-bus-name custom-event-bus")
    print("2. Monitor Step Functions: AWS Console > Step Functions")
    print("3. Subscribe to SNS topic for email notifications")
    print("4. Check CloudWatch metrics for event processing")

if __name__ == '__main__':
    main()