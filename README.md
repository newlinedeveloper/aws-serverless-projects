# 🚀 Multiple Real-World Serverless Projects with AWS CDK

This project contains **8 comprehensive serverless applications** built with **AWS CDK (Python)**, demonstrating real-world use cases and best practices for serverless architecture on AWS.

---

## 📋 Table of Contents

1. [Media Processing Stack](#1-media-processing-stack)
2. [Real-Time Data Processing Pipeline](#2-real-time-data-processing-pipeline)
3. [Scheduled ETL Pipeline](#3-scheduled-etl-pipeline)
4. [WebSocket Chat Application](#4-websocket-chat-application)
5. [Serverless Data Lake](#5-serverless-data-lake)
6. [AI Services Project](#6-ai-services-project)
7. [Event-Driven Architecture](#7-event-driven-architecture)
8. [Serverless REST API](#8-serverless-rest-api)

---

## 📂 Project Structure

```
serverless-app/
├── app.py                          # Main CDK app (instantiates all stacks)
├── requirements.txt                # Python dependencies
├── cdk.json                        # CDK configuration
├── serverless_app/
│   ├── __init__.py
│   ├── serverless_app_stack.py     # Original Media Processing Stack
│   └── stacks/                     # All new stacks
│       ├── __init__.py
│       ├── realtime_processing_stack.py
│       ├── etl_pipeline_stack.py
│       ├── websocket_chat_stack.py
│       ├── data_lake_stack.py
│       ├── ai_services_stack.py
│       ├── event_driven_stack.py
│       └── serverless_api_stack.py
└── serverless_app/lambdas/         # Lambda function code
    ├── realtime_processor/
    ├── etl_processor/
    ├── websocket_handler/
    ├── data_lake_processor/
    ├── ai_processor/
    ├── event_handlers/
    └── api_handlers/
```

---

## 🛠️ Prerequisites

1. **Python 3.11+** - [Download](https://www.python.org/downloads/)
2. **AWS CDK** - Install globally:
   ```bash
   npm install -g aws-cdk
   ```
3. **AWS CLI** - Configure with credentials:
   ```bash
   aws configure
   ```
4. **Docker** - Required for Lambda bundling (if using container images)

---

## 🚀 Getting Started

1. **Clone and setup the project:**
   ```bash
   cd serverless-app
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Bootstrap CDK (first time only):**
   ```bash
   cdk bootstrap
   ```

3. **Deploy all stacks:**
   ```bash
   cdk deploy --all
   ```

   Or deploy individual stacks:
   ```bash
   cdk deploy ServerlessAppStack
   cdk deploy RealtimeProcessingStack
   cdk deploy EtlPipelineStack
   # ... etc
   ```

4. **Synthesize CloudFormation templates:**
   ```bash
   cdk synth
   ```

---

## 📚 Project Details

### 1. Media Processing Stack

**Stack Name:** `ServerlessAppStack`

**Services:** S3, Lambda, Rekognition, DynamoDB, SNS

**Use Case:** Automatic image and video processing with AI label detection

**Features:**
- Upload images/videos to S3 bucket
- Automatic label detection using AWS Rekognition
- Results stored in DynamoDB
- Email notifications via SNS

**Test:**
```bash
aws s3 cp test.jpg s3://<MediaBucketName>/
aws dynamodb scan --table-name MediaResultsTable
```

---

### 2. Real-Time Data Processing Pipeline

**Stack Name:** `RealtimeProcessingStack`

**Services:** Kinesis Data Streams, Lambda, S3, DynamoDB, CloudWatch

**Use Case:** Real-time processing of IoT sensor data or clickstream analytics

**Features:**
- Kinesis Data Stream for real-time ingestion
- Lambda functions for transformation and aggregation
- S3 for raw data archival with lifecycle policies
- DynamoDB for processed metrics storage
- CloudWatch alarms for monitoring

**Test:**
```bash
# Send data to Kinesis stream
aws kinesis put-record \
  --stream-name realtime-data-stream \
  --partition-key sensor-001 \
  --data '{"sensorId":"sensor-001","value":25.5,"timestamp":"2024-01-01T00:00:00Z"}'

# Check processed metrics
aws dynamodb scan --table-name realtime-processed-metrics
```

---

### 3. Scheduled ETL Pipeline

**Stack Name:** `EtlPipelineStack`

**Services:** EventBridge, Step Functions, Lambda, S3, DynamoDB

**Use Case:** Daily data aggregation, data warehouse loading, report generation

**Features:**
- EventBridge rule for scheduled triggers (daily at 2 AM UTC)
- Step Functions for orchestration
- Lambda functions for Extract, Transform, Load operations
- S3 for staging and archival
- DynamoDB for source and destination storage

**Test:**
```bash
# Manually trigger Step Functions
aws stepfunctions start-execution \
  --state-machine-arn <StateMachineArn> \
  --input '{}'

# Check execution status
aws stepfunctions list-executions --state-machine-arn <StateMachineArn>
```

---

### 4. WebSocket Chat Application

**Stack Name:** `WebSocketChatStack`

**Services:** API Gateway WebSocket, Lambda, DynamoDB

**Use Case:** Real-time messaging, notifications, collaborative features

**Features:**
- WebSocket API for bidirectional communication
- Connection management ($connect, $disconnect, $default routes)
- Message persistence in DynamoDB
- Room/channel support
- User presence tracking

**Test:**
```bash
# Get WebSocket endpoint
aws apigatewayv2 get-apis --query "Items[?Name=='chat-websocket-api'].ApiEndpoint"

# Connect using wscat
npm install -g wscat
wscat -c wss://<WebSocketEndpoint>/prod?room=general&userId=user123

# Send message
{"type":"message","message":"Hello World","room":"general"}
```

---

### 5. Serverless Data Lake

**Stack Name:** `DataLakeStack`

**Services:** S3, Glue, Athena, Lambda

**Use Case:** Analytics on structured/unstructured data, data lake queries

**Features:**
- S3 buckets organized by data zones (raw, processed, curated)
- Glue Crawler for automatic schema discovery
- Glue Database and Tables
- Athena for SQL queries
- Lambda for data ingestion and transformation

**Test:**
```bash
# Upload data to raw bucket
aws s3 cp data.json s3://data-lake-raw-<account>-<region>/data/

# Trigger Glue Crawler
aws glue start-crawler --name data-lake-crawler

# Query with Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM data_lake_db.processed_table LIMIT 10" \
  --work-group data-lake-workgroup
```

---

### 6. AI Services Project

**Stack Name:** `AiServicesStack`

**Services:** Lambda, Comprehend, Translate, Polly, Textract, S3, DynamoDB, API Gateway

**Use Case:** Document processing, sentiment analysis, translation, text-to-speech

**Features:**
- Textract for document text extraction
- Comprehend for sentiment analysis and entity extraction
- Translate for multi-language support
- Polly for text-to-speech conversion
- Results stored in DynamoDB
- REST API for document upload and query

**Test:**
```bash
# Upload document
aws s3 cp document.pdf s3://ai-documents-<account>-<region>/

# Query results via API
curl https://<ApiEndpoint>/results?file_name=document.pdf

# Or query DynamoDB directly
aws dynamodb query \
  --table-name ai-processing-results \
  --key-condition-expression "file_name = :fn" \
  --expression-attribute-values '{":fn":{"S":"document.pdf"}}'
```

---

### 7. Event-Driven Architecture

**Stack Name:** `EventDrivenStack`

**Services:** EventBridge, Lambda, SQS, SNS, Step Functions, DynamoDB

**Use Case:** Microservices communication, event sourcing, decoupled systems

**Features:**
- EventBridge custom bus with rules
- Multiple Lambda functions as event consumers
- SQS dead-letter queues for error handling
- SNS for notifications
- Step Functions for complex workflows

**Test:**
```bash
# Send custom event
aws events put-events \
  --entries '[{
    "Source":"orders",
    "DetailType":"Order Created",
    "Detail":"{\"data\":{\"orderId\":\"123\",\"customerId\":\"cust-001\",\"total\":100}}"
  }]'

# Check orders table
aws dynamodb scan --table-name event-driven-orders
```

---

### 8. Serverless REST API

**Stack Name:** `ServerlessApiStack`

**Services:** API Gateway, Lambda, DynamoDB, Cognito

**Use Case:** Production-ready REST API backend with authentication

**Features:**
- REST API with CRUD operations
- Cognito User Pool for authentication
- DynamoDB with GSI for queries
- Request validation and CORS
- Rate limiting and throttling

**Test:**
```bash
# Create user in Cognito
aws cognito-idp sign-up \
  --client-id <UserPoolClientId> \
  --username testuser \
  --password TestPass123! \
  --user-attributes Name=email,Value=test@example.com

# Get authentication token
aws cognito-idp initiate-auth \
  --client-id <UserPoolClientId> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=TestPass123!

# Create item (requires auth token)
curl -X POST https://<ApiEndpoint>/items \
  -H "Authorization: Bearer <IdToken>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Item","description":"Test Description"}'

# List items (public)
curl https://<ApiEndpoint>/items
```

---

## 🔧 Configuration

### Environment Variables

You can configure stacks using CDK context or environment variables:

```bash
# Set AWS account and region
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1

# Deploy to specific environment
cdk deploy --all --context environment=production
```

### Stack-Specific Configuration

Each stack can be customized by modifying the stack files in `serverless_app/stacks/`. Common configurations:
- S3 bucket names
- DynamoDB table names
- Lambda function memory and timeout
- EventBridge schedule expressions
- API Gateway throttling limits

---

## 📊 Monitoring and Observability

All stacks include:
- **CloudWatch Logs** for Lambda functions
- **CloudWatch Metrics** for resource monitoring
- **CloudWatch Alarms** for error detection (where applicable)
- **CDK Outputs** for easy resource discovery

View logs:
```bash
aws logs tail /aws/lambda/<function-name> --follow
```

---

## 🧹 Cleanup

To remove all resources:

```bash
# Destroy all stacks
cdk destroy --all

# Or destroy individual stacks
cdk destroy ServerlessAppStack
cdk destroy RealtimeProcessingStack
# ... etc
```

**Note:** Some resources (like S3 buckets with data) may require manual cleanup if they contain data.

---

## 📝 Best Practices Implemented

1. **IAM Least Privilege** - All Lambda functions have minimal required permissions
2. **Resource Tagging** - Resources are tagged for cost management
3. **Error Handling** - Comprehensive error handling in Lambda functions
4. **Dead Letter Queues** - SQS DLQs for failed message processing
5. **Lifecycle Policies** - S3 lifecycle rules for cost optimization
6. **Monitoring** - CloudWatch alarms and metrics
7. **Security** - Encryption at rest and in transit
8. **Scalability** - Auto-scaling serverless architecture

---

## 🐛 Troubleshooting

### Common Issues

1. **CDK Bootstrap Required:**
   ```bash
   cdk bootstrap aws://<account>/<region>
   ```

2. **Lambda Timeout:**
   - Increase timeout in stack configuration
   - Check CloudWatch Logs for errors

3. **Permission Errors:**
   - Verify IAM roles have correct permissions
   - Check resource policies

4. **Import Errors:**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Verify Python version: `python --version` (should be 3.11+)

---

## 📚 Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Serverless Application Model](https://aws.amazon.com/serverless/sam/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

---

## 📄 License

This project is provided as-is for educational and demonstration purposes.

---

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

---

## 📧 Support

For questions or issues, please open an issue in the repository.
