# Serverless Application Documentation

This directory contains comprehensive documentation for each serverless stack in the application.

## Available Stacks

1. **[Real-Time Processing Stack](./realtime_processing_stack.md)** - Real-time data processing pipeline using Kinesis, Lambda, S3, and DynamoDB
2. **[ETL Pipeline Stack](./etl_pipeline_stack.md)** - Scheduled ETL pipeline using EventBridge, Step Functions, Lambda, S3, and DynamoDB
3. **[WebSocket Chat Stack](./websocket_chat_stack.md)** - Real-time chat application using API Gateway WebSocket, Lambda, and DynamoDB
4. **[Data Lake Stack](./data_lake_stack.md)** - Serverless data lake using S3, Glue, Athena, and Lambda
5. **[AI Services Stack](./ai_services_stack.md)** - AI document processing using Textract, Comprehend, Translate, Polly, Lambda, and DynamoDB
6. **[Event-Driven Stack](./event_driven_stack.md)** - Event-driven architecture using EventBridge, SNS, SQS, Step Functions, Lambda, and DynamoDB
7. **[Serverless REST API Stack](./serverless_api_stack.md)** - Production-ready REST API with authentication using API Gateway, Lambda, DynamoDB, and Cognito

## Quick Start

1. **Deploy a specific stack:**
   ```bash
   # Uncomment the desired stack in app.py
   cdk deploy StackName
   ```

2. **Test a stack:**
   ```bash
   # Navigate to the test directory
   python tests/stack_name/test_stack_name.py
   ```

3. **View stack outputs:**
   ```bash
   aws cloudformation describe-stacks --stack-name StackName --query "Stacks[0].Outputs"
   ```

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Python 3.11+
- Required Python packages (install from `requirements.txt`)

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Synthesize CloudFormation template
cdk synth

# Deploy stack
cdk deploy StackName

# Destroy stack
cdk destroy StackName

# View stack outputs
aws cloudformation describe-stacks --stack-name StackName
```

