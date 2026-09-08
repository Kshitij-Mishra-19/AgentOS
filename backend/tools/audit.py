from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditLog:
    timestamp: str
    agent_id: str
    tool_name: str
    success: bool
    duration_ms: float
    error_type: str | None = None


class AuditLogger:

    def __init__(self):
        self._logs: list[AuditLog] = []

    def log(
        self,
        agent_id: str,
        tool_name: str,
        success: bool,
        duration_ms: float,
        error_type: str | None = None,
    ) -> None:

        entry = AuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
            tool_name=tool_name,
            success=success,
            duration_ms=duration_ms,
            error_type=error_type,
        )

        self._logs.append(entry)

    def get_logs(self) -> list[dict[str, Any]]:
        return [
            asdict(log)
            for log in self._logs
        ]