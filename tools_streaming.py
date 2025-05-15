import asyncio
import os
import random
from agents import Agent, ItemHelpers, Runner, enable_verbose_stdout_logging, function_tool, set_default_openai_client, set_tracing_disabled
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

enable_verbose_stdout_logging()
set_tracing_disabled(True)

# Load environment variables from a .env file
load_dotenv()

# Read the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

print(f"API Key: {api_key}")

custom_client = AsyncAzureOpenAI(azure_endpoint="https://ruslany-openai.openai.azure.com/", api_key=api_key, api_version="2025-03-01-preview", azure_deployment="gpt-4o-mini")
set_default_openai_client(custom_client)

@function_tool
def how_many_jokes() -> int:
    return random.randint(1, 5)


async def main():
    agent = Agent(
        name="Joker",
        instructions="First call the `how_many_jokes` tool, then tell that many jokes.",
        tools=[how_many_jokes],
    )

    result = Runner.run_streamed(
        agent,
        input="Hello",
    )
    print("=== Run starting ===")

    async for event in result.stream_events():
        # We'll ignore the raw responses event deltas
        if event.type == "raw_response_event":
            continue
        # When the agent updates, print that
        elif event.type == "agent_updated_stream_event":
            print(f"Agent updated: {event.new_agent.name}")
            continue
        # When items are generated, print them
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                print("-- Tool was called")
            elif event.item.type == "tool_call_output_item":
                print(f"-- Tool output: {event.item.output}")
            elif event.item.type == "message_output_item":
                print(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
            else:
                pass  # Ignore other event types

    print("=== Run complete ===")


if __name__ == "__main__":
    asyncio.run(main())