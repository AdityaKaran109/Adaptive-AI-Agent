"""Chat and embeddings against the local Ollama server.

Reads OLLAMA_HOST, OLLAMA_MODEL and OLLAMA_EMBED_MODEL from the environment. Every
model call in the project goes through here, so swapping models is a one-line change.
Both calls stay on 127.0.0.1. Never use a model tag ending in ":cloud".
"""

from __future__ import annotations

import os
from typing import TypeVar

from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)


def _host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def chat(model: str | None = None, *, think: bool = False, **kwargs) -> ChatOllama:
    """A chat model. Thinking is off by default; it only slows these short calls down."""
    return ChatOllama(
        model=model or os.environ["OLLAMA_MODEL"],
        base_url=_host(),
        reasoning=think,
        temperature=kwargs.pop("temperature", 0.0),
        **kwargs,
    )


def structured(schema: type[T], model: str | None = None, **kwargs):
    """A chat model constrained to `schema`, so a bad shape fails loudly instead of silently."""
    return chat(model, **kwargs).with_structured_output(schema)


def embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=os.environ["OLLAMA_EMBED_MODEL"], base_url=_host())


def embed(texts: list[str]) -> list[list[float]]:
    return embeddings().embed_documents(texts)
