# Aegis AI OS — Memory Module

The Memory Module provides persistent, semantic, and short-term memory
capabilities for Aegis AI agents.

Other modules should interact with memory through `MemoryManager` or the
Memory API. They should not directly access PostgreSQL, ChromaDB, or Redis.

---

## Architecture

```text
                    Aegis Agents
                         |
                         v
                  Memory API / Manager
                         |
              +----------+----------+
              |          |          |
              v          v          v
         PostgreSQL   ChromaDB     Redis
         Long-term    Semantic     Working
         storage      retrieval    memory