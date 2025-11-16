import json
import boto3
import os
import base64
from datetime import datetime
from decimal import Decimal

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Process Kinesis records: transform, aggregate, and store data
    """
    table = dynamodb.Table(os.environ['METRICS_TABLE_NAME'])
    archive_bucket = os.environ['ARCHIVE_BUCKET_NAME']
    
    processed_records = []
    aggregated_metrics = {}
    
    for record in event['Records']:
        try:
            # Decode base64-encoded Kinesis data
            kinesis_data = record['kinesis']['data']
            decoded_data = base64.b64decode(kinesis_data).decode('utf-8')
            payload = json.loads(decoded_data)
            
            # Extract timestamp and partition key
            timestamp = datetime.fromtimestamp(record['kinesis']['approximateArrivalTimestamp'] / 1000)
            partition_key = record['kinesis']['partitionKey']
            
            # Transform data
            transformed_data = {
                'timestamp': timestamp.isoformat(),
                'partition_key': partition_key,
                'data': payload,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Aggregate metrics by partition key
            if partition_key not in aggregated_metrics:
                aggregated_metrics[partition_key] = {
                    'count': 0,
                    'total_value': 0,
                    'last_updated': timestamp.isoformat()
                }
            
            aggregated_metrics[partition_key]['count'] += 1
            if 'value' in payload:
                aggregated_metrics[partition_key]['total_value'] += float(payload.get('value', 0))
            
            # Archive raw data to S3
            archive_key = f"raw/{timestamp.strftime('%Y/%m/%d/%H')}/{partition_key}_{record['kinesis']['sequenceNumber']}.json"
            s3_client.put_object(
                Bucket=archive_bucket,
                Key=archive_key,
                Body=json.dumps(transformed_data),
                ContentType='application/json'
            )
            
            processed_records.append(transformed_data)
            
        except Exception as e:
            print(f"Error processing record: {e}")
            print(f"Record data: {record.get('kinesis', {}).get('data', 'N/A')[:100]}")
            # In production, send to DLQ
            continue
    
    # Store aggregated metrics in DynamoDB
    for partition_key, metrics in aggregated_metrics.items():
        try:
            table.put_item(
                Item={
                    'partition_key': partition_key,
                    'timestamp': aggregated_metrics[partition_key]['last_updated'],
                    'count': metrics['count'],
                    'total_value': Decimal(str(metrics['total_value'])),
                    'average_value': Decimal(str(metrics['total_value'] / metrics['count'])),
                    'ttl': int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
                }
            )
        except Exception as e:
            print(f"Error storing metrics for {partition_key}: {e}")
    
    return {
        'statusCode': 200,
        'processedRecords': len(processed_records),
        'aggregatedMetrics': len(aggregated_metrics)
    }

