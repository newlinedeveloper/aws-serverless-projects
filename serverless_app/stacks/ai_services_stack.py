from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_lambda_event_sources as sources,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigw,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class AiServicesStack(Stack):
    """
    AI Services Project Stack
    Document processing, sentiment analysis, translation, text-to-speech
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 bucket for document uploads
        documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name=f"ai-documents-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[
                s3.CorsRule(
                    allowed_origins=["*"],
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_headers=["*"]
                )
            ]
        )

        # 2. S3 bucket for AI processing outputs
        output_bucket = s3.Bucket(
            self, "AiOutputBucket",
            bucket_name=f"ai-outputs-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 3. DynamoDB table for storing AI processing results
        results_table = dynamodb.Table(
            self, "AiResultsTable",
            table_name="ai-processing-results",
            partition_key=dynamodb.Attribute(
                name="file_name",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="processed_at",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 4. Lambda function for AI processing
        ai_processor_lambda = _lambda.Function(
            self, "AiProcessorLambda",
            function_name="ai-document-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/ai_processor"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "RESULTS_TABLE_NAME": results_table.table_name,
                "OUTPUT_BUCKET_NAME": output_bucket.bucket_name
            }
        )

        # Grant permissions
        documents_bucket.grant_read(ai_processor_lambda)
        output_bucket.grant_write(ai_processor_lambda)
        results_table.grant_write_data(ai_processor_lambda)

        # Grant AI service permissions
        ai_processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:DetectDocumentText",
                    "textract:AnalyzeDocument",
                    "comprehend:DetectSentiment",
                    "comprehend:DetectEntities",
                    "comprehend:DetectKeyPhrases",
                    "comprehend:DetectDominantLanguage",
                    "translate:TranslateText",
                    "polly:SynthesizeSpeech"
                ],
                resources=["*"]
            )
        )

        # 5. S3 event triggers for Lambda (one per file type)
        # Note: Each event source can only have one suffix filter, so we add one per file type
        file_types = [".pdf", ".png", ".jpg", ".jpeg", ".txt"]
        
        for file_type in file_types:
            ai_processor_lambda.add_event_source(
                sources.S3EventSource(
                    documents_bucket,
                    events=[s3.EventType.OBJECT_CREATED],
                    filters=[s3.NotificationKeyFilter(suffix=file_type)]
                )
            )

        # 6. API Gateway for REST API (optional - for direct API calls)
        api = apigw.RestApi(
            self, "AiServicesApi",
            rest_api_name="ai-services-api",
            description="API for AI document processing services",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        # Lambda integration
        ai_integration = apigw.LambdaIntegration(
            ai_processor_lambda,
            request_templates={"application/json": '{"statusCode": "200"}'}
        )

        # API endpoints
        process_resource = api.root.add_resource("process")
        process_resource.add_method("POST", ai_integration)

        # Query results endpoint (will be configured after query_lambda is created)
        results_resource = api.root.add_resource("results")
        # Note: GET method will be added after query_lambda is created below

        # 7. Lambda function for querying results
        query_lambda = _lambda.Function(
            self, "QueryResultsLambda",
            function_name="ai-query-results",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="query.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/ai_processor"),  # Use file instead of inline
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "RESULTS_TABLE_NAME": results_table.table_name
            }
        )

        results_table.grant_read_data(query_lambda)

        query_integration = apigw.LambdaIntegration(query_lambda)
        results_resource.add_method("GET", query_integration)

        # 8. Outputs
        CfnOutput(
            self, "DocumentsBucketName",
            value=documents_bucket.bucket_name,
            description="S3 Bucket for Document Uploads"
        )

        CfnOutput(
            self, "OutputBucketName",
            value=output_bucket.bucket_name,
            description="S3 Bucket for AI Processing Outputs"
        )

        CfnOutput(
            self, "ResultsTableName",
            value=results_table.table_name,
            description="DynamoDB Table for AI Results"
        )

        CfnOutput(
            self, "ApiEndpoint",
            value=api.url,
            description="API Gateway Endpoint URL"
        )

        CfnOutput(
            self, "ApiProcessEndpoint",
            value=f"{api.url}process",
            description="API Endpoint for Processing Documents"
        )

        CfnOutput(
            self, "ApiResultsEndpoint",
            value=f"{api.url}results",
            description="API Endpoint for Querying Results"
        )

