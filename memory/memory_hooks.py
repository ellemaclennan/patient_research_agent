from agents import Agent, RunContextWrapper, RunHooks
from memory.vector_graph_store import memory_client
from tools.tools import PATIENT_NAMESPACE


class PatientMemoryHooks(RunHooks):
    """
    automatically pushes relevant memory before each run and saves the resultant converstaion after.
    This gets used in the patient-facing agent so that it always uses patient context to talk to the patient.
    """

    async def on_agent_start(
        self, ctx: RunContextWrapper, agent: Agent
    ) -> None:
        """
        get saved memories for agent on agent start
        """
        patient_id = ctx.context.get("patient_id", "default")
        query = ctx.context.get("query", "")

        if not query:
            return

        results = memory_client.search(
            query=query, user_id=f"{PATIENT_NAMESPACE}_{patient_id}"
        )
        memories = [m.get("memory") for m in results.get("results", [])]
        ctx.context["retrieved_memories"] = "\n".join(memories)

    async def on_run_end(self, ctx: RunContextWrapper, output: str) -> None:
        """
        save the convo history on run-end.
        """
        patient_id = ctx.context.get("patient_id", "default")
        query = ctx.context.get("query", "")

        if not query:
            return

        memory_client.add(
            user_id=f"{PATIENT_NAMESPACE}_{patient_id}",
            messages=[
                {"role": "user", "content": query},
                {"role": "assistant", "content": output},
            ],
        )
