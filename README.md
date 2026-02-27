# Patient Research Agent

An agentic AI system for rare/orphan disease research. Given a patient's condition, it searches PubMed for clinical papers, synthesises findings, routes them through a human review gate, and delivers a plain-language summary to the patient.

## Why these architecture choices?

I used a dual graph-vector store memory structure.The graph structure makes identifying relationships between different patients' conditions easier over time. The vector store is good for research information and answering patient questions because it performs well on similarity searces. 

I used a hook for the patient-facing agent so that its memory of the patient and context is automatically injected into every conversation, that way it can remember all the patient's details.

For the research agent, I used explicit function tool calls instead because I didn't want to save or recall everything automatically, since some information is noise. Letting the agent decide what's worth storing and recalling gives better signal.

Overall I chose agentic memory over classic RAG because I want the memory to be dynamic, Updating over time and drawing connections between different patients and previously discovered research.

---

## Architecture

Four agents orchestrated by a central coordinator:

```
orchestrator_agent
├── patient_facing_agent   —> greets patient, delivers results in plain language
├── research_agent         —> searches PubMed and saves findings
└── pseudo_phd_agent       —> synthesises research, triggers human review gate
```

### Memory

Two memory stores via [mem0](https://github.com/mem0ai/mem0):

| Store | Provider | Purpose |
|---|---|---|
| Vector | Qdrant Cloud | Semantic search over patient conversations, and research articles |
| Graph | Neo4j Aura | Relationship mapping between conditions, treatments, patients |

**Push memory (hooks):** Patient context is automatically retrieved and injected into `patient_facing_agent`'s system prompt before each run via `PatientMemoryHooks.on_agent_start`.

**Pull memory (tools):** `research_agent` and `pseudo_phd_agent` explicitly call `search_research_memory` and `search_patient_history` when they decide it's relevant — the agent chooses when to retrieve.

This push/pull split avoids unnecessary Qdrant searches for agents that don't need patient context.

### Human-in-the-loop

`pseudo_phd_agent` calls `review_summary(needs_approval=True)` which pauses the run. The researcher must approve or reject the technical summary before it reaches the patient.

---

## Setup

### Prerequisites
- Python 3.14+
- [Qdrant Cloud](https://cloud.qdrant.io) account (free tier)
- [Neo4j Aura](https://neo4j.com/cloud/platform/aura-graph-database/) account (free tier)
- OpenAI API key

### Installation

```bash
git clone <repo>
cd patient_research_agent
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=

QDRANT_ENDPOINT=https://your-cluster.qdrant.io
QDRANT_API_KEY=

NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j
```

### Known patch required

There is a bug in mem0's Neo4j integration. After installing dependencies, apply this fix in `.venv/Lib/site-packages/mem0/memory/graph_memory.py`:

```python
self.graph = Neo4jGraph(
    url=self.config.graph_store.config.url,
    username=self.config.graph_store.config.username,
    password=self.config.graph_store.config.password,
    database=self.config.graph_store.config.database,
    refresh_schema=False,
    driver_config={"notifications_min_severity": "OFF"},  # add this line
)
```

---

## Running

```bash
python -m agent.agent
```

You will be prompted for a patient ID. Use the same ID across sessions to retain memory.

---

## Project structure

```
patient_research_agent/
├── agent/
│   └── agent.py              # agent definitions and main loop
├── memory/
│   ├── memory_hooks.py       # RunHooks for automatic memory retrieval
│   └── vector_graph_store.py # mem0 config (Qdrant + Neo4j)
├── prompts/
│   └── v_1_0.py              # system prompts for all agents
├── tools/
│   └── tools.py              # PubMed search, memory tools, review gate
├── .env                      # secrets (not committed)
├── requirements.txt
└── README.md
```
