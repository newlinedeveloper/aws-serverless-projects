# ETL Pipeline Stack

## Overview

The ETL Pipeline Stack implements a scheduled Extract, Transform, Load (ETL) pipeline that runs daily to process data from a source DynamoDB table, transform it, and load it into a destination table. It uses EventBridge for scheduling, Step Functions for orchestration, Lambda functions for each ETL stage, and S3 for staging intermediate data.

## Architecture

```
EventBridge Schedule → Step Functions → Extract Lambda → S3 Staging
                                              ↓
                                    Transform Lambda → S3 Processed
                                              ↓
                                    Load Lambda → DynamoDB Destination
```

## Resources

### 1. S3 Staging Bucket
- **Name**: `etl-staging-{account}-{region}`
- **Lifecycle Rule**: Delete files after 30 days
- **Purpose**: Stores intermediate data between ETL stages

### 2. Source DynamoDB Table
- **Name**: `etl-source-data`
- **Partition Key**: `id` (String)
- **Billing**: Pay-per-request
- **Purpose**: Source system data (simulated)

### 3. Destination DynamoDB Table
- **Name**: `etl-destination-data`
- **Partition Key**: `id` (String)
- **Sort Key**: `timestamp` (String)
- **Billing**: Pay-per-request
- **Purpose**: Data warehouse for processed data

### 4. Lambda Functions

#### Extract Lambda
- **Name**: `etl-extract`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Purpose**: Extracts data from source DynamoDB table and stores in S3

#### Transform Lambda
- **Name**: `etl-transform`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Purpose**: Transforms data from S3 staging area

#### Load Lambda
- **Name**: `etl-load`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Purpose**: Loads transformed data into destination DynamoDB table

### 5. Step Functions State Machine
- **Name**: `etl-pipeline`
- **Timeout**: 30 minutes
- **Tracing**: Enabled (X-Ray)
- **Workflow**: Extract → Transform → Load (sequential)

### 6. EventBridge Rule
- **Name**: `etl-daily-schedule`
- **Schedule**: Daily at 2:00 AM UTC (cron: `0 2 * * *`)
- **Target**: Step Functions state machine
- **Purpose**: Triggers ETL pipeline automatically

## Data Flow

1. **Scheduling**: EventBridge rule triggers Step Functions at 2 AM UTC daily
2. **Extract Stage**:
   - Lambda scans source DynamoDB table
   - Filters data by timestamp (last 24 hours)
   - Writes data to S3 staging bucket as JSON
   - Returns S3 key to Step Functions
3. **Transform Stage**:
   - Lambda reads data from S3 staging bucket
   - Transforms data (e.g., aggregations, calculations, format conversions)
   - Writes transformed data to S3 processed area
   - Returns S3 key to Step Functions
4. **Load Stage**:
   - Lambda reads transformed data from S3
   - Converts data types for DynamoDB
   - Writes data to destination DynamoDB table
   - Returns success status

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.etl_pipeline_stack import EtlPipelineStack
   
   EtlPipelineStack(app, "EtlPipelineStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth EtlPipelineStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy EtlPipelineStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name EtlPipelineStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Populate Source Data

```bash
# Get source table name
SOURCE_TABLE=$(aws cloudformation describe-stacks \
  --stack-name EtlPipelineStack \
  --query "Stacks[0].Outputs[?OutputKey=='SourceTableName'].OutputValue" \
  --output text)

# Add test data
aws dynamodb put-item \
  --table-name $SOURCE_TABLE \
  --item '{
    "id": {"S": "item-001"},
    "name": {"S": "Test Item 1"},
    "value": {"N": "100"},
    "timestamp": {"S": "2024-01-15T10:00:00Z"}
  }'

# Add more test data
aws dynamodb put-item \
  --table-name $SOURCE_TABLE \
  --item '{
    "id": {"S": "item-002"},
    "name": {"S": "Test Item 2"},
    "value": {"N": "200"},
    "timestamp": {"S": "2024-01-15T11:00:00Z"}
  }'
```

### 2. Manually Trigger ETL Pipeline

**Option A: Start Step Functions Execution**
```bash
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name EtlPipelineStack \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

# Start execution
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{}' \
  --query 'executionArn' \
  --output text)

echo "Execution ARN: $EXECUTION_ARN"
```

**Option B: Trigger via EventBridge (Test Event)**
```bash
# Get EventBridge rule name
RULE_NAME="etl-daily-schedule"

# Send test event
aws events put-events \
  --entries '[{
    "Source": "manual.trigger",
    "DetailType": "ETL Pipeline Trigger",
    "Detail": "{\"action\":\"start\"}"
  }]'
```

### 3. Monitor Execution

**Check Step Functions Execution Status:**
```bash
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN
```

**View Step Functions Console:**
- Navigate to AWS Step Functions console
- Find execution by ARN
- View visual workflow and execution details

**Check Lambda Logs:**
```bash
# Extract Lambda
aws logs tail /aws/lambda/etl-extract --follow

# Transform Lambda
aws logs tail /aws/lambda/etl-transform --follow

# Load Lambda
aws logs tail /aws/lambda/etl-load --follow
```

### 4. Verify Results

**Check S3 Staging Data:**
```bash
STAGING_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name EtlPipelineStack \
  --query "Stacks[0].Outputs[?OutputKey=='StagingBucketName'].OutputValue" \
  --output text)

aws s3 ls s3://$STAGING_BUCKET/ --recursive
```

**Check Destination Table:**
```bash
DEST_TABLE=$(aws cloudformation describe-stacks \
  --stack-name EtlPipelineStack \
  --query "Stacks[0].Outputs[?OutputKey=='DestinationTableName'].OutputValue" \
  --output text)

aws dynamodb scan \
  --table-name $DEST_TABLE \
  --limit 10
```

### 5. Run Complete Test Script

```bash
python tests/etl_pipeline/test_etl_pipeline.py
```

## ETL Process Details

### Extract Stage
- Scans source DynamoDB table
- Filters items by timestamp (last 24 hours by default)
- Exports data to S3 as JSON
- Returns S3 key: `extract/{timestamp}/data.json`

### Transform Stage
- Reads JSON from S3 staging
- Performs transformations:
  - Converts DynamoDB Decimal types to Python numbers
  - Aggregates data if needed
  - Adds computed fields
  - Validates data
- Writes transformed data to S3
- Returns S3 key: `transform/{timestamp}/data.json`

### Load Stage
- Reads transformed JSON from S3
- Converts data types for DynamoDB:
  - Numbers → Decimal
  - Booleans → bool
  - Nested objects → dict
  - Lists → list
  - None values → skipped
- Writes items to destination DynamoDB table
- Returns success status

## Scheduling

The pipeline runs automatically at **2:00 AM UTC daily**. To change the schedule:

1. Edit `serverless_app/stacks/etl_pipeline_stack.py`
2. Modify the cron expression:
   ```python
   schedule=events.Schedule.cron(
       minute="0",
       hour="2",  # Change hour (0-23)
       day="*",
       month="*",
       year="*"
   )
   ```
3. Redeploy the stack

## Error Handling

- **Step Functions**: Automatically retries failed Lambda invocations
- **Lambda Timeouts**: Configured to 5 minutes per stage
- **S3 Errors**: Check IAM permissions and bucket policies
- **DynamoDB Errors**: Check table capacity and IAM permissions

## Monitoring

### CloudWatch Metrics
- Step Functions execution metrics
- Lambda invocation metrics
- DynamoDB read/write metrics
- S3 request metrics

### X-Ray Tracing
- Step Functions tracing enabled
- View detailed execution traces in X-Ray console

## Cost Optimization

- **Lambda**: Pay per invocation and compute time
- **Step Functions**: Pay per state transition
- **S3**: Pay for storage and requests (lifecycle rules auto-delete after 30 days)
- **DynamoDB**: Pay-per-request pricing
- **EventBridge**: First 1 million events/month free

## Troubleshooting

### Pipeline Not Running
- Check EventBridge rule status: `aws events describe-rule --name etl-daily-schedule`
- Verify Step Functions permissions
- Check CloudWatch logs for errors

### Data Not Appearing in Destination
- Verify Extract Lambda wrote to S3
- Check Transform Lambda logs
- Verify Load Lambda has write permissions
- Check DynamoDB table for items

### Timeout Errors
- Increase Lambda timeout if processing large datasets
- Increase Step Functions timeout
- Optimize Lambda code for performance

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy EtlPipelineStack
```

**Note**: S3 buckets with `auto_delete_objects=True` will be automatically emptied before deletion.

