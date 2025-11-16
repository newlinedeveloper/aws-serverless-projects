from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_glue as glue,
    aws_athena as athena,
    aws_lambda as _lambda,
    aws_lambda_event_sources as sources,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class DataLakeStack(Stack):
    """
    Serverless Data Lake Stack
    Analytics on structured/unstructured data, data lake queries
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 buckets organized by data zones
        raw_bucket = s3.Bucket(
            self, "RawDataBucket",
            bucket_name=f"data-lake-raw-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionToGlacier",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )

        processed_bucket = s3.Bucket(
            self, "ProcessedDataBucket",
            bucket_name=f"data-lake-processed-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        curated_bucket = s3.Bucket(
            self, "CuratedDataBucket",
            bucket_name=f"data-lake-curated-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 2. Glue Database
        glue_database = glue.CfnDatabase(
            self, "DataLakeDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="data_lake_db",
                description="Data Lake Database for analytics"
            )
        )

        # 3. Glue Crawler for schema discovery
        crawler_role = iam.Role(
            self, "GlueCrawlerRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
            ]
        )

        raw_bucket.grant_read(crawler_role)
        processed_bucket.grant_read(crawler_role)
        curated_bucket.grant_read(crawler_role)

        glue_crawler = glue.CfnCrawler(
            self, "DataLakeCrawler",
            name="data-lake-crawler",
            role=crawler_role.role_arn,
            database_name=glue_database.ref,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{processed_bucket.bucket_name}/processed/"
                    ),
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{curated_bucket.bucket_name}/"
                    )
                ]
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE",
                delete_behavior="LOG"
            )
        )

        glue_crawler.add_dependency(glue_database)

        # 4. Lambda function for data ingestion and transformation
        processor_lambda = _lambda.Function(
            self, "DataLakeProcessorLambda",
            function_name="data-lake-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/data_lake_processor"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "RAW_BUCKET_NAME": raw_bucket.bucket_name,
                "PROCESSED_BUCKET_NAME": processed_bucket.bucket_name,
                "GLUE_DATABASE_NAME": glue_database.ref,
                "GLUE_CRAWLER_NAME": glue_crawler.name
            }
        )

        # Grant permissions
        raw_bucket.grant_read(processor_lambda)
        processed_bucket.grant_write(processor_lambda)
        processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["glue:StartCrawler"],
                resources=[f"arn:aws:glue:{self.region}:{self.account}:crawler/{glue_crawler.name}"]
            )
        )

        # 5. S3 event trigger for Lambda
        processor_lambda.add_event_source(
            sources.S3EventSource(
                raw_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="data/")]
            )
        )

        # 6. Athena WorkGroup for queries
        athena_workgroup = athena.CfnWorkGroup(
            self, "DataLakeWorkGroup",
            name="data-lake-workgroup",
            description="WorkGroup for Data Lake queries",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{processed_bucket.bucket_name}/athena-results/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3"
                    )
                ),
                enforce_work_group_configuration=True
                # Removed publish_cloud_watch_metrics - not supported in this CDK version
            )
        )

        # 7. IAM role for Athena queries
        athena_role = iam.Role(
            self, "AthenaQueryRole",
            assumed_by=iam.ServicePrincipal("athena.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAthenaFullAccess")
            ]
        )

        raw_bucket.grant_read(athena_role)
        processed_bucket.grant_read_write(athena_role)
        curated_bucket.grant_read(athena_role)

        # Grant Glue access
        athena_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetPartitions"
                ],
                resources=["*"]
            )
        )

        # 7. Outputs
        CfnOutput(
            self, "RawBucketName",
            value=raw_bucket.bucket_name,
            description="Raw Data S3 Bucket Name"
        )

        CfnOutput(
            self, "ProcessedBucketName",
            value=processed_bucket.bucket_name,
            description="Processed Data S3 Bucket Name"
        )

        CfnOutput(
            self, "CuratedBucketName",
            value=curated_bucket.bucket_name,
            description="Curated Data S3 Bucket Name"
        )

        CfnOutput(
            self, "GlueDatabaseName",
            value=glue_database.ref,
            description="Glue Database Name"
        )

        CfnOutput(
            self, "GlueCrawlerName",
            value=glue_crawler.name,
            description="Glue Crawler Name"
        )

        CfnOutput(
            self, "AthenaWorkGroupName",
            value=athena_workgroup.name,
            description="Athena WorkGroup Name"
        )

        CfnOutput(
            self, "AthenaQueryExample",
            value=f"SELECT * FROM {glue_database.ref}.processed_table LIMIT 10;",
            description="Example Athena Query"
        )

