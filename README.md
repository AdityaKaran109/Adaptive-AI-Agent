# Behavior adaptation: trajectory to skill

Local version of the [DeepLearning.AI lesson](https://learn.deeplearning.ai/courses/building-adaptive-ai-agents/lesson/9i82mn/behavior-adaptation%3A-trajectory-to-skill-learning).

The course stores traces in Oracle Agent Memory and calls a hosted model. This project does not. Chat and embeddings go to Ollama at `127.0.0.1:11434`. Traces, skills, and proposals stay in `data/` on disk. `LANGCHAIN_TRACING_V2=false` keeps LangChain from uploading runs.

Models already on this Mac:

- `nemotron-3-nano:latest` is set as the chat model. It is about 24 GB, and this MacBook Pro has 24 GB of memory, so it may fail to load or swap heavily.
- `ministral-3:latest` (about 6 GB) is the local chat model that fits.
- `nomic-embed-text:latest` is the local embedding model.
- `kimi-k2-thinking:cloud` runs off this machine. Do not set it as `OLLAMA_MODEL`.

You write the code. Each file below is only a placeholder for the piece you implement.

## The loop

1. Seed five skills and synthetic traces.
2. Run the agent on “run the project test suite.” It loads `run-the-tests` v1 and fails.
3. The induction engine reads traces for one topic and proposes a new skill version, with evidence.
4. You approve or reject that proposal. A rejection includes a reason the engine can use next time.
5. An approval promotes the new version to active.
6. Run the same task again. The agent loads v2 and the suite passes.

## Layout

```
src/llm/          Ollama chat client
src/memory/       local store for traces and skills
src/traces/       episode shape: turns, tool calls, skill uses,
                  workflow steps, preferences, errors and fixes
src/skills/       skill box: name, topic, procedure, version, status
src/induction/    contract, engine, human review
src/agent/        LangGraph run: retrieve skill, call tools, write a trace
data/skills/      the five starter skills (v1)
data/traces/      synthetic episodes you load
data/proposals/   enhanced skills waiting for review
sandbox/          small project whose tests the agent runs
notebooks/        course notebook, if you download it
```

Starter skills, matching the lesson:

- `brainstorming`
- `requesting-code-review`
- `run-the-tests` (this is the one the lesson enhances)
- `systematic-debugging`
- `writing-plans`

## Suggested order

1. `src/llm/client.py` — talk to Ollama using `OLLAMA_HOST` and `OLLAMA_MODEL` from `.env`.
2. `src/memory/store.py` and `src/traces/models.py` — save and load episodes.
3. Fill `data/skills/*/SKILL.md` and `data/traces/` from the lesson, then load them.
4. `src/skills/box.py` — return the active skill for a topic.
5. `src/agent/` — run the sandbox tests with v1 and record the failure.
6. `src/induction/contract.py` then `engine.py` — one topic in, steps / tools / errors / fixes / provenance out.
7. `src/induction/review.py` — approve, or reject with a reason.
8. Run the agent again and confirm it follows the promoted skill.
