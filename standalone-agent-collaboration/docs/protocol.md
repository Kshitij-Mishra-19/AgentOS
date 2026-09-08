# Message Protocol

All inter-agent communication uses a single message envelope,
`AgentMessage` (`schemas/message.py`), validated by rules in
`core/protocol.py` before it is routed by `core/message_bus.py`.

## Message fields

| Field | Type | Description |
|---|---|---|
| `message_id` | `str` (UUID) | Unique identifier for this message |
| `task_id` | `str` | The task this message belongs to |
| `sender` | `str` | Agent id (or `"orchestrator"`) that sent the message |
| `recipient` | `str` | Agent id the message is addressed to |
| `message_type` | `MessageType` | One of the enum values below |
| `timestamp` | `str` (ISO 8601, UTC) | When the message was created |
| `payload` | `dict` (JSON-compatible) | The message body |
| `correlation_id` | `str` (UUID) | Shared across a request/reply pair (and revision chains) |
| `metadata` | `dict` (JSON-compatible) | Optional extra context |

Messages are fully JSON-serializable: `AgentMessage.to_json()` /
`AgentMessage.from_json()` round-trip losslessly, and `payload`/
`metadata` must only ever contain JSON-compatible values (str, int,
float, bool, None, list, dict).

## Message types

| Type | Sent by | Sent to | Meaning |
|---|---|---|---|
| `TASK_CREATED` | orchestrator | planner | A new user task needs a plan |
| `PLAN_CREATED` | planner | orchestrator | The Planner's structured `Plan` |
| `TASK_ASSIGNED` | orchestrator | executor | A subtask to execute |
| `EXECUTION_STARTED` | executor | — | (informational; logged, not routed) |
| `EXECUTION_COMPLETED` | executor | orchestrator | Subtask succeeded |
| `EXECUTION_FAILED` | executor | orchestrator | Subtask failed explicitly |
| `REVIEW_REQUESTED` | orchestrator | reviewer | Ask for a review of aggregated results |
| `REVIEW_APPROVED` | reviewer | orchestrator | Result accepted |
| `REVIEW_REJECTED` | reviewer | orchestrator | Result rejected, with feedback |
| `REVISION_REQUESTED` | orchestrator | planner | Re-plan using Reviewer feedback |
| `TASK_COMPLETED` | — | — | Reserved for a fully finished task (see `core.protocol.is_terminal`) |
| `TASK_FAILED` | — | — | Reserved for a permanently failed task |
| `CLARIFICATION_REQUESTED` | executor | orchestrator | Executor needs more information |

## Validation rules (`core/protocol.py`)

A message is **invalid** (`InvalidMessageError`) if:
- Any of `sender`, `recipient`, `message_type`, `task_id` is empty.
- `message_type` isn't a recognized `MessageType`.

A message is **unroutable** (`UnknownAgentError`) if:
- `recipient` isn't in `core.protocol.KNOWN_RECIPIENTS`
  (`planner`, `executor`, `reviewer`, `orchestrator` by default —
  extend with `register_recipient()` when adding a new agent).

`MessageBus.publish()` calls `validate_message()` before doing
anything else, so invalid messages never reach a handler.

## Routing

`MessageBus.subscribe(recipient, handler)` registers a coroutine
handler for a recipient name. `MessageBus.publish(message)`:

1. Validates the message.
2. Appends it to `bus.history` (useful for tests and debugging).
3. Looks up subscribers for `message.recipient`. If none exist, it
   raises `InvalidMessageError` — there is no silent drop.
4. Awaits each handler and collects any reply messages they return.
5. If a handler raises, the failure is recorded in `bus.failures` and
   re-raised (never swallowed).

Correlation IDs are preserved across a request/reply pair via
`AgentMessage.reply(...)`, which copies `correlation_id` from the
original message. This lets you trace an entire plan → execute →
review → revise chain by following `correlation_id`/`task_id` through
the logs.
