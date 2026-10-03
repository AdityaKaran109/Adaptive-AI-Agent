"""End-to-end check that Oracle Agent Memory runs against local Ollama models.

This is the one assumption the build plan rests on: Oracle documents only cloud models
as compatible, but the model layer goes through litellm, so an "ollama/" prefix plus
api_base keeps every call on 127.0.0.1. Verify it before building on it.

    .venv\\Scripts\\python.exe scripts\\smoke_agent_memory.py
"""

from __future__ import annotations

import os
import sys

import oracledb
from dotenv import load_dotenv
from oracleagentmemory.apis.searchscope import SearchScope
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm
from oracleagentmemory.core.oracleagentmemory import OracleAgentMemory, SchemaPolicy

load_dotenv()

host = os.environ["OLLAMA_HOST"]
pool = oracledb.create_pool(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=os.environ["ORACLE_DSN"],
    min=1,
    max=4,
)

memory = OracleAgentMemory(
    connection=pool,
    embedder=Embedder(
        model=f"ollama/{os.environ['OLLAMA_EMBED_MODEL'].removesuffix(':latest')}",
        api_base=host,
        embedding_dimension=768,
    ),
    llm=Llm(model=f"ollama/{os.environ['OLLAMA_MODEL']}", api_base=host),
    schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
)
print("[ ok ] memory store initialised (schema created if absent)")

thread = memory.create_thread(user_id="smoke-test")
print(f"[ ok ] thread created: {thread.thread_id}")

# The trace-shaped content Phase 1 will actually store.
thread.add_messages(
    [
        {"role": "user", "content": "Run the tests in sandbox/."},
        {
            "role": "assistant",
            "content": "pytest failed with ModuleNotFoundError: no module named src.",
        },
        {"role": "user", "content": "You need PYTHONPATH=src before running pytest here."},
        {"role": "assistant", "content": "Set PYTHONPATH=src and the suite passed."},
    ]
)
print("[ ok ] messages stored")

# Extraction is queued on a background worker, so searching straight away can race it.
thread.wait_for_memory_extraction()
print("[ ok ] memory extraction finished (this is the local LLM doing the distilling)")

thread.add_memory("Tests in this repo need PYTHONPATH=src before pytest.")
print("[ ok ] explicit memory written")

results = memory.search(query="why do the tests fail", scope=SearchScope(user_id="smoke-test"))
print(f"[ ok ] hybrid search returned {len(results)} result(s)")
for r in results[:5]:
    content = (r.content or "").replace("\n", " ")
    print(f"       [{r.record.record_type}] {content[:100]}")

if not results:
    print("\nsearch returned nothing - investigate before building on this")
    sys.exit(1)
print("\nagent memory works on local models")
