import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

s3_client = boto3.client('s3')

def handler(event, context):
    """
    Transform extracted data according to business rules
    """
    staging_bucket = os.environ['STAGING_BUCKET_NAME']
    
    # Handle Step Functions event structure
    if 'stagingKey' in event:
        staging_key = event['stagingKey']
    elif 'Payload' in event and 'stagingKey' in event['Payload']:
        staging_key = event['Payload']['stagingKey']
    else:
        print(f"Error: stagingKey not found in event. Event keys: {list(event.keys())}")
        raise ValueError("stagingKey not found in event")
    
    print(f"Transforming data from: {staging_key}")
    
    try:
        # Download extracted data
        response = s3_client.get_object(Bucket=staging_bucket, Key=staging_key)
        extracted_data = json.loads(response['Body'].read())
        
        print(f"Downloaded {len(extracted_data)} records from S3")
        
        if not extracted_data:
            print("Warning: No data to transform")
            return {
                'statusCode': 200,
                'recordsTransformed': 0,
                'transformedKey': staging_key.replace('extracted/', 'transformed/'),
                'originalKey': staging_key
            }
        
        transformed_records = []
        
        for record in extracted_data:
            try:
                # Convert DynamoDB types to Python types
                # DynamoDB items come as dicts with type info, but when loaded from JSON they're already converted
                # Handle both cases
                record_dict = {}
                for key, value in record.items():
                    if isinstance(value, Decimal):
                        record_dict[key] = float(value)
                    elif isinstance(value, dict) and 'S' in value:  # DynamoDB string type
                        record_dict[key] = value['S']
                    elif isinstance(value, dict) and 'N' in value:  # DynamoDB number type
                        record_dict[key] = float(value['N'])
                    else:
                        record_dict[key] = value
                
                # Apply transformations
                transformed_record = {
                    'id': record_dict.get('id', record_dict.get('partition_key', 'unknown')),
                    'timestamp': record_dict.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                    'processed_at': datetime.utcnow().isoformat() + 'Z',
                    'data': {}
                }
                
                # Transform numeric fields
                if 'value' in record_dict:
                    try:
                        transformed_record['data']['value'] = float(record_dict['value'])
                    except (ValueError, TypeError):
                        pass
                
                if 'count' in record_dict:
                    try:
                        transformed_record['data']['count'] = int(record_dict['count'])
                    except (ValueError, TypeError):
                        pass
                
                # Add computed fields
                if 'total_value' in record_dict and 'count' in record_dict:
                    try:
                        total = float(record_dict['total_value'])
                        count = int(record_dict['count'])
                        if count > 0:
                            transformed_record['data']['average'] = total / count
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass
                
                # Copy other fields
                for key, value in record_dict.items():
                    if key not in ['id', 'partition_key', 'timestamp', 'value', 'count', 'total_value']:
                        transformed_record['data'][key] = value
                
                transformed_records.append(transformed_record)
                
            except Exception as e:
                print(f"Error transforming record: {e}")
                print(f"Record: {json.dumps(record, default=str)}")
                continue
        
        # Write transformed data to S3
        transformed_key = staging_key.replace('extracted/', 'transformed/')
        s3_client.put_object(
            Bucket=staging_bucket,
            Key=transformed_key,
            Body=json.dumps(transformed_records, default=str),
            ContentType='application/json'
        )
        
        print(f"Transformed {len(transformed_records)} records, saved to: {transformed_key}")
        
        return {
            'statusCode': 200,
            'recordsTransformed': len(transformed_records),
            'transformedKey': transformed_key,
            'originalKey': staging_key
        }
        
    except Exception as e:
        error_msg = f"Error in transform step: {str(e)}"
        print(error_msg)
        print(f"Event received: {json.dumps(event, default=str, indent=2)}")
        raise Exception(error_msg)

