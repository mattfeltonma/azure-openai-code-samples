import logging
import sys
import os
import json
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

import time
import datetime

## This function sets up logging in a custom format
##
def configure_logging(level="ERROR"):
    try:
        # Convert the level string to uppercase so it matches what the logging library expects
        logging_level = getattr(logging, level.upper(), None)

        # Setup a logging format
        logging.basicConfig(
            level=logging_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    except Exception as e:
        print(f"Failed to set up logging: {e}", file=sys.stderr)
        sys.exit(1)

## This function obtains an access token from Entra ID using a service principal with a client id and client secret
##
def authenticate_with_service_principal(scope):
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            scope
        )
        return token_provider
    except:
        logging.error('Failed to obtain access token: ', exc_info=True)
        sys.exit(1)

## Main function
##
def main():
    # Setup logging
    #
    configure_logging("ERROR")

    # Use dotenv library to load environmental variables from .env file.
    # The variables loaded include AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
    # OPENAI_BASE_URL, and DEPLOYMENT_NAME.
    try:
        load_dotenv('.env', override=True)
    except Exception as e:
        logging.error(
            'Failed to load environmental variables: ', exc_info=True)
        sys.exit(1)

    # Obtain an access token
    #
    token_provider = authenticate_with_service_principal(
        scope="https://ai.azure.com/.default")

    # Submit an inference to the Responses API
    #
    try:
        # Create the Azure OpenAI Service client
        # 
        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=token_provider
        )

        first_response = client.responses.create(
            # Store the response in the service so it can be referenced in a follow up
            store=True,
            model=os.getenv("DEPLOYMENT_NAME"),
            tools=[
                {
                    "type": "mcp",
                    "server_label": "mslearn",
                    "server_description": "Microsoft Learn documentation MCP server",
                    "server_url": "https://learn.microsoft.com/api/mcp",
                    "require_approval": "never"
                }
            ],
            # Force the model to use the learn tool
            tool_choice={
                "type": "mcp",
                "server_label": "mslearn"
            },
            # If the model supports reasoning, print it out
            #reasoning={
            #    "effort": "medium", 
            #    "summary": "detailed"
            #},
            input=[
                {
                    "role": "system",
                    "content": """You are an expert Microsoft Azure assistant.

                    Instructions:
                    - Use the learn tool to search Microsoft Learn documentation before answering
                    - Provide accurate, well-grounded responses based on official documentation
                    - If the learn tool is unavailable or returns no results, clearly state: "I cannot answer this question at this time as I'm unable to access the documentation"
                    - Keep responses concise and relevant to Azure

                    If a question is outside the scope of Microsoft Azure, politely redirect the user."""
                },
                {
                    "role": "user",
                    "content": "I have a TB of data that needs to be accessed by external users. What type of Azure storage should I use?"
                }
            ]
        )
        # If the model supports reasoning, print out the reasoning summary and effort level
        #if first_response.reasoning:
        #    print("\n=== Reasoning Summary ===")
        #    print(first_response.reasoning.summary)
        #    print("\n=== Effort Level ===")
        #     print(first_response.reasoning.effort)
        print(first_response.output_text)
        response_id = first_response.id

        # Uncomment this to see the raw responses formatted in a way that is actually readable
        #print(first_response.model_dump_json(indent=2))

        # Use the prior response id as context for a follow up question
        follow_up_response = client.responses.create(
            store=False,
            model=os.getenv("DEPLOYMENT_NAME"),
            tools=[
                {
                    "type": "mcp",
                    "server_label": "mslearn",
                    "server_description": "Microsoft Learn documentation MCP server",
                    "server_url": "https://learn.microsoft.com/api/mcp",
                    "require_approval": "never"
                }
            ],
            # Force the model to use the learn tool
            tool_choice={
                "type": "mcp",
                "server_label": "mslearn"
            },
            # If the model supports reasoning, print out the reasoning summary and effort level
            #reasoning={
            #    "effort": "medium", 
            #    "summary": "detailed"
            #},
            input=[
                {
                    "role": "user",
                    "content": "What SKU should I use if I need the lowest latency response?"
                }
            ],
            previous_response_id=response_id
        )
        # If the model supports reasoning, print out the reasoning summary and effort level
        #if first_response.reasoning:
        #    print("\n=== Reasoning Summary ===")
        #    print(first_response.reasoning.summary)
        #    print("\n=== Effort Level ===")
        #    print(first_response.reasoning.effort)
        print(follow_up_response.output_text)

    except:
        logging.error('Failed batch chat completion: ', exc_info=True)

if __name__ == "__main__":
    main()