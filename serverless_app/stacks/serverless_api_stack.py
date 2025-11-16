from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class ServerlessApiStack(Stack):
    """
    Serverless REST API Stack
    Production-ready REST API backend with authentication
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. DynamoDB table with GSI for queries
        items_table = dynamodb.Table(
            self, "ItemsTable",
            table_name="serverless-api-items",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Add Global Secondary Index for querying by status
        items_table.add_global_secondary_index(
            index_name="status-created-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # 2. Cognito User Pool for authentication
        user_pool = cognito.UserPool(
            self, "ApiUserPool",
            user_pool_name="serverless-api-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # 3. Cognito User Pool Client
        user_pool_client = cognito.UserPoolClient(
            self, "ApiUserPoolClient",
            user_pool=user_pool,
            user_pool_client_name="serverless-api-client",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            )
        )

        # 4. Cognito Identity Pool (optional - for AWS service access)
        identity_pool = cognito.CfnIdentityPool(
            self, "ApiIdentityPool",
            identity_pool_name="serverless-api-identity",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=user_pool_client.user_pool_client_id,
                    provider_name=user_pool.user_pool_provider_name
                )
            ]
        )

        # 5. Lambda functions for CRUD operations
        create_lambda = _lambda.Function(
            self, "CreateItemLambda",
            function_name="api-create-item",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="create_item.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/api_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": items_table.table_name
            }
        )

        get_lambda = _lambda.Function(
            self, "GetItemLambda",
            function_name="api-get-item",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="get_item.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/api_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": items_table.table_name
            }
        )

        list_lambda = _lambda.Function(
            self, "ListItemsLambda",
            function_name="api-list-items",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="list_items.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/api_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": items_table.table_name
            }
        )

        update_lambda = _lambda.Function(
            self, "UpdateItemLambda",
            function_name="api-update-item",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="update_item.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/api_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": items_table.table_name
            }
        )

        delete_lambda = _lambda.Function(
            self, "DeleteItemLambda",
            function_name="api-delete-item",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="delete_item.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/api_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "TABLE_NAME": items_table.table_name
            }
        )

        # Grant DynamoDB permissions
        items_table.grant_read_write_data(create_lambda)
        items_table.grant_read_data(get_lambda)
        items_table.grant_read_data(list_lambda)
        items_table.grant_read_write_data(update_lambda)
        items_table.grant_read_write_data(delete_lambda)

        # 6. API Gateway REST API
        api = apigw.RestApi(
            self, "ServerlessApi",
            rest_api_name="serverless-api",
            description="Serverless REST API with authentication",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key"]
            ),
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200
            )
        )

        # 7. Cognito Authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "ApiAuthorizer",
            cognito_user_pools=[user_pool],
            identity_source=apigw.IdentitySource.header("Authorization")
        )

        # 8. API Resources and Methods
        items_resource = api.root.add_resource("items")

        # POST /items (Create) - Requires authentication
        items_resource.add_method(
            "POST",
            apigw.LambdaIntegration(create_lambda),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # GET /items (List) - Public
        items_resource.add_method(
            "GET",
            apigw.LambdaIntegration(list_lambda)
        )

        # GET /items/{id} (Get) - Public
        item_resource = items_resource.add_resource("{id}")
        item_resource.add_method(
            "GET",
            apigw.LambdaIntegration(get_lambda)
        )

        # PUT /items/{id} (Update) - Requires authentication
        item_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(update_lambda),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # DELETE /items/{id} (Delete) - Requires authentication
        item_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_lambda),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO
        )

        # 9. Request Validator (optional)
        request_validator = apigw.RequestValidator(
            self, "ApiRequestValidator",
            rest_api=api,
            validate_request_body=True,
            validate_request_parameters=True
        )

        # 10. Outputs
        CfnOutput(
            self, "ApiEndpoint",
            value=api.url,
            description="API Gateway Endpoint URL"
        )

        CfnOutput(
            self, "UserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )

        CfnOutput(
            self, "UserPoolClientId",
            value=user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID"
        )

        CfnOutput(
            self, "IdentityPoolId",
            value=identity_pool.ref,
            description="Cognito Identity Pool ID"
        )

        CfnOutput(
            self, "ItemsTableName",
            value=items_table.table_name,
            description="DynamoDB Items Table Name"
        )

        CfnOutput(
            self, "ApiItemsEndpoint",
            value=f"{api.url}items",
            description="API Items Endpoint URL"
        )

