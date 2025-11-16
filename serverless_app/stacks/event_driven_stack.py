from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_dynamodb as dynamodb,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class EventDrivenStack(Stack):
    """
    Event-Driven Architecture Stack
    Microservices communication, event sourcing, decoupled systems
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. EventBridge custom bus
        event_bus = events.EventBus(
            self, "CustomEventBus",
            event_bus_name="custom-event-bus"
        )

        # 2. SNS topic for notifications
        notification_topic = sns.Topic(
            self, "NotificationTopic",
            topic_name="event-notifications",
            display_name="Event Notifications"
        )

        # 3. SQS queues with dead-letter queues
        order_dlq = sqs.Queue(
            self, "OrderDlq",
            queue_name="order-dlq",
            retention_period=Duration.days(14)
        )

        order_queue = sqs.Queue(
            self, "OrderQueue",
            queue_name="order-queue",
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=order_dlq
            ),
            visibility_timeout=Duration.seconds(30)
        )

        inventory_dlq = sqs.Queue(
            self, "InventoryDlq",
            queue_name="inventory-dlq",
            retention_period=Duration.days(14)
        )

        inventory_queue = sqs.Queue(
            self, "InventoryQueue",
            queue_name="inventory-queue",
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=inventory_dlq
            ),
            visibility_timeout=Duration.seconds(30)
        )

        # 4. DynamoDB tables
        orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="event-driven-orders",
            partition_key=dynamodb.Attribute(
                name="order_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        inventory_table = dynamodb.Table(
            self, "InventoryTable",
            table_name="event-driven-inventory",
            partition_key=dynamodb.Attribute(
                name="item_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 5. Lambda functions as event consumers
        order_processor_lambda = _lambda.Function(
            self, "OrderProcessorLambda",
            function_name="event-order-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="order_processor.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/event_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "ORDERS_TABLE_NAME": orders_table.table_name,
                "NOTIFICATION_TOPIC_ARN": notification_topic.topic_arn
            }
        )

        inventory_processor_lambda = _lambda.Function(
            self, "InventoryProcessorLambda",
            function_name="event-inventory-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="inventory_processor.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/event_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "INVENTORY_TABLE_NAME": inventory_table.table_name
            }
        )

        notification_processor_lambda = _lambda.Function(
            self, "NotificationProcessorLambda",
            function_name="event-notification-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="notification_processor.handler",
            code=_lambda.Code.from_asset("serverless_app/lambdas/event_handlers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "NOTIFICATION_TOPIC_ARN": notification_topic.topic_arn
            }
        )

        # Grant permissions
        orders_table.grant_read_write_data(order_processor_lambda)
        inventory_table.grant_read_write_data(inventory_processor_lambda)
        notification_topic.grant_publish(order_processor_lambda)
        notification_topic.grant_publish(notification_processor_lambda)

        # 6. EventBridge rules with filters
        order_rule = events.Rule(
            self, "OrderEventRule",
            rule_name="order-events-rule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["orders"],
                detail_type=["Order Created", "Order Completed"]
            ),
            description="Route order events to order processor"
        )

        order_rule.add_target(
            targets.LambdaFunction(order_processor_lambda)
        )

        inventory_rule = events.Rule(
            self, "InventoryEventRule",
            rule_name="inventory-events-rule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["inventory"],
                detail_type=["Inventory Updated"]
            ),
            description="Route inventory events to inventory processor"
        )

        inventory_rule.add_target(
            targets.LambdaFunction(inventory_processor_lambda)
        )

        notification_rule = events.Rule(
            self, "NotificationEventRule",
            rule_name="notification-events-rule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["notifications"],
                detail_type=["Notification Sent"]
            ),
            description="Route notification events to notification processor"
        )

        notification_rule.add_target(
            targets.LambdaFunction(notification_processor_lambda)
        )

        # 7. Step Functions for complex workflows
        order_workflow_task = tasks.LambdaInvoke(
            self, "OrderWorkflowTask",
            lambda_function=order_processor_lambda,
            output_path="$.Payload"
        )

        inventory_workflow_task = tasks.LambdaInvoke(
            self, "InventoryWorkflowTask",
            lambda_function=inventory_processor_lambda,
            output_path="$.Payload"
        )

        # Parallel execution of order and inventory processing
        parallel_state = sfn.Parallel(
            self, "ProcessOrderAndInventory",
            comment="Process order and update inventory in parallel"
        )

        parallel_state.branch(order_workflow_task)
        parallel_state.branch(inventory_workflow_task)

        workflow_definition = parallel_state

        workflow_state_machine = sfn.StateMachine(
            self, "EventWorkflowStateMachine",
            state_machine_name="event-driven-workflow",
            definition=workflow_definition,
            timeout=Duration.minutes(5),
            tracing_enabled=True
        )

        # 8. EventBridge rule to trigger Step Functions
        workflow_rule = events.Rule(
            self, "WorkflowEventRule",
            rule_name="workflow-events-rule",
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["workflow"],
                detail_type=["Workflow Triggered"]
            ),
            description="Trigger Step Functions workflow"
        )

        workflow_rule.add_target(
            targets.SfnStateMachine(workflow_state_machine)
        )

        workflow_state_machine.grant_start_execution(
            iam.ServicePrincipal("events.amazonaws.com")
        )

        # 9. SQS subscriptions (optional - for async processing)
        order_queue.grant_send_messages(order_processor_lambda)
        inventory_queue.grant_send_messages(inventory_processor_lambda)

        # 10. Outputs
        CfnOutput(
            self, "EventBusArn",
            value=event_bus.event_bus_arn,
            description="EventBridge Custom Bus ARN"
        )

        CfnOutput(
            self, "EventBusName",
            value=event_bus.event_bus_name,
            description="EventBridge Custom Bus Name"
        )

        CfnOutput(
            self, "NotificationTopicArn",
            value=notification_topic.topic_arn,
            description="SNS Notification Topic ARN"
        )

        CfnOutput(
            self, "StateMachineArn",
            value=workflow_state_machine.state_machine_arn,
            description="Step Functions State Machine ARN"
        )

        CfnOutput(
            self, "OrdersTableName",
            value=orders_table.table_name,
            description="Orders DynamoDB Table Name"
        )

        CfnOutput(
            self, "InventoryTableName",
            value=inventory_table.table_name,
            description="Inventory DynamoDB Table Name"
        )

