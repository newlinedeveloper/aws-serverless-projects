import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Process inventory events from EventBridge
    """
    inventory_table_name = os.environ['INVENTORY_TABLE_NAME']
    
    inventory_table = dynamodb.Table(inventory_table_name)
    
    processed_items = []
    
    # EventBridge sends events directly, not in Records array
    events_to_process = []
    
    if 'Records' in event:
        # If wrapped in Records
        for record in event['Records']:
            if 'body' in record:
                events_to_process.append(json.loads(record['body']))
            else:
                events_to_process.append(record)
    else:
        # Direct EventBridge event format
        events_to_process.append(event)
    
    for event_data in events_to_process:
        try:
            # Parse EventBridge event structure
            detail = event_data.get('detail', {})
            
            # If detail is a string, parse it
            if isinstance(detail, str):
                detail = json.loads(detail)
            
            event_type = detail.get('eventType', '')
            inventory_data = detail.get('data', {})
            
            print(f"Processing event type: {event_type}, inventory data: {inventory_data}")
            
            if event_type == 'inventory.updated':
                # Update inventory
                item_id = inventory_data.get('itemId', '')
                quantity = inventory_data.get('quantity', 0)
                
                if not item_id:
                    print("Error: itemId is missing")
                    continue
                
                inventory_table.put_item(
                    Item={
                        'item_id': item_id,
                        'quantity': quantity,
                        'updated_at': inventory_data.get('updatedAt', '')
                    }
                )
                
                print(f"Updated inventory item {item_id} with quantity {quantity}")
                processed_items.append(item_id)
            else:
                print(f"Unknown event type: {event_type}")
                
        except Exception as e:
            print(f"Error processing inventory event: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return {
        'statusCode': 200,
        'processedItems': len(processed_items),
        'items': processed_items
    }

