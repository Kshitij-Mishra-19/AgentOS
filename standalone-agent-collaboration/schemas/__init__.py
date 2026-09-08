"""Typed data contracts (schemas) shared across agents and core infrastructure.

Every workflow-critical piece of data — messages, tasks, plans, execution
results, reviews — is a dataclass with explicit fields and JSON
(de)serialization helpers, rather than a free-form string or dict. This
keeps agent boundaries strict: agents communicate only through these
schemas, never through shared Python objects or direct imports of each
other's internals.
"""
