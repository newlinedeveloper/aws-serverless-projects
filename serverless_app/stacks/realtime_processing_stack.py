from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_kinesis as kinesis,
    aws_lambda as _lambda,
    aws_lambda_event_sources as sources,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct
import os


class RealtimeProcessingStack(Stack):
    """
    Real-Time Data Processing Pipeline Stack
    Processes IoT sensor data or clickstream analytics in real-time
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Kinesis Data Stream for real-time data ingestion
        data_stream = kinesis.Stream(
            self, "RealtimeDataStream",
            stream_name="realtime-data-stream",
            shard_count=2,
            retention_period=Duration.hours(24),
            encryption=kinesis.StreamEncryption.KMS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 2. S3 bucket for raw data archival
        archive_bucket = s3.Bucket(
            self, "DataArchiveBucket",
            bucket_name=f"realtime-data-archive-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveToGlacier",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(120)
                        )
                    ]
                )
            ]
        )

        # 3. DynamoDB table for processed metrics storage
        metrics_table = dynamodb.Table(
            self, "ProcessedMetricsTable",
            table_name="realtime-processed-metrics",
            partition_key=dynamodb.Attribute(
                name="partition_key",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY
        )

        # 4. Lambda function for data processing
        processor_lambda = _lambda.Function(
            self, "RealtimeProcessorLambda",
            function_name="realtime-data-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/realtime_processor"),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "METRICS_TABLE_NAME": metrics_table.table_name,
                "ARCHIVE_BUCKET_NAME": archive_bucket.bucket_name
            },
        )

        # Grant permissions
        archive_bucket.grant_write(processor_lambda)
        metrics_table.grant_write_data(processor_lambda)
        data_stream.grant_read(processor_lambda)

        # 5. Add Kinesis event source to Lambda
        processor_lambda.add_event_source(
            sources.KinesisEventSource(
                data_stream,
                starting_position=_lambda.StartingPosition.LATEST,
                batch_size=100,
                max_batching_window=Duration.seconds(5),
                parallelization_factor=2,
                retry_attempts=3
            )
        )

        # 6. CloudWatch Alarms for monitoring
        error_alarm = cloudwatch.Alarm(
            self, "ProcessorErrorAlarm",
            metric=processor_lambda.metric_errors(),
            threshold=5,
            evaluation_periods=1,
            alarm_description="Alert when Lambda errors exceed threshold"
        )

        throttling_alarm = cloudwatch.Alarm(
            self, "ProcessorThrottlingAlarm",
            metric=processor_lambda.metric_throttles(),
            threshold=1,
            evaluation_periods=1,
            alarm_description="Alert when Lambda is throttled"
        )

        # SNS topic for alerts (optional - can be configured with email)
        alert_topic = sns.Topic(
            self, "ProcessingAlertsTopic",
            topic_name="realtime-processing-alerts",
        )

        error_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))
        throttling_alarm.add_alarm_action(cw_actions.SnsAction(alert_topic))

        # 7. Outputs
        CfnOutput(
            self, "DataStreamArn",
            value=data_stream.stream_arn,
            description="Kinesis Data Stream ARN"
        )

        CfnOutput(
            self, "DataStreamName",
            value=data_stream.stream_name,
            description="Kinesis Data Stream Name"
        )

        CfnOutput(
            self, "ArchiveBucketName",
            value=archive_bucket.bucket_name,
            description="S3 Archive Bucket Name"
        )

        CfnOutput(
            self, "MetricsTableName",
            value=metrics_table.table_name,
            description="DynamoDB Metrics Table Name"
        )

        CfnOutput(
            self, "AlertTopicArn",
            value=alert_topic.topic_arn,
            description="SNS Alert Topic ARN"
        )

