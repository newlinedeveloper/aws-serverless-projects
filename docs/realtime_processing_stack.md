# Real-Time Processing Stack

## Overview

The Real-Time Processing Stack implements a serverless pipeline for processing IoT sensor data or clickstream analytics in real-time. It uses AWS Kinesis Data Streams for ingestion, Lambda for processing, S3 for archival, and DynamoDB for storing processed metrics.

## Architecture

```
Data Sources → Kinesis Data Stream → Lambda Processor → S3 Archive
                                                    ↓
                                            DynamoDB Metrics
                                                    ↓
                                            CloudWatch Alarms → SNS
```

## Resources

### 1. Kinesis Data Stream
- **Name**: `realtime-data-stream`
- **Shards**: 2
- **Retention**: 24 hours
- **Encryption**: KMS
- **Purpose**: Ingests real-time data from IoT sensors or applications

### 2. S3 Archive Bucket
- **Name**: `realtime-data-archive-{account}-{region}`
- **Versioning**: Enabled
- **Lifecycle Rules**:
  - Transition to GLACIER after 30 days
  - Transition to DEEP_ARCHIVE after 120 days
- **Purpose**: Long-term archival of processed data

### 3. DynamoDB Metrics Table
- **Name**: `realtime-processed-metrics`
- **Partition Key**: `partition_key` (String)
- **Sort Key**: `timestamp` (String)
- **TTL**: Enabled
- **Billing**: Pay-per-request
- **Purpose**: Stores aggregated metrics and processed data

### 4. Lambda Function
- **Name**: `realtime-data-processor`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Event Source**: Kinesis Data Stream
- **Batch Size**: 100 records
- **Max Batching Window**: 5 seconds
- **Parallelization Factor**: 2
- **Retry Attempts**: 3

### 5. CloudWatch Alarms
- **Error Alarm**: Triggers when Lambda errors exceed 5
- **Throttling Alarm**: Triggers when Lambda is throttled
- **Actions**: Sends notifications to SNS topic

### 6. SNS Topic
- **Name**: `realtime-processing-alerts`
- **Purpose**: Receives alarm notifications (can be configured with email subscriptions)

## Data Flow

1. **Ingestion**: Data is sent to Kinesis Data Stream using `put-record` or `put-records` API
2. **Processing**: Lambda function is automatically triggered when records arrive in the stream
3. **Processing Logic**:
   - Decodes base64-encoded Kinesis records
   - Parses JSON data
   - Extracts metrics (e.g., sensor readings, user events)
   - Aggregates data by partition and timestamp
4. **Storage**:
   - Raw data is archived to S3 with timestamp prefix
   - Processed metrics are stored in DynamoDB
5. **Monitoring**: CloudWatch alarms monitor for errors and throttling

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.realtime_processing_stack import RealtimeProcessingStack
   
   RealtimeProcessingStack(app, "RealtimeProcessingStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth RealtimeProcessingStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy RealtimeProcessingStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name RealtimeProcessingStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Send Test Data to Kinesis

**Option A: Using AWS CLI (v2)**
```bash
# Get stream name from stack outputs
STREAM_NAME=$(aws cloudformation describe-stacks \
  --stack-name RealtimeProcessingStack \
  --query "Stacks[0].Outputs[?OutputKey=='DataStreamName'].OutputValue" \
  --output text)

# Send a test record (CLI v2 handles base64 encoding automatically)
aws kinesis put-record \
  --stream-name $STREAM_NAME \
  --partition-key "sensor-001" \
  --data '{"sensorId":"sensor-001","temperature":25.5,"humidity":60,"timestamp":"2024-01-15T10:30:00Z"}' \
  --cli-binary-format raw-in-base64-out
```

**Option B: Using Python Script**
```python
import boto3
import json
import base64

kinesis = boto3.client('kinesis')
stream_name = 'realtime-data-stream'

# Create test data
data = {
    "sensorId": "sensor-001",
    "temperature": 25.5,
    "humidity": 60,
    "timestamp": "2024-01-15T10:30:00Z"
}

# Send to Kinesis
response = kinesis.put_record(
    StreamName=stream_name,
    PartitionKey="sensor-001",
    Data=json.dumps(data)
)

print(f"Record sent. Sequence number: {response['SequenceNumber']}")
```

**Option C: Send Multiple Records**
```bash
# Create a file with multiple records
cat > records.json << EOF
{"Data": "{\"sensorId\":\"sensor-001\",\"temperature\":25.5}", "PartitionKey": "sensor-001"}
{"Data": "{\"sensorId\":\"sensor-002\",\"temperature\":26.0}", "PartitionKey": "sensor-002"}
EOF

# Send records
aws kinesis put-records \
  --stream-name $STREAM_NAME \
  --records file://records.json \
  --cli-binary-format raw-in-base64-out
```

### 2. Verify Processing

**Check Lambda Logs:**
```bash
aws logs tail /aws/lambda/realtime-data-processor --follow
```

**Check DynamoDB Metrics:**
```bash
aws dynamodb scan \
  --table-name realtime-processed-metrics \
  --limit 10
```

**Check S3 Archive:**
```bash
ARCHIVE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name RealtimeProcessingStack \
  --query "Stacks[0].Outputs[?OutputKey=='ArchiveBucketName'].OutputValue" \
  --output text)

aws s3 ls s3://$ARCHIVE_BUCKET/ --recursive
```

### 3. Monitor Alarms

**Check CloudWatch Alarms:**
```bash
aws cloudwatch describe-alarms \
  --alarm-names \
    RealtimeProcessingStack-ProcessorErrorAlarm \
    RealtimeProcessingStack-ProcessorThrottlingAlarm
```

**Subscribe to SNS Alerts:**
```bash
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name RealtimeProcessingStack \
  --query "Stacks[0].Outputs[?OutputKey=='AlertTopicArn'].OutputValue" \
  --output text)

# Subscribe email to topic
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Example Use Cases

1. **IoT Sensor Data**: Process temperature, humidity, and other sensor readings
2. **Clickstream Analytics**: Track user interactions and page views
3. **Log Aggregation**: Process application logs in real-time
4. **Metrics Collection**: Aggregate system metrics and KPIs

## Cost Optimization

- **Kinesis**: Pay per shard-hour and data ingested
- **Lambda**: Pay per invocation and compute time
- **S3**: Pay for storage and requests (lifecycle rules reduce costs)
- **DynamoDB**: Pay-per-request pricing (no minimum charges)
- **CloudWatch**: First 10 alarms are free

## Troubleshooting

### Lambda Not Processing Records
- Check Lambda logs: `aws logs tail /aws/lambda/realtime-data-processor --follow`
- Verify Kinesis event source mapping: `aws lambda list-event-source-mappings`
- Check IAM permissions

### Records Not Appearing in DynamoDB
- Verify Lambda has write permissions to DynamoDB
- Check for errors in Lambda logs
- Verify table name in Lambda environment variables

### High Latency
- Increase Lambda memory allocation
- Adjust Kinesis shard count
- Optimize Lambda function code

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy RealtimeProcessingStack
```

**Note**: S3 buckets with `auto_delete_objects=True` will be automatically emptied before deletion.

