import json
import boto3
import os
from datetime import datetime

s3_client = boto3.client('s3')
glue_client = boto3.client('glue')

def handler(event, context):
    """
    Process data ingestion and transformation for data lake
    """
    raw_bucket = os.environ['RAW_BUCKET_NAME']
    processed_bucket = os.environ['PROCESSED_BUCKET_NAME']
    glue_database = os.environ['GLUE_DATABASE_NAME']
    glue_crawler = os.environ['GLUE_CRAWLER_NAME']
    
    processed_files = []
    
    for record in event.get('Records', []):
        try:
            # Get S3 object details
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Only process files in raw bucket
            if bucket != raw_bucket:
                continue
            
            # Download raw data
            response = s3_client.get_object(Bucket=bucket, Key=key)
            raw_data = response['Body'].read().decode('utf-8')
            
            # Parse and transform data
            try:
                data = json.loads(raw_data)
            except:
                # If not JSON, treat as CSV or other format
                data = {'raw_content': raw_data}
            
            # Transform data (add metadata, partition info)
            transformed_data = {
                'source_file': key,
                'ingestion_timestamp': datetime.utcnow().isoformat(),
                'data': data,
                'partition_date': datetime.utcnow().strftime('%Y-%m-%d'),
                'partition_hour': datetime.utcnow().strftime('%H')
            }
            
            # Write to processed bucket with partitioning
            processed_key = f"processed/year={transformed_data['partition_date'][:4]}/month={transformed_data['partition_date'][5:7]}/day={transformed_data['partition_date'][8:10]}/hour={transformed_data['partition_hour']}/{os.path.basename(key)}"
            
            s3_client.put_object(
                Bucket=processed_bucket,
                Key=processed_key,
                Body=json.dumps(transformed_data, default=str),
                ContentType='application/json'
            )
            
            processed_files.append(processed_key)
            
        except Exception as e:
            print(f"Error processing file {key}: {e}")
            continue
    
    # Trigger Glue Crawler to update schema (if files were processed)
    if processed_files:
        try:
            glue_client.start_crawler(Name=glue_crawler)
            print(f"Started Glue Crawler: {glue_crawler}")
        except Exception as e:
            print(f"Error starting Glue Crawler: {e}")
    
    return {
        'statusCode': 200,
        'processedFiles': len(processed_files),
        'files': processed_files
    }

