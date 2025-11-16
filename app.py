#!/usr/bin/env python3
import os

import aws_cdk as cdk

from serverless_app.serverless_app_stack import ServerlessAppStack
from serverless_app.stacks.realtime_processing_stack import RealtimeProcessingStack
from serverless_app.stacks.etl_pipeline_stack import EtlPipelineStack
from serverless_app.stacks.websocket_chat_stack import WebSocketChatStack
from serverless_app.stacks.data_lake_stack import DataLakeStack
from serverless_app.stacks.ai_services_stack import AiServicesStack
from serverless_app.stacks.event_driven_stack import EventDrivenStack
from serverless_app.stacks.serverless_api_stack import ServerlessApiStack


app = cdk.App()

# Original Media Processing Stack
# ServerlessAppStack(app, "ServerlessAppStack")

# Real-Time Data Processing Pipeline Stack
# RealtimeProcessingStack(app, "RealtimeProcessingStack")

# Scheduled ETL Pipeline Stack
# EtlPipelineStack(app, "EtlPipelineStack")

# # WebSocket Chat Application Stack
# WebSocketChatStack(app, "WebSocketChatStack")

# # Serverless Data Lake Stack
# DataLakeStack(app, "DataLakeStack")

# # AI Services Project Stack
# AiServicesStack(app, "AiServicesStack")

# # Event-Driven Architecture Stack
# EventDrivenStack(app, "EventDrivenStack")

# # Serverless REST API Stack
ServerlessApiStack(app, "ServerlessApiStack")

app.synth()
