"""The Oracle Agent Memory store, configured to run on local Ollama models.

Oracle documents only cloud models as compatible, but the model layer goes through
litellm, so an "ollama/" prefix plus api_base keeps every call on 127.0.0.1.
"""

from __future__ import annotations

import os
from functools import lru_cache

import oracledb
from dotenv import load_dotenv
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm
from oracleagentmemory.core.oracleagentmemory import OracleAgentMemory, SchemaPolicy

load_dotenv()

EMBED_DIMENSION = 768


def _ollama(model: str) -> str:
    """litellm wants a provider prefix, and Ollama's ":latest" suffix is implicit."""
    return f"ollama/{model.removesuffix(':latest')}"


@lru_cache(maxsize=1)
def connect() -> OracleAgentMemory:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    pool = oracledb.create_pool(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
        min=1,
        max=4,
    )
    return OracleAgentMemory(
        connection=pool,
        embedder=Embedder(
            model=_ollama(os.environ["OLLAMA_EMBED_MODEL"]),
            api_base=host,
            embedding_dimension=EMBED_DIMENSION,
        ),
        llm=Llm(model=_ollama(os.environ["OLLAMA_MODEL"]), api_base=host),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
    )
