from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class WebSocketChatStack(Stack):
    """
    WebSocket Chat Application Stack
    Real-time messaging, notifications, collaborative features
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. DynamoDB table for connection tracking
        connections_table = dynamodb.Table(
            self, "ConnectionsTable",
            table_name="websocket-connections",
            partition_key=dynamodb.Attribute(
                name="connection_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY
        )

        # 2. DynamoDB table for message storage
        messages_table = dynamodb.Table(
            self, "MessagesTable",
            table_name="websocket-messages",
            partition_key=dynamodb.Attribute(
                name="room",
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
        
        # Add Global Secondary Index for querying by user_id
        messages_table.add_global_secondary_index(
            index_name="user-timestamp-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            )
        )

        # 3. API Gateway WebSocket API
        websocket_api = apigwv2.WebSocketApi(
            self, "ChatWebSocketApi",
            api_name="chat-websocket-api",
            description="WebSocket API for real-time chat"
        )

        # 4. Lambda functions for WebSocket handlers
        connect_lambda = _lambda.Function(
            self, "ConnectHandler",
            function_name="websocket-connect",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="connect.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/websocket_handler"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "CONNECTIONS_TABLE_NAME": connections_table.table_name
                # Remove API_GATEWAY_ENDPOINT - we'll construct it from request context
            }
        )

        disconnect_lambda = _lambda.Function(
            self, "DisconnectHandler",
            function_name="websocket-disconnect",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="disconnect.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/websocket_handler"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "CONNECTIONS_TABLE_NAME": connections_table.table_name
            }
        )

        default_lambda = _lambda.Function(
            self, "DefaultHandler",
            function_name="websocket-default",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="default.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/websocket_handler"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "CONNECTIONS_TABLE_NAME": connections_table.table_name,
                "MESSAGES_TABLE_NAME": messages_table.table_name
                # Remove API_GATEWAY_ENDPOINT
            }
        )

        # Grant permissions
        connections_table.grant_read_write_data(connect_lambda)
        connections_table.grant_read_write_data(disconnect_lambda)
        connections_table.grant_read_data(default_lambda)
        messages_table.grant_write_data(default_lambda)

        # Grant Lambda permission to post to WebSocket connections
        connect_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[f"arn:aws:execute-api:{self.region}:{self.account}:{websocket_api.api_id}/*"]
            )
        )

        default_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[f"arn:aws:execute-api:{self.region}:{self.account}:{websocket_api.api_id}/*"]
            )
        )

        # 5. WebSocket API routes
        websocket_api.add_route(
            "$connect",
            integration=apigwv2_integrations.WebSocketLambdaIntegration(
                "ConnectIntegration",
                handler=connect_lambda
            )
        )

        websocket_api.add_route(
            "$disconnect",
            integration=apigwv2_integrations.WebSocketLambdaIntegration(
                "DisconnectIntegration",
                handler=disconnect_lambda
            )
        )

        websocket_api.add_route(
            "$default",
            integration=apigwv2_integrations.WebSocketLambdaIntegration(
                "DefaultIntegration",
                handler=default_lambda
            )
        )

        # 6. WebSocket API Stage
        stage = apigwv2.WebSocketStage(
            self, "ChatWebSocketStage",
            web_socket_api=websocket_api,
            stage_name="prod",
            auto_deploy=True
        )

        # 7. Outputs
        CfnOutput(
            self, "WebSocketApiEndpoint",
            value=stage.url,
            description="WebSocket API Endpoint URL"
        )

        CfnOutput(
            self, "WebSocketApiId",
            value=websocket_api.api_id,
            description="WebSocket API ID"
        )

        CfnOutput(
            self, "ConnectionsTableName",
            value=connections_table.table_name,
            description="Connections DynamoDB Table Name"
        )

        CfnOutput(
            self, "MessagesTableName",
            value=messages_table.table_name,
            description="Messages DynamoDB Table Name"
        )

