import asyncio
import os
from agents import Agent, GuardrailFunctionOutput, Runner, enable_verbose_stdout_logging, set_default_openai_client, set_tracing_disabled
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

class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str

guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking about homework.",
    output_type=HomeworkOutput,
)

math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="Specialist agent for math questions",
    instructions="You provide help with math problems. Explain your reasoning at each step and include examples",
)

history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="Specialist agent for historical questions",
    instructions="You provide assistance with historical queries. Explain important events and context clearly.",
)


async def homework_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(HomeworkOutput)
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.is_homework,
    )

triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's homework question",
    handoffs=[history_tutor_agent, math_tutor_agent]
)

async def main():
    result = await Runner.run(triage_agent, "I am doing a history homework and want to know who was the first president of the united states?", max_turns=2)
    print(result.final_output)

    result = await Runner.run(triage_agent, "what is life")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())