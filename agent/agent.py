import asyncio
import json

from agents import Agent, RunContextWrapper, Runner
from dotenv import find_dotenv, load_dotenv
from memory.memory_hooks import PatientMemoryHooks
from prompts.v_1_0 import SYSTEM_PROMPTS
from tools.tools import (
    review_summary,
    save_research_findings,
    search_patient_history,
    search_pubmed,
    search_research_memory,
)

load_dotenv(find_dotenv())


# OpenAI docs pass a callable as instructions for dynamic prompts that's why I did it this way
def patient_facing_instructions(ctx: RunContextWrapper, _agent: Agent) -> str:
    """Retreive patient memories from context to pass to the agent through the system prompt."""
    memories = ctx.context.get("retrieved_memories", "")
    base = SYSTEM_PROMPTS["patient_facing_agent"]
    if memories:
        return f"{base}\n\nKnown information about this patient:\n{memories}"
    return base


patient_facing_agent = Agent(
    name="Patient-Facing Agent",
    # this is where you the callable is passed so that the patient-facing agent always has patient context
    instructions=patient_facing_instructions,
)

research_agent = Agent(
    name="Research agent",
    instructions=SYSTEM_PROMPTS["research_agent"],
    tools=[search_pubmed, search_research_memory, save_research_findings],
)

pseudo_phd_agent = Agent(
    name="Pseudo PhD Agent",
    instructions=SYSTEM_PROMPTS["pseudo_phd_agent"],
    tools=[
        search_research_memory,
        search_patient_history,
        save_research_findings,
        review_summary,
    ],
)

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=SYSTEM_PROMPTS["orchestrator_agent"],
    tools=[
        patient_facing_agent.as_tool(
            tool_name="patient_facing_agent",
            tool_description="Talks to the patient. Use first to greet and gather their condition, and after research to deliver results in plain language.",
        ),
        research_agent.as_tool(
            tool_name="research_agent",
            tool_description="Searches PubMed and saves findings for a given condition.",
        ),
        pseudo_phd_agent.as_tool(
            tool_name="pseudo_phd_agent",
            tool_description="Synthesises research into treatment options and requests human review before results reach the patient.",
        ),
    ],
)


async def main():
    patient_id = input("Enter patient ID: ").strip()

    # Trigger the initial greeting before patient writes anything past their ID
    greeting = await Runner.run(
        # tried calling patient_facing here instead but I think it messed-up the history so I switched back for consistencyu
        orchestrator_agent,
        input="Please greet the patient and ask what condition they have.",
        context={"patient_id": patient_id, "query": ""},
        hooks=PatientMemoryHooks(),
    )
    print(f"\nAgent: {greeting.final_output}\n")

    # save the convo history so the agent remembers
    # everything said earlier in the session
    history = greeting.to_input_list()

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        result = await Runner.run(
            orchestrator_agent,
            input=history + [{"role": "user", "content": user_input}],
            context={"patient_id": patient_id, "query": user_input},
            hooks=PatientMemoryHooks(),
        )

        # review_summary uses needs_approval=True, which pauses the run.
        # refer to Human in the loop section in openai docs
        while result.interruptions:
            for interruption in result.interruptions:
                raw = interruption.raw_item
                raw_args = getattr(raw, "arguments", "{}")
                args = (
                    json.loads(raw_args)
                    if isinstance(raw_args, str)
                    else (raw_args or {})
                )
                summary = args.get("summary", str(raw))
                print(f"\n[PhD REVIEW REQUIRED]\n{summary}\n")
                decision = input("Approve summary? (y/n): ").strip().lower()
                state = result.to_state()
                if decision == "y":
                    state.approve(interruption)
                else:
                    state.reject(
                        interruption, message="Summary rejected by reviewer."
                    )
            result = await Runner.run(
                orchestrator_agent, state, hooks=PatientMemoryHooks()
            )

        # final_output is None if the orchestrator ends on a tool call
        # and doesn't produce its own text output so we fall back to the last tool result
        output = result.final_output
        if output is None:
            for item in reversed(result.new_items):
                if hasattr(item, "output") and isinstance(item.output, str):
                    output = item.output
                    break
        print(f"\nAgent: {output}\n")

        # uncomment this  to see the raw result with tool calls etc.
        # print(result.raw_responses)

        history = result.to_input_list()


asyncio.run(main())
