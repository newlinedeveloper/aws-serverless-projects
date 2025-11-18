# AI Services Stack

## Overview

The AI Services Stack implements a serverless document processing system using AWS AI services. It processes documents uploaded to S3 using Textract (OCR), Comprehend (sentiment analysis, entity extraction), Translate (language translation), and Polly (text-to-speech). Results are stored in DynamoDB and can be queried via API Gateway.

## Architecture

```
Document Upload → S3 → Lambda Trigger → AI Services Processing
                                              ↓
                                    DynamoDB (Results)
                                              ↓
                                    API Gateway (Query)
```

## Resources

### 1. S3 Buckets

#### Documents Bucket
- **Name**: `ai-documents-{account}-{region}`
- **CORS**: Enabled for web uploads
- **Purpose**: Stores uploaded documents (PDF, images, text files)
- **Supported Formats**: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`

#### Output Bucket
- **Name**: `ai-outputs-{account}-{region}`
- **Purpose**: Stores AI processing outputs (audio files from Polly, etc.)

### 2. DynamoDB Table
- **Name**: `ai-processing-results`
- **Partition Key**: `file_name` (String)
- **Sort Key**: `processed_at` (String)
- **Billing**: Pay-per-request
- **Purpose**: Stores AI processing results for each document

### 3. Lambda Functions

#### AI Processor Lambda
- **Name**: `ai-document-processor`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 5 minutes
- **Event Source**: S3 object creation (multiple file types)
- **AI Services Used**:
  - **Textract**: Extract text from PDFs and images
  - **Comprehend**: Sentiment analysis, entity extraction, key phrases, language detection
  - **Translate**: Translate text to different languages
  - **Polly**: Convert text to speech (audio files)
- **Purpose**: Processes documents and stores results

#### Query Results Lambda
- **Name**: `ai-query-results`
- **Runtime**: Python 3.11
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Purpose**: Queries DynamoDB for processing results via API Gateway

### 4. API Gateway REST API
- **Name**: `ai-services-api`
- **Endpoints**:
  - `POST /process`: Trigger processing (optional, mainly for S3-triggered)
  - `GET /results`: Query processing results
- **CORS**: Enabled for all origins
- **Purpose**: Provides REST API for querying results

## AI Services Used

### Amazon Textract
- **Purpose**: Extract text from PDFs and images
- **Operations**: `DetectDocumentText`, `AnalyzeDocument`
- **Supported Formats**: PDF, PNG, JPG, JPEG

### Amazon Comprehend
- **Purpose**: Natural language processing
- **Operations**:
  - `DetectSentiment`: Analyze sentiment (positive, negative, neutral, mixed)
  - `DetectEntities`: Extract entities (persons, organizations, locations, etc.)
  - `DetectKeyPhrases`: Extract key phrases
  - `DetectDominantLanguage`: Detect document language

### Amazon Translate
- **Purpose**: Translate text between languages
- **Operation**: `TranslateText`
- **Supported Languages**: 75+ languages

### Amazon Polly
- **Purpose**: Text-to-speech conversion
- **Operation**: `SynthesizeSpeech`
- **Output**: Audio file (MP3) stored in S3 output bucket

## Data Flow

1. **Document Upload**:
   - Document uploaded to S3 documents bucket
   - S3 event triggers Lambda function (for supported file types)

2. **Text Extraction**:
   - For PDFs/images: Textract extracts text
   - For text files: Directly read from S3

3. **AI Processing**:
   - Comprehend analyzes sentiment, entities, key phrases, language
   - Translate translates text (if needed)
   - Polly generates speech audio (if requested)

4. **Result Storage**:
   - Results stored in DynamoDB with file name and timestamp
   - Audio files stored in S3 output bucket

5. **Query Results**:
   - Query DynamoDB via API Gateway endpoint
   - Retrieve processing results by file name

## Deployment

### Prerequisites
- AWS CDK CLI installed
- Python 3.11+
- AWS credentials configured

### Steps

1. **Update app.py** to include the stack:
   ```python
   from serverless_app.stacks.ai_services_stack import AiServicesStack
   
   AiServicesStack(app, "AiServicesStack")
   ```

2. **Synthesize the stack**:
   ```bash
   cdk synth AiServicesStack
   ```

3. **Deploy the stack**:
   ```bash
   cdk deploy AiServicesStack
   ```

4. **Get stack outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name AiServicesStack \
     --query "Stacks[0].Outputs"
   ```

## Testing

### 1. Upload Test Documents

```bash
# Get bucket name
DOCUMENTS_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name AiServicesStack \
  --query "Stacks[0].Outputs[?OutputKey=='DocumentsBucketName'].OutputValue" \
  --output text)

# Create a test text file
echo "This is a great product! I love it. The quality is excellent." > test-document.txt

# Upload text file
aws s3 cp test-document.txt s3://$DOCUMENTS_BUCKET/test-document.txt

# Upload a PDF (if you have one)
aws s3 cp sample.pdf s3://$DOCUMENTS_BUCKET/sample.pdf

# Upload an image
aws s3 cp sample.png s3://$DOCUMENTS_BUCKET/sample.png
```

### 2. Monitor Processing

**Check Lambda Logs:**
```bash
aws logs tail /aws/lambda/ai-document-processor --follow
```

**Check Processing Status:**
```bash
# Wait a few seconds for processing, then check DynamoDB
RESULTS_TABLE=$(aws cloudformation describe-stacks \
  --stack-name AiServicesStack \
  --query "Stacks[0].Outputs[?OutputKey=='ResultsTableName'].OutputValue" \
  --output text)

aws dynamodb scan \
  --table-name $RESULTS_TABLE \
  --limit 10
```

### 3. Query Results via API

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name AiServicesStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiResultsEndpoint'].OutputValue" \
  --output text)

# Query results by file name
curl "$API_ENDPOINT?file_name=test-document.txt" | jq

# Query all results
curl "$API_ENDPOINT" | jq
```

### 4. Check Output Bucket

```bash
OUTPUT_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name AiServicesStack \
  --query "Stacks[0].Outputs[?OutputKey=='OutputBucketName'].OutputValue" \
  --output text)

# Check for audio files (from Polly)
aws s3 ls s3://$OUTPUT_BUCKET/ --recursive
```

### 5. Run Complete Test Script

```bash
python tests/ai_services/test_ai_services.py
```

## Processing Results Structure

Results stored in DynamoDB:

```json
{
  "file_name": "test-document.txt",
  "processed_at": "2024-01-15T10:30:00Z",
  "text": "Extracted text content...",
  "sentiment": {
    "sentiment": "POSITIVE",
    "sentiment_score": {
      "positive": 0.95,
      "negative": 0.02,
      "neutral": 0.03,
      "mixed": 0.00
    }
  },
  "entities": [
    {
      "text": "Product",
      "type": "OTHER",
      "score": 0.95
    }
  ],
  "key_phrases": [
    "great product",
    "excellent quality"
  ],
  "language": "en",
  "translation": {
    "target_language": "es",
    "translated_text": "Este es un gran producto..."
  },
  "audio_file": "s3://ai-outputs-xxx/audio/test-document.mp3"
}
```

## Supported File Types

### Text Files (`.txt`)
- Directly read from S3
- Processed with Comprehend, Translate, Polly

### PDF Files (`.pdf`)
- Processed with Textract for text extraction
- Then processed with Comprehend, Translate, Polly

### Image Files (`.png`, `.jpg`, `.jpeg`)
- Processed with Textract for OCR
- Then processed with Comprehend, Translate, Polly

## API Endpoints

### GET /results
Query processing results.

**Query Parameters:**
- `file_name` (optional): Filter by file name

**Response:**
```json
{
  "results": [
    {
      "file_name": "test-document.txt",
      "processed_at": "2024-01-15T10:30:00Z",
      "sentiment": "POSITIVE",
      "entities": [...],
      "key_phrases": [...]
    }
  ]
}
```

### POST /process
Manually trigger processing (optional, mainly for S3-triggered processing).

## Cost Optimization

- **Textract**: Pay per page processed
- **Comprehend**: Pay per 100 characters analyzed
- **Translate**: Pay per character translated
- **Polly**: Pay per character synthesized
- **S3**: Pay for storage and requests
- **DynamoDB**: Pay-per-request pricing
- **Lambda**: Pay per invocation and compute time

### Cost Optimization Tips
- Process only necessary documents
- Use appropriate file formats (text files are cheaper than PDFs)
- Cache results to avoid reprocessing
- Use lifecycle rules to archive old documents

## Troubleshooting

### Processing Not Triggered
- Verify file type is supported (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`)
- Check S3 event trigger configuration
- Verify Lambda has S3 read permissions
- Check Lambda logs for errors

### Textract Errors
- Verify file format is supported
- Check file size limits (Textract has limits)
- Verify IAM permissions for Textract

### No Results in DynamoDB
- Check Lambda logs for processing errors
- Verify DynamoDB write permissions
- Check for exceptions in Lambda execution

### API Gateway 502 Errors
- Verify Query Lambda is deployed correctly
- Check Lambda logs
- Verify API Gateway integration

## Security Considerations

- **Document Privacy**: Documents may contain sensitive information
- **Access Control**: Restrict S3 bucket access
- **IAM Permissions**: Use least privilege for AI services
- **Data Encryption**: Enable S3 encryption at rest

## Cleanup

To destroy the stack and all resources:

```bash
cdk destroy AiServicesStack
```

**Note**: S3 buckets with `auto_delete_objects=True` will be automatically emptied before deletion.

