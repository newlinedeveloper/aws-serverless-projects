import boto3
import json
import time
from datetime import datetime

# Initialize clients
s3 = boto3.client('s3')
glue = boto3.client('glue')
athena = boto3.client('athena')
cloudformation = boto3.client('cloudformation')

def get_stack_outputs(stack_name):
    """Get stack outputs"""
    response = cloudformation.describe_stacks(StackName=stack_name)
    outputs = {o['OutputKey']: o['OutputValue'] 
               for o in response['Stacks'][0]['Outputs']}
    return outputs

def create_test_data():
    """Create sample test data"""
    print("=" * 60)
    print("Step 1: Creating Test Data")
    print("=" * 60)
    
    test_data = [
        {
            "id": "001",
            "name": "Product A",
            "category": "Electronics",
            "price": 99.99,
            "quantity": 50,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        {
            "id": "002",
            "name": "Product B",
            "category": "Clothing",
            "price": 49.99,
            "quantity": 100,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        {
            "id": "003",
            "name": "Product C",
            "category": "Electronics",
            "price": 199.99,
            "quantity": 25,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    ]
    
    return test_data

def upload_to_raw_bucket(bucket_name, test_data):
    """Upload test data to raw bucket"""
    print("\n" + "=" * 60)
    print("Step 2: Uploading Data to Raw Bucket")
    print("=" * 60)
    
    uploaded_files = []
    for i, data in enumerate(test_data, 1):
        key = f"data/sample_data_{i}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(data),
            ContentType='application/json'
        )
        print(f"✓ Uploaded: {key}")
        uploaded_files.append(key)
    
    return uploaded_files

def verify_processed_data(processed_bucket):
    """Verify data was processed"""
    print("\n" + "=" * 60)
    print("Step 3: Verifying Processed Data")
    print("=" * 60)
    
    # Wait for Lambda to process
    print("Waiting 10 seconds for Lambda processing...")
    time.sleep(10)
    
    # List processed files
    response = s3.list_objects_v2(
        Bucket=processed_bucket,
        Prefix='processed/',
        MaxKeys=10
    )
    
    if 'Contents' in response:
        print(f"✓ Found {len(response['Contents'])} processed files:")
        for obj in response['Contents'][:5]:
            print(f"  - {obj['Key']} ({obj['Size']} bytes)")
        
        # Download and view one file
        if response['Contents']:
            sample_key = response['Contents'][0]['Key']
            file_obj = s3.get_object(Bucket=processed_bucket, Key=sample_key)
            data = json.loads(file_obj['Body'].read())
            print(f"\nSample processed data structure:")
            print(json.dumps(data, indent=2, default=str))
            return True
    else:
        print("✗ No processed files found")
        return False

def wait_for_crawler(crawler_name, timeout=300):
    """Wait for Glue crawler to complete"""
    print("\n" + "=" * 60)
    print("Step 4: Waiting for Glue Crawler")
    print("=" * 60)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = glue.get_crawler(Name=crawler_name)
        state = response['Crawler']['State']
        print(f"Crawler state: {state}")
        
        if state == 'READY':
            print("✓ Crawler is ready")
            # Check last crawl status
            try:
                last_crawl = response['Crawler'].get('LastCrawl', {})
                if last_crawl:
                    status = last_crawl.get('Status', 'UNKNOWN')
                    print(f"  Last crawl status: {status}")
                    if status == 'SUCCEEDED':
                        print("✓ Last crawl succeeded")
                    elif status == 'FAILED':
                        error = last_crawl.get('ErrorMessage', 'Unknown error')
                        print(f"✗ Last crawl failed: {error}")
                        return False
            except Exception as e:
                print(f"  Could not get last crawl info: {e}")
            return True
        elif state == 'STOPPING':
            # Wait for it to transition to final state
            print("  Crawler is stopping, waiting for final state...")
            time.sleep(5)
            continue
        elif state == 'STOPPED':
            print("⚠ Crawler is stopped")
            # Check if there was an error
            try:
                response = glue.get_crawler(Name=crawler_name)
                last_crawl = response['Crawler'].get('LastCrawl', {})
                if last_crawl:
                    status = last_crawl.get('Status', 'UNKNOWN')
                    error = last_crawl.get('ErrorMessage', '')
                    print(f"  Last crawl status: {status}")
                    if status == 'SUCCEEDED':
                        print("✓ Last crawl succeeded despite STOPPED state")
                        return True
                    elif status == 'FAILED':
                        print(f"✗ Last crawl failed: {error}")
                        return False
            except Exception as e:
                print(f"  Error checking crawler status: {e}")
            return False
        
        time.sleep(5)
    
    print("✗ Crawler timeout")
    return False

def verify_glue_tables(database_name):
    """Verify Glue tables were created"""
    print("\n" + "=" * 60)
    print("Step 5: Verifying Glue Tables")
    print("=" * 60)
    
    try:
        response = glue.get_tables(DatabaseName=database_name)
        tables = response['TableList']
        
        if tables:
            print(f"✓ Found {len(tables)} table(s):")
            for table in tables:
                print(f"  - {table['Name']}")
                print(f"    Location: {table.get('StorageDescriptor', {}).get('Location', 'N/A')}")
                print(f"    Columns: {len(table.get('StorageDescriptor', {}).get('Columns', []))}")
            return tables[0]['Name'] if tables else None
        else:
            print("✗ No tables found")
            return None
    except Exception as e:
        print(f"✗ Error getting tables: {e}")
        return None

def query_athena(workgroup, database, table):
    """Query data using Athena"""
    print("\n" + "=" * 60)
    print("Step 6: Querying Data with Athena")
    print("=" * 60)
    
    query = f'SELECT * FROM "{database}"."{table}" LIMIT 10'
    print(f"Query: {query}")
    
    try:
        # Start query
        response = athena.start_query_execution(
            QueryString=query,
            WorkGroup=workgroup
        )
        execution_id = response['QueryExecutionId']
        print(f"✓ Query started: {execution_id}")
        
        # Wait for completion
        while True:
            response = athena.get_query_execution(QueryExecutionId=execution_id)
            status = response['QueryExecution']['Status']['State']
            
            print(f"  Status: {status}")
            
            if status == 'SUCCEEDED':
                print("✓ Query succeeded")
                break
            elif status == 'FAILED':
                print("✗ Query failed")
                print(f"  Error: {response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')}")
                return False
            
            time.sleep(2)
        
        # Get results
        response = athena.get_query_results(QueryExecutionId=execution_id)
        rows = response['ResultSet']['Rows']
        
        print(f"\n✓ Query Results ({len(rows)} rows):")
        for i, row in enumerate(rows[:5]):  # Show first 5 rows
            values = [col.get('VarCharValue', '') for col in row['Data']]
            print(f"  Row {i}: {values}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error querying Athena: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run complete data lake test"""
    print("\n" + "=" * 60)
    print("DataLakeStack - End-to-End Test Suite")
    print("=" * 60)
    
    # Get stack outputs
    try:
        outputs = get_stack_outputs('DataLakeStack')
        raw_bucket = outputs['RawBucketName']
        processed_bucket = outputs['ProcessedBucketName']
        glue_db = outputs['GlueDatabaseName']
        crawler_name = outputs['GlueCrawlerName']
        workgroup = outputs['AthenaWorkGroupName']
        
        print(f"\nStack Resources:")
        print(f"  Raw Bucket: {raw_bucket}")
        print(f"  Processed Bucket: {processed_bucket}")
        print(f"  Glue Database: {glue_db}")
        print(f"  Crawler: {crawler_name}")
        print(f"  WorkGroup: {workgroup}")
    except Exception as e:
        print(f"✗ Error getting stack outputs: {e}")
        return
    
    # Run tests
    test_data = create_test_data()
    upload_to_raw_bucket(raw_bucket, test_data)
    
    if verify_processed_data(processed_bucket):
        if wait_for_crawler(crawler_name):
            table_name = verify_glue_tables(glue_db)
            if table_name:
                query_athena(workgroup, glue_db, table_name)
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check Lambda logs: /aws/lambda/data-lake-processor")
    print("2. View processed data: aws s3 ls s3://<processed-bucket>/processed/ --recursive")
    print("3. Query Athena: Use AWS Console or CLI")

if __name__ == '__main__':
    main()