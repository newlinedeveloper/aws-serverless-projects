import boto3
import json
import time
from datetime import datetime

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
cloudformation = boto3.client('cloudformation')

def get_stack_outputs(stack_name):
    """Get stack outputs"""
    response = cloudformation.describe_stacks(StackName=stack_name)
    outputs = {o['OutputKey']: o['OutputValue'] 
               for o in response['Stacks'][0]['Outputs']}
    return outputs

def create_test_documents():
    """Create test documents"""
    print("=" * 60)
    print("Step 1: Creating Test Documents")
    print("=" * 60)
    
    test_text = """This is a sample document for AI processing. 
The weather is beautiful today and I feel very happy about it.
Amazon Web Services provides excellent cloud computing solutions.
I love working with serverless technologies like Lambda and API Gateway.
The company is located in Seattle, Washington.
We provide innovative solutions for customers worldwide."""
    
    return test_text

def upload_document(bucket_name, content, filename):
    """Upload document to S3"""
    print(f"\n[Step 2] Uploading {filename} to S3...")
    
    s3.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=content.encode('utf-8'),
        ContentType='text/plain'
    )
    print(f"✓ Uploaded: {filename}")

def wait_for_processing(timeout=120):
    """Wait for Lambda to process"""
    print(f"\n[Step 3] Waiting {timeout} seconds for Lambda processing...")
    time.sleep(timeout)

def verify_dynamodb_results(table_name, filename):
    """Verify results in DynamoDB"""
    print("\n" + "=" * 60)
    print("Step 4: Verifying DynamoDB Results")
    print("=" * 60)
    
    try:
        table = dynamodb.Table(table_name)
        response = table.query(
            KeyConditionExpression='file_name = :fn',
            ExpressionAttributeValues={':fn': filename},
            ScanIndexForward=False,
            Limit=1
        )
        
        if response['Items']:
            item = response['Items'][0]
            print(f"✓ Found results for {filename}")
            print(f"\nProcessing Results:")
            print(f"  File Type: {item.get('file_type', 'N/A')}")
            print(f"  Processed At: {item.get('processed_at', 'N/A')}")
            
            # Check Textract results
            if 'textract' in item:
                textract_data = item['textract']
                if 'extracted_text' in textract_data:
                    text = textract_data['extracted_text']
                    print(f"\n  Textract:")
                    print(f"    Extracted Text: {text[:100]}...")
                    print(f"    Full Text Length: {textract_data.get('full_text_length', 'N/A')}")
                elif 'error' in textract_data:
                    print(f"    Textract Error: {textract_data['error']}")
            
            # Check Comprehend results
            if 'comprehend' in item:
                comprehend_data = item['comprehend']
                if 'sentiment' in comprehend_data:
                    print(f"\n  Comprehend:")
                    print(f"    Sentiment: {comprehend_data['sentiment']}")
                    print(f"    Sentiment Scores: {comprehend_data.get('sentiment_scores', {})}")
                    if 'entities' in comprehend_data:
                        print(f"    Entities: {len(comprehend_data['entities'])} found")
                    if 'key_phrases' in comprehend_data:
                        print(f"    Key Phrases: {len(comprehend_data['key_phrases'])} found")
                elif 'error' in comprehend_data:
                    print(f"    Comprehend Error: {comprehend_data['error']}")
            
            # Check Translate results
            if 'translate' in item:
                translate_data = item['translate']
                if 'translated_text' in translate_data:
                    print(f"\n  Translate:")
                    print(f"    Source: {translate_data.get('source_language', 'N/A')}")
                    print(f"    Target: {translate_data.get('target_language', 'N/A')}")
                    print(f"    Translated: {translate_data['translated_text'][:100]}...")
                elif 'error' in translate_data:
                    print(f"    Translate Error: {translate_data['error']}")
            
            # Check Polly results
            if 'polly' in item:
                polly_data = item['polly']
                if 'audio_s3_key' in polly_data:
                    print(f"\n  Polly:")
                    print(f"    Audio File: {polly_data['audio_s3_key']}")
                    print(f"    Voice: {polly_data.get('voice_id', 'N/A')}")
                elif 'error' in polly_data:
                    print(f"    Polly Error: {polly_data['error']}")
            
            return True
        else:
            print(f"✗ No results found for {filename}")
            return False
            
    except Exception as e:
        print(f"✗ Error querying DynamoDB: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_s3_outputs(output_bucket, filename):
    """Verify output files in S3"""
    print("\n" + "=" * 60)
    print("Step 5: Verifying S3 Output Files")
    print("=" * 60)
    
    try:
        # Check for Polly audio
        polly_prefix = f"polly/{filename}_audio.mp3"
        try:
            s3.head_object(Bucket=output_bucket, Key=polly_prefix)
            print(f"✓ Found Polly audio: {polly_prefix}")
        except:
            print(f"⚠ No Polly audio found (may not have been generated)")
        
        # Check for Textract full text (if text was too long)
        textract_prefix = f"textract/{filename}_full_text.txt"
        try:
            s3.head_object(Bucket=output_bucket, Key=textract_prefix)
            print(f"✓ Found Textract full text: {textract_prefix}")
        except:
            print(f"⚠ No separate Textract file (text may be short enough for DynamoDB)")
        
        # List all outputs
        response = s3.list_objects_v2(Bucket=output_bucket, MaxKeys=10)
        if 'Contents' in response:
            print(f"\nAll output files ({len(response['Contents'])}):")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
        
        return True
    except Exception as e:
        print(f"✗ Error checking S3 outputs: {e}")
        return False

def test_api_endpoints(api_endpoint):
    """Test API Gateway endpoints"""
    print("\n" + "=" * 60)
    print("Step 6: Testing API Gateway Endpoints")
    print("=" * 60)
    
    import urllib.request
    import urllib.parse
    import urllib.error
    
    try:
        # Test GET /results (all results)
        url = f"{api_endpoint}results"
        print(f"\nTesting: GET {url}")
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                print(f"✓ API Response: {data.get('count', 0)} results")
                if data.get('results'):
                    print(f"  Sample result keys: {list(data['results'][0].keys())}")
        except urllib.error.HTTPError as e:
            print(f"✗ HTTP Error {e.code}: {e.reason}")
            print(f"  Response: {e.read().decode()[:200]}")
            # Check Lambda logs
            print("\n  Checking Lambda logs for errors...")
            return False
        
        # Test GET /results?file_name=sample.txt
        url = f"{api_endpoint}results?file_name=sample.txt"
        print(f"\nTesting: GET {url}")
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                print(f"✓ API Response: {data.get('count', 0)} results for sample.txt")
        except urllib.error.HTTPError as e:
            print(f"✗ HTTP Error {e.code}: {e.reason}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_lambda_logs(function_name='ai-document-processor', minutes=10):
    """Check Lambda logs"""
    print("\n" + "=" * 60)
    print("Step 7: Checking Lambda Logs")
    print("=" * 60)
    
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
                    print(f"  ✗ {message[:200]}")
                elif 'processedFiles' in message or 'Success' in message:
                    print(f"  ✓ {message[:200]}")
                else:
                    print(f"  - {message[:100]}")
        else:
            print("⚠ No recent log events found")
    except Exception as e:
        print(f"✗ Error checking logs: {e}")

def main():
    """Run complete AI Services test"""
    print("\n" + "=" * 60)
    print("AI Services Stack - End-to-End Test Suite")
    print("=" * 60)
    
    # Get stack outputs
    try:
        outputs = get_stack_outputs('AiServicesStack')
        documents_bucket = outputs['DocumentsBucketName']
        output_bucket = outputs['OutputBucketName']
        api_endpoint = outputs['ApiEndpoint']
        table_name = outputs['ResultsTableName']
        
        print(f"\nStack Resources:")
        print(f"  Documents Bucket: {documents_bucket}")
        print(f"  Output Bucket: {output_bucket}")
        print(f"  API Endpoint: {api_endpoint}")
        print(f"  Results Table: {table_name}")
    except Exception as e:
        print(f"✗ Error getting stack outputs: {e}")
        return
    
    # Run tests
    test_text = create_test_documents()
    filename = "sample.txt"
    
    upload_document(documents_bucket, test_text, filename)
    wait_for_processing(timeout=60)  # Wait 60 seconds for processing
    
    if verify_dynamodb_results(table_name, filename):
        verify_s3_outputs(output_bucket, filename)
        test_api_endpoints(api_endpoint)
        check_lambda_logs()
    
    print("\n" + "=" * 60)
    print("Test Suite Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Upload image files (PNG, JPG) or PDFs for Textract testing")
    print("2. Check Lambda logs: /aws/lambda/ai-document-processor")
    print("3. Query results: curl " + api_endpoint + "results")
    print("4. Download audio files from output bucket")

if __name__ == '__main__':
    main()