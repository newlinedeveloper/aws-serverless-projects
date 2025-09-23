from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_iam as iam,
    aws_logs as logs,
    custom_resources as cr,
)
from constructs import Construct

class ServerlessAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the Bedrock model ID
        bedrock_model_id = "meta.llama3-70b-instruct-v1:0"  # Replace with your preferred model

        # -------------------------
        # DynamoDB: FAQ table
        # -------------------------
        faq_table = dynamodb.Table(
            self, "FaqTable",
            partition_key=dynamodb.Attribute(name="question", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # -------------------------
        # S3: Knowledge base bucket
        # -------------------------
        kb_bucket = s3.Bucket(
            self, "KnowledgeBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Deploy local `kb/` folder contents to the bucket (create folder and files before deploy)
        s3deploy.BucketDeployment(
            self, "DeployKnowledgeBase",
            sources=[s3deploy.Source.asset("kb")],
            destination_bucket=kb_bucket,
            destination_key_prefix="knowledge"
        )

        # -------------------------
        # Lambda: Chatbot
        # -------------------------
        # Inline code for the Lambda (kept readable)
        chatbot_code = r"""
import os, json, boto3, textwrap
from urllib.parse import unquote_plus

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL = os.environ["BEDROCK_MODEL"]
FAQ_TABLE = os.environ["FAQ_TABLE"]
KB_BUCKET = os.environ["KB_BUCKET"]
KB_PREFIX = os.environ.get("KB_PREFIX", "knowledge/")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

table = dynamodb.Table(FAQ_TABLE)

def read_kb_documents(max_chars=1500):
    # List objects under prefix and fetch small docs (text) to include as context
    try:
        objs = s3.list_objects_v2(Bucket=KB_BUCKET, Prefix=KB_PREFIX).get("Contents", [])
        texts = []
        for o in objs:
            key = o["Key"]
            if key.endswith("/") or key.endswith(".pdf") or key.endswith(".png") or key.endswith(".jpg"):
                continue
            try:
                resp = s3.get_object(Bucket=KB_BUCKET, Key=key)
                body = resp["Body"].read().decode("utf-8")
                texts.append(f"--- {key} ---\n{body}")
                if sum(len(t) for t in texts) > max_chars:
                    break
            except Exception as e:
                print(f"Error reading file {key}: {e}")
                continue
        print(f"Loaded knowledge base: {texts}")
        return "\n\n".join(texts)
    except Exception as e:
        print(f"Error reading KB documents: {e}")
        return ""

def call_bedrock(prompt, max_tokens=1024, temperature=0.7):
    # Calls Bedrock modelId in BEDROCK_MODEL env var. Uses invoke_model API.
    try:
        print(f"Prompt sent to Bedrock: {prompt}")
        payload = {
            "prompt": prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }

        resp = bedrock.invoke_model(
            modelId=os.environ["BEDROCK_MODEL"],
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8")
        )

        body_bytes = resp["body"].read()
        parsed = json.loads(body_bytes)

        return parsed.get("generation", "No response from model")

    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return f"Error: {str(e)}"

def handler(event, context):
    # API Gateway proxy expects event["body"]
    try:
        # Handle both direct invocation and API Gateway
        if "body" in event:
            body = json.loads(event.get("body") or "{}")
        else:
            body = event
            
        q = body.get("query", "").strip()
        if not q:
            return {"statusCode": 400, "body": json.dumps({"error": "query missing"})}

        # 1) exact FAQ lookup
        resp = table.get_item(Key={"question": q})
        if "Item" in resp:
            return {"statusCode": 200, "body": json.dumps({"query": q, "answer": resp["Item"]["answer"], "source": "faq"})}

        # 2) prepare context: small KB docs
        kb_text = read_kb_documents(max_chars=2000)
        print(f"KB text: {kb_text}")
        if kb_text:
            prompt = f"Based on the following knowledge base information, please answer the user's question:\n\n {kb_text} \n\n Question: {q} \n\n\n Please provide a clear and concise answer based on the information above."
        else:
            prompt = f"Please answer the user's question:\n\n Question: {q} \n\n\n Please provide a clear and concise answer."
        print(f"Prompt sent to call Bedrock : {prompt}")

        # 3) call Bedrock
        answer = call_bedrock(prompt, max_tokens=512, temperature=0.0)

        return {"statusCode": 200, "body": json.dumps({"query": q, "answer": answer, "source": "bedrock"})}

    except Exception as e:
        print(f"Handler error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
"""

        # Create log group explicitly to avoid deprecation warning
        log_group = logs.LogGroup(
            self, "ChatbotLambdaLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        chatbot_lambda = _lambda.Function(
            self, "ChatbotLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_inline(chatbot_code),
            timeout=Duration.seconds(120),  # Increased timeout for Bedrock calls
            memory_size=1024,
            environment={
                "BEDROCK_MODEL": bedrock_model_id,
                "FAQ_TABLE": faq_table.table_name,
                "KB_BUCKET": kb_bucket.bucket_name,
                "KB_PREFIX": "knowledge/"
            },
            log_group=log_group  # Use explicit log group instead of deprecated logRetention
        )

        # Grant Lambda permissions to read FAQ and KB
        faq_table.grant_read_data(chatbot_lambda)
        kb_bucket.grant_read(chatbot_lambda)

        # Allow Lambda to read objects under knowledge prefix explicitly
        chatbot_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[kb_bucket.bucket_arn, f"{kb_bucket.bucket_arn}/*"]
        ))

        # Bedrock permissions (InvokeModel)
        chatbot_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"]
        ))

        # -------------------------
        # API Gateway
        # -------------------------
        api = apigateway.LambdaRestApi(
            self, "ChatbotApi",
            handler=chatbot_lambda,
            proxy=False,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        chat = api.root.add_resource("chat")
        chat.add_method("POST")  # POST /chat

        # -------------------------
        # Seed DynamoDB FAQ items (small set) using AwsCustomResource
        # -------------------------
        sample_faqs = [
            {"question": "What is your return policy?", "answer": "You can return items within 30 days of delivery for a full refund."},
            {"question": "How can I track my order?", "answer": "Use the tracking link in your order confirmation email; contact support if missing."},
            {"question": "Do you ship internationally?", "answer": "Yes—we ship to 50+ countries. Delivery times vary by country."},
            {"question": "What payment methods are accepted?", "answer": "We accept credit cards, PayPal, and Amazon Pay."},
            {"question": "How do I contact support?", "answer": "Email support@myshop.com or call 1-800-123-4567."},
        ]

        # Create a role for the custom resource to call DynamoDB with proper permissions
        cust_role = iam.Role(self, "FaqSeederRole",
                             assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        cust_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
        cust_role.add_to_policy(iam.PolicyStatement(
            actions=["dynamodb:PutItem"],
            resources=[faq_table.table_arn]
        ))

        for i, item in enumerate(sample_faqs):
            AwsSdkCall = cr.AwsSdkCall(
                service="DynamoDB",
                action="putItem",
                parameters={
                    "TableName": faq_table.table_name,
                    "Item": {
                        "question": {"S": item["question"]},
                        "answer": {"S": item["answer"]}
                    }
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"FaqItem{i}")
            )
            cr.AwsCustomResource(self, f"SeedFaq{i}",
                on_create=AwsSdkCall,
                role=cust_role,
                policy=cr.AwsCustomResourcePolicy.from_statements([
                    iam.PolicyStatement(actions=["dynamodb:PutItem"], resources=[faq_table.table_arn])
                ])
            )

        # -------------------------
        # Outputs for user convenience (with unique names)
        # -------------------------
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "KnowledgeBucketName", value=kb_bucket.bucket_name)  # Changed name to avoid conflict
        CfnOutput(self, "FaqTableName", value=faq_table.table_name)
