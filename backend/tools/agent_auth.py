import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCredential:
    agent_id: str
    api_key: str
    active: bool = True


class AgentAuthManager:

    def __init__(self):
        self._credentials: dict[str, AgentCredential] = {}

    def register_agent(
        self,
        agent_id: str,
        api_key: str,
    ) -> None:

        if not agent_id or not agent_id.strip():
            raise ValueError(
                "Agent ID cannot be empty."
            )

        if not api_key or not api_key.strip():
            raise ValueError(
                "Agent API key cannot be empty."
            )

        if agent_id in self._credentials:
            raise ValueError(
                f"Agent already registered: {agent_id}"
            )

        self._credentials[agent_id] = AgentCredential(
            agent_id=agent_id,
            api_key=api_key,
            active=True,
        )

    def generate_agent_key(
        self,
        agent_id: str,
    ) -> str:

        if not agent_id or not agent_id.strip():
            raise ValueError(
                "Agent ID cannot be empty."
            )

        if agent_id in self._credentials:
            raise ValueError(
                f"Agent already registered: {agent_id}"
            )

        api_key = secrets.token_urlsafe(32)

        self._credentials[agent_id] = AgentCredential(
            agent_id=agent_id,
            api_key=api_key,
            active=True,
        )

        return api_key

    def authenticate(
        self,
        agent_id: str,
        api_key: str,
    ) -> bool:

        credential = self._credentials.get(
            agent_id
        )

        if credential is None:
            return False

        if not credential.active:
            return False

        return secrets.compare_digest(
            credential.api_key,
            api_key,
        )

    def deactivate(
        self,
        agent_id: str,
    ) -> None:

        credential = self._credentials.get(
            agent_id
        )

        if credential is None:
            raise KeyError(
                f"Agent not found: {agent_id}"
            )

        self._credentials[agent_id] = AgentCredential(
            agent_id=credential.agent_id,
            api_key=credential.api_key,
            active=False,
        )

    def activate(
        self,
        agent_id: str,
    ) -> None:

        credential = self._credentials.get(
            agent_id
        )

        if credential is None:
            raise KeyError(
                f"Agent not found: {agent_id}"
            )

        self._credentials[agent_id] = AgentCredential(
            agent_id=credential.agent_id,
            api_key=credential.api_key,
            active=True,
        )

    def exists(
        self,
        agent_id: str,
    ) -> bool:

        return agent_id in self._credentials