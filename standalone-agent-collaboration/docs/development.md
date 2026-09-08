# Development

## Prerequisites

- Python 3.11+
- No external services or API keys required for local development —
  the default LLM provider (`MockLLMProvider`) runs entirely offline.

## Setup

```bash
git clone <this-repository>
cd standalone-agent-collaboration
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optionally copy `.env.example` to `.env` if/when you plug in a real
LLM provider (see below). The default configuration doesn't read `.env`
at all.

## Running the example

```bash
python examples/basic_task.py
python examples/sample_workflow.py   # demonstrates a reject -> revise -> approve cycle
```

## Running the CLI

```bash
python -m app "Create a project plan for launching a website"

# machine-readable output, non-zero exit code on failure:
python -m app "Create a project plan for launching a website" --json
```

## Running tests

```bash
pytest
pytest -v                          # verbose
pytest tests/test_orchestrator.py  # a single file
```

Tests run fully offline (no network access, no API keys) and complete
in well under a second.

## Project layout

See `README.md` for the full repository structure and `docs/architecture.md`
for how the pieces fit together.

## Replacing the mock LLM provider

The system is built against the `LLMProvider` interface
(`core/llm_provider.py`), not a specific vendor SDK:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, *, system: str, prompt: str, context: dict | None = None) -> LLMResponse:
        ...
```

To use a real provider:

1. Subclass `RealLLMProvider` (or `LLMProvider` directly) and implement
   `complete` to call your vendor's SDK/HTTP API. Read the API key from
   an environment variable (see `.env.example`) — never hard-code it.
2. Update `build_llm_provider()` in `app/bootstrap.py` to construct
   your subclass when `config/collaboration.yaml` sets `llm.provider`
   to something other than `mock`.
3. No agent code needs to change: agents only ever call
   `self.llm_provider.complete(...)`.

Because each agent's prompt (`agents/<role>/prompts.py`) asks for a
single JSON object matching that agent's schema, any provider you plug
in must be instructed to respond the same way — see the `_system_prompt`
constants for the exact contract each agent expects.

## Extending the state backend

`core/state_manager.py` defines a small `StateBackend` interface:

```python
class StateBackend(ABC):
    def get(self, task_id: str) -> WorkflowState | None: ...
    def put(self, state: WorkflowState) -> None: ...
    def delete(self, task_id: str) -> None: ...
    def all_task_ids(self) -> list[str]: ...
```

`InMemoryStateBackend` is the only implementation shipped here. To add
persistence (SQLite, Postgres, Redis, ...):

1. Implement `StateBackend` against your storage of choice, storing
   `WorkflowState` however makes sense (e.g. serialize the dataclass
   fields to JSON columns).
2. Pass an instance of your backend to `StateManager(backend=...)`.
3. No agent or orchestrator code needs to change — they only use
   `StateManager`'s methods, never the backend directly.

## Code style

- Type hints throughout; dataclasses for all schemas.
- `async`/`await` for every agent and bus operation.
- Errors are explicit subclasses of `core.errors.CollaborationError` —
  avoid raising or catching bare `Exception` except at the orchestrator
  boundary, where it's deliberately translated into a structured
  `WorkflowResult` rather than swallowed.
- Logging goes through `core.logging.get_logger` / `log_context`, and
  is written to **stderr** so `python -m app ... --json` can be piped
  without log lines mixed into the JSON output.

## Git workflow

- `.gitignore` excludes `.env`, virtual environments, caches, and IDE
  files — never commit secrets or local artifacts.
- Before pushing, review `git status` and `git diff` for anything
  unexpected (stray credentials, unrelated files).
- This repository has no dependency on any other private repository or
  project; it's designed to be cloned and run standalone.
