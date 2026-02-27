import requests
from agents import function_tool
from memory.vector_graph_store import memory_client

# Separate namespaces so research findings and patient conversations
# are stored and retrieved seperately
PHD_NAMESPACE = "phd"
PATIENT_NAMESPACE = "patient"

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
)


@function_tool
# I used claude to write this function
def search_pubmed(query: str, max_results: int = 3) -> str:
    """Search PubMed for clinical papers relevant to a disease or condition.
    Returns titles, authors, journal, and year for the top results."""

    search_response = requests.get(
        PUBMED_SEARCH_URL,
        params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
        },
    )
    search_response.raise_for_status()
    ids = search_response.json().get("esearchresult", {}).get("idlist", [])

    if not ids:
        return "No PubMed results found for that query."

    summary_response = requests.get(
        PUBMED_SUMMARY_URL,
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
    )
    summary_response.raise_for_status()
    articles = summary_response.json().get("result", {})

    results = []
    for pmid in ids:
        article = articles.get(pmid, {})
        title = article.get("title", "No title")
        authors = ", ".join(
            a.get("name", "") for a in article.get("authors", [])[:3]
        )
        journal = article.get("fulljournalname", "")
        year = article.get("pubdate", "")[:4]
        results.append(
            f"PMID {pmid}: {title}\n  {authors} — {journal} ({year})"
        )

    return "\n\n".join(results)


@function_tool
def search_research_memory(query: str, patient_id: str) -> str:
    """Search past research findings previously saved about a patient's condition"""
    results = memory_client.search(
        query=query, user_id=f"{PHD_NAMESPACE}_{patient_id}"
    )
    memories = [m.get("memory") for m in results.get("results", [])]
    return "\n".join(memories) if memories else "No prior research found."


@function_tool
def search_patient_history(query: str, patient_id: str) -> str:
    """Search the patient's past conversations to understand what they've been told and what they've shared"""
    results = memory_client.search(
        query=query, user_id=f"{PATIENT_NAMESPACE}_{patient_id}"
    )
    memories = [m.get("memory") for m in results.get("results", [])]
    return (
        "\n".join(memories)
        if memories
        else "No patient conversation history found."
    )


@function_tool
def save_research_findings(patient_id: str, context: str, findings: str) -> str:
    """Save research findings about a patient's condition to memory"""
    memory_client.add(
        user_id=f"{PHD_NAMESPACE}_{patient_id}",
        messages=[
            {"role": "user", "content": context},
            {"role": "assistant", "content": findings},
        ],
    )
    return "Research findings saved."


@function_tool(needs_approval=True)
async def review_summary(summary: str, patient_id: str) -> str:
    """Pause for human review of the technical summary before it reaches the patient
    This uses interruption in the agent loop"""
    return f"Patient ID: {patient_id}, Patient Summary: '{summary}'"
