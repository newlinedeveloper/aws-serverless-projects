import boto3
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')
s3 = boto3.client('s3')
cloudformation = boto3.client('cloudformation')

# Get stack outputs
def get_stack_outputs(stack_name):
    response = cloudformation.describe_stacks(StackName=stack_name)
    outputs = {o['OutputKey']: o['OutputValue'] 
               for o in response['Stacks'][0]['Outputs']}
    return outputs

def setup_test_data(source_table_name):
    """Populate source table with test data"""
    print("=" * 60)
    print("Step 1: Setting up test data in source table")
    print("=" * 60)
    
    table = dynamodb.Table(source_table_name)
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    test_records = []
    for i in range(5):
        record = {
            'id': f'record-{i+1:03d}',
            'timestamp': yesterday.isoformat() + 'Z',
            'value': Decimal(str(100 + i * 10)),
            'count': i + 10,
            'total_value': Decimal(str(1000 + i * 100)),
            'location': f'building-{chr(65 + i)}',
            'status': 'active'
        }
        table.put_item(Item=record)
        test_records.append(record)
        print(f"✓ Added record: {record['id']}")
    
    print(f"\n✓ Total records added: {len(test_records)}")
    return test_records

def trigger_etl_pipeline(state_machine_arn):
    """Manually trigger ETL pipeline"""
    print("\n" + "=" * 60)
    print("Step 2: Triggering ETL Pipeline")
    print("=" * 60)
    
    response = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps({})
    )
    
    execution_arn = response['executionArn']
    print(f"✓ Execution started: {execution_arn}")
    return execution_arn

def monitor_execution(execution_arn, timeout=300):
    """Monitor Step Functions execution"""
    print("\n" + "=" * 60)
    print("Step 3: Monitoring execution")
    print("=" * 60)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = stepfunctions.describe_execution(executionArn=execution_arn)
        status = response['status']
        
        print(f"Status: {status}", end='\r')
        
        if status == 'SUCCEEDED':
            print(f"\n✓ Execution completed successfully!")
            print(f"  Start time: {response['startDate']}")
            print(f"  Stop time: {response['stopDate']}")
            return True
        elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
            print(f"\n✗ Execution {status.lower()}")
            print(f"  Error: {response.get('error', 'Unknown error')}")
            return False
        
        time.sleep(5)
    
    print(f"\n✗ Execution timeout after {timeout} seconds")
    return False

def verify_extract_step(bucket_name):
    """Verify Extract step output"""
    print("\n" + "=" * 60)
    print("Step 4: Verifying Extract Step")
    print("=" * 60)
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    prefix = f"extracted/{yesterday.strftime('%Y/%m/%d')}/"
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' in response:
            print(f"✓ Found {len(response['Contents'])} extracted file(s)")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
                
                # Download and check content
                file_obj = s3.get_object(Bucket=bucket_name, Key=obj['Key'])
                data = json.loads(file_obj['Body'].read())
                print(f"    Records: {len(data)}")
                return True
        else:
            print("✗ No extracted files found")
            return False
    except Exception as e:
        print(f"✗ Error verifying extract: {e}")
        return False

def verify_transform_step(bucket_name):
    """Verify Transform step output"""
    print("\n" + "=" * 60)
    print("Step 5: Verifying Transform Step")
    print("=" * 60)
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    prefix = f"transformed/{yesterday.strftime('%Y/%m/%d')}/"
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' in response:
            print(f"✓ Found {len(response['Contents'])} transformed file(s)")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
                
                # Download and check content
                file_obj = s3.get_object(Bucket=bucket_name, Key=obj['Key'])
                data = json.loads(file_obj['Body'].read())
                print(f"    Records: {len(data)}")
                if data:
                    print(f"    Sample record: {json.dumps(data[0], default=str, indent=2)}")
                return True
        else:
            print("✗ No transformed files found")
            return False
    except Exception as e:
        print(f"✗ Error verifying transform: {e}")
        return False

def verify_load_step(destination_table_name):
    """Verify Load step output"""
    print("\n" + "=" * 60)
    print("Step 6: Verifying Load Step")
    print("=" * 60)
    
    try:
        table = dynamodb.Table(destination_table_name)
        response = table.scan(Limit=10)
        
        if response['Items']:
            print(f"✓ Found {len(response['Items'])} records in destination table")
            for item in response['Items'][:3]:
                print(f"  - ID: {item.get('id')}, Timestamp: {item.get('timestamp')}")
                if 'data' in item:
                    print(f"    Data: {json.dumps(item['data'], default=str)}")
            return True
        else:
            print("✗ No records found in destination table")
            return False
    except Exception as e:
        print(f"✗ Error verifying load: {e}")
        return False

def verify_archive(bucket_name):
    """Verify archived files"""
    print("\n" + "=" * 60)
    print("Step 7: Verifying Archive")
    print("=" * 60)
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    prefix = f"archived/{yesterday.strftime('%Y/%m/%d')}/"
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' in response:
            print(f"✓ Found {len(response['Contents'])} archived file(s)")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
            return True
        else:
            print("✗ No archived files found")
            return False
    except Exception as e:
        print(f"✗ Error verifying archive: {e}")
        return False

def main():
    """Run complete ETL pipeline test"""
    print("\n" + "=" * 60)
    print("ETL Pipeline Stack - Complete Test Suite")
    print("=" * 60)
    
    # Get stack outputs
    try:
        outputs = get_stack_outputs('EtlPipelineStack')
        state_machine_arn = outputs['StateMachineArn']
        bucket_name = outputs['StagingBucketName']
        source_table = outputs['SourceTableName']
        destination_table = outputs['DestinationTableName']
        
        print(f"\nStack Resources:")
        print(f"  State Machine: {state_machine_arn}")
        print(f"  Staging Bucket: {bucket_name}")
        print(f"  Source Table: {source_table}")
        print(f"  Destination Table: {destination_table}")
    except Exception as e:
        print(f"✗ Error getting stack outputs: {e}")
        return
    
    # Run tests
    setup_test_data(source_table)
    execution_arn = trigger_etl_pipeline(state_machine_arn)
    
    if monitor_execution(execution_arn):
        verify_extract_step(bucket_name)
        verify_transform_step(bucket_name)
        verify_load_step(destination_table)
        verify_archive(bucket_name)
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check Step Functions console for execution details")
    print("2. Review CloudWatch Logs for each Lambda function")
    print("3. Query destination table: aws dynamodb scan --table-name etl-destination-data")

if __name__ == '__main__':
    main()