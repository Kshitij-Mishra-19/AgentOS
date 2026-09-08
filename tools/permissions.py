from dataclasses import dataclass


@dataclass(frozen=True)
class Permission:
    agent_id: str
    tool_name: str
    action: str
    allowed: bool = True


class PermissionManager:

    def __init__(self):
        self._permissions: dict[
            tuple[str, str, str],
            Permission
        ] = {}

    def grant(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
    ) -> None:

        key = (agent_id, tool_name, action)

        self._permissions[key] = Permission(
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            allowed=True,
        )

    def revoke(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
    ) -> None:

        key = (agent_id, tool_name, action)

        self._permissions[key] = Permission(
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            allowed=False,
        )

    def check(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
    ) -> bool:

        key = (agent_id, tool_name, action)

        permission = self._permissions.get(key)

        if permission is None:
            return False

        return permission.allowed