import json
import boto3
import os
from decimal import Decimal

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Load transformed data into destination (DynamoDB)
    """
    staging_bucket = os.environ['STAGING_BUCKET_NAME']
    destination_table_name = os.environ['DESTINATION_TABLE_NAME']
    
    # Handle Step Functions event structure
    # Step Functions wraps Lambda response in $.Payload, but passes it directly to next step
    # So event should have transformedKey directly, but let's handle both cases
    if 'transformedKey' in event:
        transformed_key = event['transformedKey']
    elif 'Payload' in event and 'transformedKey' in event['Payload']:
        transformed_key = event['Payload']['transformedKey']
    else:
        print(f"Error: transformedKey not found in event. Event keys: {list(event.keys())}")
        print(f"Event structure: {json.dumps(event, default=str, indent=2)}")
        raise ValueError("transformedKey not found in event")
    
    print(f"Loading data from: {transformed_key}")
    
    try:
        # Download transformed data
        response = s3_client.get_object(Bucket=staging_bucket, Key=transformed_key)
        transformed_data = json.loads(response['Body'].read())
        
        print(f"Downloaded {len(transformed_data)} records from S3")
        
        if not transformed_data:
            print("Warning: No transformed data to load")
            return {
                'statusCode': 200,
                'recordsLoaded': 0,
                'errors': 0,
                'errorDetails': []
            }
        
        table = dynamodb.Table(destination_table_name)
        
        loaded_count = 0
        errors = []
        
        for record in transformed_data:
            try:
                # Ensure required fields exist
                if 'id' not in record:
                    error_msg = f"Record missing 'id' field: {record}"
                    print(error_msg)
                    errors.append(error_msg)
                    continue
                
                if 'timestamp' not in record:
                    error_msg = f"Record {record.get('id')} missing 'timestamp' field"
                    print(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Convert to DynamoDB format
                item = {}
                for key, value in record.items():
                    if value is None:
                        continue  # Skip None values
                    elif isinstance(value, (int, float)):
                        item[key] = Decimal(str(value))
                    elif isinstance(value, bool):
                        item[key] = value
                    elif isinstance(value, dict):
                        # Handle nested dict (like 'data' field)
                        nested_dict = {}
                        for k, v in value.items():
                            if v is None:
                                continue
                            elif isinstance(v, (int, float)):
                                nested_dict[k] = Decimal(str(v))
                            elif isinstance(v, bool):
                                nested_dict[k] = v
                            else:
                                nested_dict[k] = str(v)
                        item[key] = nested_dict
                    elif isinstance(value, list):
                        # Handle lists
                        item[key] = [str(v) for v in value]
                    else:
                        item[key] = str(value)
                
                # Write to DynamoDB
                table.put_item(Item=item)
                loaded_count += 1
                print(f"Loaded record: {item.get('id')}")
                
            except Exception as e:
                error_msg = f"Error loading record {record.get('id', 'unknown')}: {str(e)}"
                print(error_msg)
                print(f"Record data: {json.dumps(record, default=str)}")
                errors.append(error_msg)
        
        # Archive processed file
        try:
            archive_key = transformed_key.replace('transformed/', 'archived/')
            s3_client.copy_object(
                Bucket=staging_bucket,
                CopySource={'Bucket': staging_bucket, 'Key': transformed_key},
                Key=archive_key
            )
            print(f"Archived file to: {archive_key}")
        except Exception as e:
            print(f"Warning: Could not archive file: {e}")
        
        print(f"Successfully loaded {loaded_count} records, {len(errors)} errors")
        
        return {
            'statusCode': 200,
            'recordsLoaded': loaded_count,
            'errors': len(errors),
            'errorDetails': errors[:5]  # Return first 5 errors
        }
        
    except Exception as e:
        error_msg = f"Error in load step: {str(e)}"
        print(error_msg)
        print(f"Event received: {json.dumps(event, default=str, indent=2)}")
        raise Exception(error_msg)

