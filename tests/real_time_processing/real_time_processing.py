import boto3
import json
import time
from datetime import datetime

kinesis = boto3.client('kinesis')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

stream_name = 'realtime-data-stream'
table_name = 'realtime-processed-metrics'

def send_single_record():
    """Send a single test record to Kinesis"""
    print("=" * 50)
    print("Sending single record...")
    print("=" * 50)
    
    data = {
        'sensorId': 'sensor-001',
        'value': 25.5,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'location': 'building-A'
    }
    
    try:
        response = kinesis.put_record(
            StreamName=stream_name,
            PartitionKey='sensor-001',
            Data=json.dumps(data)
        )
        
        print(f"✓ Success! SequenceNumber: {response['SequenceNumber']}")
        print(f"✓ ShardId: {response['ShardId']}")
        return response['SequenceNumber']
    except Exception as e:
        print(f"✗ Error sending record: {e}")
        return None

def send_multiple_records():
    """Send multiple test records to Kinesis"""
    print("\n" + "=" * 50)
    print("Sending multiple records...")
    print("=" * 50)
    
    records = []
    for i in range(5):
        record_data = {
            'sensorId': f'sensor-{(i % 3) + 1:03d}',
            'value': 20 + (i * 2.5),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'location': f'building-{chr(65 + (i % 3))}'
        }
        records.append({
            'Data': json.dumps(record_data),
            'PartitionKey': record_data['sensorId']
        })
    
    try:
        response = kinesis.put_records(
            StreamName=stream_name,
            Records=records
        )
        
        print(f"✓ Sent {len(records)} records")
        print(f"✓ Failed: {response['FailedRecordCount']}")
        print(f"✓ Successful: {len(records) - response['FailedRecordCount']}")
        
        if response['FailedRecordCount'] > 0:
            print("\nFailed records:")
            for record in response.get('Records', []):
                if 'ErrorCode' in record:
                    print(f"  - Error: {record.get('ErrorCode')} - {record.get('ErrorMessage')}")
        
        return response['FailedRecordCount'] == 0
    except Exception as e:
        print(f"✗ Error sending records: {e}")
        return False

def verify_dynamodb(partition_key='sensor-001', wait_seconds=10):
    """Verify that metrics were stored in DynamoDB"""
    print("\n" + "=" * 50)
    print(f"Verifying DynamoDB (waiting {wait_seconds}s for processing)...")
    print("=" * 50)
    
    time.sleep(wait_seconds)  # Wait for Lambda to process
    
    try:
        table = dynamodb.Table(table_name)
        response = table.query(
            KeyConditionExpression='partition_key = :pk',
            ExpressionAttributeValues={':pk': partition_key},
            ScanIndexForward=False,
            Limit=1
        )
        
        if response['Items']:
            item = response['Items'][0]
            print(f"✓ Found metrics for {partition_key}:")
            print(f"  - Count: {item.get('count', 'N/A')}")
            print(f"  - Total Value: {item.get('total_value', 'N/A')}")
            print(f"  - Average Value: {item.get('average_value', 'N/A')}")
            print(f"  - Timestamp: {item.get('timestamp', 'N/A')}")
            return True
        else:
            print(f"✗ No metrics found for {partition_key}")
            return False
    except Exception as e:
        print(f"✗ Error querying DynamoDB: {e}")
        return False

def verify_s3_archive(bucket_name, wait_seconds=10):
    """Verify that raw data was archived to S3"""
    print("\n" + "=" * 50)
    print(f"Verifying S3 archive (waiting {wait_seconds}s for processing)...")
    print("=" * 50)
    
    time.sleep(wait_seconds)  # Wait for Lambda to process
    
    try:
        # List objects in the raw/ prefix
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='raw/',
            MaxKeys=5
        )
        
        if 'Contents' in response and len(response['Contents']) > 0:
            print(f"✓ Found {len(response['Contents'])} archived files:")
            for obj in response['Contents'][:5]:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
            return True
        else:
            print("✗ No archived files found")
            return False
    except Exception as e:
        print(f"✗ Error checking S3: {e}")
        print(f"  Note: Make sure to replace <account> and <region> in bucket name")
        return False

def check_lambda_logs(function_name='realtime-data-processor', minutes=5):
    """Check recent Lambda logs"""
    print("\n" + "=" * 50)
    print("Checking Lambda logs...")
    print("=" * 50)
    
    try:
        logs = boto3.client('logs')
        log_group = f'/aws/lambda/{function_name}'
        
        end_time = int(time.time() * 1000)
        start_time = end_time - (minutes * 60 * 1000)
        
        response = logs.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            limit=20
        )
        
        if response['events']:
            print(f"✓ Found {len(response['events'])} log events:")
            for event in response['events'][-10:]:  # Show last 10
                message = event['message'].strip()
                if 'Error' in message or 'error' in message.lower():
                    print(f"  ✗ {message}")
                elif 'processedRecords' in message or 'Success' in message:
                    print(f"  ✓ {message}")
                else:
                    print(f"  - {message}")
        else:
            print("✗ No recent log events found")
    except Exception as e:
        print(f"✗ Error checking logs: {e}")

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("Real-Time Processing Stack - Test Suite")
    print("=" * 50)
    
    # Test 1: Send single record
    seq_number = send_single_record()
    
    # Test 2: Send multiple records
    success = send_multiple_records()
    
    # Test 3: Verify DynamoDB
    verify_dynamodb('sensor-001', wait_seconds=10)
    
    # Test 4: Verify S3 (update bucket name with your account and region)
    # Get bucket name from CDK outputs or CloudFormation
    # bucket_name = 'realtime-data-archive-<account>-<region>'
    # verify_s3_archive(bucket_name, wait_seconds=10)
    
    # Test 5: Check Lambda logs
    check_lambda_logs()
    
    print("\n" + "=" * 50)
    print("Test Suite Complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Check CloudWatch Logs: /aws/lambda/realtime-data-processor")
    print("2. Query DynamoDB: aws dynamodb query --table-name realtime-processed-metrics")
    print("3. List S3 files: aws s3 ls s3://<bucket-name>/raw/ --recursive")

if __name__ == '__main__':
    main()