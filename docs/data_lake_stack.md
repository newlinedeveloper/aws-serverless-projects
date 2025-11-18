# Data Lake Stack

## Overview

The Data Lake Stack implements a serverless data lake architecture for analytics on structured and unstructured data. It uses S3 for data storage (organized in raw, processed, and curated zones), AWS Glue for schema discovery, Athena for querying, and Lambda for data ingestion and transformation.

## Architecture

```
Data Sources → S3 Raw Zone → Lambda Processor → S3 Processed Zone
                                              ↓
                                    Glue Crawler → Glue Catalog
                                              ↓
                                    Athena Queries → Results
```

## Resources

### 1. S3 Buckets (Data Zones)

#### Raw Data Bucket
- **Name**: `data-lake-raw-{account}-{region}`
- **Lifecycle Rule**: Transition to GLACIER after 90 days
- **Purpose**: Stores raw, unprocessed data

#### Processed Data Bucket
- **Name**: `data-lake-processed-{account}-{region}`
- **Purpose**: Stores processed/transformed data
- **Structure**: `processed/{date}/data.json`

#### Curated Data Bucket
- **Name**: `data-lake-curated-{account}-{region}`
- **Purpose**: Stores final, business-ready data

### 2. AWS Glue

#### Glue Database
- **Name**: `data_lake_db`
- **Purpose**: Catalog for data lake tables

#### Glue Crawler
- **Name**: `data-lake-crawler`
- **Targets**:
  - `s3://{processed-bucket}/processed/`
  - `s3://{curated-bucket}/`
- **Schema Change Policy**: Update in database, log deletes
- **Purpose**: Automatically discovers schema from S3 data

### 3. Lambda Function
- **Name**: `data-lake-processor`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Event Source**: S3 object creation in raw bucket
- **Purpose**: Processes raw data and triggers Glue Crawler

### 4. Amazon Athena
- **WorkGroup**: `data-lake-workgroup`
- **Result Location**: `s3://{processed-bucket}/athena-results/`
- **Encryption**: SSE-S3
- **Purpose**: Query data lake using SQL

## Data Flow

1. **Ingestion**:
   - Data uploaded to S3 raw bucket (prefix: `data/`)
   - S3 event triggers Lambda function
   
2. **Processing**:
   - Lambda reads data from raw bucket
   - Transforms/processes data (e.g., JSON parsing, validation)
   - Writes processed data to processed bucket
   - Triggers Glue Crawler to discover schema
   
3. **Schema Discovery**:
   - Glue Crawler scans processed/curated buckets
   - Discovers schema and creates/updates Glue tables
   - Tables registered in Glue Data Catalog
   
4. **Querying**:
   - Use Athena to query data using SQL
   - Queries run against Glue tables
   - Results stored in S3

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.data_lake_stack import DataLakeStack
   
   DataLakeStack(app, "DataLakeStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth DataLakeStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy DataLakeStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name DataLakeStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Upload Test Data to Raw Bucket

```bash
# Get bucket name
RAW_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name DataLakeStack \
  --query "Stacks[0].Outputs[?OutputKey=='RawBucketName'].OutputValue" \
  --output text)

# Create test data file
cat > test-data.json << EOF
{"id": "1", "name": "Product A", "price": 29.99, "category": "Electronics", "timestamp": "2024-01-15T10:00:00Z"}
{"id": "2", "name": "Product B", "price": 49.99, "category": "Clothing", "timestamp": "2024-01-15T11:00:00Z"}
{"id": "3", "name": "Product C", "price": 19.99, "category": "Electronics", "timestamp": "2024-01-15T12:00:00Z"}
EOF

# Upload to raw bucket (with data/ prefix to trigger Lambda)
aws s3 cp test-data.json s3://$RAW_BUCKET/data/test-data.json
```

### 2. Monitor Processing

**Check Lambda Logs:**
```bash
aws logs tail /aws/lambda/data-lake-processor --follow
```

**Check Processed Bucket:**
```bash
PROCESSED_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name DataLakeStack \
  --query "Stacks[0].Outputs[?OutputKey=='ProcessedBucketName'].OutputValue" \
  --output text)

aws s3 ls s3://$PROCESSED_BUCKET/processed/ --recursive
```

### 3. Trigger Glue Crawler

**Option A: Automatic (via Lambda)**
- Lambda automatically triggers crawler after processing

**Option B: Manual Trigger**
```bash
CRAWLER_NAME=$(aws cloudformation describe-stacks \
  --stack-name DataLakeStack \
  --query "Stacks[0].Outputs[?OutputKey=='GlueCrawlerName'].OutputValue" \
  --output text)

# Start crawler
aws glue start-crawler --name $CRAWLER_NAME

# Check crawler status
aws glue get-crawler --name $CRAWLER_NAME --query 'Crawler.State'
```

### 4. Wait for Crawler to Complete

```bash
# Wait for crawler to finish
while true; do
  STATE=$(aws glue get-crawler --name $CRAWLER_NAME --query 'Crawler.State' --output text)
  echo "Crawler state: $STATE"
  
  if [ "$STATE" == "READY" ] || [ "$STATE" == "STOPPED" ]; then
    # Check last crawl status
    LAST_CRAWL=$(aws glue get-crawler --name $CRAWLER_NAME --query 'Crawler.LastCrawl.Status' --output text)
    echo "Last crawl status: $LAST_CRAWL"
    break
  fi
  
  sleep 10
done
```

### 5. Query Data with Athena

**Option A: Using AWS CLI**
```bash
WORKGROUP=$(aws cloudformation describe-stacks \
  --stack-name DataLakeStack \
  --query "Stacks[0].Outputs[?OutputKey=='AthenaWorkGroupName'].OutputValue" \
  --output text)

DATABASE=$(aws cloudformation describe-stacks \
  --stack-name DataLakeStack \
  --query "Stacks[0].Outputs[?OutputKey=='GlueDatabaseName'].OutputValue" \
  --output text)

# Start query
QUERY_ID=$(aws athena start-query-execution \
  --work-group $WORKGROUP \
  --query-string "SELECT * FROM $DATABASE.processed_table LIMIT 10" \
  --query 'QueryExecutionId' \
  --output text)

echo "Query ID: $QUERY_ID"

# Wait for query to complete
while true; do
  STATUS=$(aws athena get-query-execution \
    --query-execution-id $QUERY_ID \
    --query 'QueryExecution.Status.State' \
    --output text)
  
  echo "Query status: $STATUS"
  
  if [ "$STATUS" == "SUCCEEDED" ] || [ "$STATUS" == "FAILED" ]; then
    break
  fi
  
  sleep 2
done

# Get query results
aws athena get-query-results --query-execution-id $QUERY_ID
```

**Option B: Using Athena Console**
1. Navigate to AWS Athena console
2. Select workgroup: `data-lake-workgroup`
3. Select database: `data_lake_db`
4. Run query:
   ```sql
   SELECT * FROM processed_table LIMIT 10;
   ```

### 6. Run Complete Test Script

```bash
python tests/data_lake/test_data_lake.py
```

## Data Lake Zones

### Raw Zone
- **Purpose**: Store original, unmodified data
- **Format**: As received from source systems
- **Retention**: Long-term (with lifecycle rules)

### Processed Zone
- **Purpose**: Store cleaned and transformed data
- **Format**: Structured (JSON, Parquet, etc.)
- **Schema**: Discovered by Glue Crawler

### Curated Zone
- **Purpose**: Store business-ready, aggregated data
- **Format**: Optimized for analytics
- **Usage**: Direct querying by analysts

## Glue Crawler Behavior

- **Schema Discovery**: Automatically infers schema from data
- **Table Creation**: Creates tables in Glue Data Catalog
- **Schema Updates**: Updates schema when data structure changes
- **Partitioning**: Detects partitions if data is organized by date/path

## Athena Query Examples

```sql
-- Count records
SELECT COUNT(*) FROM processed_table;

-- Filter by category
SELECT * FROM processed_table WHERE category = 'Electronics';

-- Aggregate by category
SELECT category, COUNT(*) as count, AVG(price) as avg_price
FROM processed_table
GROUP BY category;

-- Date-based queries (if partitioned)
SELECT * FROM processed_table
WHERE date_partition = '2024-01-15';
```

## Cost Optimization

- **S3**: Pay for storage and requests (lifecycle rules reduce costs)
- **Glue**: Pay per crawler run and DPU-hours
- **Athena**: Pay per query (per TB scanned)
- **Lambda**: Pay per invocation and compute time

### Cost Optimization Tips
- Use columnar formats (Parquet) to reduce Athena scan costs
- Partition data by date/category to enable partition pruning
- Use lifecycle rules to archive old data to Glacier
- Compress data files

## Troubleshooting

### Crawler Not Running
- Check IAM permissions for Glue Crawler role
- Verify S3 bucket permissions
- Check crawler logs in CloudWatch

### No Tables Created
- Verify crawler completed successfully
- Check Glue database exists
- Verify data format is supported (JSON, CSV, Parquet)

### Athena Query Fails
- Verify table exists in Glue catalog
- Check S3 bucket permissions for Athena
- Verify data format matches table schema
- Check query syntax

### Lambda Not Processing
- Check S3 event trigger configuration
- Verify Lambda has S3 read permissions
- Check Lambda logs for errors

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy DataLakeStack
```

**Important**: Before destroying, clean up Athena query results:

```bash
# Delete Athena query results
PROCESSED_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name DataLakeStack \
  --query "Stacks[0].Outputs[?OutputKey=='ProcessedBucketName'].OutputValue" \
  --output text)

aws s3 rm s3://$PROCESSED_BUCKET/athena-results/ --recursive

# Stop and delete crawler manually if needed
aws glue stop-crawler --name data-lake-crawler
aws glue delete-crawler --name data-lake-crawler

# Delete workgroup manually
aws athena delete-work-group --work-group data-lake-workgroup --recursive-delete-option
```

**Note**: S3 buckets with `auto_delete_objects=True` will be automatically emptied before deletion.

