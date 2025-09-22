from aws_cdk import (
    Stack,
    Duration,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_lambda_event_sources as sources,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_iam as iam,
    RemovalPolicy  # Import RemovalPolicy directly
)
from constructs import Construct

class ServerlessAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

         # 🔹 1. S3 bucket for uploads
        media_bucket = s3.Bucket(
            self, "MediaBucket",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # Use RemovalPolicy directly
            auto_delete_objects=True
        )

        # 🔹 2. DynamoDB table for results
        results_table = dynamodb.Table(
            self, "MediaResultsTable",
            partition_key=dynamodb.Attribute(
                name="fileName",
                type=dynamodb.AttributeType.STRING
            )
        )

        # 🔹 3. SNS Topic for notifications
        notification_topic = sns.Topic(self, "MediaNotifications")
        notification_topic.add_subscription(
            subs.EmailSubscription("veerasolaiyappan@gmail.com")
        )

        # 🔹 4. Lambda function for media processing
        media_lambda = _lambda.Function(
            self, "MediaProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            timeout=Duration.seconds(300),  # Increased timeout for video processing
            memory_size=1024,
            code=_lambda.Code.from_inline(
                """
import json, os, boto3
import urllib.parse

region = os.environ["AWS_REGION"]
s3 = boto3.client('s3')
rekognition = boto3.client("rekognition", region_name=region)
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')


table = dynamodb.Table(os.environ['TABLE_NAME'])
topic_arn = os.environ['TOPIC_ARN']

def handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        file_name = key.split("/")[-1]

        # Detect if image or video based on extension
        if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                response = rekognition.detect_labels(
                    Image={"S3Object": {"Bucket": bucket, "Name": key}},
                    MaxLabels=5
                )
                labels = [label['Name'] for label in response['Labels']]
                status = "IMAGE_PROCESSED"
                result = {"fileName": file_name, "type": "image", "labels": labels, "status": status}
            except Exception as e:
                print(f"Error processing image {file_name}: {e}")
                result = {"fileName": file_name, "status": "ERROR", "error": str(e)}

        elif file_name.lower().endswith(('.mp4', '.mov', '.avi')):
            try:
                # Start video label detection
                start_response = rekognition.start_label_detection(
                    Video={"S3Object": {"Bucket": bucket, "Name": key}}
                )
                job_id = start_response['JobId']
                print(f"Started video label detection for {file_name}, JobId: {job_id}")

                # Wait for the job to complete (polling)
                while True:
                    job_status = rekognition.get_label_detection(JobId=job_id)
                    status = job_status['JobStatus']
                    if status in ['SUCCEEDED', 'FAILED']:
                        break

                if status == 'SUCCEEDED':
                    labels = [
                        label['Label']['Name']
                        for label in job_status['Labels']
                    ]
                    result = {"fileName": file_name, "type": "video", "labels": labels, "status": "VIDEO_PROCESSED"}
                else:
                    result = {"fileName": file_name, "type": "video", "status": "VIDEO_PROCESSING_FAILED"}
            except Exception as e:
                print(f"Error processing video {file_name}: {e}")
                result = {"fileName": file_name, "status": "ERROR", "error": str(e)}

        else:
            result = {"fileName": file_name, "status": "UNSUPPORTED"}
        
        # Save to DynamoDB
        table.put_item(Item=result)

        # Notify via SNS
        sns.publish(
            TopicArn=topic_arn,
            Subject="Media Processing Result",
            Message=json.dumps(result)
        )
    return {"statusCode": 200}
                """
            ),
            environment={
                "TABLE_NAME": results_table.table_name,
                "TOPIC_ARN": notification_topic.topic_arn
            }
        )

        # Permissions
        results_table.grant_write_data(media_lambda)
        notification_topic.grant_publish(media_lambda)
        media_bucket.grant_read(media_lambda)

        # Explicit permission for Rekognition to access S3 bucket
        media_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"{media_bucket.bucket_arn}/*"],
                principals=[iam.ServicePrincipal("rekognition.amazonaws.com")]
            )
        )


        media_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "rekognition:DetectLabels",
                "rekognition:StartLabelDetection",
                "rekognition:GetLabelDetection"
            ],
            resources=["*"]
        ))

        # 🔹 5. Add S3 event trigger
        media_lambda.add_event_source(
            sources.S3EventSource(
                media_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(suffix=".jpg")]
            )
        )
        media_lambda.add_event_source(
            sources.S3EventSource(
                media_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(suffix=".mp4")]
            )
        )
