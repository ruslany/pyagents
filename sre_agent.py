import asyncio
import os
from agents import Agent, Runner, enable_verbose_stdout_logging, set_default_openai_api, set_default_openai_client, set_tracing_disabled
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from sre_agent_tools import (
    check_nsg_rules, 
    check_dns, 
    get_cpu_usage, 
    get_memory_usage, 
    get_logs
)

enable_verbose_stdout_logging()
set_tracing_disabled(True)
set_default_openai_api("chat_completions")


# Load environment variables from a .env file
load_dotenv()

# Read the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

custom_client = AsyncAzureOpenAI(azure_endpoint="https://ruslany-net.openai.azure.com", api_key=api_key, api_version="2025-03-01-preview", azure_deployment="gpt-4o-mini")
set_default_openai_client(custom_client)

# Define coordinator_agent first with empty handoffs to resolve circular reference
coordinator_agent = Agent(
    name="Container Apps Coordinating Agent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are a coordinator for an Azure Container Apps SRE agent. Your job is to:
1. Understand the user's request about their Azure Container app. 
   The container app may be having a problem that needs diagnosis or user is just asking questions about it 
2. Determine which specialized diagnostic agent to use to handle user's request
3. Handoff to the appropriate diagnostic agent
""",
    handoffs=[]
)

networking_diagnostic_agent = Agent(
    name="Networking Diagnostic Agent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are a specialized Azure networking diagnostic agent. Your job is to diagnose networking issues with Azure applications.

Focus on these common networking issues:
1. NSG rules blocking traffic
2. DNS resolution issues

If you need more information, ask the user specific questions.
If you need to run a diagnostic tool, use the appropriate function.
If the question is outside of your expertise then handoff to coordinator agent

If you've identified the issue, respond with a line starting with DIAGNOSIS: followed by a brief description of the issue.
Example: DIAGNOSIS: NSG rule blocking port 443 traffic to the web tier

After any tool usage or diagnosis, provide a clear explanation to the user.
""",
    handoffs=[],
    tools=[check_nsg_rules, check_dns]
)

availability_diagnostic_agent = Agent(
    name="Availability Diagnostic Agent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
You are a specialized Azure Container Apps availability diagnostic agent. Your job is to diagnose availability issues with Azure Container Apps applications.

Focus on these common availability issues:
1. High CPU or memory usage makes the app unresponsive
2. High request count makes the app unresponsive
3. Image pull failures in the logs result in the latest revision unable to activate

If you need more information, ask the user specific questions.
If you need to run a diagnostic tool, use the appropriate function.
If the question is outside of your expertise then handoff to coordinator agent

If you've identified the issue, respond with a line starting with DIAGNOSIS: followed by a brief description of the issue.
Example: DIAGNOSIS: Image pull failure due to incorrect credentials

After any tool usage or diagnosis, provide a clear explanation to the user.
""",
    handoffs=[],
    tools=[get_cpu_usage, get_memory_usage, get_logs]
)

# Now update handoffs to reference the correct agents
networking_diagnostic_agent.handoffs = [coordinator_agent]
availability_diagnostic_agent.handoffs = [coordinator_agent]
coordinator_agent.handoffs = [networking_diagnostic_agent, availability_diagnostic_agent]

async def main():
    agent = coordinator_agent
    messages = []

    while True:
        user = input("User: ")
        messages.append({"role": "user", "content": user})

        response = await Runner.run(agent, messages)
        agent = response.last_agent
        messages = response.to_input_list()

if __name__ == "__main__":
    asyncio.run(main())
