import os

from dotenv import find_dotenv, load_dotenv
from mem0 import Memory
from openai import OpenAI

load_dotenv(find_dotenv())

client = OpenAI()
# Pre-load lazy OpenAI resources before any threads start.
# I hit deadlock because they weren't loaded before the first threads started executing
_ = client.embeddings
_ = client.chat

# i reused this config from a different project and I didn't look at any potential
# improvements yet. So there could be better alternatives

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

config = {
    "version": "v1.1",
    "embedder": {
        "provider": "openai",
        "config": {
            "api_key": OPENAI_API_KEY,
            "model": "text-embedding-3-small",
        },
    },
    "llm": {
        "provider": "openai",
        "config": {"api_key": OPENAI_API_KEY, "model": "gpt-4.1"},
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": QDRANT_ENDPOINT,
            "api_key": QDRANT_API_KEY,
            "collection_name": "patient_memory",
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": NEO4J_URI,
            "username": NEO4J_USERNAME,
            "password": NEO4J_PASSWORD,
            "database": NEO4J_DATABASE,
        },
    },
}


memory_client = Memory.from_config(config)
