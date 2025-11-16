import json
import boto3
import os

sns = boto3.client('sns')

def handler(event, context):
    """
    Process notification events from EventBridge
    """
    notification_topic_arn = os.environ['NOTIFICATION_TOPIC_ARN']
    
    processed_notifications = []
    
    # EventBridge sends events directly
    events_to_process = []
    
    if 'Records' in event:
        for record in event['Records']:
            if 'body' in record:
                events_to_process.append(json.loads(record['body']))
            else:
                events_to_process.append(record)
    else:
        events_to_process.append(event)
    
    for event_data in events_to_process:
        try:
            # Parse EventBridge event structure
            detail = event_data.get('detail', {})
            
            # If detail is a string, parse it
            if isinstance(detail, str):
                detail = json.loads(detail)
            
            notification_data = detail.get('data', {})
            
            print(f"Processing notification: {notification_data}")
            
            # Send to SNS topic
            sns.publish(
                TopicArn=notification_topic_arn,
                Subject=notification_data.get('subject', 'Notification'),
                Message=json.dumps(notification_data)
            )
            
            print(f"Sent notification: {notification_data.get('id', 'unknown')}")
            processed_notifications.append(notification_data.get('id', ''))
            
        except Exception as e:
            print(f"Error processing notification: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return {
        'statusCode': 200,
        'processedNotifications': len(processed_notifications)
    }

