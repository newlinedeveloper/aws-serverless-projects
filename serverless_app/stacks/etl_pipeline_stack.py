from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class EtlPipelineStack(Stack):
    """
    Scheduled ETL Pipeline Stack
    Daily data aggregation, data warehouse loading, report generation
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 bucket for staging and archival
        staging_bucket = s3.Bucket(
            self, "EtlStagingBucket",
            bucket_name=f"etl-staging-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldFiles",
                    enabled=True,
                    expiration=Duration.days(30)
                )
            ]
        )

        # 2. Source DynamoDB table (simulating source system)
        source_table = dynamodb.Table(
            self, "SourceDataTable",
            table_name="etl-source-data",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 3. Destination DynamoDB table (data warehouse)
        destination_table = dynamodb.Table(
            self, "DestinationDataTable",
            table_name="etl-destination-data",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 4. Lambda functions for ETL steps
        extract_lambda = _lambda.Function(
            self, "ExtractLambda",
            function_name="etl-extract",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="extract.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/etl_processor"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "SOURCE_TABLE_NAME": source_table.table_name,
                "STAGING_BUCKET_NAME": staging_bucket.bucket_name
            }
        )

        transform_lambda = _lambda.Function(
            self, "TransformLambda",
            function_name="etl-transform",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="transform.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/etl_processor"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "STAGING_BUCKET_NAME": staging_bucket.bucket_name
            }
        )

        load_lambda = _lambda.Function(
            self, "LoadLambda",
            function_name="etl-load",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="load.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/etl_processor"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "STAGING_BUCKET_NAME": staging_bucket.bucket_name,
                "DESTINATION_TABLE_NAME": destination_table.table_name
            }
        )

        # Grant permissions
        staging_bucket.grant_read_write(extract_lambda)
        staging_bucket.grant_read_write(transform_lambda)
        staging_bucket.grant_read_write(load_lambda)
        source_table.grant_read_data(extract_lambda)
        destination_table.grant_write_data(load_lambda)

        # 5. Step Functions state machine for orchestration
        extract_task = tasks.LambdaInvoke(
            self, "ExtractTask",
            lambda_function=extract_lambda,
            output_path="$.Payload"
        )

        transform_task = tasks.LambdaInvoke(
            self, "TransformTask",
            lambda_function=transform_lambda,
            output_path="$.Payload"
        )

        load_task = tasks.LambdaInvoke(
            self, "LoadTask",
            lambda_function=load_lambda,
            output_path="$.Payload"
        )

        # Define the workflow
        definition = extract_task.next(
            transform_task.next(load_task)
        )

        state_machine = sfn.StateMachine(
            self, "EtlStateMachine",
            state_machine_name="etl-pipeline",
            definition=definition,
            timeout=Duration.minutes(30),
            tracing_enabled=True
        )

        # 6. EventBridge rule for scheduled trigger (daily at 2 AM UTC)
        schedule_rule = events.Rule(
            self, "EtlScheduleRule",
            rule_name="etl-daily-schedule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="2",
                day="*",
                month="*",
                year="*"
            ),
            description="Trigger ETL pipeline daily"
        )

        schedule_rule.add_target(
            targets.SfnStateMachine(state_machine)
        )

        # Grant EventBridge permission to start Step Functions
        state_machine.grant_start_execution(
            iam.ServicePrincipal("events.amazonaws.com")
        )

        # 7. Outputs
        CfnOutput(
            self, "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="Step Functions State Machine ARN"
        )

        CfnOutput(
            self, "StagingBucketName",
            value=staging_bucket.bucket_name,
            description="S3 Staging Bucket Name"
        )

        CfnOutput(
            self, "SourceTableName",
            value=source_table.table_name,
            description="Source DynamoDB Table Name"
        )

        CfnOutput(
            self, "DestinationTableName",
            value=destination_table.table_name,
            description="Destination DynamoDB Table Name"
        )

