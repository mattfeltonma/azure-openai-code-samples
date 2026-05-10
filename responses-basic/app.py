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
            model=os.getenv("DEPLOYMENT_NAME"),
            # Store the response in the service so it can be referenced in a follow up
            store=True,
            input=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": "What is the capital of Sweden"
                }
            ]
        )

        print(first_response.output_text)
        response_id = first_response.id

        # Uncomment this to see the raw responses formatted in a way that is actually readable
        #print(first_response.model_dump_json(indent=2))

        # Use the prior response id as context for a follow up question
        follow_up_response = client.responses.create(
            model=os.getenv("DEPLOYMENT_NAME"),
            input=[
                {
                    "role": "user",
                    "content": "What is the population of Sweden?"
                }
            ],
            previous_response_id=response_id
        )
        print(follow_up_response.output_text)

    except:
        logging.error('Failed batch chat completion: ', exc_info=True)

if __name__ == "__main__":
    main()