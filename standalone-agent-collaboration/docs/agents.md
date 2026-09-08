# Agents

This system defines exactly three agent roles. Each lives under
`agents/<role>/` with the same internal shape:

```
agents/<role>/
├── __init__.py
├── agent.py       # the concrete BaseAgent subclass
├── prompts.py      # system prompt + prompt-building helpers
└── config.yaml     # default configuration for this agent
```

All three subclass `core.agent.BaseAgent` and implement a single
method:

```python
async def handle(message: AgentMessage) -> AgentMessage:
    ...
```

## Planner (`agents/planner/`)

**Responsibilities**
- Receives the high-level task (`TASK_CREATED`) or revision feedback
  (`REVISION_REQUESTED`).
- Breaks the task into subtasks with explicit dependencies.
- Produces a structured `Plan` (see `schemas/plan.py`).
- Never executes anything itself.
- Re-plans when given Reviewer feedback, incorporating it into
  `revision_notes`.

**Reply:** `PLAN_CREATED`, carrying the `Plan` in `payload["plan"]`.

## Executor (`agents/executor/`)

**Responsibilities**
- Executes one assigned subtask (`TASK_ASSIGNED`).
- Produces a structured `ExecutionResult` (see `schemas/result.py`).
- Reports errors explicitly via `status=FAILED` and a populated
  `errors` list — it never claims success it didn't achieve.
- Can request clarification (`status=NEEDS_CLARIFICATION`) instead of
  guessing when a subtask is ambiguous.

**Reply:** `EXECUTION_COMPLETED`, `EXECUTION_FAILED`, or
`CLARIFICATION_REQUESTED`, carrying the `ExecutionResult` in
`payload["result"]`.

## Reviewer (`agents/reviewer/`)

**Responsibilities**
- Reviews an (aggregated) `ExecutionResult` against the *original*
  task description (`REVIEW_REQUESTED`), not just the Executor's own
  summary.
- Produces a structured `Review` (see `schemas/review.py`) with a
  decision, score, per-criterion pass/fail, issues, and actionable
  `required_changes`.
- Never leaves a decision ambiguous: `decision` is exactly `APPROVED`
  or `REJECTED`.
- As a safety net, the agent itself (not just the LLM) enforces that
  any executor-reported error forces rejection when
  `review.reject_on_any_error` is enabled in its config — the
  underlying LLM's own judgment can't override that policy.

**Reply:** `REVIEW_APPROVED` or `REVIEW_REJECTED`, carrying the
`Review` in `payload["review"]`.

## Adding another agent

1. Create `agents/<new_role>/` with `__init__.py`, `agent.py`,
   `prompts.py`, `config.yaml` following the existing agents as a
   template.
2. Subclass `core.agent.BaseAgent`, set `role = "<new_role>"`, and
   implement `handle`.
3. Register the new role as a valid message recipient:
   `core.protocol.register_recipient("<new_role>")`.
4. Subscribe an instance to the bus:
   `bus.subscribe("<new_role>", agent.handle)` (see `app/bootstrap.py`
   for where the existing three agents are wired up).
5. Decide where the new agent fits in the workflow and update
   `core/orchestrator.py` to send it messages at the right point, or
   have an existing agent address it directly through the bus.
6. Add tests for the new agent in isolation (see `tests/test_agents.py`
   for the pattern: construct a message, call `handle`, assert on the
   reply's `message_type` and payload).
