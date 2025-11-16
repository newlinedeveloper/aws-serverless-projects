import json
import boto3
import os
from datetime import datetime, timedelta, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Extract data from source systems (DynamoDB in this example)
    """
    source_table_name = os.environ['SOURCE_TABLE_NAME']
    staging_bucket = os.environ['STAGING_BUCKET_NAME']
    
    table = dynamodb.Table(source_table_name)
    
    # Calculate date range (yesterday's data) - Make timezone-aware
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    extracted_records = []
    last_evaluated_key = None
    
    try:
        # Scan table (in production, use query with date range)
        while True:
            if last_evaluated_key:
                response = table.scan(ExclusiveStartKey=last_evaluated_key)
            else:
                response = table.scan()
            
            for item in response.get('Items', []):
                # Filter by date if timestamp exists
                if 'timestamp' in item:
                    # Parse timestamp - handle both with and without timezone
                    timestamp_str = item['timestamp']
                    if timestamp_str.endswith('Z'):
                        item_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                        # Already has timezone info
                        item_timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        # No timezone info, assume UTC
                        item_timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
                    
                    if start_date <= item_timestamp < end_date:
                        extracted_records.append(item)
                else:
                    extracted_records.append(item)
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        # Write extracted data to S3 staging area
        staging_key = f"extracted/{start_date.strftime('%Y/%m/%d')}/data_{datetime.now(timezone.utc).isoformat()}.json"
        s3_client.put_object(
            Bucket=staging_bucket,
            Key=staging_key,
            Body=json.dumps(extracted_records, default=str),
            ContentType='application/json'
        )
        
        return {
            'statusCode': 200,
            'recordsExtracted': len(extracted_records),
            'stagingKey': staging_key,
            'dateRange': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
        
    except Exception as e:
        print(f"Error in extraction: {e}")
        raise

