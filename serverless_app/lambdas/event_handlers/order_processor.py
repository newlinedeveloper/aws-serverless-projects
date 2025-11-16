import json
import boto3
import os

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Process order events from EventBridge
    """
    orders_table_name = os.environ['ORDERS_TABLE_NAME']
    notification_topic_arn = os.environ['NOTIFICATION_TOPIC_ARN']
    
    orders_table = dynamodb.Table(orders_table_name)
    
    processed_orders = []
    
    # EventBridge sends events directly, not in Records array
    # Handle both EventBridge format and potential batch format
    events_to_process = []
    
    if 'Records' in event:
        # If wrapped in Records (shouldn't happen with EventBridge, but handle it)
        for record in event['Records']:
            if 'body' in record:
                # SQS format - parse body
                events_to_process.append(json.loads(record['body']))
            else:
                events_to_process.append(record)
    else:
        # Direct EventBridge event format
        events_to_process.append(event)
    
    for event_data in events_to_process:
        try:
            # Parse EventBridge event structure
            # EventBridge format: event['detail'] contains the detail JSON string or object
            detail = event_data.get('detail', {})
            
            # If detail is a string, parse it
            if isinstance(detail, str):
                detail = json.loads(detail)
            
            event_type = detail.get('eventType', '')
            order_data = detail.get('data', {})
            
            print(f"Processing event type: {event_type}, order data: {order_data}")
            
            if event_type == 'order.created':
                # Process new order
                order_id = order_data.get('orderId', '')
                
                if not order_id:
                    print("Error: orderId is missing")
                    continue
                
                # Store order in DynamoDB
                orders_table.put_item(
                    Item={
                        'order_id': order_id,
                        'status': 'processing',
                        'customer_id': order_data.get('customerId', ''),
                        'items': order_data.get('items', []),
                        'total': order_data.get('total', 0),
                        'created_at': order_data.get('createdAt', '')
                    }
                )
                
                print(f"Stored order {order_id} in DynamoDB")
                
                # Send notification
                try:
                    sns.publish(
                        TopicArn=notification_topic_arn,
                        Subject='New Order Created',
                        Message=json.dumps({
                            'orderId': order_id,
                            'status': 'processing',
                            'message': f'Order {order_id} has been created and is being processed'
                        })
                    )
                    print(f"Sent notification for order {order_id}")
                except Exception as e:
                    print(f"Error sending notification: {e}")
                
                processed_orders.append(order_id)
                
            elif event_type == 'order.completed':
                # Update order status
                order_id = order_data.get('orderId', '')
                
                if not order_id:
                    print("Error: orderId is missing")
                    continue
                
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression='SET #status = :status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': 'completed'}
                )
                
                print(f"Updated order {order_id} status to completed")
                
                # Send notification
                try:
                    sns.publish(
                        TopicArn=notification_topic_arn,
                        Subject='Order Completed',
                        Message=json.dumps({
                            'orderId': order_id,
                            'status': 'completed',
                            'message': f'Order {order_id} has been completed'
                        })
                    )
                    print(f"Sent notification for completed order {order_id}")
                except Exception as e:
                    print(f"Error sending notification: {e}")
                
                processed_orders.append(order_id)
            else:
                print(f"Unknown event type: {event_type}")
                
        except Exception as e:
            print(f"Error processing event: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return {
        'statusCode': 200,
        'processedOrders': len(processed_orders),
        'orders': processed_orders
    }

