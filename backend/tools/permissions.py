from dataclasses import dataclass
from typing import Any

from .storage import JSONStorage


@dataclass(frozen=True)
class Permission:
    agent_id: str
    tool_name: str
    action: str
    allowed: bool = True


@dataclass(frozen=True)
class RolePermission:
    role: str
    tool_name: str
    action: str


class PermissionManager:

    def __init__(self, storage: JSONStorage | None = None):
        self.storage = storage

        self._permissions: dict[
            tuple[str, str, str],
            Permission
        ] = {}

        self._role_permissions: dict[
            tuple[str, str, str],
            RolePermission
        ] = {}

        self._roles: set[str] = set()

        self._agent_roles: dict[
            str,
            set[str]
        ] = {}

        self._load()

    # ---------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------

    def _load(self) -> None:

        if self.storage is None:
            return

        data = self.storage.load()

        # Direct permissions
        for item in data.get("permissions", []):
            permission = Permission(
                agent_id=item["agent_id"],
                tool_name=item["tool_name"],
                action=item["action"],
                allowed=item.get("allowed", True),
            )

            key = (
                permission.agent_id,
                permission.tool_name,
                permission.action,
            )

            self._permissions[key] = permission

        # Roles
        self._roles = set(
            data.get("roles", [])
        )

        # Agent roles
        for agent_id, roles in data.get(
            "agent_roles",
            {}
        ).items():

            self._agent_roles[agent_id] = set(roles)

        # Role permissions
        for item in data.get(
            "role_permissions",
            []
        ):

            permission = RolePermission(
                role=item["role"],
                tool_name=item["tool_name"],
                action=item["action"],
            )

            key = (
                permission.role,
                permission.tool_name,
                permission.action,
            )

            self._role_permissions[key] = permission

    def _save(self) -> None:

        if self.storage is None:
            return

        data = {
            "permissions": [
                {
                    "agent_id": permission.agent_id,
                    "tool_name": permission.tool_name,
                    "action": permission.action,
                    "allowed": permission.allowed,
                }
                for permission in self._permissions.values()
            ],

            "roles": sorted(
                self._roles
            ),

            "agent_roles": {
                agent_id: sorted(roles)
                for agent_id, roles
                in self._agent_roles.items()
            },

            "role_permissions": [
                {
                    "role": permission.role,
                    "tool_name": permission.tool_name,
                    "action": permission.action,
                }
                for permission
                in self._role_permissions.values()
            ],
        }

        self.storage.save(data)

    # ---------------------------------------------------------
    # Direct Permissions
    # ---------------------------------------------------------

    def grant(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
    ) -> None:

        if not agent_id or not agent_id.strip():
            raise ValueError(
                "Agent ID cannot be empty."
            )

        if not tool_name or not tool_name.strip():
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not action or not action.strip():
            raise ValueError(
                "Action cannot be empty."
            )

        key = (
            agent_id,
            tool_name,
            action,
        )

        self._permissions[key] = Permission(
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            allowed=True,
        )

        self._save()

    def revoke(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
    ) -> None:

        if not agent_id or not agent_id.strip():
            raise ValueError(
                "Agent ID cannot be empty."
            )

        if not tool_name or not tool_name.strip():
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not action or not action.strip():
            raise ValueError(
                "Action cannot be empty."
            )

        key = (
            agent_id,
            tool_name,
            action,
        )

        self._permissions[key] = Permission(
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            allowed=False,
        )

        self._save()

    # ---------------------------------------------------------
    # Roles
    # ---------------------------------------------------------

    def create_role(
        self,
        role: str,
    ) -> None:

        if not role or not role.strip():
            raise ValueError(
                "Role name cannot be empty."
            )

        if role in self._roles:
            raise ValueError(
                f"Role already exists: {role}"
            )

        self._roles.add(role)

        self._save()

    def delete_role(
        self,
        role: str,
    ) -> None:

        if role not in self._roles:
            raise KeyError(
                f"Role not found: {role}"
            )

        self._roles.remove(role)

        # Delete role permissions
        keys_to_delete = [
            key
            for key in self._role_permissions
            if key[0] == role
        ]

        for key in keys_to_delete:
            del self._role_permissions[key]

        # Remove role from agents
        for roles in self._agent_roles.values():
            roles.discard(role)

        self._save()

    def role_exists(
        self,
        role: str,
    ) -> bool:

        return role in self._roles

    # ---------------------------------------------------------
    # Agent Roles
    # ---------------------------------------------------------

    def assign_role(
        self,
        agent_id: str,
        role: str,
    ) -> None:

        if not agent_id or not agent_id.strip():
            raise ValueError(
                "Agent ID cannot be empty."
            )

        if role not in self._roles:
            raise KeyError(
                f"Role not found: {role}"
            )

        self._agent_roles.setdefault(
            agent_id,
            set(),
        )

        self._agent_roles[agent_id].add(
            role
        )

        self._save()

    def remove_role(
        self,
        agent_id: str,
        role: str,
    ) -> None:

        roles = self._agent_roles.get(
            agent_id
        )

        if roles is None:
            return

        roles.discard(role)

        self._save()

    # ---------------------------------------------------------
    # Role Permissions
    # ---------------------------------------------------------

    def grant_role_permission(
        self,
        role: str,
        tool_name: str,
        action: str,
    ) -> None:

        if role not in self._roles:
            raise KeyError(
                f"Role not found: {role}"
            )

        if not tool_name or not tool_name.strip():
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not action or not action.strip():
            raise ValueError(
                "Action cannot be empty."
            )

        key = (
            role,
            tool_name,
            action,
        )

        self._role_permissions[key] = RolePermission(
            role=role,
            tool_name=tool_name,
            action=action,
        )

        self._save()

    def revoke_role_permission(
        self,
        role: str,
        tool_name: str,
        action: str,
    ) -> None:

        key = (
            role,
            tool_name,
            action,
        )

        self._role_permissions.pop(
            key,
            None,
        )

        self._save()

    # ---------------------------------------------------------
    # Permission Check
    # ---------------------------------------------------------

    def check(
        self,
        agent_id: str,
        tool_name: str,
        action: str,
    ) -> bool:

        # Direct permission has highest priority.
        key = (
            agent_id,
            tool_name,
            action,
        )

        direct_permission = self._permissions.get(
            key
        )

        if direct_permission is not None:
            return direct_permission.allowed

        # Check roles.
        roles = self._agent_roles.get(
            agent_id,
            set(),
        )

        for role in roles:

            role_key = (
                role,
                tool_name,
                action,
            )

            if role_key in self._role_permissions:
                return True

        return False

    # ---------------------------------------------------------
    # Listing
    # ---------------------------------------------------------

    def list_permissions(
        self,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:

        results = []

        for permission in self._permissions.values():

            if (
                agent_id is not None
                and permission.agent_id != agent_id
            ):
                continue

            results.append(
                {
                    "type": "direct",
                    "agent_id": permission.agent_id,
                    "tool_name": permission.tool_name,
                    "action": permission.action,
                    "allowed": permission.allowed,
                }
            )

        return results

    def list_roles(self) -> list[str]:

        return sorted(
            self._roles
        )

    def list_agent_roles(
        self,
        agent_id: str,
    ) -> list[str]:

        return sorted(
            self._agent_roles.get(
                agent_id,
                set(),
            )
        )